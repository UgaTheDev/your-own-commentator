"""Two-voice booth track: a play-by-play call per event, plus an analyst reaction when there's room.

python pipeline/booth.py <clip_id> [--allow-unreviewed]  ->  data/<clip>/lines.booth.json (+ lines.booth.rejected.json)

Both voices pass the same gates (write.gate) against the same facts; the analyst also sees the pbp
call it reacts to, but that call is not a fact, so the judge still checks against FACTS only.
voice.py schedules the analyst right after its pbp line and drops it first when air time runs out.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

import common
import write

TRACK = "booth-en"
ANALYST_PRIORITY = 0  # below every pbp call: the first thing to go when the next play arrives
MIN_ROOM = 2.0  # seconds; less than this after the pbp call and the analyst stays quiet
LEAD_AND_PAUSE = 0.65  # voice.LEAD before the call + voice.GAP before the reaction


def room_after(pbp_text, gap, lang="en"):
    """Seconds left before the next event once the pbp call (estimated from its length) is done."""
    unit, rate = write.RATE[lang]
    size = len(pbp_text.split()) if unit == "words" else len(pbp_text)
    return gap - LEAD_AND_PAUSE - size / rate


def analyst_prompt(persona, facts, room, pbp_text):
    return (f"{write.prompt_for(persona, facts, room)}\n"
            f"You are the analyst. Your partner just called the play: {pbp_text!r}. React to it; don't repeat it.")


def booth_event(personas, event, facts, gap):
    """Returns (lines, rejections) for one event."""
    pbp_p, an_p = personas["pbp"], personas["analyst"]
    text, reason = write.gate(write.prompt_for(pbp_p, facts, gap), facts)
    if reason:
        return [], [{"trackId": TRACK, "eventId": event["id"], "role": "pbp", "lastText": text, "reason": reason}]
    lines = [write.make_line(TRACK, pbp_p, event, text, role="pbp")]
    room = room_after(text, gap, pbp_p["lang"])
    if room < MIN_ROOM:
        return lines, []
    a_text, reason = write.gate(analyst_prompt(an_p, facts, room, text), facts)
    if reason:
        return lines, [{"trackId": TRACK, "eventId": event["id"], "role": "analyst", "lastText": a_text, "reason": reason}]
    return lines + [write.make_line(TRACK, an_p, event, a_text, ANALYST_PRIORITY, role="analyst")], []


def main(clip_id, allow_unreviewed=False):
    d, clip, events, by_id, rules, personas = write.inputs(clip_id)
    jobs = [(e, write.build_facts(e, by_id[e["id"]], rules, clip.get("roster", [])), gap)
            for e, gap in write.gaps(write.speakable(events, allow_unreviewed))]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda j: booth_event(personas[TRACK], *j), jobs))
    lines = [x for ls, _ in results for x in ls]
    rejected = [x for _, rs in results for x in rs]
    common.save(d / "lines.booth.json", lines)
    common.save(d / "lines.booth.rejected.json", rejected)
    n_an = sum(x["role"] == "analyst" for x in lines)
    print(f"booth: {len(lines) - n_an} pbp + {n_an} analyst lines passed, {len(rejected)} rejected after retry")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--allow-unreviewed", action="store_true", help="DEV ONLY: speak events not yet accepted in review")
    a = ap.parse_args()
    main(a.clip_id, a.allow_unreviewed)
