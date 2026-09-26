import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import write  # noqa: E402

EVENT = {"id": "e7", "t": 30.0, "type": "made_3", "team": "red", "jersey": 23, "confidence": 0.8, "status": "accepted"}
STATE = {"eventId": "e7", "t": 30.0, "score": {"red": 31, "blue": 28}, "teamFouls": {"red": 1, "blue": 2},
         "fantasy": {"red#23": 6}, "fantasyDelta": {"red#23": 3}, "andOne": False}
RULES = {"made_3": {"title": "Three-pointer", "body": "Worth 3 points."}, "and_one": {"title": "And-one", "body": "x"}}
ROSTER = [{"jersey": 23, "team": "red", "name": "Sam"}, {"jersey": 23, "team": "blue", "name": "Ali"}]
PERSONA = {"lang": "en", "voice": "Matthew", "engine": "neural", "style": "calm"}


def scripted(monkeypatch, replies):
    calls = []

    def fake(model_key, prompt, **kw):
        calls.append((model_key, prompt))
        return replies.pop(0)

    monkeypatch.setattr(write.common, "converse", fake)
    return calls


def facts():
    return write.build_facts(EVENT, STATE, RULES, ROSTER)


def test_facts_drop_review_fields_and_pick_the_right_team_player():
    f = facts()
    assert "confidence" not in f["event"] and "status" not in f["event"]
    assert f["player"]["name"] == "Sam"  # same jersey on the other team must not leak "Ali"
    assert f["rule"]["title"] == "Three-pointer"
    assert write.build_facts(EVENT, {**STATE, "andOne": True}, RULES, ROSTER)["rule"]["title"] == "And-one"
    assert "player" not in write.build_facts({**EVENT, "jersey": None}, STATE, RULES, ROSTER)


def test_budget_scales_with_gap_and_language():
    assert write.budget(4, "en") == (10, "words")
    assert write.budget(4, "zh") == (16, "characters")
    assert write.budget(0.2, "en") == (3, "words")  # floor


def test_good_line_passes_both_gates(monkeypatch):
    calls = scripted(monkeypatch, ["Sam hits the 3! Red 31, Blue 28.", '{"verdict": "supported", "reason": ""}'])
    line, rej = write.write_line("rookie-en", PERSONA, EVENT, facts(), 5)
    assert rej is None and line["text"].startswith("Sam") and line["priority"] == 3
    assert [c[0] for c in calls] == ["write", "judge"]


def test_invented_number_is_retried_then_dropped(monkeypatch):
    calls = scripted(monkeypatch, ["Red 33!", "Red leads 40 to 28!"])
    line, rej = write.write_line("rookie-en", PERSONA, EVENT, facts(), 5)
    assert line is None and "40" in rej["reason"]
    assert [c[0] for c in calls] == ["write", "write"]  # judge never called for digit failures
    assert "previous line was rejected" in calls[1][1]


def test_judge_rejection_then_recovery(monkeypatch):
    scripted(monkeypatch, ["Sam's fifth three tonight!", '{"verdict": "unsupported", "reason": "streak"}',
                           "Sam from deep, that's 3!", '{"verdict": "supported"}'])
    line, rej = write.write_line("rookie-en", PERSONA, EVENT, facts(), 5)
    assert rej is None and line["text"] == "Sam from deep, that's 3!"


def test_unparseable_judge_fails_closed(monkeypatch):
    scripted(monkeypatch, ["Sam scores!", "sure looks fine", "Sam scores!", "yes"])
    line, rej = write.write_line("rookie-en", PERSONA, EVENT, facts(), 5)
    assert line is None and "unparseable" in rej["reason"]
