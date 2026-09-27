import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reel  # noqa: E402


def test_window_ends_two_replay_seconds_after_the_shot():
    assert reel.window(63.5, 62.3) == 1.6  # shot at replay 7.6 s -> keep 1.6..9.6
    assert reel.window(31.0, 31.0) == 4.0  # shot at the event: clamp to the clip end
    assert reel.window(10.0, 5.1) == 0.0  # shot at the very start: keep the first 8 s
    assert reel.window(10.0) == 4.0  # no ball window: the last 8 s


def test_plan_is_in_event_time_order_after_the_title():
    events = {"a": {"t": 50}, "b": {"t": 10}}
    replays = [{"eventId": "a", "duration": 12}, {"eventId": "b", "duration": 12}]
    assert [(r["eventId"], at) for r, _, at in reel.plan(replays, events, {})] == [("b", 4.0), ("a", 12.0)]


def test_card_is_a_full_frame_ppm(tmp_path):
    p = reel.card(["Highlights", reel.score_text({"pink": 20, "blue": 6}, ["pink", "blue"])], tmp_path / "c.ppm")
    header = b"P6 1920 1080 255\n"
    data = p.read_bytes()
    assert data.startswith(header) and len(data) == len(header) + 1920 * 1080 * 3
    assert bytes(reel.FG) in data  # some text was drawn


def test_a_line_that_fails_the_gate_goes_to_answer_never_ungated(monkeypatch):
    calls = []

    def fake_gate(prompt, facts, **kw):
        calls.append(facts)
        return ("Blue free throw: 3 to 11", None) if facts["event"]["id"] == "e2" else ("Pink by 99", "numbers")
    monkeypatch.setattr(reel, "gate", fake_gate)
    monkeypatch.setattr(reel, "answer", lambda q, facts, p: {"text": "Blue three.", "gated": True, "fallback": True})
    ev = [{"id": "e2", "t": 31, "type": "ft_made", "team": "blue", "jersey": None},
          {"id": "e3", "t": 63, "type": "made_3", "team": "blue", "jersey": None}]
    st = {e["id"]: {"score": {"pink": 11, "blue": 3}, "teamFouls": {}, "fantasy": {}, "fantasyDelta": {},
                    "andOne": False} for e in ev}
    out = reel.lines_for(ev, st, {}, [], {"style": "calm", "lang": "en"})
    assert out == {"e2": ("Blue free throw: 3 to 11", "gate"), "e3": ("Blue three.", "answer fallback (gate: numbers)")}
    assert "Pink by 99" not in str(out)
    assert calls[0]["state"]["score"] == {"pink": 11, "blue": 3}  # the gate sees the reviewed facts
