"""Pure watch-party logic: rooms, members, predictions, resolution.

No AWS, no I/O — handlers.py wires this to DynamoDB and API Gateway. Everything here operates on
plain dicts so state round-trips through JSON (DynamoDB blob, tests) without a translation layer.

Grounding rule (C6): resolve_predictions() only ever looks at events the caller passes in, and only
consults ones with status == "accepted" — callers must fetch those from the manifest, never invent them.
"""
import random
import time

CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # base32, matches ^[A-Z2-7]{6}$ in messages.schema.json
ROOM_TTL_SECONDS = 2 * 60 * 60  # rooms expire 2h after creation (V2-PLAN Sprint 1)
SCORING_EVENT_TYPES = {"made_2", "made_3", "ft_made"}


def new_code(rng=random):
    """A random 6-char session code. Not used by join (the code comes from the TV/C4 session);
    kept for callers (e.g. a future host-side room precreate) that need one."""
    return "".join(rng.choice(CODE_ALPHABET) for _ in range(6))


def new_room(code, now=None):
    now = now if now is not None else time.time()
    return {
        "code": code,
        "playhead": 0.0,
        "members": {},  # connectionId -> {name, trackId, points, prediction}
        "createdAt": now,
        "expiresAt": now + ROOM_TTL_SECONDS,
    }


def is_expired(room, now=None):
    now = now if now is not None else time.time()
    return now >= room["expiresAt"]


def join(room, connection_id, name, track_id):
    room["members"][connection_id] = {
        "name": (name or "player")[:32], "trackId": track_id, "points": 0, "prediction": None,
    }


def leave(room, connection_id):
    room["members"].pop(connection_id, None)


def predict(room, connection_id, value):
    """Sets the member's one open prediction, at the room's current playhead.

    A second predict() before the first resolves replaces it (the old guess is simply discarded) —
    ponytail: simplest reading of "one open prediction per member at a time" that needs no queue.
    """
    member = room["members"].get(connection_id)
    if member is None:
        return False
    member["prediction"] = {"kind": "next_score_team", "value": value, "t": room["playhead"]}
    return True


def set_playhead(room, t):
    room["playhead"] = t


def resolve_predictions(room, manifest_events):
    """Resolves every open prediction against accepted scoring events up to the room's playhead.

    Each open prediction resolves against the FIRST accepted made_2/made_3/ft_made event with
    t > prediction.t and t <= room["playhead"]; 1 point if event.team == prediction.value. Only
    status == "accepted" events are ever consulted. Returns the list of {connectionId, predictionId,
    correct, eventId} just resolved (points and cleared predictions are already applied to `room`).
    """
    playhead = room["playhead"]
    scoring = sorted(
        (e for e in manifest_events if e.get("status") == "accepted" and e.get("type") in SCORING_EVENT_TYPES),
        key=lambda e: e["t"],
    )
    resolved = []
    for connection_id, member in room["members"].items():
        pred = member.get("prediction")
        if pred is None:
            continue
        hit = next((e for e in scoring if e["t"] > pred["t"] and e["t"] <= playhead), None)
        if hit is None:
            continue
        correct = hit.get("team") == pred["value"]
        if correct:
            member["points"] += 1
        member["prediction"] = None
        resolved.append({
            "connectionId": connection_id,
            "predictionId": f"{connection_id}:{pred['t']}",
            "correct": correct,
            "eventId": hit["id"],
        })
    return resolved


def state_message(room):
    return {"type": "state", "members": [
        {"name": m["name"], "trackId": m["trackId"], "points": m["points"]} for m in room["members"].values()
    ]}
