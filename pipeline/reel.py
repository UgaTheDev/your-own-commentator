"""Auto highlight reel: title card, each replay of an accepted event in time order (best ~8 s) with a short
gated voice line over its start and the crowd bed ducked under it, then an end card with the final score.

python pipeline/reel.py <clip_id> [--no-upload]
  -> data/<clip>/render/highlights.mp4, published/<clip>/highlights.mp4, data/<clip>/highlights.json (C3 `highlights`)

Grounding: every spoken line comes from write.gate() over that event's reviewed facts (write.build_facts);
a line that fails it goes to answer.answer() (gated, else its facts-only template). Cards show the reviewed final score.
"""
import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

from answer import answer
from common import DATA, ROOT, clip_dir, load, save
from mix import build_mix_args, duration_of
from voice import voiced
from write import build_facts, gate, speakable

TRACK = "rookie-en"  # the demo's default persona, Polly Matthew
CARD_SECS = 4.0
KEEP = 8.0  # seconds kept of each 12 s replay
VOICE_AT = 0.3  # the line starts this long into its replay
PRE, SLOW = 5.0, 0.5  # cv/replay.py: a replay covers event t - 5 s .. t + 1 s at half speed
W, H, BG, FG = 1920, 1080, (11, 15, 26), (255, 255, 255)

# 5x7 bitmap font (this ffmpeg has no drawtext and the venv has no Pillow). ponytail: only what cards need.
FONT = {c: g.split() for c, g in {
    "A": ".###. #...# #...# ##### #...# #...# #...#", "B": "####. #...# #...# ####. #...# #...# ####.",
    "C": ".#### #.... #.... #.... #.... #.... .####", "D": "####. #...# #...# #...# #...# #...# ####.",
    "E": "##### #.... #.... ####. #.... #.... #####", "F": "##### #.... #.... ####. #.... #.... #....",
    "G": ".#### #.... #.... #.### #...# #...# .####", "H": "#...# #...# #...# ##### #...# #...# #...#",
    "I": "##### ..#.. ..#.. ..#.. ..#.. ..#.. #####", "J": "..### ...#. ...#. ...#. ...#. #..#. .##..",
    "K": "#...# #..#. #.#.. ##... #.#.. #..#. #...#", "L": "#.... #.... #.... #.... #.... #.... #####",
    "M": "#...# ##.## #.#.# #.#.# #...# #...# #...#", "N": "#...# ##..# #.#.# #..## #...# #...# #...#",
    "O": ".###. #...# #...# #...# #...# #...# .###.", "P": "####. #...# #...# ####. #.... #.... #....",
    "Q": ".###. #...# #...# #...# #.#.# #..#. .##.#", "R": "####. #...# #...# ####. #.#.. #..#. #...#",
    "S": ".#### #.... #.... .###. ....# ....# ####.", "T": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
    "U": "#...# #...# #...# #...# #...# #...# .###.", "V": "#...# #...# #...# #...# #...# .#.#. ..#..",
    "W": "#...# #...# #...# #.#.# #.#.# ##.## #...#", "X": "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
    "Y": "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..", "Z": "##### ....# ...#. ..#.. .#... #.... #####",
    "0": ".###. #...# #..## #.#.# ##..# #...# .###.", "1": "..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.",
    "2": ".###. #...# ....# ...#. ..#.. .#... #####", "3": "####. ....# ....# .###. ....# ....# ####.",
    "4": "...#. ..##. .#.#. #..#. ##### ...#. ...#.", "5": "##### #.... ####. ....# ....# #...# .###.",
    "6": ".###. #.... #.... ####. #...# #...# .###.", "7": "##### ....# ...#. ..#.. .#... .#... .#...",
    "8": ".###. #...# #...# .###. #...# #...# .###.", "9": ".###. #...# #...# .#### ....# ....# .###.",
    " ": "..... ..... ..... ..... ..... ..... .....", "-": "..... ..... ..... .###. ..... ..... .....",
    "·": "..... ..... ..... ..#.. ..... ..... .....",
}.items()}


