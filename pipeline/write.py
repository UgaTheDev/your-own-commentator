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
MVP_TRACKS = ["rookie-en", "kid-en", "rookie-es", "fantasy-en", "rookie-hi", "rookie-zh"]
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
    """Numbers a line may state anywhere. Jersey values are left out: see jersey_numbers()."""
    found = set()
    if isinstance(facts, dict):
        for k, v in facts.items():
            if k not in NOT_FACTS and k != "jersey":
                found |= (set() if TEAM_JERSEY.match(str(k)) else _numbers(k)) | allowed_numbers(v)
    elif isinstance(facts, (list, tuple)):
        for v in facts:
            found |= allowed_numbers(v)
    elif facts is not None and not isinstance(facts, bool):
        found |= _numbers(facts)
    return found


TEAM_JERSEY = re.compile(r"^\w+#\d+$")  # fantasy keys: "blue#5"


def jersey_numbers(facts):
    if isinstance(facts, dict):
        return set().union(_numbers(facts["jersey"]) if facts.get("jersey") is not None else set(),
                           *(_numbers(k.split("#")[1]) for k in facts if TEAM_JERSEY.match(str(k))),
                           *(jersey_numbers(v) for k, v in facts.items() if k != "jersey"))
    if isinstance(facts, (list, tuple)):
        return set().union(*(jersey_numbers(v) for v in facts))
    return set()


# A jersey number may only be said AS a jersey: "number 5", "#5", "No. 5", "número 5", "नंबर 5", "5号".
# Otherwise a jersey 5 in FACTS would license "blue scored 5 points" (it did, in a Lake Region recap).
JERSEY_AFTER = re.compile(r"\s*(?:号|नंबर)")  # zh "5号", hi "५ नंबर"
JERSEY_BEFORE = re.compile(r"(?:#|\bno\.|\bnumbers?|\bnúmero|\bdorsal|\bd?el|नंबर|जर्सी)\s*$", re.I)  # es: "el 23"
# Unambiguous cues ("el" also precedes scores): a number said this way must BE a jersey in the facts, even when the
# same number is a score ("नंबर १३" for pink's 13 points made up a player 13)
JERSEY_CUE = re.compile(r"(?:#|\bno\.|\bnumbers?|\bnúmero|\bdorsal|नंबर|जर्सी)\s*$", re.I)


