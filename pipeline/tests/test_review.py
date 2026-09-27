import http.client
import json
import re
import shutil
import subprocess
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


def test_events_without_source_or_status_are_backward_compatible(srv):
    """Old files (pre-C1) have no source/status; review must still accept and round-trip them."""
    d, port = srv
    events = [ev(1, 3, "made_2")]  # no source, no status
    status, _, body = post(port, events)
    assert status == 200 and json.loads(body) == {"ok": True, "warning": None}
    saved = common.load(d / "events.reviewed.json")
    assert saved[0].get("source") is None and saved[0].get("status") is None


def test_post_rejected_when_event_fails_schema(srv):
    """confidence out of [0,1] is invalid per schemas/event.schema.json, on top of the existing checks."""
    d, port = srv
    status, _, body = post(port, [{**ev(1, 3, "made_2"), "confidence": 5}])
    assert status == 400 and json.loads(body)["error"]
    assert not (d / "events.reviewed.json").exists()


def test_human_added_event_accepted(srv):
    d, port = srv
    status, _, body = post(port, [{**ev(1, 3, "made_2"), "source": "human", "status": "accepted"}])
    assert status == 200 and json.loads(body) == {"ok": True, "warning": None}


def cv(i, t, type, team="red"):
    return {**ev(i, t, type, team), "confidence": 0.6, "source": "cv", "status": "accepted"}  # status is forced back


def test_merge_cv_dedupes_by_type_team_and_time():
    base = [ev(1, 10.0, "made_2"), ev(2, 30.0, "rebound", "blue")]
    merged = review.merge_cv(base, [cv(1, 11.5, "made_2"),           # same play (dt 1.5 s): dropped
                                    cv(9, 12.5, "made_2"),           # dt 2.5 s: kept
                                    cv(8, 30.5, "rebound", "red"),   # other team: kept
                                    cv(7, 30.5, "steal", "blue")])   # other type: kept
    assert [(e["id"], e["t"]) for e in merged] == [("e1", 10.0), ("e9", 12.5), ("e2", 30.0), ("e8", 30.5), ("e7", 30.5)]
    assert all(e["source"] == "cv" and e["status"] == "proposed" for e in merged if e["id"] in ("e7", "e8", "e9"))
    assert base == [ev(1, 10.0, "made_2"), ev(2, 30.0, "rebound", "blue")]  # input untouched


def test_merge_cv_renames_colliding_ids():
    merged = review.merge_cv([ev(1, 10.0, "made_2")], [cv(1, 50.0, "steal"), cv(1, 60.0, "block")])
    assert sorted(e["id"] for e in merged) == ["cv-cv-e1", "cv-e1", "e1"]


def test_events_serve_cv_merged_without_writing(srv):
    d, port = srv
    common.save(d / "events.cv.json", [cv(5, 20.0, "steal")])
    before = sorted(p.name for p in d.iterdir())
    got = json.loads(req(port, "GET", "/events")[2])
    assert [(e["id"], e.get("source"), e.get("status")) for e in got] == [("e1", None, None), ("e5", "cv", "proposed")]
    assert sorted(p.name for p in d.iterdir()) == before  # nothing written until the human saves


def test_accept_all_scoreboard_only_touches_proposed_scoreboard_events():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    html = Path(review.__file__).with_name("review.html").read_text()
    fn = re.search(r"function pendingScoreboard\(events\) \{.*?\n\}", html, re.S).group(0)
    events = [{"id": "a", "source": "scoreboard", "status": "proposed"}, {"id": "b", "source": "scoreboard", "status": "accepted"},
              {"id": "c", "source": "cv", "status": "proposed"}, {"id": "d", "source": "nova"}, {"id": "e", "source": "scoreboard"}]
    js = f"{fn}\nconsole.log(JSON.stringify(pendingScoreboard({json.dumps(events)}).map(e => e.id)))"
    out = subprocess.run([node, "-e", js], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == ["a", "e"]
    assert 'k === "a" && ev.shiftKey' in html and "confirm(" in html  # the shortcut asks before accepting
