"""Offline clean-up of the detection pass (pure functions, tested in tests/test_post.py):
ID stitching, ball filtering, the floor heuristic and the C3 minimap."""
import numpy as np


def fragments(frames, team):
    """frames: [(t, [player dict with id, court, spx, hist])]. Returns {id: fragment} with
    the first/last time, court xy, pan-stable px and the mean colour histogram."""
    fr = {}
    for t, ps in frames:
        for p in ps:
            f = fr.setdefault(p["id"], {"team": team.get(p["id"]), "t0": t, "c0": p["court"], "s0": p["spx"],
                                        "hs": []})
            f.update(t1=t, c1=p["court"], s1=p["spx"])
            if p.get("hist") is not None:
                f["hs"].append(p["hist"])
    for f in fr.values():
        f["hist"] = np.mean(f.pop("hs"), 0) if f["hs"] else None
    return fr


def bhattacharyya(a, b):
    """0 = identical L1-normalised histograms, 1 = disjoint."""
    return float(np.sqrt(max(0.0, 1 - np.sum(np.sqrt(np.asarray(a) * np.asarray(b))))))


def stitch(frags, max_gap=1.5, max_m=2.0, max_px=150, max_app=0.6):
    """Join fragment b onto a when both have the same non-null team, b starts 0-max_gap s after
    a ends, b's first position is within max_m metres (court) or max_px pan-stable px (no
    homography) of a's last, and their colour histograms are close. Greedy on a cost that mixes
    all three; each tail and each head is used once, so chains stay time-ordered.
    Returns {fragment id: stitched id (the chain's first fragment)}."""
    pairs = []
    for ia, a in frags.items():
        if a["team"] is None:
            continue
        for ib, b in frags.items():
            if ib == ia or b["team"] != a["team"]:
                continue
            gap = b["t0"] - a["t1"]
            if not 0 < gap <= max_gap:
                continue
            if a["c1"] is not None and b["c0"] is not None:
                d = float(np.hypot(*np.subtract(b["c0"], a["c1"]))) / max_m
            else:
                d = float(np.hypot(*np.subtract(b["s0"], a["s1"]))) / max_px
            if d > 1:
                continue
            app = bhattacharyya(a["hist"], b["hist"]) if a["hist"] is not None and b["hist"] is not None else max_app
            if app > max_app:
                continue
            pairs.append((d + gap / max_gap + app / max_app, ia, ib))
    nxt, used_head = {}, set()
    for _, ia, ib in sorted(pairs):
        if ia not in nxt and ib not in used_head:
            nxt[ia] = ib
            used_head.add(ib)
    remap = {}
    for root in frags:
        if root in used_head:
            continue
        cur = root
        while cur is not None:
            remap[cur] = root
            cur = nxt.get(cur)
    return remap


def track_lengths(frames):
    """frames: [(t, [id, ...])] -> {'ids': n, 'median_s': median first-to-last span}."""
    span = {}
    for t, ids in frames:
        for i in ids:
            a, _ = span.get(i, (t, t))
            span[i] = (a, t)
    lens = [b - a for a, b in span.values()]
    return {"ids": len(span), "median_s": round(float(np.median(lens)), 2) if lens else 0.0}


def filter_ball(ts, cands, min_conf=0.5, vmax=1500.0, slack=40.0, min_run=3, max_gap=0.6):
    """ts: frame times; cands[i]: [[x1, y1, x2, y2, conf], ...] in pan-stable px.
    Keeps the most confident candidate >= min_conf per frame, links consecutive picks into runs
    while the centre moves <= vmax px/s (+ slack) with gaps <= max_gap s, drops runs shorter
    than min_run (isolated false positives), then fills gaps <= max_gap linearly.
    Returns a box [x1, y1, x2, y2] or None per frame."""
    ctr = lambda b: np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])  # noqa: E731
    ok = lambda i, j: (ts[j] - ts[i] <= max_gap and  # noqa: E731
                       np.hypot(*(ctr(pick[j]) - ctr(pick[i]))) <= vmax * (ts[j] - ts[i]) + slack)
    pick = [max((c for c in cs if c[4] >= min_conf), key=lambda c: c[4], default=None) for cs in cands]
    runs, cur = [], []
    for i, b in enumerate(pick):
        if b is None:
            continue
        if cur and ok(cur[-1], i):
            cur.append(i)
        else:
            if cur:
                runs.append(cur)
            cur = [i]
    if cur:
        runs.append(cur)
    out = [None] * len(ts)
    kept = sorted(i for r in runs if len(r) >= min_run for i in r)
    for i in kept:
        out[i] = [float(v) for v in pick[i][:4]]
    for i, j in zip(kept, kept[1:]):
        if j - i > 1 and ok(i, j):
            for k in range(i + 1, j):
                w = (ts[k] - ts[i]) / (ts[j] - ts[i])
                out[k] = [float((1 - w) * a + w * b) for a, b in zip(pick[i][:4], pick[j][:4])]
    return out


def ball_on_floor(ball, players, tol=0.12):
    """True when the ball's bottom is level with some player's feet (within tol x that player's
    height) and horizontally near them: the only time its floor projection means anything.
    ponytail: a ball rolling alone on the floor reads as airborne; fine for a minimap."""
    bx, by = (ball[0] + ball[2]) / 2, ball[3]
    for x1, y1, x2, y2 in players:
        w, h = x2 - x1, y2 - y1
        if x1 - w <= bx <= x2 + w and abs(by - y2) <= tol * h:
            return True
    return False


def minimap(frames, hz=2):
    """C3 minimap from C2 frames: nearest frame to each 1/hz tick, players with a court
    position only, ball only when it has one (i.e. on the floor)."""
    if not frames:
        return {"hz": hz, "frames": []}
    ts = np.array([f["t"] for f in frames])
    out = []
    for tick in np.arange(np.ceil(ts[0] * hz) / hz, ts[-1] + 1e-9, 1 / hz):
        i = int(np.argmin(np.abs(ts - tick)))
        if abs(ts[i] - tick) > 0.5 / hz:
            continue
        f = frames[i]
        b = f["ball"]
        out.append({"t": round(float(tick), 2),
                    "players": [{"id": p["id"], "team": p["team"], "x": p["court"][0], "y": p["court"][1]}
                                for p in f["players"] if p["court"] is not None],
                    "ball": {"x": b["court"][0], "y": b["court"][1]} if b and b["court"] else None})
    return {"hz": hz, "frames": out}
