import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import answer  # noqa: E402

MANIFEST = {
    "events": [{"id": "e1", "t": 10.0, "type": "ft_made", "team": "blue", "jersey": None, "ruleCardId": "ft_made"},
               {"id": "e2", "t": 40.0, "type": "made_3", "team": "blue", "jersey": 23, "ruleCardId": "made_3"}],
    "state": [{"eventId": "e1", "t": 10.0, "score": {"pink": 11, "blue": 3}},
              {"eventId": "e2", "t": 40.0, "score": {"pink": 11, "blue": 6}}],
    "ruleCards": {"ft_made": {"title": "Free throw", "body": "1 point."}, "made_3": {"title": "Three-pointer", "body": "3 points."}},
}
PERSONA = {"lang": "en", "style": "calm"}


def scripted(monkeypatch, replies):
    monkeypatch.setattr(answer.common, "converse", lambda *a, **k: replies.pop(0))


def test_facts_at_playhead():
    assert answer.facts_at(5.0, MANIFEST)["event"] is None
    f = answer.facts_at(45.0, MANIFEST)
    assert f["event"]["id"] == "e2" and f["state"]["score"] == {"pink": 11, "blue": 6}
    assert f["rule"]["title"] == "Three-pointer" and len(f["recent"]) == 1  # e1 is older than 30 s


def test_gated_answer(monkeypatch):
    scripted(monkeypatch, ["Blue hit a 3, so it's 11 to 6.", '{"verdict": "supported"}'])
    r = answer.answer("who's winning?", answer.facts_at(45.0, MANIFEST), PERSONA)
    assert r == {"text": "Blue hit a 3, so it's 11 to 6.", "gated": True, "fallback": False}


def test_two_failures_fall_back_to_facts_only_template(monkeypatch):
    scripted(monkeypatch, ["Blue is up 30 to 2!", "Number 9 fouled."])  # both fail the digit gate; judge never runs
    r = answer.answer("why?", answer.facts_at(45.0, MANIFEST), PERSONA)
    assert r["fallback"] and r["gated"]
    assert r["text"] == "The last play was Three-pointer by the blue team. The score is pink 11, blue 6."


def test_fallback_before_any_event_invents_nothing():
    assert answer.fallback(answer.facts_at(0.0, MANIFEST), "es") == "Solo puedo hablar de lo que pasó en la cancha."
