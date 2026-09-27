"""Catch me up: at every 60 s mark t, a <= 25-word voiced recap of the plays in [t-120, t].

python pipeline/recap.py <clip_id> [--track rookie-en] [--allow-unreviewed]
  -> data/<clip>/recaps.json  [{t, text, audio}]   (publish.py turns `audio` into the C3 `src`)

Facts are those events plus the state at t; the recap passes write.gate (digit gate, 25-word cap,
judge, one retry) or that mark is dropped.
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor

import common
import voice
import write

EVERY, WINDOW, MAX_WORDS = 60, 120, 25
STATE_KEYS = ("score", "teamFouls")


def recap_facts(t, events, by_id):
    """None when nothing happened in the window."""
    window = [e for e in events if t - WINDOW <= e["t"] <= t]
    if not window:
        return None
    state = by_id[window[-1]["id"]]
    return {"plays": [{k: e.get(k) for k in ("type", "team", "jersey")} for e in window],
            "state": {k: state[k] for k in STATE_KEYS if k in state}}


def prompt_for(persona, facts):
    return (
        f"You are a basketball commentator. Style: {persona['style']}\n"
        f"A viewer stepped away and just came back. In language '{persona['lang']}', catch them up in ONE or TWO "
        f"spoken sentences, at most {MAX_WORDS} words total, on FACTS.plays (in order, oldest first) and the score. "
        "Hard rules: state only facts in FACTS. Never invent names, stats, times or streaks. Refer to a player by "
        "jersey only if it is set, otherwise by team. Write numbers as digits. Only state the score using "
        "FACTS.state.score exactly: it is the score NOW, and you know no earlier score, so never say who led before, "
        "who is on a run or by how much anyone scored. Reply with the recap only, no quotes.\n"
        f"FACTS: {json.dumps(facts, ensure_ascii=False)}"
    )


def recap_at(t, facts, persona):
    text, reason = write.gate(prompt_for(persona, facts), facts, max_words=MAX_WORDS)
    if reason:
        return None, {"t": t, "lastText": text, "reason": reason}
    audio = voice.synth({"text": text, **{k: persona[k] for k in ("voice", "engine", "lang")}})
    return {"t": t, "text": text, "audio": str(audio)}, None


def main(clip_id, track, allow_unreviewed=False):
    d, _, events, by_id, _, personas = write.inputs(clip_id)
    events = write.speakable(events, allow_unreviewed)
    end = events[-1]["t"] if events else 0
    marks = [(t, f) for t in range(EVERY, int(end) + 1, EVERY) if (f := recap_facts(t, events, by_id))]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda m: recap_at(m[0], m[1], personas[track]), marks))
    recaps = [r for r, _ in results if r]
    rejected = [x for _, x in results if x]
    common.save(d / "recaps.json", recaps)
    common.save(d / "recaps.rejected.json", rejected)
    print(f"recap: {len(recaps)}/{len(marks)} marks passed, {len(rejected)} dropped after retry")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--track", default="rookie-en", help="persona (voice and style) that reads the recaps")
    ap.add_argument("--allow-unreviewed", action="store_true", help="DEV ONLY: speak events not yet accepted in review")
    a = ap.parse_args()
    main(a.clip_id, a.track, a.allow_unreviewed)
