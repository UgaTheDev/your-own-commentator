"""Live replay: play a clip's source.mp4 as if it were live, and call only what the score graphic proves.

python pipeline/live.py <clip_id> [--port 8770] [--speed 1] [--start 0] [--duration 180] [--chunk 5]

Every `chunk` seconds of wall clock (chunk/speed with --speed) the next chunk of video is processed through the
scoreboard reader only: pixel-change detection on the score-bug crop, then a Nova read of the digits. Score-graphic
deltas are the only facts that count as verified live, so every other event type is excluded. Each scoring event
gets one rookie-en line through write.gate() (digit gate, play-word gate, judge), Polly audio uploaded to
s3://$YOC_BUCKET/published/<clip>/live/ (https://$YOC_CDN/<clip>/live/...), and a C4-style cue pushed to every
WebSocket client on ws://127.0.0.1:<port>:
    {"type": "cue", "t", "text", "audioUrl", "label": "live replay"}
A line that fails the gate is never spoken. Latency printed per cue = audio ready minus the moment the graphic
changed on the (simulated) live timeline.
"""
import argparse
import asyncio
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import common
import scoreboard
import voice
import write

CHUNK = 5.0
FPS = 2  # thumbnails per video second: change-detection resolution
SETTLE = 1.0  # read the digits 1 s after a change, once the graphic has finished animating (as extract_scores does)
TRACK = "rookie-en"
LABEL = "live replay"


def chunk_due(i, start_wall, chunk=CHUNK, speed=1.0):
    """Wall time at which chunk i (video [start + i*chunk, start + (i+1)*chunk)) has fully aired."""
    return start_wall + (i + 1) * chunk / speed


def aired_at(t, start_wall, start=0.0, speed=1.0):
    """Wall time at which video moment t was on screen."""
    return start_wall + (t - start) / speed


def chunk_thumbnails(video, crop, t0, dur, fps=FPS):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(dur), "-i", str(video), "-vf",
         f"fps={fps},crop={crop},scale={scoreboard.W}:{scoreboard.H},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    n = scoreboard.W * scoreboard.H
    return [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)]


class Reader:
    """Stateful score-graphic reader over consecutive chunks. thumbs(t0, dur) -> frames; read(t) -> {team: points}."""

    def __init__(self, thumbs, read, fps=FPS):
        self.thumbs, self.read, self.fps = thumbs, read, fps
        self.ref = self.score = None
        self.score_t, self.n = 0.0, 0
        self.pending = []  # [t_change, t_read]
        self.warnings = []

    def process(self, t0, t1):
        """Video [t0, t1) has aired. Returns [(event, t_change)] for score changes whose read frame has aired."""
        frames = self.thumbs(t0, t1 - t0)
        if frames and self.ref is None:
            self.ref, self.score, self.score_t = frames[0], self.read(t0), t0  # baseline
            frames = frames[1:]
            t0 += 1 / self.fps
        for i in scoreboard.change_points([self.ref, *frames])[1:]:
            self.ref, tc = frames[i - 1], t0 + (i - 1) / self.fps
            # a change inside a pending read's settle window is the same animation; players passing behind the
            # graphic make changes every frame for seconds, so windows are never extended (that starved reads)
            if not self.pending or tc > self.pending[-1][1]:
                self.pending.append([tc, tc + SETTLE])
        out = []
        while self.pending and self.pending[0][1] < t1:  # ponytail: a read due in a later chunk waits for it
            tc, tr = self.pending.pop(0)
            s = self.read(tr)
            if s == self.score:
                continue
            if not scoreboard.plausible(self.score, s):
                self.warnings.append(f"{tr:.1f}s implausible read {s} after {self.score}, ignored")
                continue
            events, warn = scoreboard.score_events([(self.score_t, self.score), (tr, s)])
            self.warnings += warn
            self.score, self.score_t = s, tr
            for e in events:
                self.n += 1
                out.append(({"id": f"live{self.n}", **e, "state": dict(s)}, tc))
        return out


def live_facts(event, rules):
    """Score-graphic facts only: the event, the score the graphic shows, and our rule card. No jersey is ever known."""
    facts = {"event": {k: event.get(k) for k in ("id", "t", "type", "team", "jersey")},
             "state": {"score": dict(event["state"])}}
    if event["type"] in rules:
        facts["rule"] = rules[event["type"]]
    return facts


