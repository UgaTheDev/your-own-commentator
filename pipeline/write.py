"""Persona writer: one grounded commentary line per (track, event).

Usage: python pipeline/write.py <clip_id> [--tracks rookie-en,kid-en,rookie-es] [--allow-unreviewed]
Only events with status "accepted" are spoken (CONTRACTS.md); --allow-unreviewed is a dev-only escape hatch.
Reads clip.json, events.reviewed.json, state.json, rules.json, personas.json.
Writes lines.json (lines that passed both gates, input to voice.py) and lines.rejected.json.

Rule (CLAUDE.md): commentary may only state facts present in the verified event and
game-state JSON (plus our hand-written rules.json entry). The writer must write numbers as
digits; unsupported_digits() rejects any digit sequence not in the allowed facts. Names,
claims and spelled-out numbers ("tres", 三) are the Bedrock judge's job.
"""
import argparse
import json
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common

# t/ids are bookkeeping, not facts a commentator may say
NOT_FACTS = {"t", "id", "eventId", "ruleCardId"}
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")  # \d matches any Unicode digit: ३, ３, etc.
MVP_TRACKS = ["rookie-en", "kid-en", "rookie-es"]
PRIORITY = {"made_2": 3, "made_3": 3, "ft_made": 3, "foul": 2, "travel": 2, "turnover": 2}  # rest: 1
# ponytail: rough speech rates (units per second) to size the budget; voice.py measures real durations
RATE = {"en": ("words", 2.5), "es": ("words", 2.5), "hi": ("words", 2.2), "zh": ("characters", 4.0)}
MAX_LEN = {"words": 20, "characters": 35}  # TV commentary is short even when the next play is far away
LAST_GAP = 6.0  # seconds of room after the final event


def _canon(match):
    # "३" -> "3", "1,2" (es decimal) -> "1.2", "12.0" -> "12"
    s = "".join(str(unicodedata.decimal(c)) if c.isdigit() else "." for c in match)
    return str(float(s)).removesuffix(".0")


def _numbers(s):
    return {_canon(m) for m in NUMBER.findall(str(s))}


def allowed_numbers(facts):
    found = set()
    if isinstance(facts, dict):
        for k, v in facts.items():
            if k not in NOT_FACTS:
                found |= _numbers(k) | allowed_numbers(v)
    elif isinstance(facts, (list, tuple)):
        for v in facts:
            found |= allowed_numbers(v)
    elif facts is not None and not isinstance(facts, bool):
        found |= _numbers(facts)
    return found


def unsupported_digits(text, facts):
    """Numbers in `text` that appear nowhere in `facts`. Empty set = passes the gate."""
    return _numbers(text) - allowed_numbers(facts)


def build_facts(event, state, rules, roster):
    """The only things a line may state. Review-only fields (confidence, status) are dropped."""
    ev = {k: event.get(k) for k in ("id", "t", "type", "team", "jersey")}
    kind = "and_one" if state.get("andOne") and "and_one" in rules else event["type"]
    player = next((p for p in roster if p["team"] == event.get("team") and p["jersey"] == event.get("jersey")), None)
    facts = {"event": ev, "state": {k: state[k] for k in ("score", "teamFouls", "fantasy", "fantasyDelta", "andOne")}}
    if kind in rules:
        facts["rule"] = rules[kind]
    if player:
        facts["player"] = {"name": player["name"], "jersey": player["jersey"], "team": player["team"]}
    return facts


def budget(gap, lang):
    unit, rate = RATE[lang]
    return max(3, min(MAX_LEN[unit], int(gap * rate))), unit


def prompt_for(persona, facts, gap):
    n, unit = budget(gap, persona["lang"])
    return (
        f"You are a live basketball commentator. Style: {persona['style']}\n"
        f"Write ONE spoken line in language '{persona['lang']}' about this play, at most {n} {unit}.\n"
        "Hard rules: state only facts in FACTS. Never invent names, stats, times, streaks or anything not in FACTS. "
        "Speak in the third person as the commentator, never as a player. "
        "Refer to players by jersey number only if FACTS.event.jersey is set (and by name only if FACTS.player has one); "
        "if the jersey is null, say 'a pink player' or similar, never 'number'. Write all numbers as digits. "
        "Only state the score using FACTS.state.score exactly. "
        "Reply with the line only, no quotes.\n"
        f"FACTS: {json.dumps(facts, ensure_ascii=False)}"
    )


JUDGE = (
    "You check sports commentary for invented facts. FACTS is the only ground truth. "
    "A LINE is 'unsupported' if it states any name, number, statistic, event, time or claim not present in or directly "
    "implied by FACTS (general rule explanations from FACTS.rule are allowed; tone and excitement are fine). "
    "Any statement about a team's score or points total (e.g. 'on the board with 1 point', 'leads by 5') must match "
    "FACTS.state.score exactly, otherwise it is unsupported. "
    'Reply with JSON only: {"verdict": "supported" | "unsupported", "reason": "<short>"}\n'
)


