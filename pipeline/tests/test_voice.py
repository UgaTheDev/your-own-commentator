import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from voice import schedule  # noqa: E402


def line(event, t, dur, prio=1, track="rookie-en"):
    return {"trackId": track, "eventId": event, "t": t, "duration": dur, "priority": prio, "text": event, "audio": f"{event}.mp3"}


def ids(kept):
    return [x["eventId"] for x in kept]


def test_empty():
    assert schedule([], []) == ([], [])


def test_starts_after_lead_and_keeps_fields():
    kept, dropped = schedule([line("e1", 1.0, 2.0)], [1.0])
    assert kept == [{"trackId": "rookie-en", "eventId": "e1", "start": 1.4, "duration": 2.0, "text": "e1", "audio": "e1.mp3"}]
    assert dropped == []


def test_overlap_drops_lower_priority():
    kept, dropped = schedule([line("e1", 0, 3, prio=1), line("e2", 2, 1, prio=5)], [0, 2])
    assert ids(kept) == ["e2"] and ids(dropped) == ["e1"]
    kept, _ = schedule([line("e1", 0, 3, prio=5), line("e2", 2, 1, prio=1)], [0, 2])
    assert ids(kept) == ["e1"]


def test_tie_keeps_earlier():
    kept, dropped = schedule([line("e2", 2, 1, prio=3), line("e1", 0, 3, prio=3)], [0, 2])
    assert ids(kept) == ["e1"] and ids(dropped) == ["e2"]


def test_line_running_into_unvoiced_next_event_is_dropped():
    kept, dropped = schedule([line("e1", 0, 3, prio=9), line("e3", 10, 1)], [0, 2, 10])
    assert ids(kept) == ["e3"] and ids(dropped) == ["e1"]


def test_tracks_are_independent():
    kept, _ = schedule([line("e1", 0, 3), line("e1", 0, 1, track="kid-en")], [0])
    assert [x["trackId"] for x in kept] == ["kid-en", "rookie-en"]


def booth(event, t, dur, role, prio):
    return {**line(event, t, dur, prio, track="booth-en"), "role": role}


def test_analyst_follows_its_pbp_line_without_overlap():
    kept, dropped = schedule([booth("e1", 0, 2.0, "analyst", 0), booth("e1", 0, 1.5, "pbp", 3)], [0, 10])
    assert [(x["role"], x["start"]) for x in kept] == [("pbp", 0.4), ("analyst", 2.15)] and dropped == []


def test_analyst_dropped_with_its_pbp_or_when_the_next_call_needs_the_air():
    kept, _ = schedule([booth("e1", 0, 3, "pbp", 1), booth("e1", 0, 1, "analyst", 0), booth("e2", 2, 1, "pbp", 3)], [0, 2])
    assert [(x["eventId"], x["role"]) for x in kept] == [("e2", "pbp")]  # e1 pbp loses, so its analyst goes too
    kept, dropped = schedule([booth("e1", 0, 1, "pbp", 3), booth("e1", 0, 2, "analyst", 0), booth("e2", 2, 1, "pbp", 1)], [0, 2])
    assert [(x["eventId"], x["role"]) for x in kept] == [("e1", "pbp"), ("e2", "pbp")]
    assert [x["role"] for x in dropped] == ["analyst"]