def card(lines, path, scale=14):
    """Write a W x H binary PPM with `lines` of text centered, one font pixel = scale px."""
    bg, fg = bytes(BG), bytes(FG)
    rows = []
    for text in lines:
        glyphs = [FONT[c] for c in text.upper()]  # KeyError = a card character the font lacks
        width = len(glyphs) * 6 * scale - scale
        if width > W:
            raise ValueError(f"card line too wide: {text!r}")
        pad = bg * ((W - width) // 2)
        for r in range(7):
            px = b"".join(b"".join((fg if ch == "#" else bg) * scale for ch in g[r]) + bg * scale for g in glyphs)
            line = pad + px[:width * 3] + bg * (W - width - (W - width) // 2)
            rows += [line] * scale
        rows += [bg * W] * (scale * 4)  # gap between lines
    rows = rows[:-scale * 4]
    top = (H - len(rows)) // 2
    body = bg * W * top + b"".join(rows) + bg * W * (H - top - len(rows))
    path.write_bytes(b"P6 %d %d 255\n" % (W, H) + body)
    return path


def window(te, ball_end=None, dur=12.0, keep=KEEP):
    """Start (replay seconds) of the best `keep` s: ends 2 replay-seconds after the shot. Scoreboard events lag the
    shot, so the shot is the last tracked-ball time (cv index ball_window_end) when known, else 1 s before the end."""
    shot = dur - 2.0 if ball_end is None else (ball_end - (te - PRE)) / SLOW
    end = min(dur, max(keep, shot + 2.0))
    return round(end - keep, 2)


def score_text(score, teams):
    return " · ".join(f"{t} {score[t]}" for t in teams)


def prompt_for(persona, facts):
    return (
        f"You are a basketball commentator voicing a highlight reel. Style: {persona['style']}\n"
        f"Write ONE very short spoken line in language '{persona['lang']}' introducing this replay, at most 8 words, "
        "like 'Blue free throw: 3 to 11' or 'Pink hits a three: 20 to 6': the team, the play, then the score from "
        "FACTS.state.score with the scoring team first. Use ONLY FACTS; never invent names, stats or times. "
        "Write numbers as digits. Reply with the line only.\n"
        f"FACTS: {json.dumps(facts, ensure_ascii=False)}"
    )


ASK = "Introduce the replay of this play in at most 10 words: the team, the play, and the score."


def lines_for(events, states, rules, roster, persona):
    """{eventId: (text, how)}. The short gate() line; if it fails both tries, answer.answer() over the same facts
    (itself gated, or its facts-only template). Nothing ungated is ever spoken."""
    def one(e):
        facts = build_facts(e, states[e["id"]], rules, roster)
        text, reason = gate(prompt_for(persona, facts), facts, max_words=10)
        if not reason:
            return e["id"], (text, "gate")
        a = answer(ASK, {"event": facts["event"], "state": {"score": facts["state"]["score"]},
                         "rule": facts.get("rule"), "recent": []}, persona)
        return e["id"], (a["text"], f"answer{' fallback' if a['fallback'] else ''} (gate: {reason})")
    with ThreadPoolExecutor(8) as pool:
        return dict(pool.map(one, events))


def plan(replays, events, meta, start=CARD_SECS):
    """[(replay, trim start, reel time the segment starts)] in event time order."""
    out = []
    for r in sorted(replays, key=lambda r: events[r["eventId"]]["t"]):
        m = meta.get(r["eventId"], {})
        out.append((r, window(events[r["eventId"]]["t"], m.get("ball_window_end"), r["duration"]), start))
        start += min(KEEP, r["duration"])
    return out


def main(clip_id, upload=True):
    d = clip_dir(clip_id)
    clip = load(d / "clip.json")
    rules = load(ROOT / "pipeline" / "rules.json")
    persona = load(ROOT / "pipeline" / "personas.json")[TRACK]
    events = {e["id"]: e for e in speakable(load(d / "events.reviewed.json"))}
    states = {s["eventId"]: s for s in load(d / "state.json")}
    index = d / "render" / "replays" / "index.json"
    meta = {m["eventId"]: m for m in load(index)} if index.exists() else {}
    replays = [r for r in load(d / "replays.json") if r["eventId"] in events]  # accepted events only
    segs = plan(replays, events, meta)
    final = max(states.values(), key=lambda s: s["t"])["score"]  # reviewed state, not clip.json's assertion
    teams = clip["teams"]
    work = d / "render"
    title = card(["Highlights", score_text(final, teams)], work / "highlights-title.ppm")
    end = card(["Final", score_text(final, teams)], work / "highlights-end.ppm")

    said = lines_for([events[r["eventId"]] for r, _, _ in segs], states, rules, clip.get("roster", []), persona)
    speech = []
    for r, _, at in segs:
        text, how = said[r["eventId"]]
        print(f"{r['eventId']}: {how}: {text!r}")
        if text:
            v = voiced({"text": text, "voice": persona["voice"], "engine": persona["engine"], "lang": persona["lang"]})
            speech.append({"eventId": r["eventId"], "start": round(at + VOICE_AT, 2), "text": text,
                           "audio": v["audio"], "duration": v["duration"]})
    save(d / "highlights.lines.json", speech)

    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-framerate", "30",
            "-t", str(CARD_SECS), "-i", str(title)]
    for r, ss, _ in segs:
        args += ["-ss", str(ss), "-t", str(KEEP), "-i", str(d / "render" / "replays" / f"{r['eventId']}.mp4")]
    args += ["-loop", "1", "-framerate", "30", "-t", str(CARD_SECS), "-i", str(end)]
    n = len(segs) + 2
    graph = ";".join(f"[{k}:v]scale={W}:{H},setsar=1,fps=30,format=yuv420p[v{k}]" for k in range(n))
    graph += ";" + "".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    silent = work / "highlights-silent.mp4"
    subprocess.run(args + ["-filter_complex", graph, "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-an", str(silent)], check=True)
    out = work / "highlights.mp4"
    bed = DATA.parent / clip["audioBed"]
    subprocess.run(build_mix_args(silent, {TRACK: [(x["start"], x["audio"]) for x in speech]}, out, bed,
                                  duration_of(silent)), check=True)  # h264 copied, crowd ducked under each line
    dur = round(duration_of(out), 2)
    print(f"{out} {dur}s")
    if upload:
        from publish import upload as put  # lazy: boto3 only when publishing
        put(clip_id, {"highlights.mp4": out})
        save(d / "highlights.json", {"src": f"https://{os.environ['YOC_CDN']}/{clip_id}/highlights.mp4",
                                     "duration": dur, "events": [r["eventId"] for r, _, _ in segs]})
        print(f"wrote {d / 'highlights.json'}; now run publish.py {clip_id}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args()
    main(a.clip_id, not a.no_upload)
