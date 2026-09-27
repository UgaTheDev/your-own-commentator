import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval import match, prf, report, scores  # noqa: E402


def ev(t, type="made_2"):
    return {"t": t, "type": type}


def test_matching_is_one_to_one():
    assert scores([ev(10.0), ev(10.5)], [ev(10.4)])["overall"] == (1, 1, 0)
    assert match([ev(10.0), ev(10.5)], [ev(10.4)]) == [(1, 0)]


def test_type_and_window_must_both_match():
    assert scores([ev(10, "foul"), ev(20)], [ev(10), ev(22.5)])["overall"] == (0, 2, 2)


def test_per_type_rows():
    s = scores([ev(1), ev(5, "foul")], [ev(1.5), ev(9, "steal")])
    assert s["made_2"] == (1, 0, 0) and s["foul"] == (0, 1, 0) and s["steal"] == (0, 0, 1)


def test_empty_inputs_do_not_divide_by_zero():
    assert prf(0, 0, 0) == (0.0, 0.0, 0.0)
    assert scores([], [])["overall"] == (0, 0, 0)
    assert "| overall | 0 | 0 | 0 |" in report("x", [], [])


def test_faithfulness_section_only_with_lines():
    lines = [{"grounded": True, "judge": "supported"}, {"grounded": True, "judge": "unsupported"},
             {"grounded": False, "judge": "supported"}]
    assert "2 unsupported / 3 lines" in report("x", [], [], lines)
    assert "Faithfulness" not in report("x", [], [])


def test_by_source_uses_wider_scoreboard_window():
    from eval import by_source
    proposed = [{"t": 34.5, "type": "ft_made", "source": "scoreboard"}, {"t": 10.0, "type": "rebound", "source": "nova"},
                {"t": 50.0, "type": "missed_shot", "source": "nova"}]
    reviewed = [{"t": 31.0, "type": "ft_made", "source": "scoreboard"}, {"t": 50.5, "type": "missed_shot", "source": "nova"}]
    rows = by_source(proposed, reviewed)
    assert rows["scoreboard"][:3] == (1, 0, 0)  # 3.5 s apart: a miss at 2 s, a hit at 6 s
    assert rows["nova"][:3] == (1, 1, 0)
