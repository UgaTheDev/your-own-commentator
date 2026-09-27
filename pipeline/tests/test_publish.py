import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publish import build_manifest  # noqa: E402

KEYS = {"clipId", "videoUrl", "tracks", "events", "cues", "ruleCards", "state", "questions", "roster"}
EVENTS = [{"id": "e2", "t": 9, "type": "foul", "team": "blue", "jersey": 5, "status": "accepted"},
          {"id": "e1", "t": 1, "type": "made_2", "team": "red", "jersey": 23, "status": "accepted"},
          {"id": "e9", "t": 5, "type": "steal", "team": "red", "jersey": None, "status": "proposed"}]
STATES = [{"eventId": "e2", "t": 9, "score": {"red": 2, "blue": 0}, "fantasy": {"23": 2}, "andOne": False},
          {"eventId": "e1", "t": 1, "score": {"red": 2, "blue": 0}, "fantasy": {"23": 2}, "andOne": True}]
VOICED = [{"trackId": "rookie-en", "eventId": "e2", "start": 9.4, "duration": 1, "text": "Foul.", "audio": "x"},
          {"trackId": "rookie-en", "eventId": "e1", "start": 1.4, "duration": 1, "text": "Two.", "audio": "y"},
          {"trackId": "kid-en", "eventId": "e1", "start": 1.4, "duration": 1, "text": "Yay!", "audio": "z"}]
RULES = {"foul": {"title": "Foul", "body": "..."}, "and_one": {"title": "And-one", "body": "..."}}
CLIP = {"roster": [{"jersey": 23, "team": "red", "name": "Sam"}]}


def test_pertrack_manifest():
    m = build_manifest("c1", CLIP, EVENTS, STATES, VOICED, RULES, {}, "https://cdn/published/c1/")
    assert set(m) == KEYS
    assert [t["id"] for t in m["tracks"]] == ["rookie-en", "kid-en"]  # Rookie opens the demo, not alphabetical
    assert m["videoUrl"] == "https://cdn/published/c1/render/rookie-en.mp4"
    assert m["tracks"][0] == {"id": "rookie-en", "persona": "rookie", "lang": "en", "label": "Rookie (EN)",
                              "src": "https://cdn/published/c1/render/rookie-en.mp4"}
    assert [c["t"] for c in m["cues"]["rookie-en"]] == [1.4, 9.4]
    assert [e["id"] for e in m["events"]] == ["e1", "e2"]
    assert [e["ruleCardId"] for e in m["events"]] == ["and_one", "foul"]
    assert [s["t"] for s in m["state"]] == [1, 9]
    assert m["roster"] == CLIP["roster"]


def test_multitrack_local_and_no_rules():
    m = build_manifest("c1", {}, EVENTS, STATES, VOICED, {}, {}, multitrack=True)
    assert set(m) == KEYS and m["videoUrl"] == "render/multi.mp4"
    assert [t["audioTrackIndex"] for t in m["tracks"]] == [0, 1] and "src" not in m["tracks"][0]
    assert all(e["ruleCardId"] is None for e in m["events"]) and m["roster"] == []


def test_empty():
    m = build_manifest("c1", {}, [], [], [], {}, {})
    assert set(m) == KEYS and m["tracks"] == [] and m["cues"] == {} and m["videoUrl"] is None


def test_v2_booth_questions_recaps_validate_against_schema():
    import json

    import jsonschema

    voiced = VOICED + [
        {"trackId": "booth-en", "eventId": "e1", "start": 1.4, "duration": 1, "text": "Two!", "audio": "p", "role": "pbp"},
        {"trackId": "booth-en", "eventId": "e1", "start": 2.6, "duration": 1, "text": "In.", "audio": "a", "role": "analyst"}]
    personas = {"booth-en": {"kind": "booth", "pbp": {"voice": "Matthew"}, "analyst": {"voice": "Ruth"}}}
    questions = {"e1": [{"q": "Why 2?", "answers": {"rookie-en": {"text": "Inside the arc.", "audio": "/c/polly/ab.mp3",
                                                                   "fallback": False}}}]}
    recaps = [{"t": 120, "text": "Red scored 2.", "audio": "/c/polly/cd.mp3"}]
    base = "https://cdn.example/c1/"
    m = build_manifest("c1", CLIP, EVENTS, STATES, voiced, RULES, questions, base, personas=personas, recaps=recaps)
    schema = json.loads((Path(__file__).resolve().parents[2] / "schemas" / "manifest.schema.json").read_text())
    jsonschema.validate(m, schema)
    booth = next(t for t in m["tracks"] if t["id"] == "booth-en")
    assert booth["kind"] == "booth" and [v["voice"] for v in booth["voices"]] == ["Matthew", "Ruth"]
    assert [c["role"] for c in m["cues"]["booth-en"]] == ["pbp", "analyst"] and "role" not in m["cues"]["kid-en"][0]
    assert m["questions"]["e1"][0]["answers"]["rookie-en"] == {"text": "Inside the arc.", "audioUrl": base + "audio/ab.mp3"}
    assert m["recaps"] == [{"t": 120, "src": base + "audio/cd.mp3", "text": "Red scored 2."}]


def test_proposed_events_never_reach_the_manifest():
    m = build_manifest("c1", CLIP, EVENTS, STATES, VOICED, RULES, {})
    assert [e["id"] for e in m["events"]] == ["e1", "e2"]
    dev = build_manifest("c1", CLIP, EVENTS, STATES, VOICED, RULES, {}, allow_unreviewed=True)
    assert [e["id"] for e in dev["events"]] == ["e1", "e9", "e2"]


def test_extras_pick_up_cv_files_and_service_urls(tmp_path):
    import json
    from publish import extras
    (tmp_path / "replays.json").write_text(json.dumps([{"eventId": "e3", "src": "https://x/r.mp4", "duration": 12.0}]))
    clip = {"talk": {"wsUrl": "wss://t"}, "party": {"wsUrl": "wss://p"}, "teams": ["pink", "blue"]}
    out = extras(tmp_path, clip)
    assert out == {"replays": [{"eventId": "e3", "src": "https://x/r.mp4", "duration": 12.0}],
                   "talk": {"wsUrl": "wss://t"}, "party": {"wsUrl": "wss://p"}}
    assert extras(tmp_path / "nope", {}) == {}
