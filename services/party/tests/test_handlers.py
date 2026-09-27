import json

import pytest

import handlers


class FakeBroadcaster:
    def __init__(self):
        self.sent = []  # list of (connectionId, decoded message dict)

    def send(self, connection_id, data):
        self.sent.append((connection_id, json.loads(data)))


def ws_event(connection_id, body=None):
    e = {"requestContext": {"connectionId": connection_id}}
    if body is not None:
        e["body"] = json.dumps(body)
    return e


def test_connect_is_a_no_op():
    storage = handlers.InMemoryStorage()
    assert handlers.handle_connect(ws_event("c1"), storage) == {"statusCode": 200}


def test_join_creates_room_and_broadcasts_state():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    resp = handlers.handle_default(
        ws_event("c1", {"type": "join", "code": "K7Q2MX", "name": "Kush", "trackId": "rookie-en"}),
        storage, bc,
    )
    assert resp == {"statusCode": 200}
    room = storage.get_room("K7Q2MX")
    assert room["members"]["c1"]["name"] == "Kush"
    assert storage.get_connection_room("c1") == "K7Q2MX"
    assert bc.sent == [("c1", {"type": "state", "members": [
        {"name": "Kush", "trackId": "rookie-en", "points": 0}
    ]})]


def test_invalid_message_rejected():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    resp = handlers.handle_default(ws_event("c1", {"type": "join"}), storage, bc)  # missing required "code"
    assert resp["statusCode"] == 400
    assert storage.get_room("K7Q2MX") is None


def test_unsupported_type_rejected():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    resp = handlers.handle_default(ws_event("c1", {"type": "hello", "clipId": "x"}), storage, bc)
    assert resp["statusCode"] == 400


def test_predict_requires_prior_join():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    resp = handlers.handle_default(
        ws_event("c1", {"type": "predict", "kind": "next_score_team", "value": "pink"}), storage, bc,
    )
    assert resp["statusCode"] == 404


def test_predict_then_playhead_resolves_and_broadcasts():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    handlers.handle_default(
        ws_event("c1", {"type": "join", "code": "K7Q2MX", "name": "Kush", "trackId": "rookie-en"}), storage, bc,
    )
    handlers.handle_default(
        ws_event("c1", {"type": "playhead", "t": 10.0, "trackId": "rookie-en", "paused": False}),
        storage, bc, fetch_manifest=lambda: [],
    )
    handlers.handle_default(
        ws_event("c1", {"type": "predict", "kind": "next_score_team", "value": "pink"}), storage, bc,
    )
    bc.sent.clear()

    events = [{"id": "e1", "t": 15.0, "type": "made_3", "team": "pink", "status": "accepted"}]
    resp = handlers.handle_default(
        ws_event("c1", {"type": "playhead", "t": 20.0, "trackId": "rookie-en", "paused": False}),
        storage, bc, fetch_manifest=lambda: events,
    )
    assert resp == {"statusCode": 200}
    kinds = [m["type"] for _, m in bc.sent]
    assert kinds == ["resolve", "state"]
    resolve_msg = bc.sent[0][1]
    assert resolve_msg["correct"] is True
    assert resolve_msg["eventId"] == "e1"
    state_msg = bc.sent[1][1]
    assert state_msg["members"][0]["points"] == 1


def test_playhead_never_resolves_from_proposed_events():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    handlers.handle_default(
        ws_event("c1", {"type": "join", "code": "K7Q2MX", "name": "Kush", "trackId": "rookie-en"}), storage, bc,
    )
    handlers.handle_default(
        ws_event("c1", {"type": "predict", "kind": "next_score_team", "value": "pink"}), storage, bc,
    )
    bc.sent.clear()
    events = [{"id": "e1", "t": 5.0, "type": "made_3", "team": "pink", "status": "proposed"}]
    handlers.handle_default(
        ws_event("c1", {"type": "playhead", "t": 20.0, "trackId": "rookie-en", "paused": False}),
        storage, bc, fetch_manifest=lambda: events,
    )
    assert bc.sent == []  # nothing resolved, so nothing broadcast


def test_disconnect_removes_member_and_broadcasts_state():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    handlers.handle_default(
        ws_event("c1", {"type": "join", "code": "K7Q2MX", "name": "Kush", "trackId": "rookie-en"}), storage, bc,
    )
    handlers.handle_default(
        ws_event("c2", {"type": "join", "code": "K7Q2MX", "name": "Ana", "trackId": "rookie-en"}), storage, bc,
    )
    bc.sent.clear()
    resp = handlers.handle_disconnect(ws_event("c1"), storage, bc)
    assert resp == {"statusCode": 200}
    room = storage.get_room("K7Q2MX")
    assert "c1" not in room["members"]
    assert storage.get_connection_room("c1") is None
    assert bc.sent == [("c2", {"type": "state", "members": [{"name": "Ana", "trackId": "rookie-en", "points": 0}]})]


def test_disconnect_unknown_connection_is_a_no_op():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    assert handlers.handle_disconnect(ws_event("ghost"), storage, bc) == {"statusCode": 200}


def test_join_after_room_expiry_starts_fresh_room():
    storage = handlers.InMemoryStorage()
    bc = FakeBroadcaster()
    room = handlers.game.new_room("K7Q2MX", now=0.0)
    handlers.game.join(room, "stale", "Old", "rookie-en")
    storage.put_room("K7Q2MX", room)
    storage.link_connection("stale", "K7Q2MX")

    handlers.handle_default(
        ws_event("c1", {"type": "join", "code": "K7Q2MX", "name": "Kush", "trackId": "rookie-en"}), storage, bc,
    )
    fresh = storage.get_room("K7Q2MX")
    assert "stale" not in fresh["members"]
    assert "c1" in fresh["members"]
