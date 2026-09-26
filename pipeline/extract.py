"""Propose basketball events from a clip with Amazon Nova.

Usage: python pipeline/extract.py <clip_id>
Reads data/<clip>/source.mp4, writes events.proposed.json (reviewed by hand before state.py uses it).
"""
import json
import re
import subprocess
import sys

import common
from state import EVENT_TYPES

CHUNK = 20.0
STEP = 15.0  # 5s overlap so an event on a chunk boundary is seen whole at least once
MAX_BYTES = 18 * 1024 * 1024  # 25 MB inline limit, minus ~33% base64 overhead
DEDUPE_WINDOW = 2.0

SYSTEM = ("You are the vision component of an accessibility app that narrates amateur and recreational basketball games "
          "for new fans, kids and non-English speakers. The footage is public domain or filmed by the app's users with the "
          "players' consent. Describing visible game events (shots, makes, misses, fouls, rebounds) is the intended, safe use.")

PROMPT = f"""You are watching a {CHUNK:.0f}-second clip of a basketball game.
List every event you can actually see, as a JSON array. Each item:
{{"t": seconds from the start of this clip (number), "type": one of {sorted(EVENT_TYPES)},
 "team": jersey color as seen, lowercase (e.g. "red"), or null,
 "jersey": jersey number as an integer, or null unless the number is clearly legible,
 "confidence": 0 to 1}}
Each event is one distinct play; real plays are usually several seconds apart. Never repeat an event.
List at most 8 events. Only output events you can see. Do not guess. If there are none, output [].
Output only the JSON array."""


MAX_PER_CHUNK = 12  # more than this in 20s means the model is looping, not seeing


def salvage(reply):
    """Parse the reply's JSON; if it was cut off mid-array, keep every complete {...} object."""
    try:
        return common.parse_json(reply)
    except (ValueError, json.JSONDecodeError):
        objs = [json.loads(m) for m in re.findall(r"\{[^{}]*\}", reply)]
        if not objs:
            raise
        return objs


def chunk_starts(duration):
    # ponytail: a trailing chunk shorter than the overlap is skipped; its content is already in the previous chunk
    starts, s = [], 0.0
    while s < duration and (s == 0 or s + (CHUNK - STEP) < duration):
        starts.append(s)
        s += STEP
    return starts


def validate(item):
    """Return a clean event dict or None."""
    if not isinstance(item, dict) or item.get("type") not in EVENT_TYPES:
        return None
    t, conf, team, jersey = item.get("t"), item.get("confidence", 0.5), item.get("team"), item.get("jersey")
    if isinstance(t, bool) or not isinstance(t, (int, float)) or t < 0:
        return None
    if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
        return None
    if team is not None and not (isinstance(team, str) and team.strip()):
        return None
    if jersey is not None and (isinstance(jersey, bool) or not isinstance(jersey, int)):
        return None
    return {"t": float(t), "type": item["type"], "team": team.strip().lower() if team else None,
            "jersey": jersey, "confidence": float(conf)}


def to_absolute(events, chunk_start):
    return [{**e, "t": round(chunk_start + e["t"], 2)} for e in events]


def dedupe(events):
    # ponytail: greedy by confidence, O(n^2); fine for a few hundred events per clip
    kept = []
    for e in sorted(events, key=lambda e: -e["confidence"]):
        if not any(k["type"] == e["type"] and abs(k["t"] - e["t"]) <= DEDUPE_WINDOW for k in kept):
            kept.append(e)
    kept.sort(key=lambda e: e["t"])
    return [{"id": f"e{i}", **e} for i, e in enumerate(kept, 1)]


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return float(out)


def make_chunks(src, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for s in chunk_starts(duration(src)):
        p = out_dir / f"chunk_{int(s):05d}.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(s), "-i", str(src), "-t", str(CHUNK),
                        "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                        "-an", "-movflags", "+faststart", str(p)], check=True)
        assert p.stat().st_size < MAX_BYTES, f"{p} is {p.stat().st_size} bytes, over the inline limit"
        paths.append((s, p))
    return paths


def main(clip_id):
    d = common.clip_dir(clip_id)
    events, dropped = [], 0
    for start, path in make_chunks(d / "source.mp4", d / "render" / "chunks"):
        video = {"video": {"format": "mp4", "source": {"bytes": path.read_bytes()}}}
        reply = common.converse("extract", PROMPT, system=SYSTEM, content=[video], max_tokens=1024, temperature=0)
        try:
            items = salvage(reply)
        except (ValueError, json.JSONDecodeError) as err:
            print(f"chunk {start:.0f}s: unparseable reply, skipped ({err})")
            continue
        if isinstance(items, dict):  # model sometimes wraps: {"events": [...]}
            items = items.get("events", [])
        items = items if isinstance(items, list) else []
        if len(items) > MAX_PER_CHUNK:
            print(f"chunk {start:.0f}s: {len(items)} events looks like a looping reply, skipped")
            continue
        clean = [v for v in map(validate, items) if v]
        dropped += len(items) - len(clean)
        events += to_absolute(clean, start)
    events = dedupe(events)
    common.save(d / "events.proposed.json", events)
    print(f"{len(events)} events -> {d / 'events.proposed.json'} ({dropped} invalid items dropped)")


if __name__ == "__main__":
    main(sys.argv[1])
