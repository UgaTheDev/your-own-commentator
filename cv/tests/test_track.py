import json
import sys
from pathlib import Path

import cv2
import jsonschema
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import track  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def patch(bgr, frac=1.0, other=(20, 20, 20)):
    """40x20 crop, `frac` of it in colour bgr, the rest `other`."""
    img = np.full((40, 20, 3), other, np.uint8)
    img[: int(40 * frac)] = bgr
    return img


def test_team_colours():
    assert track.team_of(patch((180, 60, 255))) == "pink"      # hot pink
    assert track.team_of(patch((220, 150, 40))) == "blue"      # light blue
    assert track.team_of(patch((90, 40, 20))) == "blue"        # navy
    stripes = np.zeros((40, 20, 3), np.uint8)
    stripes[::4] = 255
    assert track.team_of(stripes) is None                      # referee
    assert track.team_of(patch((150, 170, 200))) is None       # skin / beige
    assert track.team_of(patch((180, 60, 255), frac=0.05)) is None  # too little colour
    assert track.team_of(np.zeros((0, 0, 3), np.uint8)) is None


def test_vote():
    assert track.vote(["pink", "pink", None, "blue", "pink"]) == "pink"
    assert track.vote(["pink", "blue"]) is None
    assert track.vote([None, None]) is None


def test_chain_recovers_synthetic_pan():
    """A textured image panned by known translations: chained G must map the same
    world point to the same court coordinate in every frame."""
    rng = np.random.default_rng(0)
    world = cv2.GaussianBlur((rng.random((700, 1400)) * 255).astype(np.uint8), (3, 3), 0)
    shifts = [0, 12, 30, 55, 80]
    feats = [track.features(cv2.resize(world[100:640, s:s + 960], None, fx=1, fy=1), [], 0, 0)
             for s in shifts]
    # features() doubles coordinates (it expects a half-res frame), so work in 2x px
    G0 = np.diag([0.01, 0.01, 1.0])  # frame-0 px -> "court"
    out = track.chain(feats, {0: G0})
    assert all(G is not None for G, _ in out)
    for (G, steps), s in zip(out, shifts):
        world_px = np.array([[600.0, 400.0]])            # frame-0 px
        cur_px = world_px - [2 * s, 0]                    # same world point in frame i
        np.testing.assert_allclose(track.apply_h(G, cur_px), track.apply_h(G0, world_px), atol=0.05)
    assert [st for _, st in out] == [0, 1, 2, 3, 4]


def test_compose_and_best_of():
    G = np.eye(3)
    M = np.array([[1, 0, 5], [0, 1, 0], [0, 0, 1.0]])   # prev -> curr shifts x by +5
    np.testing.assert_allclose(track.apply_h(track.compose(G, M), [[15, 0]]), [[10, 0]])
    a, b = np.eye(3), 2 * np.eye(3)
    assert track.best_of([(a, 3), (None, 1e9)], [(b, 1), (b, 2)])[0] is b
    assert track.best_of([(a, 3), (None, 1e9)], [(b, 1), (b, 2)])[1] is b


def test_writer_matches_schema(tmp_path):
    frames = [{"t": 30.0, "players": [{"id": 4, "team": "pink", "jersey": None,
                                       "box": track.norm_box([100, 200, 160, 380], 1920, 1080),
                                       "court": [9.2, 5.5]},
                                      {"id": 7, "team": None, "jersey": None,
                                       "box": track.norm_box([-5, 0, 40, 1100], 1920, 1080), "court": None}],
               "ball": {"box": track.norm_box([900, 500, 920, 520], 1920, 1080), "court": None}},
              {"t": 30.1, "players": [], "ball": None}]
    p = tmp_path / "tracks.json"
    track.write_tracks(p, 10, {"w": 25.6, "h": 15.24}, frames)
    schema = json.loads((ROOT / "schemas" / "tracks.schema.json").read_text())
    jsonschema.validate(json.loads(p.read_text()), schema)