def judge(line, facts):
    reply = common.converse("judge", f"{JUDGE}FACTS: {json.dumps(facts, ensure_ascii=False)}\nLINE: {line}",
                            max_tokens=200, temperature=0)
    try:
        v = common.parse_json(reply)
        return v.get("verdict") == "supported", v.get("reason", "")
    except (ValueError, json.JSONDecodeError, AttributeError):
        return False, f"judge reply unparseable: {reply[:80]!r}"  # fail closed


def gate(prompt, facts, retry="Your previous line was rejected ({reason}). Write a new one.",
         temperature=0.7, max_words=None):
    """The grounding gate every spoken sentence passes: write, digit gate, judge; one regeneration.
    Returns (text, None) on success, else (last_text, reason)."""
    reason = text = ""
    for attempt in range(2):
        p = prompt if attempt == 0 else f"{prompt}\n{retry.format(reason=reason)}"
        text = common.converse("write", p, max_tokens=200, temperature=temperature).replace("*", "").strip().strip('"')
        bad = unsupported_digits(text, facts)
        if bad:
            reason = f"numbers not in facts: {sorted(bad)}"
            continue
        if max_words and len(text.split()) > max_words:
            reason = f"longer than {max_words} words"
            continue
        ok, why = judge(text, facts)
        if not ok:
            reason = f"judge: {why}"
            continue
        return text, None
    return text, reason


def make_line(track_id, persona, event, text, priority=None, **extra):
    return {"trackId": track_id, "eventId": event["id"], "t": event["t"],
            "priority": PRIORITY.get(event["type"], 1) if priority is None else priority, "text": text,
            "lang": persona["lang"], "voice": persona["voice"], "engine": persona["engine"], "grounded": True,
            "judge": "supported", **extra}


def write_line(track_id, persona, event, facts, gap):
    """Returns (line, None) if it passes both gates, else (None, rejection). One regeneration allowed."""
    text, reason = gate(prompt_for(persona, facts, gap), facts)
    if reason:
        return None, {"trackId": track_id, "eventId": event["id"], "lastText": text, "reason": reason}
    return make_line(track_id, persona, event, text), None


def speakable(events, allow_unreviewed=False):
    """Only accepted events may feed speech. allow_unreviewed is for dev clips of unreviewed proposals."""
    if allow_unreviewed:
        bar = "!" * 78
        print(f"{bar}\n!! --allow-unreviewed: speaking UNREVIEWED events. Dev clips only, never a submission.\n{bar}",
              file=sys.stderr)
        return list(events)
    return [e for e in events if e.get("status") == "accepted"]


def inputs(clip_id):
    """(dir, clip, events sorted by t, state by eventId, rules, personas) for one clip."""
    d = common.clip_dir(clip_id)
    here = Path(__file__).parent
    clip, events, states = (common.load(d / f) for f in ("clip.json", "events.reviewed.json", "state.json"))
    events = sorted(events, key=lambda e: e["t"])
    by_id = {s["eventId"]: s for s in states}
    missing = [e["id"] for e in events if e["id"] not in by_id]
    if missing:
        raise SystemExit(f"state.json is stale (no state for {missing[:5]}); rerun state.py")
    return d, clip, events, by_id, common.load(here / "rules.json"), common.load(here / "personas.json")


def gaps(events):
    """[(event, seconds until the next event)]."""
    return [(e, events[i + 1]["t"] - e["t"] if i + 1 < len(events) else LAST_GAP) for i, e in enumerate(events)]


def main(clip_id, tracks, allow_unreviewed=False):
    d, clip, events, by_id, rules, personas = inputs(clip_id)
    jobs = [(tid, personas[tid], e, build_facts(e, by_id[e["id"]], rules, clip.get("roster", [])), gap)
            for tid in tracks for e, gap in gaps(speakable(events, allow_unreviewed))]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda j: write_line(*j), jobs))
    lines = [r for r, _ in results if r]
    rejected = [x for _, x in results if x]
    common.save(d / "lines.json", lines)
    common.save(d / "lines.rejected.json", rejected)
    print(f"{len(lines)} lines passed, {len(rejected)} rejected after retry (see lines.rejected.json)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--tracks", default=",".join(MVP_TRACKS))
    ap.add_argument("--allow-unreviewed", action="store_true", help="DEV ONLY: speak events not yet accepted in review")
    a = ap.parse_args()
    main(a.clip_id, a.tracks.split(","), a.allow_unreviewed)
