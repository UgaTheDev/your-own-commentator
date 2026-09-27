import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoreboard import change_points, drop_periodic, score_events  # noqa: E402

A, B = bytes([10] * 32), bytes([200] * 32)


def test_change_points_track_the_last_stable_frame():
    assert change_points([]) == []
    assert change_points([A, A, B, B, A]) == [0, 2, 4]
    assert change_points([A, bytes([12] * 32)]) == [0]  # small noise is not a change


def test_score_events_from_deltas():
    tl = [(0.0, {"pink": 11, "blue": 2}), (30.0, {"pink": 11, "blue": 3}), (50.0, {"pink": 11, "blue": 6}),
          (90.0, {"pink": 13, "blue": 6})]
    ev, warn = score_events(tl)
    assert [(e["t"], e["type"], e["team"]) for e in ev] == [
        (28.5, "ft_made", "blue"), (48.5, "made_3", "blue"), (88.5, "made_2", "pink")]
    assert warn == [] and all(e["source"] == "scoreboard" and e["status"] == "proposed" for e in ev)


def test_implausible_jumps_warn_instead_of_inventing_events():
    ev, warn = score_events([(0.0, {"pink": 11, "blue": 2}), (10.0, {"pink": 16, "blue": 2}),
                             (20.0, {"pink": 11, "blue": 2})])
    assert ev == [] and len(warn) == 2  # +5 (misread or missed updates) and -5


def ev(t, type="made_2"):
    return {"t": t, "type": type}


def test_drop_periodic_removes_model_loops_but_keeps_real_plays():
    loop = [ev(18.1), ev(20.2), ev(22.3), ev(24.4)]
    real = [ev(5.0), ev(40.0), ev(41.0, "rebound"), ev(43.5, "rebound")]
    kept = drop_periodic(loop + real)
    assert sorted(e["t"] for e in kept) == [5.0, 40.0, 41.0, 43.5]


def test_drop_periodic_needs_three_in_a_row_and_same_type():
    assert len(drop_periodic([ev(1.0), ev(3.1)])) == 2
    assert len(drop_periodic([ev(1.0), ev(3.0, "foul"), ev(5.0)])) == 3


def test_plausible_rejects_misreads_and_jumps():
    from scoreboard import plausible
    last = {"pink": 17, "blue": 6}
    assert plausible(last, {"pink": 17, "blue": 6})
    assert plausible(last, {"pink": 20, "blue": 6})
    assert not plausible(last, {"pink": 7, "blue": 6})    # "17" misread as "7"
    assert not plausible(last, {"pink": 28, "blue": 35})  # garbage at a transition
