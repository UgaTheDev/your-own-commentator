import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publish import build_manifest  # noqa: E402

KEYS = {"clipId", "videoUrl", "tracks", "events", "cues", "ruleCards", "state", "questions", "roster"}
EVENTS = [{"id": "e2", "t": 9, "type": "foul", "team": "blue", "jersey": 5},
          {"id": "e1", "t": 1, "type": "made_2", "team": "red", "jersey": 23}]
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
    assert [t["id"] for t in m["tracks"]] == ["kid-en", "rookie-en"]
    assert m["tracks"][1] == {"id": "rookie-en", "persona": "rookie", "lang": "en", "label": "Rookie (EN)",
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
