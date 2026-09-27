"""C7: the one grounded answer path for Why, Catch me up and live talk-back.

answer(question, facts, persona) runs the same two gates as write.write_line (digit gate, then
the Bedrock judge), retries once, and otherwise falls back to a template built only from `facts`.
It never returns an ungated model sentence.
"""
import json

import common  # noqa: F401  (tests patch common.converse through here)
from write import gate

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
    "hi": ("पिछला खेल {team} टीम का {what} था।", "स्कोर {score} है।", "मैं केवल कोर्ट पर हुई बातों के बारे में बता सकता हूँ।"),
    "zh": ("上一个回合是{team}队的{what}。", "比分是{score}。", "我只能谈论场上发生的事情。"),
}


NO_TEAM = {"en": "The last play was a {what}.", "es": "La última jugada fue {what}.",
           "hi": "पिछला खेल {what} था।", "zh": "上一个回合是{what}。"}  # team-less plays (timeouts): never say "the ? team"


def fallback(facts, lang):
    """Deterministic, built only from facts: can't invent anything."""
    play, score, none = TEMPLATES.get(lang, TEMPLATES["en"])
    ev, st = facts.get("event"), facts.get("state")
    if not ev:
        return none
    what = (facts.get("rule") or {}).get("title") or ev["type"].replace("_", " ")
    team = ev.get("team")
    parts = [play.format(what=what, team=team) if team else NO_TEAM.get(lang, NO_TEAM["en"]).format(what=what)]
    if st and st.get("score"):
        parts.append(score.format(score=", ".join(f"{k} {v}" for k, v in st["score"].items())))
    return " ".join(parts)


def answer(question, facts, persona):
    text, reason = gate(prompt_for(question, facts, persona), facts,
                        retry="Your previous answer was rejected ({reason}). Answer again.", temperature=0.4,
                        rule_words=True)  # answers explain the rule card, so its plays may be named
    if not reason:
        return {"text": text, "gated": True, "fallback": False}
    return {"text": fallback(facts, persona["lang"]), "gated": True, "fallback": True}
