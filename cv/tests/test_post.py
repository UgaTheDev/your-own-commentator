import json
import sys
from pathlib import Path

import jsonschema
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import post  # noqa: E402
import publish_replays  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
H = [1.0] + [0.0] * 63  # an L1-normalised colour histogram


def frag(team, t0, t1, c0, c1, s0=(0, 0), s1=(0, 0), hist=H):
    return {"team": team, "t0": t0, "t1": t1, "c0": c0, "c1": c1, "s0": list(s0), "s1": list(s1),
            "hist": np.array(hist)}


def test_stitch_joins_close_same_team_fragments():
    fr = {1: frag("pink", 0, 2, [5, 5], [6, 5]),
          2: frag("pink", 2.8, 4, [6.5, 5.2], [8, 5]),   # 0.8 s, 0.54 m later -> joins 1
          3: frag("pink", 4.5, 6, [8.2, 5], [9, 5]),     # joins 2, so 1-2-3 is one ID
          4: frag("blue", 2.5, 3, [6.1, 5], [6, 5]),     # other team, never joins
          5: frag("pink", 6.1, 7, [20, 5], [21, 5]),     # 11 m away
          6: frag("pink", 8.0, 9, [9, 5], [9, 5]),       # 2 s gap
          7: frag(None, 6.2, 7, [9, 5], [9, 5])}         # no team (referee) never joins
    m = post.stitch(fr)
    assert m[1] == m[2] == m[3] == 1
    assert {m[4], m[5], m[6], m[7]} == {4, 5, 6, 7}


def test_stitch_pixel_fallback_and_appearance():
    fr = {1: frag("blue", 0, 1, None, None, s1=(100, 500)),
          2: frag("blue", 1.5, 2, None, None, s0=(200, 520)),      # 102 px -> joins
          3: frag("blue", 2.5, 3, None, None, s0=(500, 520)),      # 300 px from 2 -> no
          10: frag("blue", 0, 1, [1, 1], [1, 1]),
          11: frag("blue", 1.2, 2, [1.2, 1], [2, 1], hist=[0.0] * 63 + [1.0])}  # other colours -> no
    m = post.stitch(fr)
    assert m[2] == 1 and m[3] == 3 and m[11] == 11


def test_stitch_each_head_used_once():
    fr = {1: frag("pink", 0, 1, [5, 5], [5, 5]), 2: frag("pink", 0, 1.1, [5, 6], [5, 6]),
          3: frag("pink", 1.3, 2, [5, 5.2], [5, 5])}
    m = post.stitch(fr)
    assert sorted(m.values()).count(m[3]) == 2  # 3 joined exactly one of 1 or 2
    assert m[1] != m[2]


def test_track_lengths():
    assert post.track_lengths([(0, [1, 2]), (1, [1]), (3, [1, 3])]) == {"ids": 3, "median_s": 0.0}
    assert post.track_lengths([(0, [1]), (2, [1])])["median_s"] == 2.0


def box(x, y, c=0.9):
    return [x - 5, y - 5, x + 5, y + 5, c]


def test_filter_ball():
    ts = [i / 10 for i in range(12)]
    cands = [[box(100 + 10 * i, 300)] for i in range(12)]
    cands[3] = [box(1500, 100, 0.95), box(130, 300, 0.2)]   # confident jump: rejected
    cands[5] = []                                          # gap: filled
    cands[6] = [box(160, 300, 0.3)]                        # low confidence: dropped, filled
    cands[9] = [box(900, 900)]                              # isolated false positive ...
    cands[10] = [box(200, 300)]                             # ... one frame only: dropped
    cands[11] = [box(210, 300)]
    out = post.filter_ball(ts, cands)
    assert out[0] == [95, 295, 105, 305]
    assert out[3] is None or abs((out[3][0] + out[3][2]) / 2 - 130) < 1  # not the jump
    np.testing.assert_allclose(out[5], [145, 295, 155, 305])
    np.testing.assert_allclose(out[6], [155, 295, 165, 305])
    np.testing.assert_allclose(out[9], [185, 295, 195, 305])  # FP dropped, gap filled
    assert out[10] == [195, 295, 205, 305]
    assert all(o is None for o in post.filter_ball([0, 0.1], [[], []]))


def test_ball_on_floor():
    feet = [[100, 200, 140, 400]]
    assert post.ball_on_floor([150, 380, 170, 398], feet)
    assert not post.ball_on_floor([150, 200, 170, 220], feet)  # in the air
    assert not post.ball_on_floor([600, 380, 620, 398], feet)  # far from anyone


def sub(name):
    s = json.loads((ROOT / "schemas" / "manifest.schema.json").read_text())
    return {"$defs": s.get("$defs", {}), **s["properties"][name]}


def test_minimap_matches_c3():
    frames = [{"t": 30.0 + i / 10, "players": [{"id": 4, "team": "pink", "jersey": None, "box": [0, 0, .1, .1],
                                                 "court": [9.2, 5.5]},
                                                {"id": 5, "team": None, "jersey": None, "box": [0, 0, .1, .1],
                                                 "court": None}],
               "ball": {"box": [0, 0, .01, .01], "court": [9.0, 5.0] if i % 2 else None}} for i in range(21)]
    m = post.minimap(frames)
    jsonschema.validate(m, sub("minimap"))
    assert m["hz"] == 2 and [f["t"] for f in m["frames"]] == [30.0, 30.5, 31.0, 31.5, 32.0]
    assert m["frames"][0]["players"] == [{"id": 4, "team": "pink", "x": 9.2, "y": 5.5}]
    assert m["frames"][0]["ball"] is None and m["frames"][1]["ball"] == {"x": 9.0, "y": 5.0}


def test_replays_match_c3():
    doc = publish_replays.replays_doc([{"eventId": "e3", "duration": 12.0}], "lake-region-dev")
    jsonschema.validate(doc, sub("replays"))
    assert doc[0]["src"].startswith("https://") and doc[0]["src"].endswith("/lake-region-dev/replays/e3.mp4")
