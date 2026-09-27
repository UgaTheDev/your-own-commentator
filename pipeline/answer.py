"""C7: the one grounded answer path for Why, Catch me up and live talk-back.

answer(question, facts, persona) runs the same two gates as write.write_line (digit gate, then
the Bedrock judge), retries once, and otherwise falls back to a template built only from `facts`.
It never returns an ungated model sentence.
"""
import json

import common
from write import judge, unsupported_digits

WINDOW = 30.0  # seconds of recent verified events a viewer's question may refer to


def facts_at(t, manifest):
    """Facts at the playhead: the latest event, its state and rule card, plus the last WINDOW s of events."""
    events = sorted(manifest["events"], key=lambda e: e["t"])
    past = [e for e in events if e["t"] <= t]
    if not past:
        return {"event": None, "state": None, "rule": None, "recent": []}
    ev = past[-1]
    state = next((s for s in manifest["state"] if s["eventId"] == ev["id"]), None)
    rule = manifest["ruleCards"].get(ev.get("ruleCardId") or "")
    recent = [{k: e[k] for k in ("type", "team", "jersey")} for e in past if t - e["t"] <= WINDOW]
    return {"event": {k: ev[k] for k in ("id", "t", "type", "team", "jersey")},
            "state": state and {k: state[k] for k in ("score",) if k in state}, "rule": rule, "recent": recent}


def prompt_for(question, facts, persona):
    return (
        f"You are a basketball commentator. Style: {persona['style']}\n"
        f"A viewer asks: {question!r}\n"
        f"Answer in language '{persona['lang']}' in at most 2 short spoken sentences, using ONLY FACTS. "
        "If FACTS don't answer the question, say you can only speak to what happened on the court and give the latest "
        "fact instead. Never invent names, stats, times or reasons. Write numbers as digits. Reply with the answer only.\n"
        f"FACTS: {json.dumps(facts, ensure_ascii=False)}"
    )


TEMPLATES = {
    "en": ("The last play was {what} by the {team} team.", "The score is {score}.", "I can only speak to what happened on the court."),
    "es": ("La última jugada fue {what} del equipo {team}.", "El marcador es {score}.", "Solo puedo hablar de lo que pasó en la cancha."),
}


def fallback(facts, lang):
    """Deterministic, built only from facts: can't invent anything."""
    play, score, none = TEMPLATES.get(lang, TEMPLATES["en"])
    ev, st = facts.get("event"), facts.get("state")
    if not ev:
        return none
    what = (facts.get("rule") or {}).get("title") or ev["type"].replace("_", " ")
    parts = [play.format(what=what, team=ev.get("team") or "?")]
    if st and st.get("score"):
        parts.append(score.format(score=", ".join(f"{k} {v}" for k, v in st["score"].items())))
    return " ".join(parts)


def answer(question, facts, persona):
    base = prompt_for(question, facts, persona)
    reason = ""
    for attempt in range(2):
        p = base if attempt == 0 else f"{base}\nYour previous answer was rejected ({reason}). Answer again."
        text = common.converse("write", p, max_tokens=200, temperature=0.4).strip().strip('"')
        bad = unsupported_digits(text, facts)
        if bad:
            reason = f"numbers not in facts: {sorted(bad)}"
            continue
        ok, why = judge(text, facts)
        if ok:
            return {"text": text, "gated": True, "fallback": False}
        reason = f"judge: {why}"
    return {"text": fallback(facts, persona["lang"]), "gated": True, "fallback": True}
