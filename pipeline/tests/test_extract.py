import json
import sys
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract import chunk_starts, dedupe, salvage, to_absolute, validate  # noqa: E402

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "schemas" / "event.schema.json").read_text())


def ev(t, type="made_2", confidence=0.5):
    return {"t": t, "type": type, "team": "red", "jersey": None, "confidence": confidence}


def test_chunk_starts():
    assert chunk_starts(0) == []
    assert chunk_starts(10) == [0]
    assert chunk_starts(20) == [0]
    assert chunk_starts(21) == [0, 15]
    assert chunk_starts(50) == [0, 15, 30]


def test_to_absolute_offsets_by_chunk_start():
    assert to_absolute([ev(3.5)], 15)[0]["t"] == 18.5


def test_dedupe_keeps_higher_confidence_and_assigns_ids():
    out = dedupe([ev(10.0, confidence=0.4), ev(11.5, confidence=0.9), ev(1.0)])
    assert [(e["id"], e["t"], e["confidence"]) for e in out] == [("e1", 1.0, 0.5), ("e2", 11.5, 0.9)]


def test_dedupe_keeps_different_types_and_far_events():
    assert len(dedupe([ev(10, "made_2"), ev(10, "foul")])) == 2
    assert len(dedupe([ev(10), ev(12.5)])) == 2


def test_validate():
    assert validate({"t": 2, "type": "steal", "team": " Red ", "jersey": 7, "confidence": 0.8}) == {
        "t": 2.0, "type": "steal", "team": "red", "jersey": 7, "confidence": 0.8,
        "source": "nova", "status": "proposed"}
    assert validate({"t": 2, "type": "dunk", "confidence": 0.8}) is None
    assert validate({"t": "2", "type": "steal", "confidence": 0.8}) is None
    assert validate({"t": 2, "type": "steal", "jersey": "7", "confidence": 0.8}) is None
    assert validate({"t": 2, "type": "steal", "confidence": 1.5}) is None
    assert validate("made_2") is None


def test_salvage_keeps_complete_objects_from_truncated_reply():
    cut = '[{"t": 1.0, "type": "made_2"}, {"t": 4.0, "type": "foul"}, {"t": 5.5, "type": "made_'
    assert salvage(cut) == [{"t": 1.0, "type": "made_2"}, {"t": 4.0, "type": "foul"}]
    assert salvage('[{"t": 1.0, "type": "made_2"}]') == [{"t": 1.0, "type": "made_2"}]


def test_extract_output_validates_against_event_schema():
    raw = [{"t": 1.0, "type": "made_2", "team": "red", "jersey": 7, "confidence": 0.8},
           {"t": 2.0, "type": "foul", "team": None, "confidence": 0.5}]
    events = dedupe(to_absolute([validate(r) for r in raw], 0))
    assert events  # sanity: something was produced
    for e in events:
        jsonschema.validate(e, SCHEMA)
