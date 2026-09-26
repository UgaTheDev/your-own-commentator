import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract import chunk_starts, dedupe, to_absolute, validate  # noqa: E402


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
        "t": 2.0, "type": "steal", "team": "red", "jersey": 7, "confidence": 0.8}
    assert validate({"t": 2, "type": "dunk", "confidence": 0.8}) is None
    assert validate({"t": "2", "type": "steal", "confidence": 0.8}) is None
    assert validate({"t": 2, "type": "steal", "jersey": "7", "confidence": 0.8}) is None
    assert validate({"t": 2, "type": "steal", "confidence": 1.5}) is None
    assert validate("made_2") is None
