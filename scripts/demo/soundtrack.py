"""Rebuild the demo soundtrack from the app's `YOC: @<epoch_ms> <msg>` log (the VVD's audio can't be captured).

  soundtrack.py --log stream.log --start-ms <epoch> --duration 170 \
      --manifest https://d2og06dnam3owj.cloudfront.net/lake-region/manifest.json --out audio.wav

Each media action in app/src/screens/Player.tsx becomes a segment (record-time start/end, source URL, source
offset); each segment's audio is cut from the real MP4/MP3 and written in place into a silent 48 kHz stereo wav.
"""
import argparse
import array
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.common import CACHE  # noqa: E402

RATE = 48000
LINE = re.compile(r"YOC: @(\d+) (.*?)\s*$")
FINISH = re.compile(r"^(?:seeked|playing|switch timeout) (.+) t=([\d.]+) at=[\d.]+ after")
URL = re.compile(r"-> (\S+)$")


def parse(lines):
    """[(epoch_ms, msg)], sorted, with the stream's doubled lines removed."""
    seen = set()
    out = []
    for line in lines:
        m = LINE.search(line)
        if m and m.group(0) not in seen:
            seen.add(m.group(0))
            out.append((int(m.group(1)), m.group(2)))
    return sorted(out, key=lambda e: e[0])


def timeline(events, start_ms, tracks):
    """Segments {start, end, src, offset} in seconds of recording time. `tracks` maps track id -> src.

    Game audio: one segment per stretch of continuous playback. Clips (Why answers, recaps, talk answers,
    replays, highlights) are their own segments; the game is paused or swapped out while they play.
    """
    segs = []
    game = None  # open game segment while playing
    clip = None  # open clip segment
    track = None
    overlay = False
    pending = {}  # loadSrc label -> src, for replays and highlights waiting on their finish line

    def game_stop(now):
        nonlocal game
        if game:
            game["end"] = now
            segs.append(game)
            game = None

    def game_start(now, tid, t):
        nonlocal game, track
        game_stop(now)
        track = tid
        game = {"start": now, "src": tracks[tid], "offset": t, "kind": "game"}

    def clip_stop(now):
        nonlocal clip
        if clip:
            clip["end"] = now
            segs.append(clip)
            clip = None

    def clip_start(now, src):
        nonlocal clip
        clip_stop(now)
        clip = {"start": now, "src": src, "offset": 0.0, "kind": "clip"}

    for ms, msg in events:
        now = (ms - start_ms) / 1000
        url = URL.search(msg)
        fin = FINISH.match(msg)
        if msg.startswith("play "):
            game_start(now, msg.split()[1], 0.0)
        elif msg.startswith("switch to "):
            game_stop(now)  # silent until the new src has seeked (the finish line)
            track = msg.split()[2]
        elif fin:
            what, t = fin.group(1), float(fin.group(2))
            back = re.match(r"(?:replay|highlights) back (\S+)$", what)
            if back:
                clip_stop(now)
                game_start(now, back.group(1), t)
            elif what in pending:
                clip_start(now, pending.pop(what))
            elif what in tracks:
                game_start(now, what, t)
        elif msg.startswith(("replay ", "highlights at")) and url:
            game_stop(now)
            label = "highlights" if msg.startswith("highlights") else f"replay {msg.split()[1]}"
            pending[label] = url.group(1)
        elif re.match(r"highlights (ended|timeout) after", msg):
            clip_stop(now)
        elif m := re.match(r"(?:queued )?seek ([\d.]+)(?: applied)?$", msg):
            if game:  # a seek while paused is carried by the resume line
                game_start(now, track, float(m.group(1)))
        elif re.match(r"(why|recap|talk) audio playing after", msg):
            if clip:
                clip["start"] = now  # the clip really started here, not when it was requested
        elif re.match(r"why \S+ at t=|why answer |recap t=|talk .*-> |predict open", msg):
            overlay = True
            if not msg.startswith("predict"):  # predict leaves the game running
                game_stop(now)
            if url:
                clip_start(now, url.group(1))
        elif m := re.match(r"overlay closed .*resume t=([\d.]+)", msg):
            overlay = False
            clip_stop(now)
            if track:
                game_start(now, track, float(m.group(1)))
        elif msg == "back" and not overlay:  # left the Player
            game_stop(now)
            clip_stop(now)
            track = None
    end = (events[-1][0] - start_ms) / 1000 + 3600 if events else 0  # open segments run to the end
    game_stop(end)
    clip_stop(end)
    return sorted(segs, key=lambda s: (s["kind"] == "clip", s["start"]))  # clips written last win overlaps


def fetch(url):
    """Download once into data/.cache/demo/."""
    d = CACHE / "demo"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (hashlib.sha256(url.encode()).hexdigest()[:24] + Path(url).suffix)
    if not p.exists():
        if not url.startswith("https://"):
            raise ValueError(f"refusing non-https url {url}")
        tmp = p.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=60) as r, tmp.open("wb") as f:
            shutil.copyfileobj(r, f)  # track MP4s are ~370 MB
        tmp.rename(p)
    return p


def pcm(path, offset, dur):
    """Signed 16-bit interleaved stereo samples of `dur` s from `offset`."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{offset:.3f}", "-t", f"{dur:.3f}", "-i", str(path), "-vn",
         "-ac", "2", "-ar", str(RATE), "-f", "s16le", "-"], check=True, capture_output=True).stdout
    return array.array("h", raw)


def render(segs, duration, out):
    buf = array.array("h", bytes(int(duration * RATE) * 4))
    for s in segs:
        start, end, offset = s["start"], min(s["end"], duration), s["offset"]
        if start < 0:  # began before the recording
            offset, start = offset - start, 0.0
        if end <= start:
            continue
        a = pcm(fetch(s["src"]), offset, end - start)
        i = int(start * RATE) * 2
        a = a[: len(buf) - i]
        buf[i:i + len(a)] = a
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(buf.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--start-ms", type=int, required=True, help="epoch ms of the recording's first frame")
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with urllib.request.urlopen(a.manifest, timeout=30) as r:
        manifest = json.load(r)
    tracks = {t["id"]: t["src"] for t in manifest["tracks"]}
    segs = timeline(parse(Path(a.log).read_text(errors="replace").splitlines()), a.start_ms, tracks)
    for s in segs:
        print(f'{s["start"]:8.2f}-{min(s["end"], a.duration):8.2f} {s["kind"]:4} @{s["offset"]:7.2f} {s["src"]}')
    render(segs, a.duration, a.out)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
