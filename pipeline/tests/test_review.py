import http.client
import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import review  # noqa: E402

CLIP = {"teams": ["red", "blue"], "start_score": {"red": 10, "blue": 8}, "final_score": {"red": 12, "blue": 8}}
VIDEO = bytes(range(256)) * 4  # 1024 fake bytes


def ev(i, t, type, team="red", jersey=None):
    return {"id": f"e{i}", "t": t, "type": type, "team": team, "jersey": jersey}


@pytest.fixture
def srv(tmp_path, monkeypatch):
    d = tmp_path / "game1"
    d.mkdir()
    common.save(d / "clip.json", CLIP)
    (d / "source.mp4").write_bytes(VIDEO)
    common.save(d / "events.proposed.json", [ev(1, 3, "missed_shot")])
    (tmp_path / "secret.txt").write_text("SECRET")
    monkeypatch.setattr(common, "DATA", tmp_path)
    server = review.make_server("game1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield d, server.server_port
    server.shutdown()
    server.server_close()


def req(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request(method, path, body=body, headers=headers or {})  # http.client sends the path verbatim
    r = c.getresponse()
    out = r.status, dict(r.getheaders()), r.read()
    c.close()
    return out


def post(port, events):
    return req(port, "POST", "/events", json.dumps(events), {"Content-Type": "application/json"})


def test_clip_dir_reads_data_at_call_time(srv):
    d, _ = srv
    assert common.clip_dir("game1") == d


def test_events_fall_back_to_proposed(srv):
    _, port = srv
    status, _, body = req(port, "GET", "/events")
    assert status == 200 and json.loads(body) == [ev(1, 3, "missed_shot")]


def test_post_valid_saves_reviewed_and_is_served(srv):
    d, port = srv
    events = [ev(2, 9, "made_2", jersey=4), ev(1, 3, "timeout", None)]
    status, _, body = post(port, events)
    assert status == 200 and json.loads(body) == {"ok": True, "warning": None}
    saved = common.load(d / "events.reviewed.json")
    assert [e["id"] for e in saved] == ["e1", "e2"]
    assert json.loads(req(port, "GET", "/events")[2]) == saved
    assert not (d / "events.reviewed.json.tmp").exists()


@pytest.mark.parametrize("bad", [
    [ev(1, 3, "dunk")],
    [ev(1, -1, "made_2")],
    [ev(1, "3", "made_2")],
    [ev(1, 3, "made_2", "green")],
    [ev(1, 3, "made_2", None)],
    [ev(1, 3, "made_2", jersey="4")],
    [ev(1, 3, "made_2"), ev(1, 4, "made_2")],
    {"not": "a list"},
])
def test_post_invalid_is_rejected(srv, bad):
    d, port = srv
    status, _, body = post(port, bad)
    assert status == 400 and json.loads(body)["error"]
    assert not (d / "events.reviewed.json").exists()


def test_post_bad_json_and_oversize(srv):
    _, port = srv
    assert req(port, "POST", "/events", "{nope")[0] == 400
    assert req(port, "POST", "/events", "x", {"Content-Length": str(review.MAX_BODY + 1)})[0] == 413


def test_final_score_mismatch_saves_with_warning(srv):
    d, port = srv
    status, _, body = post(port, [ev(1, 3, "made_3")])
    assert status == 200 and "final_score" in json.loads(body)["warning"]
    assert (d / "events.reviewed.json").exists()


def test_video_range(srv):
    _, port = srv
    status, h, body = req(port, "GET", "/video", headers={"Range": "bytes=100-199"})
    assert status == 206 and h["Content-Range"] == "bytes 100-199/1024" and body == VIDEO[100:200]
    status, h, body = req(port, "GET", "/video", headers={"Range": "bytes=1000-"})
    assert status == 206 and h["Content-Range"] == "bytes 1000-1023/1024" and body == VIDEO[1000:]
    status, h, body = req(port, "GET", "/video", headers={"Range": "bytes=-24"})
    assert status == 206 and body == VIDEO[-24:]
    assert req(port, "GET", "/video", headers={"Range": "bytes=2000-"})[0] == 416
    status, h, body = req(port, "GET", "/video")
    assert status == 200 and body == VIDEO and h["Accept-Ranges"] == "bytes"


@pytest.mark.parametrize("path", ["/../secret.txt", "/../x", "/video/../../secret.txt", "/../../etc/passwd",
                                  "/clip.json", "/game1/clip.json", "//etc/passwd", "/%2e%2e/secret.txt"])
def test_no_path_traversal(srv, path):
    _, port = srv
    status, _, body = req(port, "GET", path)
    assert status == 404 and b"SECRET" not in body and b"root:" not in body


def test_bad_clip_id_rejected(srv):
    with pytest.raises(ValueError):
        review.make_server("../game1", 0)
