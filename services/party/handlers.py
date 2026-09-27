"""Lambda handlers for the watch-party WebSocket API ($connect, $disconnect, join/predict/playhead via $default).

Pure `handle_*` functions take injected `storage` (a tiny duck-typed interface — get_room/put_room/
link_connection/get_connection_room/unlink_connection), `broadcaster` (post_to_connection, injectable)
and `fetch_manifest` (returns the deployment's manifest events), so tests can pass fakes with no AWS.
The `lambda_*` functions at the bottom are the real Lambda entrypoints: thin wiring only, not unit tested.

Assumption (undocumented gap in C6): the join/playhead messages carry no clipId, so this deployment
resolves every room against ONE configured manifest (MANIFEST_URL env var, default = the Phase 0
fixture). Fine for a single demo game; if multiple concurrent games are ever needed, that's a contract
change for the integrator, not something this stream can add unilaterally.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

import jsonschema

import game

# Deploy bundles a copy at services/party/schemas/ (see build.sh) since SAM's CodeUri is this dir
# alone; local/dev runs (tests, `sam local`) fall back to the repo's schemas/ two levels up.
_BUNDLED = Path(__file__).resolve().parent / "schemas" / "messages.schema.json"
_REPO = Path(__file__).resolve().parents[2] / "schemas" / "messages.schema.json"
SCHEMA_PATH = _BUNDLED if _BUNDLED.exists() else _REPO
MANIFEST_URL = os.environ.get(
    "MANIFEST_URL", "https://d2og06dnam3owj.cloudfront.net/fixture-v2/manifest.json"
)

_schema = None


def _load_schema():
    global _schema
    if _schema is None:
        _schema = json.loads(SCHEMA_PATH.read_text())
    return _schema


def validate_message(body):
    """Raises jsonschema.ValidationError if `body` matches none of the C4-C6 message shapes."""
    jsonschema.validate(instance=body, schema=_load_schema())


def fetch_manifest_events(url=MANIFEST_URL):
    """Real fetch: stdlib only (no `requests` in this venv) — GET the manifest, return its events list."""
    with urllib.request.urlopen(url, timeout=5) as resp:
        manifest = json.load(resp)
    return manifest_events(manifest)


def manifest_events(manifest):
    """A published manifest contains only speakable (accepted) events (CONTRACTS.md C3), so they settle predictions."""
    return [{**e, "status": "accepted"} for e in manifest.get("events", [])]


def broadcast(broadcaster, room, message):
    data = json.dumps(message).encode()
    for connection_id in room["members"]:
        broadcaster.send(connection_id, data)


# ---- pure handlers (unit tested) -------------------------------------------------

def handle_connect(event, storage):
    return {"statusCode": 200}


def handle_disconnect(event, storage, broadcaster):
    connection_id = event["requestContext"]["connectionId"]
    code = storage.get_connection_room(connection_id)
    storage.unlink_connection(connection_id)
    if not code:
        return {"statusCode": 200}
    room = storage.get_room(code)
    if not room:
        return {"statusCode": 200}
    game.leave(room, connection_id)
    storage.put_room(code, room)
    broadcast(broadcaster, room, game.state_message(room))
    return {"statusCode": 200}


def handle_default(event, storage, broadcaster, fetch_manifest=fetch_manifest_events):
    connection_id = event["requestContext"]["connectionId"]
    try:
        body = json.loads(event.get("body") or "{}")
        validate_message(body)
    except (json.JSONDecodeError, jsonschema.ValidationError) as e:
        return {"statusCode": 400, "body": f"bad message: {e}"}

    msg_type = body["type"]
    if msg_type == "join":
        return _handle_join(connection_id, body, storage, broadcaster)
    if msg_type == "predict":
        return _handle_predict(connection_id, body, storage)
    if msg_type == "playhead":
        return _handle_playhead(connection_id, body, storage, broadcaster, fetch_manifest)
    return {"statusCode": 400, "body": f"unsupported type for party route: {msg_type}"}


def _get_room_for_connection(connection_id, storage):
    code = storage.get_connection_room(connection_id)
    if not code:
        return None, None
    room = storage.get_room(code)
    if not room or game.is_expired(room):
        return code, None
    return code, room


def _handle_join(connection_id, body, storage, broadcaster):
    code = body["code"]
    room = storage.get_room(code)
    if room is None or game.is_expired(room):
        room = game.new_room(code)
    game.join(room, connection_id, body.get("name"), body.get("trackId"))
    storage.link_connection(connection_id, code)
    storage.put_room(code, room)
    broadcast(broadcaster, room, game.state_message(room))
    return {"statusCode": 200}


def _handle_predict(connection_id, body, storage):
    code, room = _get_room_for_connection(connection_id, storage)
    if room is None:
        return {"statusCode": 404, "body": "not joined to a room"}
    game.predict(room, connection_id, body["value"])
    storage.put_room(code, room)
    return {"statusCode": 200}


def _handle_playhead(connection_id, body, storage, broadcaster, fetch_manifest):
    code, room = _get_room_for_connection(connection_id, storage)
    if room is None:
        return {"statusCode": 404, "body": "not joined to a room"}
    game.set_playhead(room, body["t"])
    events = fetch_manifest()
    resolved = game.resolve_predictions(room, events)
    storage.put_room(code, room)
    for r in resolved:
        broadcast(broadcaster, room, {
            "type": "resolve", "predictionId": r["predictionId"],
            "correct": r["correct"], "eventId": r["eventId"],
        })
    if resolved:
        broadcast(broadcaster, room, game.state_message(room))
    return {"statusCode": 200}


# ---- storage backends -------------------------------------------------------------

class InMemoryStorage:
    """Test fake: same interface as DynamoStorage, no AWS, no TTL sweep (is_expired() is checked on read)."""

    def __init__(self):
        self.rooms = {}
        self.connections = {}

    def get_room(self, code):
        return self.rooms.get(code)

    def put_room(self, code, room):
        self.rooms[code] = room

    def link_connection(self, connection_id, code):
        self.connections[connection_id] = code

    def get_connection_room(self, connection_id):
        return self.connections.get(connection_id)

    def unlink_connection(self, connection_id):
        self.connections.pop(connection_id, None)


class DynamoStorage:
    """Real backend: one item per room (JSON blob) in ROOMS_TABLE, one row per live connection in
    CONNECTIONS_TABLE. Both tables set `expiresAt` (epoch seconds) as their TTL attribute (template.yaml)."""

    def __init__(self, rooms_table, connections_table):
        self._rooms = rooms_table
        self._connections = connections_table

    def get_room(self, code):
        item = self._rooms.get_item(Key={"code": code}).get("Item")
        return json.loads(item["state"]) if item else None

    def put_room(self, code, room):
        self._rooms.put_item(Item={"code": code, "state": json.dumps(room), "expiresAt": int(room["expiresAt"])})

    def link_connection(self, connection_id, code):
        self._connections.put_item(Item={
            "connectionId": connection_id, "code": code, "expiresAt": int(time.time()) + game.ROOM_TTL_SECONDS,
        })

    def get_connection_room(self, connection_id):
        item = self._connections.get_item(Key={"connectionId": connection_id}).get("Item")
        return item["code"] if item else None

    def unlink_connection(self, connection_id):
        self._connections.delete_item(Key={"connectionId": connection_id})


class Broadcaster:
    """Wraps ApiGatewayManagementApi.post_to_connection so tests can inject a fake with a `.send`."""

    def __init__(self, client):
        self.client = client

    def send(self, connection_id, data):
        try:
            self.client.post_to_connection(ConnectionId=connection_id, Data=data)
        except self.client.exceptions.GoneException:
            pass  # stale connection; its $disconnect (or the next broadcast's failure) will clean it up


# ---- real Lambda entrypoints (thin wiring, not unit tested) -----------------------

def _real_storage():
    import boto3
    ddb = boto3.resource("dynamodb")
    return DynamoStorage(ddb.Table(os.environ["ROOMS_TABLE"]), ddb.Table(os.environ["CONNECTIONS_TABLE"]))


def _real_broadcaster(event):
    import boto3
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    client = boto3.client("apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}")
    return Broadcaster(client)


def lambda_connect(event, context):
    return handle_connect(event, _real_storage())


def lambda_disconnect(event, context):
    return handle_disconnect(event, _real_storage(), _real_broadcaster(event))


def lambda_default(event, context):
    return handle_default(event, _real_storage(), _real_broadcaster(event))


def lambda_handler(event, context):
    """Single entrypoint for all routes (the template wires $connect, $disconnect and $default to one function)."""
    route = event.get("requestContext", {}).get("routeKey")
    if route == "$connect":
        return lambda_connect(event, context)
    if route == "$disconnect":
        return lambda_disconnect(event, context)
    return lambda_default(event, context)
