"""Third gate (play words) on real lake-region-dev lines from the live manifest, 2026-09-27."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recap  # noqa: E402
import write  # noqa: E402

RULES = json.loads((Path(__file__).resolve().parents[1] / "rules.json").read_text())
STATE = {"score": {"pink": 16, "blue": 6}, "teamFouls": {"pink": 0, "blue": 0}, "fantasy": {}, "fantasyDelta": {},
         "andOne": False}


def facts(type_, team, and_one=False):
    ev = {"id": "e1", "t": 1.0, "type": type_, "team": team, "jersey": None}
    return write.build_facts(ev, {**STATE, "andOne": and_one}, RULES, [])


def recap_facts(*plays):
    events = [{"id": f"e{i}", "t": 200.0 + i, "type": p, "team": team, "jersey": None}
              for i, (p, team) in enumerate(plays)]
    return recap.recap_facts(300, events, {e["id"]: STATE for e in events})


def test_real_failures_are_rejected():
    # booth pbp on a blue turnover; the steal was a separate event the facts don't carry
    assert write.unsupported_plays("A pink player steals, it's 16 to 6.", facts("turnover", "blue"))
    # recap: a rebound is never scored, even though a rebound is in the window
    f = recap_facts(("timeout", "blue"), ("rebound", "blue"), ("made_2", "pink"))
    bad = write.unsupported_plays("The blue team took a timeout, then scored a rebound before the pink team made a "
                                  "two-pointer; the score is now pink 16, blue 6.", f)
    assert bad and "scored a rebound" in bad[0]


GOOD = [
    ("A pink player steals, 11 to 6.", "steal", "pink"),
    ("A blue player turns over the ball, making the score pink 11, blue 6.", "turnover", "blue"),
    ("That's a turnover, meaning blue lost possession without taking a shot.", "turnover", "blue"),
    ("A pink player travels, turnover.", "travel", "pink"),
    ("A pink player took too many steps without dribbling, so it's a traveling violation, and the blue team gets "
     "the ball.", "travel", "pink"),
    ("A blue player calls timeout, score pink 17, blue 6.", "timeout", "blue"),
    ("Blue grabs the rebound, 16 to 6.", "rebound", "blue"),
    ("El jugador rosa cometió pasos; ahora el equipo azul tiene la pelota.", "travel", "pink"),
    ("El equipo rosa pide tiempo fuera para descansar.", "timeout", "pink"),
    ("Parece que el equipo rosa cometió una falta de pasos (travel). Por eso perdieron el balón y el equipo azul "
     "tomó la posesión.", "travel", "pink"),
]


def test_real_good_lines_pass():
    for text, type_, team in GOOD:
        assert write.unsupported_plays(text, facts(type_, team)) == [], text
    f = recap_facts(("travel", "blue"), ("travel", "pink"), ("ft_made", "pink"))
    assert write.unsupported_plays("Pink scored a free throw after two traveling violations; the score is now "
                                   "Pink 17, Blue 6.", f) == []


def test_edge_cases():
    assert write.unsupported_plays("Blue has 2 team fouls.", facts("made_2", "blue")) == []  # a count, not a play
    assert write.unsupported_plays("And-one! The free throw counts too.", facts("made_2", "pink", and_one=True)) == []
    assert write.unsupported_plays("Un robo del equipo rosa.", facts("turnover", "blue"))
    assert write.unsupported_plays("El azul anota un rebote.", facts("rebound", "blue"))
    # a live call may not name a play the rule card merely mentions; a Why answer explaining the rule may
    assert write.unsupported_plays("Un rebote para los azules.", facts("missed_shot", "blue"))
    assert write.unsupported_plays("Either team can grab the rebound.", facts("missed_shot", "blue"), rule_words=True) == []
    assert write.unsupported_plays("पिंक टीम का रिबाउंड।", facts("missed_shot", "blue"))  # real rookie-hi line
    assert write.unsupported_plays("蓝队球员走步犯规，球权转交粉队。", facts("travel", "blue")) == []
    # wrong team (real fantasy-en lines on blue plays)
    assert write.unsupported_plays("A pink player turns over.", facts("turnover", "blue"))
    assert write.unsupported_plays("A pink player misses, no fantasy change.", facts("missed_shot", "blue"))
    assert write.unsupported_plays("El equipo rosa pierde el balón.", facts("turnover", "blue"))
    assert write.unsupported_plays("Pink stole it, and blue turned it over.", facts("steal", "pink")) == []  # implied
    # answer.facts_at: plays in `recent` count
    f = {"event": {"type": "turnover"}, "state": None, "rule": None, "recent": [{"type": "steal"}]}
    assert write.unsupported_plays("Pink stole it.", f) == []


def test_gate_retries_on_play_word(monkeypatch):
    replies = ["A pink player steals!", "Blue turns it over.", '{"verdict": "supported"}']
    monkeypatch.setattr(write.common, "converse", lambda *a, **k: replies.pop(0))
    text, reason = write.gate("p", facts("turnover", "blue"))
    assert (text, reason) == ("Blue turns it over.", None)


def test_team_less_event_rejects_invented_team_but_allows_score():
    # found in the integrator's spot check: team-less timeouts credited to pink
    facts = {"event": {"id": "e11", "t": 1, "type": "timeout", "team": None, "jersey": None},
             "state": {"score": {"pink": 14, "blue": 6}}}
    assert write.unsupported_plays("A pink player calls a timeout.", facts)
    assert write.unsupported_plays("That timeout lets the pink team regroup.", facts)
    assert write.unsupported_plays("El equipo rosa pide tiempo muerto.", facts)
    assert write.unsupported_plays("Timeout on the floor, pink leads 14 to 6.", facts) == []
