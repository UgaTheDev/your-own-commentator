"""QA the cut before anyone watches it. Exits non-zero on any issue.

  .venv/bin/python scripts/demo/qa.py   (after cut.py + assemble.py)

From the app logs and the published line timings it rebuilds when every voice is speaking (commentator lines on
the on-air track, Why/recap/talk answers, highlight-reel lines), then checks the EDL:
  1. no shot starts or ends inside someone's sentence,
  2. no narration over a voice,
  3. no shot shorter than 1.5 s,
and, on the rendered demo.mp4, 4. no second of screen footage with fewer than 15 new frames.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
CLIP = ROOT / "data" / "lake-region"
EV = re.compile(r"YOC: @(\d+) (.*)")
EPS = 0.08


def events(log):
    return [(int(m.group(1)) / 1000, m.group(2)) for m in map(EV.search, log.read_text(errors="replace").splitlines())
            if m]


def speech(evs):
    """[(start, end, who)] in epoch seconds, from one recording's log."""
    lines = {}
    for x in json.load(open(CLIP / "voiced.json")):
        lines.setdefault(x["trackId"], []).append((x["start"], x["start"] + x["duration"], x["text"]))
    reel = [(x["start"], x["start"] + x["duration"], x["text"]) for x in json.load(open(CLIP / "highlights.lines.json"))]
    out, track, mode, prev = [], None, "track", None
    opened = {}
    for t, msg in evs:
        if m := re.match(r"play (\S+)$", msg):
            track = m.group(1)
        elif m := re.match(r"seeked (?:replay back |highlights back )?(\S+) ", msg):
            track, mode = m.group(1), "track"
        elif msg.startswith(("switch to ", "replay e")):
            mode = "other"
        elif msg.startswith("playing highlights"):
            mode = "reel"
            out += [(t + a, t + b, f"reel: {txt}") for a, b, txt in reel]
        elif m := re.match(r"(why|recap|talk) audio playing", msg):
            opened[m.group(1)] = t
        elif m := re.match(r"overlay closed \((why|recap|talk)", msg):
            if m.group(1) in opened:
                out.append((opened.pop(m.group(1)), t, f"{m.group(1)} answer"))
        elif m := re.match(r"tick t=([\d.]+)", msg):
            g = float(m.group(1))
            if prev and mode == "track" and track and 0 < g - prev[1] < 1.6 and t - prev[0] < 2:
                (t1, g1), rate = prev, (t - prev[0]) / (g - prev[1])
                for a, b, txt in lines.get(track, []):
                    lo, hi = max(a, g1), min(b, g)
                    if lo < hi:
                        out.append((t1 + (lo - g1) * rate, t1 + (hi - g1) * rate, f"{track}: {txt}"))
            prev = (t, g)
            continue
        if not msg.startswith("tick"):
            prev = None if mode != "track" else prev
    merged = []  # consecutive tick pieces of one line -> one interval
    for a, b, who in sorted(out):
        if merged and merged[-1][2] == who and a - merged[-1][1] < 0.3:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]), who)
        else:
            merged.append((a, b, who))
    return merged


def still(evs):
    """[(start, end)] epochs where the picture is meant to hold still: Home before playback, the paused Why/recap/
    talk panels, and the reel's title card. Frame-drop checks skip these."""
    out, opened = [], None
    play = next((t for t, m in evs if re.match(r"play \S+$", m)), None)
    if play:
        out.append((0.0, play + 1.0))
    for t, msg in evs:
        if re.match(r"(why e\d+ |recap t=|talk answer )", msg) and opened is None:
            opened = t
        elif msg.startswith("overlay closed") and opened is not None:
            out.append((opened, t + 0.5))
            opened = None
        elif msg.startswith("playing highlights"):
            out.append((t - 1.0, t + 4.0))
    return out


