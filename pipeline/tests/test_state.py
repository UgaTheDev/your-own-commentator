import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from state import compute  # noqa: E402

CLIP = {"teams": ["red", "blue"], "start_score": {"red": 10, "blue": 8}}


def ev(i, t, type, team: str | None = "red", jersey=None):
    return {"id": f"e{i}", "t": t, "type": type, "team": team, "jersey": jersey}


def test_score_starts_mid_game_and_counts_all_shot_types():
    s = compute(CLIP, [ev(1, 1, "made_2"), ev(2, 5, "made_3", "blue"), ev(3, 9, "ft_made"), ev(4, 12, "missed_shot")])
    assert [x["score"] for x in s] == [
        {"red": 12, "blue": 8}, {"red": 12, "blue": 11}, {"red": 13, "blue": 11}, {"red": 13, "blue": 11}]


def test_events_are_sorted_by_time():
    s = compute(CLIP, [ev(2, 9, "made_3"), ev(1, 1, "made_2")])
    assert [x["eventId"] for x in s] == ["e1", "e2"]


def test_team_fouls_and_fantasy():
    s = compute(CLIP, [
        ev(1, 1, "made_3", jersey=23), ev(2, 4, "rebound", jersey=23), ev(3, 8, "rebound", jersey=23),
        ev(4, 10, "turnover", jersey=23), ev(5, 12, "steal", "blue", 5), ev(6, 15, "foul", "blue", 5),
    ])
    assert s[-1]["fantasy"] == {"red#23": 4.4, "blue#5": 3}  # 3 + 1.2 + 1.2 - 1, no float noise
    assert s[-1]["teamFouls"] == {"red": 0, "blue": 1}
    assert s[0]["fantasyDelta"] == {"red#23": 3}
    assert s[-1]["fantasyDelta"] == {}  # fouls score no fantasy points


def test_and_one_needs_opponent_foul_within_window():
    s = compute(CLIP, [ev(1, 10, "made_2"), ev(2, 10.5, "foul", "blue"), ev(3, 20, "made_2"), ev(4, 22, "foul", "blue"),
                       ev(5, 30, "made_2"), ev(6, 30.2, "foul", "red")])
    by_id = {x["eventId"]: x["andOne"] for x in s}
    assert by_id["e1"] is True
    assert by_id["e3"] is False  # foul too late
    assert by_id["e5"] is False  # own team's foul


def test_final_score_mismatch_fails_loudly():
    with pytest.raises(ValueError, match="final_score"):
        compute({**CLIP, "final_score": {"red": 14, "blue": 8}}, [ev(1, 1, "made_2")])
    assert compute({**CLIP, "final_score": {"red": 12, "blue": 8}}, [ev(1, 1, "made_2")])


@pytest.mark.parametrize("bad", [ev(1, 1, "dunk_of_the_year"), ev(1, 1, "made_2", team="green"), ev(1, 1, "foul", team=None)])
def test_bad_events_rejected(bad):
    with pytest.raises(ValueError):
        compute(CLIP, [bad])


def test_timeout_without_team_and_empty_clip():
    assert compute(CLIP, [ev(1, 1, "timeout", team=None)])[0]["score"] == {"red": 10, "blue": 8}
    assert compute(CLIP, []) == []
