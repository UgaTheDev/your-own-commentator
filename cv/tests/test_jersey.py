import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jersey  # noqa: E402

COURT = {"w": 28.0, "h": 15.0}


def r(j, legible=True):
    return {"jersey": j, "legible": legible}


def test_majority_vote_wins():
    assert jersey.vote([r(3), r(3), r(8)]) == (3, {"3": 2, "8": 1})


def test_single_legible_read_is_not_enough():
    assert jersey.vote([r(3), r(None, False), r(3, False)])[0] is None


def test_tie_is_inconsistent():
    assert jersey.vote([r(3), r(3), r(8), r(8)])[0] is None


def test_nothing_legible():
    assert jersey.vote([r(None, False)] * 4) == (None, {})


def frame(t, players, ball=None):
    return {"t": t, "players": players, "ball": {"box": ball} if ball else None}


def p(pid, team, box, court=None):
    return {"id": pid, "team": team, "jersey": None, "box": box, "court": court}


def test_shooter_nearest_ball_same_team_only():
    ps = [p(1, "pink", [0.10, 0.4, 0.05, 0.2]), p(2, "pink", [0.60, 0.4, 0.05, 0.2]),
          p(3, "blue", [0.45, 0.4, 0.05, 0.2])]  # blue 3 is closest to the ball but on the wrong team
    frames = [frame(t / 10, ps, ball=[0.47, 0.45, 0.01, 0.01]) for t in range(90, 101)]
    assert jersey.candidates(frames, "pink", 10.0, "made_2", COURT) == [2]


def test_no_ball_falls_back_to_rim_and_ft_spot():
    ps = [p(1, "pink", [0.1, 0.4, 0.05, 0.2], court=[1.8, 7.5]),   # under the rim
          p(2, "pink", [0.5, 0.4, 0.05, 0.2], court=[5.9, 7.4])]   # on the free-throw line
    frames = [frame(t / 10, ps) for t in range(90, 101)]
    assert jersey.candidates(frames, "pink", 10.0, "made_2", COURT, k=1) == [1]
    assert jersey.candidates(frames, "pink", 10.0, "ft_made", COURT, k=1) == [2]


def test_window_excludes_frames_after_release():
    early = [frame(9.5, [p(1, "pink", [0.4, 0.4, 0.05, 0.2])], ball=[0.42, 0.45, 0.01, 0.01])]
    late = [frame(10.5, [p(2, "pink", [0.4, 0.4, 0.05, 0.2])], ball=[0.42, 0.45, 0.01, 0.01])]
    assert jersey.candidates(early + late, "pink", 10.0, "made_3", COURT) == [1]


def test_best_frames_biggest_and_spaced():
    frames = [frame(t / 10, [p(7, "pink", [0.4, 0.4, 0.05, 0.1 + t / 1000])]) for t in range(85, 101)]
    got = jersey.best_frames(frames, 7, 10.0, n=3, gap=0.2)
    assert [round(t, 1) for t, _ in got] == [9.6, 9.8, 10.0]
