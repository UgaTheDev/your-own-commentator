"""Persona writer: one grounded commentary line per (track, event).

Usage: python pipeline/write.py <clip_id> [--tracks rookie-en,kid-en,rookie-es]
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
    return max(3, int(gap * rate)), unit


def prompt_for(persona, facts, gap):
    n, unit = budget(gap, persona["lang"])
    return (
        f"You are a live basketball commentator. Style: {persona['style']}\n"
        f"Write ONE spoken line in language '{persona['lang']}' about this play, at most {n} {unit}.\n"
        "Hard rules: state only facts in FACTS. Never invent names, stats, times, streaks or anything not in FACTS. "
        "Speak in the third person as the commentator, never as a player. "
        "Refer to players by jersey number (and name only if FACTS.player has one). Write all numbers as digits. "
        "Reply with the line only, no quotes.\n"
        f"FACTS: {json.dumps(facts, ensure_ascii=False)}"
    )


JUDGE = (
    "You check sports commentary for invented facts. FACTS is the only ground truth. "
    "A LINE is 'unsupported' if it states any name, number, statistic, event, time or claim not present in or directly "
    "implied by FACTS (general rule explanations from FACTS.rule are allowed; tone and excitement are fine). "
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


def write_line(track_id, persona, event, facts, gap):
    """Returns (line, None) if it passes both gates, else (None, rejection). One regeneration allowed."""
    prompt = prompt_for(persona, facts, gap)
    reason = text = ""
    for attempt in range(2):
        p = prompt if attempt == 0 else f"{prompt}\nYour previous line was rejected ({reason}). Write a new one."
        text = common.converse("write", p, max_tokens=200, temperature=0.7).strip().strip('"')
        bad = unsupported_digits(text, facts)
        if bad:
            reason = f"numbers not in facts: {sorted(bad)}"
            continue
        ok, why = judge(text, facts)
        if not ok:
            reason = f"judge: {why}"
            continue
        return {
            "trackId": track_id, "eventId": event["id"], "t": event["t"],
            "priority": PRIORITY.get(event["type"], 1), "text": text, "lang": persona["lang"],
            "voice": persona["voice"], "engine": persona["engine"], "grounded": True, "judge": "supported",
        }, None
    return None, {"trackId": track_id, "eventId": event["id"], "lastText": text, "reason": reason}


def main(clip_id, tracks):
    d = common.clip_dir(clip_id)
    here = Path(__file__).parent
    clip, events, states = (common.load(d / f) for f in ("clip.json", "events.reviewed.json", "state.json"))
    rules, personas = common.load(here / "rules.json"), common.load(here / "personas.json")
    events = sorted(events, key=lambda e: e["t"])
    by_id = {s["eventId"]: s for s in states}
    missing = [e["id"] for e in events if e["id"] not in by_id]
    if missing:
        raise SystemExit(f"state.json is stale (no state for {missing[:5]}); rerun state.py")

    jobs = []
    for track_id in tracks:
        for i, e in enumerate(events):
            gap = events[i + 1]["t"] - e["t"] if i + 1 < len(events) else LAST_GAP
            facts = build_facts(e, by_id[e["id"]], rules, clip.get("roster", []))
            jobs.append((track_id, personas[track_id], e, facts, gap))

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
    a = ap.parse_args()
    main(a.clip_id, a.tracks.split(","))
