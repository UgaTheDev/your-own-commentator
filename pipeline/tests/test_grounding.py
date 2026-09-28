import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from write import unsupported_digits  # noqa: E402

FACTS = {
    "event": {"id": "e17", "t": 41.5, "type": "made_3", "team": "red", "jersey": 23},
    "state": {"score": {"red": 31, "blue": 28}, "fantasy": {"red#23": 4.4}},
    "rule": {"title": "Three-point shot", "body": "A shot from behind the arc is worth 3 points."},
}


def test_grounded_line_passes():
    assert unsupported_digits("Number 23 hits the 3! Red leads 31 to 28.", FACTS) == set()
    assert unsupported_digits("That's 4.4 fantasy points for 23.", FACTS) == set()


def test_invented_number_and_wrong_jersey_rejected():
    assert unsupported_digits("Red leads 33 to 28.", FACTS) == {"33"}
    assert unsupported_digits("Number 32 drains it!", FACTS) == {"32"}


def test_bookkeeping_fields_are_not_facts():
    # t=41.5 and id e17 must not license saying "41" or "17"
    assert unsupported_digits("41 seconds in, 17 straight points!", FACTS) == {"41", "17"}


def test_other_languages_and_digit_scripts():
    assert unsupported_digits("¡Triple del 23! Rojo gana 31 a 28.", FACTS) == set()
    assert unsupported_digits("Rojo gana 31 a 29.", FACTS) == {"29"}
    assert unsupported_digits("4,4 puntos de fantasía", FACTS) == set()  # es decimal comma
    assert unsupported_digits("२३ नंबर, स्कोर ३१-२८", FACTS) == set()  # Devanagari digits
    assert unsupported_digits("स्कोर ३५-२८", FACTS) == {"35"}
    assert unsupported_digits("２３号投中三分", FACTS) == set()  # full-width digits


def test_no_numbers_passes():
    assert unsupported_digits("What a shot!", FACTS) == set()


def test_spelled_numbers_are_checked_too():
    # found in review: "white forty, maroon thirty" when the state was 39-30
    facts = {"state": {"score": {"white": 39, "maroon": 30}}}
    assert unsupported_digits("making the score white forty, maroon thirty", facts) == {"40"}
    assert unsupported_digits("white thirty-nine, maroon thirty", facts) == set()
    assert unsupported_digits("blanco cuarenta y cuatro, granate treinta", facts) == {"44"}
    assert unsupported_digits("比分四十四比三十", facts) == {"44"}
    assert unsupported_digits("El equipo anota una canasta", facts) == set()  # 'una' is an article, not a number
