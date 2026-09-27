"""Pre-rendered "Why?" answers: per teachable event, up to 3 viewer questions, one voiced answer per track.

python pipeline/why.py <clip_id> [--tracks rookie-en,kid-en,rookie-es,booth-en,fantasy-en,rookie-hi,rookie-zh] [--allow-unreviewed]
  -> data/<clip>/questions.json  {eventId: [{q, answers: {trackId: {text, audio, fallback}}}]}
publish.py turns `audio` (a local Polly cache file) into the C3 `audioUrl`.

The questions are hand-written per play type (no model, so they can't smuggle in a fact). Every
answer is answer.answer() over write.build_facts, so it is gated or a facts-only template.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

import common
import voice
import write
from answer import answer

# ponytail: fixed questions per play type; generate them per event when the rule cards can't cover it
QUESTIONS = {
    "foul": ["Why was that a foul?", "What happens after a foul?", "Can a player foul out?"],
    "travel": ["What is traveling?", "Why did they lose the ball?", "How do you avoid a travel?"],
    "turnover": ["What is a turnover?", "Who gets the ball now?"],
    "made_3": ["Why is that worth 3?", "Where do you shoot a 3 from?", "What's the score now?"],
    "ft_made": ["Why did they get a free shot?", "How much is a free throw worth?", "What's the score now?"],
    "and_one": ["What is an and-one?", "Why does the basket still count?", "What's the score now?"],
}
TRACKS = ["rookie-en", "kid-en", "rookie-es", "booth-en", "fantasy-en", "rookie-hi", "rookie-zh"]


def persona_for(personas, track_id):
    p = personas[track_id]
    return p["analyst"] if p.get("kind") == "booth" else p  # the booth's analyst explains


def kind_of(event, state):
    return "and_one" if state.get("andOne") else event["type"]


def voiced_answer(question, facts, persona):
    r = answer(question, facts, persona)
    audio = voice.synth({"text": r["text"], **{k: persona[k] for k in ("voice", "engine", "lang")}})
    return {"text": r["text"], "audio": str(audio), "fallback": r["fallback"]}


def main(clip_id, tracks, allow_unreviewed=False):
    d, clip, events, by_id, rules, personas = write.inputs(clip_id)
    jobs = []
    for e in write.speakable(events, allow_unreviewed):
        kind = kind_of(e, by_id[e["id"]])
        if kind in QUESTIONS:
            facts = write.build_facts(e, by_id[e["id"]], rules, clip.get("roster", []))
            jobs += [(e["id"], q, tid, facts) for q in QUESTIONS[kind][:3] for tid in tracks]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda j: voiced_answer(j[1], j[3], persona_for(personas, j[2])), jobs))
    questions = {}
    for (eid, q, tid, _), r in zip(jobs, results):
        qs = questions.setdefault(eid, [])
        if not qs or qs[-1]["q"] != q:
            qs.append({"q": q, "answers": {}})
        qs[-1]["answers"][tid] = r
    common.save(d / "questions.json", questions)
    fb = sum(r["fallback"] for r in results)
    print(f"why: {len(questions)} events, {len(results)} answers ({fb} facts-only template fallbacks)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--tracks", default=",".join(TRACKS))
    ap.add_argument("--allow-unreviewed", action="store_true", help="DEV ONLY: speak events not yet accepted in review")
    a = ap.parse_args()
    main(a.clip_id, a.tracks.split(","), a.allow_unreviewed)