def cue(event, text, audio_url):
    return {"type": "cue", "t": event["t"], "text": text, "audioUrl": audio_url, "label": LABEL}


def upload(mp3, clip_id, name):
    key = f"{clip_id}/live/{name}"
    common.aws("s3").upload_file(str(mp3), os.environ["YOC_BUCKET"], f"published/{key}",
                                 ExtraArgs={"ContentType": "audio/mpeg"})
    return f"https://{os.environ.get('YOC_CDN', 'd2og06dnam3owj.cloudfront.net')}/{key}"


def narrate(clip_id, event, facts, persona):
    """(cue, None) or (None, rejection reason). Nothing ungated is ever voiced."""
    text, reason = write.gate(write.prompt_for(persona, facts, write.LAST_GAP), facts)
    if reason:
        return None, reason
    mp3 = voice.synth(write.make_line(TRACK, persona, event, text))
    name = f"{event['id']}-{hashlib.sha256(text.encode()).hexdigest()[:8]}.mp3"
    return cue(event, text, upload(mp3, clip_id, name)), None


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, round(p / 100 * (len(xs) - 1)))] if xs else None


async def run(clip_id, port, speed, start, duration, chunk):
    from websockets.asyncio.server import broadcast, serve

    d = common.clip_dir(clip_id)
    clip, video = common.load(d / "clip.json"), d / "source.mp4"
    bug = clip["scoreBug"]
    here = Path(__file__).parent
    rules, persona = common.load(here / "rules.json"), common.load(here / "personas.json")[TRACK]
    end = start + duration
    reader = Reader(lambda t0, dur: chunk_thumbnails(video, bug["crop"], t0, dur),
                    lambda t: scoreboard.read_score(video, t, bug["crop"], bug["labels"]))
    clients, latencies = set(), []

    async def handler(ws):
        clients.add(ws)
        try:
            async for _ in ws:  # drain playhead messages; live replay doesn't need them
                pass
        finally:
            clients.discard(ws)

    async with serve(handler, "127.0.0.1", port, max_size=4096):
        print(f"live replay of {clip_id} [{start:.0f}s, {end:.0f}s) at {speed}x on ws://127.0.0.1:{port}", flush=True)
        wall0, i = time.time(), 0
        while start + i * chunk < end:
            await asyncio.sleep(max(0.0, chunk_due(i, wall0, chunk, speed) - time.time()))
            t0 = start + i * chunk
            # ponytail: chunks run one after another; a slow narration delays the next chunk, which then catches up
            for event, tc in await asyncio.to_thread(reader.process, t0, min(t0 + chunk, end)):
                facts = live_facts(event, rules)
                msg, reason = await asyncio.to_thread(narrate, clip_id, event, facts, persona)
                lat = time.time() - aired_at(tc, wall0, start, speed)
                if msg is None:
                    print(f"  {event['t']:6.1f}s {event['type']} {event['team']}: NOT SPOKEN ({reason})", flush=True)
                    continue
                latencies.append(lat)
                broadcast(clients, json.dumps(msg))
                print(f"  {event['t']:6.1f}s {event['type']:8} {event['team']:5} {event['state']}  latency {lat:5.1f}s"
                      f"  {msg['text']!r}  -> {len(clients)} client(s)", flush=True)
            i += 1
        for w in reader.warnings:
            print(f"  warning: {w}", flush=True)
        if latencies:
            print(f"{len(latencies)} cues, latency p50 {pct(latencies, 50):.1f}s p95 {pct(latencies, 95):.1f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--speed", type=float, default=1.0, help="> 1 runs faster than real time (testing)")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--duration", type=float, default=float("inf"), help="clip seconds to replay")
    ap.add_argument("--chunk", type=float, default=CHUNK)
    ap.add_argument("--local", action="store_true", help="no S3 upload; audioUrl is a local file:// URL (not for a TV)")
    a = ap.parse_args()
    if a.local:
        upload = lambda mp3, clip_id, name: Path(mp3).resolve().as_uri()  # noqa: E731
    elif not os.environ.get("YOC_BUCKET"):
        sys.exit("set YOC_BUCKET (cue audio must be HTTPS for the TV), or pass --local")
    if a.duration == float("inf"):
        a.duration = voice.duration(common.clip_dir(a.clip_id) / "source.mp4") - a.start
    asyncio.run(run(a.clip_id, a.port, a.speed, a.start, a.duration, a.chunk))