def stalls(evs):
    """[(start, end)] epochs where playback froze: the game clock barely moved while the game was meant to play."""
    out, prev, mode, paused = [], None, "track", False
    for t, msg in evs:
        if msg.startswith(("switch to ", "replay e", "highlights at")):
            mode, prev = "other", None
        elif msg.startswith("seeked "):
            mode, prev = "track", None
        elif re.match(r"(why e\d+ |recap t=|talk answer )", msg):
            paused, prev = True, None
        elif msg.startswith("overlay closed"):
            paused, prev = False, None
        elif msg.startswith("seek "):
            prev = None
        elif m := re.match(r"tick t=([\d.]+)", msg):
            g = float(m.group(1))
            if prev and mode == "track" and not paused and 0.5 < t - prev[0] < 5 and g - prev[1] < 0.5 * (t - prev[0]):
                out.append((prev[0], t))
            prev = (t, g)
    return out


def main():
    edl = json.load(open(D / "edl.json"))
    bases = edl["_bases"]
    logs = {f: ROOT / "scripts/demo/out" / ("hook.log" if "hook" in f else "take.log") for f in bases}
    talk = {f: speech(events(logs[f])) for f in bases}
    calm = {f: still(events(logs[f])) for f in bases}
    froze = {f: stalls(events(logs[f])) for f in bases}
    quiet = []  # output-time intervals that are still on purpose
    durs = json.load(open(ROOT / edl["vo_dir"] / "durations.json"))
    issues, voices, T, shots = [], [], 0.0, []

    def at(x):
        return f"{int(x // 60)}:{x % 60:04.1f}"

    for seg in edl["segments"]:
        a, b = seg["in"], seg["out"]
        if b - a < 1.5:
            issues.append(f"{at(T)} shot only {b - a:.1f}s ({seg['file']})")
        for line_id, off in seg.get("vo", []):
            voices.append((T + off, T + off + durs[line_id], f"narration '{line_id}'"))
        if seg["type"] == "screen":
            shots.append((T, T + b - a))
            base = bases[seg["file"]]
            for s, e in froze[seg["file"]]:
                if s - base < b and e - base > a:
                    issues.append(f"{at(T + max(s - base, a) - a)} playback froze for {e - s:.1f}s (picture and sound)")
            quiet += [(T + max(s - base, a) - a, T + min(e - base, b) - a) for s, e in calm[seg["file"]]
                      if s - base < b and e - base > a]
            for s, e, who in talk[seg["file"]]:
                fs, fe = s - base, e - base
                if fs < a - EPS < fe - 2 * EPS:
                    issues.append(f"{at(T)} shot starts mid-sentence: {who[:70]}")
                if fs + 2 * EPS < b < fe - EPS:
                    issues.append(f"{at(T + b - a)} shot cuts off: {who[:70]}")
                if max(fs, a) < min(fe, b):
                    voices.append((T + max(fs, a) - a, T + min(fe, b) - a, who))
        T += b - a
    voices.sort()
    for i, (_, e1, w1) in enumerate(voices):
        for s2, e2, w2 in voices[i + 1:]:
            if s2 >= e1:
                break
            if min(e1, e2) - s2 > 0.15 and ("narration" in w1 or "narration" in w2):
                issues.append(f"{at(s2)} {w1[:40]} overlaps {w2[:40]} by {min(e1, e2) - s2:.1f}s")

    err = subprocess.run(["ffmpeg", "-i", ROOT / edl["out"], "-an", "-vf", "mpdecimate,showinfo", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    fresh = {}
    for x in re.findall(r"pts_time:([\d.]+)", err):
        fresh[int(float(x))] = fresh.get(int(float(x)), 0) + 1
    for sec in range(int(T)):
        moving = any(s + 0.5 <= sec and sec + 1 <= e - 0.5 for s, e in shots) and not any(
            s < sec + 1 and e > sec for s, e in quiet)
        if moving and fresh.get(sec, 0) < 15:
            issues.append(f"{at(sec)} only {fresh.get(sec, 0)} new frames that second")

    print(f"{T:.1f}s, {len(edl['segments'])} segments, {len(voices)} voice intervals")
    for x in sorted(issues):
        print("ISSUE", x)
    print("PASS" if not issues else f"{len(issues)} issues")
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
