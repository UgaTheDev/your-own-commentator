"""The frozen contracts: the fixture and real outputs must validate against schemas/."""
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from state import EVENT_TYPES  # noqa: E402

SCHEMAS = ROOT / "schemas"


def schema(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text())


def test_fixture_manifest_validates():
    m = json.loads((ROOT / "fixtures" / "manifest-v2.json").read_text())
    jsonschema.validate(m, schema("manifest"))
    for key in ("replays", "minimap", "recaps", "questions"):
        assert m[key], f"fixture must exercise {key}"
    assert any(t.get("kind") == "booth" for t in m["tracks"])


def test_event_schema_matches_state_event_types():
    assert set(schema("event")["properties"]["type"]["enum"]) == EVENT_TYPES


@pytest.mark.parametrize("bad", [{"jersey": "23"}, {"status": "maybe"}, {"source": "guess"}, {"t": -1}])
def test_event_schema_rejects_contract_violations(bad):
    ev = {"id": "e1", "t": 1.0, "type": "made_2", "team": "pink", "jersey": None}
    jsonschema.validate(ev, schema("event"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**ev, **bad}, schema("event"))


def test_messages_cover_every_protocol_type():
    s = schema("messages")
    types = {alt["properties"]["type"]["const"] for alt in s["oneOf"]}
    assert types == {"hello", "session", "playhead", "answer", "join", "start", "stop", "transcript", "predict", "resolve", "state"}
    jsonschema.validate({"type": "playhead", "t": 3.2, "trackId": "rookie-en", "paused": False}, s)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"type": "session", "code": "abc"}, s)