EN_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                         "fifteen sixteen seventeen eighteen nineteen".split())}
EN_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if i > 1}
# es: un/una/uno are left out, they're mostly articles ("una canasta")
ES_UNITS = {"cero": 0, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
            "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciséis": 16, "diecisiete": 17,
            "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidós": 22, "veintitrés": 23,
            "veinticuatro": 24, "veinticinco": 25, "veintiséis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29}
ES_TENS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
ES_Y = {"uno": 1, **{k: v for k, v in ES_UNITS.items() if 2 <= v <= 9}}
ZH_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
EN_NUM = re.compile(r"\b(" + "|".join(EN_TENS) + r")(?:[- ](" + "|".join(k for k in EN_UNITS if 0 < EN_UNITS[k] < 10) + r"))?\b|\b("
                    + "|".join(EN_UNITS) + r")\b", re.I)
ES_NUM = re.compile(r"\b(" + "|".join(ES_TENS) + r")(?:\s+y\s+(" + "|".join(ES_Y) + r"))?\b|\b(" + "|".join(ES_UNITS) + r")\b", re.I)
ZH_NUM = re.compile(r"[零一二两三四五六七八九十百]+")


def _zh_value(s):
    total, cur = 0, 0
    for ch in s:
        if ch == "百":
            total += (cur or 1) * 100; cur = 0
        elif ch == "十":
            total += (cur or 1) * 10; cur = 0
        else:
            cur = ZH_DIGIT[ch]
    return total + cur


def spelled_numbers(text):
    """Numbers written as words ('forty-four', 'cuarenta y cuatro', '四十四') as canonical digit strings.
    The digit gate can't see words, so an invented score spelled out would otherwise pass. TODO: Hindi number words."""
    out = set()
    for m in EN_NUM.finditer(text):
        out.add(str(EN_TENS[m.group(1).lower()] + (EN_UNITS[m.group(2).lower()] if m.group(2) else 0)) if m.group(1)
                else str(EN_UNITS[m.group(3).lower()]))
    for m in ES_NUM.finditer(text):
        out.add(str(ES_TENS[m.group(1).lower()] + (ES_Y[m.group(2).lower()] if m.group(2) else 0)) if m.group(1)
                else str(ES_UNITS[m.group(3).lower()]))
    for m in ZH_NUM.finditer(text):
        out.add(str(_zh_value(m.group())))
    return out


def unsupported_digits(text, facts):
    """Numbers in `text` that appear nowhere in `facts`. Empty set = passes the gate."""
    allowed, jerseys, bad = allowed_numbers(facts), jersey_numbers(facts), set()
    for m in NUMBER.finditer(text):
        n = _canon(m.group())
        # ponytail: "Pink 5" is NOT a jersey cue: lines say scores that way ("white 51, maroon 34")
        as_jersey = JERSEY_BEFORE.search(text[:m.start()]) or JERSEY_AFTER.match(text[m.end():])
        if n not in allowed and not (n in jerseys and as_jersey):
            bad.add(n)
        elif n not in jerseys and (JERSEY_CUE.search(text[:m.start()]) or JERSEY_AFTER.match(text[m.end():])):
            bad.add(n)
    return bad | (spelled_numbers(text) - allowed)


# Third gate: every play a line names must be a play in FACTS. {lang: [(regex, event types it names)]}
FT, MISS = {"ft_made", "ft_missed"}, {"missed_shot", "ft_missed"}
LEXICON = {
    "en": [(r"\bst(eal|eals|ealing|ole|olen)\b", {"steal"}), (r"\bfoul(s|ed|ing)?\b", {"foul"}),
           (r"\brebound(s|ed|ing)?\b", {"rebound"}), (r"\bblock(s|ed|ing)?\b", {"block"}),
           (r"\btravel(s|ed|ing|led|ling)?\b", {"travel"}),
           (r"\bthree\b|\b(3|three)[- ]pointers?\b|\btriples?\b", {"made_3"}), (r"\bfree[- ]throws?\b", FT),
           (r"\btime[- ]?outs?\b", {"timeout"}),
           (r"\bturnovers?\b|\bturn(s|ed|ing)? (it |the ball )?over\b", {"turnover"}),
           (r"\bmiss(es|ed|ing)?\b", MISS)],
    "es": [(r"\brob(o|os|a|an|ó|aron|ar)\b", {"steal"}), (r"\bfaltas?\b(?! de pasos)", {"foul"}), (r"\brebot(e|es|ea)\b", {"rebound"}),
           (r"\btap(ón|ones)\b|\bbloque(o|a|ó)\b", {"block"}), (r"\bpasos\b|\bpaso de más\b", {"travel"}),
           (r"\btiros? libres?\b", FT), (r"\btiempos? (muertos?|fuera)\b", {"timeout"}),
           (r"\bpérdidas?\b|\bpierden? el balón\b|\bperdi(ó|eron) el balón\b", {"turnover"}),
           (r"\bfall(a|an|ó|aron)\b", MISS)],
    # no \b: Python's \b splits Devanagari words at vowel signs, and Chinese has no spaces.
    # TODO: hi/zh "scored" collocation, and native speakers to review these lists
    "hi": [(r"स्टील|चुरा", {"steal"}), (r"फ़ाउल|फाउल", {"foul"}), (r"रिबाउंड", {"rebound"}), (r"ब्लॉक", {"block"}),
           (r"ट्रैवल", {"travel"}), (r"थ्री[- ]?पॉइंटर|तीन[- ]पॉइंटर", {"made_3"}), (r"फ़्री थ्रो|फ्री थ्रो", FT),
           (r"टाइमआउट|टाइम-आउट", {"timeout"}), (r"टर्नओवर", {"turnover"}), (r"मिस", MISS)],
    "zh": [(r"抢断", {"steal"}), (r"(?<!走步)犯规", {"foul"}), (r"篮板", {"rebound"}), (r"盖帽", {"block"}),
           (r"走步", {"travel"}), (r"三分", {"made_3"}), (r"罚球", FT), (r"暂停", {"timeout"}), (r"失误", {"turnover"}),
           (r"未中|投丢|没进|不中", MISS)],
}
# ponytail: every lexicon runs on every line (a Spanish line can say "travel"); per-language when that misfires
PLAY_WORDS = [(re.compile(p), types) for lex in LEXICON.values() for p, types in lex]
IMPLIES = {"travel": {"turnover"}, "steal": {"turnover"}, "and_one": {"ft_made", "foul"}, "rebound": MISS,
           "ft_made": {"foul"}, "ft_missed": {"foul"}}  # true by definition: a rebound follows a miss, free throws a foul
SCORING = {"made_2", "made_3", "ft_made", "and_one"}
SCORE_VERB = re.compile(r"\bscor(e|es|ed|ing)\b|\banot(a|an|ó|aron|ar)\b")
NOT_A_PLAY = re.compile(r"\bteam fouls?\b|\bfaltas? (de|del) equipo\b")  # state.teamFouls is a count, not a play


def plays_named(text):
    """[(start, end, types)] for each play word in `text`."""
    text = NOT_A_PLAY.sub(lambda m: " " * len(m.group()), text.lower())
    return sorted((m.start(), m.end(), types) for rx, types in PLAY_WORDS for m in rx.finditer(text))


def fact_plays(facts, rule_words=False):
    """Event types FACTS supports: every `type` (event, recent, recap plays), and-one, and with rule_words the
    plays the rule card text mentions (Why answers explain rules; a live call that says "rebound" on a miss invents one)."""
    found = set()

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("type"), str):
                found.add(x["type"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(facts)
    if (facts.get("state") or {}).get("andOne"):
        found.add("and_one")
    rule = facts.get("rule") or {}
    if rule_words:
        found |= {t for _, _, ts in plays_named(f"{rule.get('title', '')} {rule.get('body', '')}") for t in ts}
    return found | {i for t in list(found) for i in IMPLIES.get(t, ())}


COLOR_ES = {"pink": ("rosa", "rosado", "rosados"), "blue": ("azul", "azules")}  # ponytail: color-named teams only


def team_plays(facts):
    """{(type, team)} a team word may be attached to: every typed fact with its team (None = no team, so no word fits)."""
    pairs = set()

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("type"), str) and "team" in x:
                pairs.add((x["type"], x.get("team")))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(facts)
    return pairs


def wrong_team(text, facts, named):
    """'A pink player turns over' on a blue turnover: a team word <= 2 words before a play word that team didn't make.
    Plays FACTS only imply (the turnover in a steal) carry no team, so they're not checked."""
    pairs = team_plays(facts)
    teams = {t for _, t in pairs if t} | set(((facts.get("state") or {}).get("score") or {}))
    words = {w: t for t in teams for w in (t, *COLOR_ES.get(t, ()))}
    if not words or not pairs:
        return []
    low = text.lower()
    marks = [(m.end(), words[m.group()]) for m in re.finditer(r"\b(" + "|".join(map(re.escape, words)) + r")\b", low)]
    bad = []
    for s, e, ts in named:
        before = [(end, t) for end, t in marks if end <= s and len(low[end:s].split()) <= 2]
        typed = {typ for typ, _ in pairs}
        if before and ts & typed and not any((typ, before[-1][1]) in pairs for typ in ts):
            bad.append(f"{before[-1][1]} didn't make that play: {text[before[-1][0] - len(before[-1][1]):e]!r}")
    return bad


AGENT = re.compile(r"\b(pink|blue|rosa|azul)\s+(players?|team)\b|\b(jugador|jugadora|equipo)\s+(rosa|azul)\b")


def teamless_agent(text, facts, named):
    """A play whose only fact has no team ('A pink player calls a timeout' on a team-less timeout): naming a team as
    the actor invents it. Score phrases ('pink leads 14 to 6') aren't actor phrases, so they still pass."""
    pairs = team_plays(facts)
    orphan = {typ for typ, t in pairs if t is None} - {typ for typ, t in pairs if t}
    if not any(ts & orphan for _, _, ts in named):
        return []
    m = AGENT.search(text.lower())
    return [f"credits a team-less play to a team: {m.group()!r}"] if m else []


def unsupported_plays(text, facts, rule_words=False):
    """Reasons `text` names a play FACTS don't have, credits it to the wrong team, or 'scores' a non-scoring play."""
    ok = fact_plays(facts, rule_words)
    named = plays_named(text)
    bad = [f"names a {'/'.join(sorted(ts))} not in facts: {text[s:e]!r}" for s, e, ts in named if not ts & ok]
    bad += wrong_team(text, facts, named)
    bad += teamless_agent(text, facts, named)
    for v in SCORE_VERB.finditer(text.lower()):
        nxt = next(((s, e, ts) for s, e, ts in named if s >= v.end()), None)
        if nxt and len(text[v.end():nxt[0]].split()) <= 2 and not nxt[2] & SCORING:
            bad.append(f"'{v.group()}' on a non-scoring play: {text[v.start():nxt[1]]!r}")
    return bad


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
        "if the jersey is null, say 'a pink player' or similar, never 'number'. Write all numbers, including jerseys, as digits "
        "(e.g. 'number 5'). Never use he/his/she/her for players; say 'the player' or use the jersey. "
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


NUMBER_WORDS = ("zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
                "sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty")
SPELLED_JERSEY = re.compile(rf"\b(number|no\.?|#)\s*({NUMBER_WORDS})\b", re.I)
PRONOUN = re.compile(r"\b(he|his|him|himself|she|her|hers|herself)\b", re.I)


def style_violations(text, lang="en"):
    """Deterministic checks the judge misses: a jersey spelled as a word slips past the digit gate (so an invented
    'number five' would pass), and a player's gender is not a fact we have."""
    bad = []
    if SPELLED_JERSEY.search(text):
        bad.append(f"jersey spelled as a word ({SPELLED_JERSEY.search(text).group()!r}); write it as a digit")
    if lang == "en" and PRONOUN.search(text):
        bad.append(f"gendered pronoun ({PRONOUN.search(text).group()!r}); say 'the player' or use the jersey")
    return bad


def gate(prompt, facts, retry="Your previous line was rejected ({reason}). Write a new one.",
         temperature=0.7, max_words=None, rule_words=False):
    """The grounding gate every spoken sentence passes: write, digit gate, play-word gate, judge; one regeneration.
    Returns (text, None) on success, else (last_text, reason)."""
    reason = text = ""
    for attempt in range(2):
        p = prompt if attempt == 0 else f"{prompt}\n{retry.format(reason=reason)}"
        text = common.converse("write", p, max_tokens=200, temperature=temperature).replace("*", "").strip().strip('"')
        bad = unsupported_digits(text, facts)
        if bad:
            reason = f"numbers not in facts: {sorted(bad)}"
            continue
        bad = style_violations(text) + unsupported_plays(text, facts, rule_words)
        if bad:
            reason = "; ".join(bad)
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
    spoken = gaps(speakable(events, allow_unreviewed))
    jobs = [(tid, personas[tid], e, build_facts(e, by_id[e["id"]], rules, clip.get("roster", [])), gap)
            for tid in tracks for e, gap in spoken]
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
