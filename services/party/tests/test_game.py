import game


def accepted(id, t, type, team):
    return {"id": id, "t": t, "type": type, "team": team, "status": "accepted"}


def test_new_code_matches_pattern():
    code = game.new_code()
    assert len(code) == 6
    assert all(c in game.CODE_ALPHABET for c in code)


def test_join_and_leave():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    assert room["members"]["c1"] == {"name": "Kush", "trackId": "rookie-en", "points": 0, "prediction": None}
    game.leave(room, "c1")
    assert "c1" not in room["members"]


def test_join_truncates_long_name():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "x" * 100, "rookie-en")
    assert len(room["members"]["c1"]["name"]) == 32


def test_one_open_prediction_per_member_second_replaces_first():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    game.set_playhead(room, 10.0)
    game.predict(room, "c1", "pink")
    game.set_playhead(room, 20.0)
    game.predict(room, "c1", "blue")
    assert room["members"]["c1"]["prediction"] == {"kind": "next_score_team", "value": "blue", "t": 20.0}


def test_resolve_awards_point_on_matching_team():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    game.set_playhead(room, 10.0)
    game.predict(room, "c1", "pink")
    game.set_playhead(room, 70.0)
    events = [accepted("e1", 63.5, "made_3", "pink")]
    resolved = game.resolve_predictions(room, events)
    assert resolved == [{"connectionId": "c1", "predictionId": "c1:10.0", "correct": True, "eventId": "e1"}]
    assert room["members"]["c1"]["points"] == 1
    assert room["members"]["c1"]["prediction"] is None


def test_resolve_no_point_on_wrong_team():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    game.set_playhead(room, 10.0)
    game.predict(room, "c1", "pink")
    game.set_playhead(room, 70.0)
    events = [accepted("e1", 63.5, "made_3", "blue")]
    resolved = game.resolve_predictions(room, events)
    assert resolved[0]["correct"] is False
    assert room["members"]["c1"]["points"] == 0


def test_resolve_only_from_first_scoring_event_after_prediction_t():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    game.set_playhead(room, 10.0)
    game.predict(room, "c1", "blue")
    game.set_playhead(room, 100.0)
    events = [
        accepted("e0", 5.0, "made_2", "blue"),   # before the prediction was made: ignored
        accepted("e1", 30.0, "made_2", "pink"),  # first event after t=10: this is the one that resolves it
        accepted("e2", 40.0, "made_3", "blue"),  # later: never consulted
    ]
    resolved = game.resolve_predictions(room, events)
    assert resolved[0]["eventId"] == "e1"
    assert resolved[0]["correct"] is False


def test_resolve_never_uses_proposed_events():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    game.set_playhead(room, 10.0)
    game.predict(room, "c1", "pink")
    game.set_playhead(room, 100.0)
    events = [{"id": "e1", "t": 20.0, "type": "made_3", "team": "pink", "status": "proposed"}]
    resolved = game.resolve_predictions(room, events)
    assert resolved == []
    assert room["members"]["c1"]["points"] == 0
    assert room["members"]["c1"]["prediction"] is not None  # still open


def test_resolve_ignores_non_scoring_event_types():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    game.set_playhead(room, 10.0)
    game.predict(room, "c1", "pink")
    game.set_playhead(room, 100.0)
    events = [accepted("e1", 20.0, "foul", "pink"), accepted("e2", 25.0, "made_2", "pink")]
    resolved = game.resolve_predictions(room, events)
    assert resolved[0]["eventId"] == "e2"


def test_resolve_not_yet_reached_playhead_stays_open():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    game.set_playhead(room, 10.0)
    game.predict(room, "c1", "pink")
    game.set_playhead(room, 15.0)
    events = [accepted("e1", 20.0, "made_2", "pink")]  # t > playhead
    resolved = game.resolve_predictions(room, events)
    assert resolved == []
    assert room["members"]["c1"]["prediction"] is not None


def test_room_expiry():
    room = game.new_room("K7Q2MX", now=1000.0)
    assert not game.is_expired(room, now=1000.0 + game.ROOM_TTL_SECONDS - 1)
    assert game.is_expired(room, now=1000.0 + game.ROOM_TTL_SECONDS)


def test_state_message_shape():
    room = game.new_room("K7Q2MX")
    game.join(room, "c1", "Kush", "rookie-en")
    assert game.state_message(room) == {
        "type": "state", "members": [{"name": "Kush", "trackId": "rookie-en", "points": 0}]
    }
