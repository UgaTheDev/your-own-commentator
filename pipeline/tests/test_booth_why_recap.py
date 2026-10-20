import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import booth  # noqa: E402
import recap  # noqa: E402
import why  # noqa: E402
import write  # noqa: E402

EVENT = {"id": "e7", "t": 30.0, "type": "made_3", "team": "red", "jersey": 23}
STATE = {"eventId": "e7", "t": 30.0, "score": {"red": 31, "blue": 28}, "teamFouls": {"red": 1, "blue": 2},
         "fantasy": {}, "fantasyDelta": {}, "andOne": False}
FACTS = write.build_facts(EVENT, STATE, {"made_3": {"title": "Three-pointer", "body": "Worth 3 points."}}, [])
P = {"lang": "en", "voice": "Matthew", "engine": "neural", "style": "x"}
PERSONAS = {"pbp": P, "analyst": {**P, "voice": "Ruth", "engine": "generative"}}
OK = '{"verdict": "supported"}'


def scripted(monkeypatch, replies):
    prompts = []
    monkeypatch.setattr(write.common, "converse", lambda k, p, **kw: (prompts.append(p), replies.pop(0))[1])
    return prompts


def test_speakable_keeps_only_accepted_unless_dev_flag(capsys):
    evs = [{"id": "a", "status": "accepted"}, {"id": "b", "status": "proposed"}, {"id": "c"}]
    assert [e["id"] for e in write.speakable(evs)] == ["a"]
    assert len(write.speakable(evs, allow_unreviewed=True)) == 3 and "UNREVIEWED" in capsys.readouterr().err


def test_booth_pbp_then_analyst_when_there_is_room(monkeypatch):
    prompts = scripted(monkeypatch, ["Number 23 hits the 3!", OK, "Behind the arc, so it's worth 3.", OK])
    lines, rej = booth.booth_event(PERSONAS, EVENT, FACTS, gap=8.0)
    assert rej == [] and [(x["role"], x["voice"], x["priority"]) for x in lines] == [("pbp", "Matthew", 3),
                                                                                       ("analyst", "Ruth", 0)]
    assert "Number 23 hits the 3!" in prompts[2]  # the analyst reacts to the call


def test_booth_no_analyst_without_room_and_analyst_is_gated(monkeypatch):
    scripted(monkeypatch, ["Number 23 hits the 3!", OK])
    lines, _ = booth.booth_event(PERSONAS, EVENT, FACTS, gap=2.5)
    assert [x["role"] for x in lines] == ["pbp"]
    scripted(monkeypatch, ["Number 23 hits the 3!", OK, "Red leads by 40!", "That's 9 in a row!"])
    lines, rej = booth.booth_event(PERSONAS, EVENT, FACTS, gap=8.0)
    assert [x["role"] for x in lines] == ["pbp"] and rej[0]["role"] == "analyst" and "numbers" in rej[0]["reason"]


def test_why_questions_per_kind():
    assert why.kind_of(EVENT, STATE) == "made_3" and why.kind_of(EVENT, {**STATE, "andOne": True}) == "and_one"
    assert all(1 <= len(qs) <= 3 for qs in why.QUESTIONS.values())
    assert why.persona_for({"booth-en": {"kind": "booth", **PERSONAS}}, "booth-en")["voice"] == "Ruth"


def test_recap_window_and_word_cap(monkeypatch):
    events = [{"id": "e1", "t": 10.0, "type": "made_2", "team": "red", "jersey": None}, EVENT]
    by_id = {"e1": {**STATE, "score": {"red": 28, "blue": 28}}, "e7": STATE}
    assert recap.recap_facts(200, events, by_id) is None  # nothing in [80, 200]
    f = recap.recap_facts(60, events, by_id)
    assert [p["type"] for p in f["plays"]] == ["made_2", "made_3"] and f["state"]["score"] == {"red": 31, "blue": 28}
    scripted(monkeypatch, [" ".join(["word"] * 26), "Red scored 2, then a 3. Red 31, blue 28.", OK])
    monkeypatch.setattr(recap.voice, "synth", lambda line: Path("/c/x.mp3"))
    r, rej = recap.recap_at(60, f, P)
    assert rej is None and r == {"t": 60, "text": "Red scored 2, then a 3. Red 31, blue 28.", "audio": "/c/x.mp3"}
