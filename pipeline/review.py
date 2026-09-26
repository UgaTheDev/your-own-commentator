"""Local review page: accept/fix/add Nova's proposed events, producing events.reviewed.json.

Usage: python pipeline/review.py <clip_id> [--port 8765]
Binds to 127.0.0.1 only. Serves a fixed set of routes, never arbitrary paths.
"""
import argparse
import json
import os
import re
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import common
from state import EVENT_TYPES, compute

HTML = Path(__file__).with_name("review.html")
MAX_BODY = 1 << 20
RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


def validate(clip, events):
    if not isinstance(events, list):
        raise ValueError("body must be a list of events")
    teams = clip["teams"]
    for i, e in enumerate(events):
        if not isinstance(e, dict):
            raise ValueError(f"event {i}: not an object")
        if not isinstance(e.get("id"), str) or not e["id"]:
            raise ValueError(f"event {i}: id must be a non-empty string")
        if e.get("type") not in EVENT_TYPES:
            raise ValueError(f"event {e['id']}: unknown type {e.get('type')!r}")
        t = e.get("t")
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 <= t < float("inf"):
            raise ValueError(f"event {e['id']}: t must be a number >= 0")
        if e.get("team") is None and e["type"] != "timeout" or e.get("team") is not None and e["team"] not in teams:
            raise ValueError(f"event {e['id']}: team {e.get('team')!r} not in {teams}")
        j = e.get("jersey")
        if j is not None and (isinstance(j, bool) or not isinstance(j, int)):
            raise ValueError(f"event {e['id']}: jersey must be an integer or null")
    if len({e["id"] for e in events}) != len(events):
        raise ValueError("duplicate event ids")


def save_events(d, events):
    """Validate, compute state, save atomically. Returns a warning string (final score mismatch) or None."""
    clip = common.load(d / "clip.json")
    validate(clip, events)
    states = compute({**clip, "final_score": None}, events)
    score = states[-1]["score"] if states else clip["start_score"]
    tmp = d / "events.reviewed.json.tmp"
    common.save(tmp, sorted(events, key=lambda e: e["t"]))
    os.replace(tmp, d / "events.reviewed.json")
    final = clip.get("final_score")
    if final is not None and score != final:
        return f"computed final score {score} != clip final_score {final} (fine while review is in progress)"
    return None


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, clip_dir, **kw):
        self.d = clip_dir
        super().__init__(*args, **kw)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")
        elif path == "/clip":
            self._send(200, (self.d / "clip.json").read_bytes(), "application/json")
        elif path == "/events":
            for name in ("events.reviewed.json", "events.proposed.json"):
                if (self.d / name).exists():
                    return self._send(200, (self.d / name).read_bytes(), "application/json")
            self._send(200, b"[]", "application/json")
        elif path == "/video":
            self._video()
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if urlsplit(self.path).path != "/events":
            return self._send(404, b"not found", "text/plain")
        n = int(self.headers.get("Content-Length") or 0)
        if not 0 < n <= MAX_BODY:
            return self._json(413 if n else 400, {"error": "body must be 1 byte to 1 MB"})
        try:
            warning = save_events(self.d, json.loads(self.rfile.read(n)))
        except (ValueError, KeyError, TypeError) as e:  # JSONDecodeError is a ValueError
            return self._json(400, {"error": str(e)})
        self._json(200, {"ok": True, "warning": warning})

    def _video(self):
        f = self.d / "source.mp4"
        if not f.exists():
            return self._send(404, b"no source.mp4", "text/plain")
        size = f.stat().st_size
        start, end = 0, size - 1
        rng = self.headers.get("Range")
        if rng:
            m = RANGE.match(rng.strip())
            if not m or m.groups() == ("", ""):
                return self._send(416, b"", "text/plain", {"Content-Range": f"bytes */{size}"})
            a, b = m.groups()
            if a:
                start, end = int(a), min(int(b), size - 1) if b else size - 1
            else:
                start = max(size - int(b), 0)
            if start > end or start >= size:
                return self._send(416, b"", "text/plain", {"Content-Range": f"bytes */{size}"})
        length = end - start + 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with f.open("rb") as fh:
            fh.seek(start)
            while length > 0:
                chunk = fh.read(min(length, 1 << 16))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):  # browsers abort ranges while seeking
                    return
                length -= len(chunk)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _send(self, code, body, ctype, headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


def make_server(clip_id, port=8765):
    return ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, clip_dir=common.clip_dir(clip_id)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    server = make_server(args.clip_id, args.port)
    print(f"reviewing {args.clip_id} at http://127.0.0.1:{server.server_port}/")
    server.serve_forever()
