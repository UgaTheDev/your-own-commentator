"""Stream A: detect + track + team + court position -> tracks.json (contract C2).

    ~/.venvs/yoc-cv/bin/python cv/track.py lake-region            # whole clip
    ~/.venvs/yoc-cv/bin/python cv/track.py lake-region --detect-only

The slow detection pass is cached under data/<clip>/render/cv-raw-*; re-running without
--redetect only redoes homography, stitching (post.py) and ball filtering.

RF-DETR Medium (Apache-2.0) on COCO person/sports ball, ByteTrack via supervision,
team by torso colour, court position via a hand-calibrated keyframe homography chained
frame to frame with ORB + RANSAC. Output is visuals-only until a human reviews it
(CONTRACTS.md grounding rule).
"""
import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("YOC_DATA", HERE.parent / "data"))
PERSON, BALL = 1, 37  # COCO ids in rfdetr.assets.coco_classes

# ---------- team by jersey colour (pure, tested) ----------

def team_of(bgr_crop, min_frac=0.12, ratio=2.0):
    """'pink' | 'blue' | None from a torso crop. Stripes/black/white/skin fall to None.

    ponytail: fixed HSV ranges tuned to this clip's two kits; k-means per clip if a new
    game has other colours.
    """
    if bgr_crop is None or bgr_crop.size == 0:
        return None
    h, s, v = cv2.split(cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2HSV))
    n = h.size
    pink = (((h >= 145) | (h <= 4)) & (s >= 70) & (v >= 110)).sum() / n
    blue = ((h >= 95) & (h <= 128) & (s >= 60) & (v >= 40)).sum() / n
    if pink >= min_frac and pink >= ratio * blue:
        return "pink"
    if blue >= min_frac and blue >= ratio * pink:
        return "blue"
    return None


def torso(frame, xyxy):
    x1, y1, x2, y2 = xyxy
    w, h = x2 - x1, y2 - y1
    return frame[int(y1 + .18 * h):int(y1 + .5 * h), int(x1 + .25 * w):int(x2 - .25 * w)]


def vote(labels):
    """Majority non-null label for one track, or None."""
    c = Counter(l for l in labels if l)
    if not c:
        return None
    lab, k = c.most_common(1)[0]
    return lab if k >= 0.6 * sum(c.values()) else None

# ---------- homography chaining (pure parts tested) ----------

def apply_h(H, pts):
    p = np.asarray(pts, float).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(p, H).reshape(-1, 2)


def compose(G_prev, M):
    """G maps image px -> court m; M maps prev px -> curr px. Returns G for curr."""
    return G_prev @ np.linalg.inv(M)


ORB = cv2.ORB_create(3000)
BF = cv2.BFMatcher(cv2.NORM_HAMMING)


def features(gray_half, boxes, h_full, w_full):
    """ORB on a half-res frame, masking players and the score graphic (bottom-left)."""
    m = np.full(gray_half.shape, 255, np.uint8)
    hh, ww = gray_half.shape
    m[int(hh * .82):, :int(ww * .2)] = 0
    for x1, y1, x2, y2 in boxes:
        m[max(0, int(y1 / 2) - 4):int(y2 / 2) + 4, max(0, int(x1 / 2) - 4):int(x2 / 2) + 4] = 0
    kp, des = ORB.detectAndCompute(gray_half, m)
    pts = np.float32([k.pt for k in kp]) * 2 if kp else np.zeros((0, 2), np.float32)
    return pts, des


def match(fa, fb, min_inl=60, min_ratio=0.35):
    """Homography a->b in full-res px, or None when too few / too inconsistent matches."""
    (pa, da), (pb, db) = fa, fb
    if da is None or db is None or len(pa) < 20 or len(pb) < 20:
        return None, 0.0
    good = [m for m, n in (p for p in BF.knnMatch(da, db, k=2) if len(p) == 2) if m.distance < .75 * n.distance]
    if len(good) < min_inl:
        return None, 0.0
    src = pa[[m.queryIdx for m in good]]
    dst = pb[[m.trainIdx for m in good]]
    M, inl = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if M is None:
        return None, 0.0
    r = inl.sum() / len(good)
    return (M if inl.sum() >= min_inl and r >= min_ratio else None), float(r)


def chain(feats, keyframes, max_gap=10):
    """One pass over feats in the given order. keyframes: {index: G}. Returns
    [(G or None, steps since keyframe)] per position. A failed match keeps the last
    good frame as reference; after max_gap failures the chain is lost until a keyframe."""
    out, ref, G_ref, steps, miss = [], None, None, 0, 0
    for i, f in enumerate(feats):
        if i in keyframes:
            ref, G_ref, steps, miss = f, keyframes[i], 0, 0
            out.append((G_ref, 0))
            continue
        if G_ref is None:
            out.append((None, 1e9))
            continue
        M, _ = match(ref, f)
        if M is None:
            miss += 1
            if miss > max_gap:
                G_ref = None
            out.append((None, 1e9))
            continue
        G_ref, ref, steps, miss = compose(G_ref, M), f, steps + 1, 0
        out.append((G_ref, steps))
    return out


def best_of(fwd, bwd):
    """Per frame, the valid G that is fewer chain steps from its keyframe (less drift)."""
    return [(a if a[1] <= b[1] else b)[0] for a, b in zip(fwd, bwd)]


def stable_boxes(C, xyxy):
    """Map boxes through homography C, returning axis-aligned xyxy of the warped corners."""
    x1, y1, x2, y2 = np.asarray(xyxy, float).T
    pts = apply_h(C, np.stack([np.c_[x1, y1], np.c_[x2, y1], np.c_[x1, y2], np.c_[x2, y2]], 1).reshape(-1, 2))
    pts = pts.reshape(-1, 4, 2)
    return np.c_[pts[:, :, 0].min(1), pts[:, :, 1].min(1), pts[:, :, 0].max(1), pts[:, :, 1].max(1)]


def on_court(xy, court, mx=1.5, my=0.6):
    return xy is not None and -mx <= xy[0] <= court["w"] + mx and -my <= xy[1] <= court["h"] + my

def norm_box(xyxy, W, H):
    """Pixel xyxy -> normalized [x, y, w, h], clipped to the frame (C2 box)."""
    x1, y1, x2, y2 = np.clip(xyxy, 0, [W, H, W, H])
    return [round(float(v), 4) for v in (x1 / W, y1 / H, (x2 - x1) / W, (y2 - y1) / H)]

# ---------- writer (tested against the schema) ----------

def write_tracks(path, fps, court, frames):
    doc = {"fps": fps, "court": court, "frames": frames}
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(doc, separators=(",", ":")))
    tmp.replace(path)
    return doc

# ---------- detection pass (slow, cached) ----------

def hist(crop):
    """16x4 hue/sat histogram of a torso crop, L1-normalised (appearance term for stitching)."""
    if crop is None or crop.size == 0:
        return None
    h = cv2.calcHist([cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 4], [0, 180, 0, 256]).ravel()
    return [round(float(v), 4) for v in h / max(h.sum(), 1)]


def detect(src, t0, t1, fps, model_name):
    """RF-DETR + pan-compensated ByteTrack over [t0, t1]. Returns (raw, feats, W, H); raw
    keeps every ball candidate and the pan transform C so the post pass can be re-run cheaply."""
    import rfdetr
    import supervision as sv
    model = {"nano": rfdetr.RFDETRNano, "small": rfdetr.RFDETRSmall,
             "medium": rfdetr.RFDETRMedium, "large": rfdetr.RFDETRLarge}[model_name]()
    tracker = sv.ByteTrack(track_activation_threshold=0.3, lost_track_buffer=90, frame_rate=int(fps))
    cap = cv2.VideoCapture(str(src))
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    step = max(1, round(src_fps / fps))
    f0 = round(t0 * src_fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0)
    fi, raw, feats, C, t_start = f0, [], [], np.eye(3), time.time()
    while fi <= t1 * src_fps:
        if (fi - f0) % step:
            fi += 1
            if not cap.grab():
                break
            continue
        ok, frame = cap.read()
        if not ok:
            break
        t = round(fi / src_fps, 3)
        fi += 1
        det = model.predict(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), threshold=0.2)
        ppl = det[(det.class_id == PERSON) & (det.confidence >= 0.25)]
        gray = cv2.cvtColor(cv2.resize(frame, None, fx=.5, fy=.5), cv2.COLOR_BGR2GRAY)
        feats.append(features(gray, ppl.xyxy, 0, 0))
        # camera-motion compensation: track in a pan-stable pixel frame so ByteTrack's
        # IoU matching survives pans (C maps current px -> first-frame px)
        M = match(feats[-2], feats[-1])[0] if len(feats) > 1 else None
        if M is not None:
            C = C @ np.linalg.inv(M)  # ponytail: a failed match holds C; small jump for one frame
        ppl.data["orig"] = ppl.xyxy.copy()
        if len(ppl):
            ppl.xyxy = stable_boxes(C, ppl.xyxy)
        ppl = tracker.update_with_detections(ppl)
        balls = det[det.class_id == BALL]
        raw.append({"t": t, "C": C.tolist(), "n_det": int((det.class_id == PERSON).sum()),
                    "players": [{"id": int(tid), "xyxy": [round(float(v), 1) for v in xy],
                                 "team": team_of(torso(frame, xy)), "hist": hist(torso(frame, xy))}
                                for xy, tid in zip(ppl.data["orig"], ppl.tracker_id)],
                    "balls": [[round(float(v), 1) for v in xy] + [round(float(c), 3)]
                              for xy, c in zip(balls.xyxy, balls.confidence)]})
        if len(raw) % 200 == 0:
            print(f"{len(raw)} frames, t={t:.0f}, {time.time() - t_start:.0f}s", file=sys.stderr, flush=True)
    return raw, feats, float(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


def save_cache(stem, raw, feats, W, H):
    """raw -> JSON, ORB features -> one npz of concatenated arrays + offsets."""
    Path(str(stem) + ".json").write_text(json.dumps({"W": W, "H": H, "raw": raw}, separators=(",", ":")))
    off = np.cumsum([0] + [len(p) for p, _ in feats])
    des = [d if d is not None else np.zeros((0, 32), np.uint8) for _, d in feats]
    np.savez(str(stem) + ".npz", off=off, pts=np.concatenate([p for p, _ in feats]), des=np.concatenate(des))


def load_cache(stem):
    doc = json.loads(Path(str(stem) + ".json").read_text())
    z = np.load(str(stem) + ".npz")
    off, pts, des = z["off"], z["pts"], z["des"]
    feats = [(pts[a:b], des[a:b] if b > a else None) for a, b in zip(off, off[1:])]
    for r in doc["raw"]:
        r["C"] = np.array(r["C"])
    return doc["raw"], feats, doc["W"], doc["H"]

# ---------- post pass (fast) ----------

def homographies(raw, feats, calib, anchor_every=3):
    """Per-frame image->court G: keyframes, direct re-anchoring to the nearest-in-time
    matching keyframe on every `anchor_every`-th frame, then chained forward and backward."""
    ts = [r["t"] for r in raw]
    kf = {}
    for k in calib["keyframes"]:
        i = min(range(len(raw)), key=lambda j: abs(ts[j] - k["t"]))
        if abs(ts[i] - k["t"]) > 0.2:
            continue  # keyframe outside this run
        img = np.float32([p["px"] for p in k["points"]])
        crt = np.float32([p["court"] for p in k["points"]])
        kf[i] = cv2.findHomography(img, crt, 0)[0]  # least squares over all landmarks
    anchors = dict(kf)
    for i in range(0, len(raw), anchor_every):
        if i in kf:
            continue
        for k in sorted(kf, key=lambda k: abs(k - i)):
            M, _ = match(feats[k], feats[i], min_inl=100, min_ratio=0.4)
            if M is not None:
                anchors[i] = compose(kf[k], M)
                break
    n = len(raw)
    fwd = chain(feats, anchors)
    bwd = chain(feats[::-1], {n - 1 - i: G for i, G in anchors.items()})[::-1]
    return best_of(fwd, bwd), len(anchors)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--t0", type=float, default=0)
    ap.add_argument("--t1", type=float, default=1e9)
    ap.add_argument("--fps", type=float, default=10)
    ap.add_argument("--model", default="medium", choices=["nano", "small", "medium", "large"])
    ap.add_argument("--redetect", action="store_true", help="ignore the cached detection pass")
    ap.add_argument("--detect-only", action="store_true")
    ap.add_argument("--ball-conf", type=float, default=0.5)
    a = ap.parse_args()

    d = DATA / a.clip
    (d / "render").mkdir(exist_ok=True)
    stem = d / "render" / f"cv-raw-{a.t0:g}-{a.t1:g}"
    t_start = time.time()
    if Path(str(stem) + ".npz").exists() and not a.redetect:
        raw, feats, W, Hh = load_cache(stem)
    else:
        raw, feats, W, Hh = detect(d / "source.mp4", a.t0, a.t1, a.fps, a.model)
        save_cache(stem, raw, feats, W, Hh)
        for r in raw:
            r["C"] = np.array(r["C"])
    det_s = time.time() - t_start
    if a.detect_only:
        print(f"cached {len(raw)} frames in {det_s:.0f}s -> {stem}")
        return

    import post
    calib = json.loads((HERE / "calib" / f"{a.clip}.json").read_text())
    court = calib["court"]
    Gs, n_anchor = homographies(raw, feats, calib)
    n = len(raw)

    # 1. keep plausible on-court people, with court xy and pan-stable feet px
    team_raw = {}
    for r in raw:
        for p in r["players"]:
            team_raw.setdefault(p["id"], []).append(p["team"])
    team = {tid: vote(v) for tid, v in team_raw.items()}
    kept = []
    for r, G in zip(raw, Gs):
        ps = []
        for p in r["players"]:
            x1, y1, x2, y2 = p["xyxy"]
            if y2 - y1 < 1.5 * (x2 - x1):
                continue  # ponytail: seated bench/crowd; a crouching player can be lost too
            xy = apply_h(G, [((x1 + x2) / 2, y2)])[0].round(2).tolist() if G is not None else None
            if G is not None and not on_court(xy, court):
                continue  # fans, bench, table crew
            if G is None and team[p["id"]] is None:
                continue  # can't tell a referee from a fan without the court
            ps.append({**p, "court": xy, "spx": apply_h(r["C"], [((x1 + x2) / 2, y2)])[0].tolist()})
        kept.append(ps)

    # 2. stitch fragments into longer IDs (same team, close in time, space and colour)
    ts = [r["t"] for r in raw]
    before = post.track_lengths([(t, [p["id"] for p in ps]) for t, ps in zip(ts, kept)])
    remap = post.stitch(post.fragments(list(zip(ts, kept)), team))
    sid = lambda tid: remap.get(tid, tid)  # noqa: E731
    after = post.track_lengths([(t, [sid(p["id"]) for p in ps]) for t, ps in zip(ts, kept)])
    team_s = {}
    for ps in kept:
        for p in ps:
            team_s.setdefault(sid(p["id"]), []).append(team[p["id"]])
    team_s = {k: vote(v) for k, v in team_s.items()}

    # 3. ball: confident, physically consistent, short gaps filled, court only near the floor
    cands = [[list(stable_boxes(r["C"], [b[:4]])[0]) + [b[4]] for b in r["balls"]] for r in raw]
    ball_s = post.filter_ball(ts, cands, min_conf=a.ball_conf)

    frames = []
    for i, (r, G, ps) in enumerate(zip(raw, Gs, kept)):
        players = [{"id": sid(p["id"]), "team": team_s[sid(p["id"])], "jersey": None,
                    "box": norm_box(p["xyxy"], W, Hh), "court": p["court"]} for p in ps]
        ball = None
        if ball_s[i] is not None:
            bx = stable_boxes(np.linalg.inv(r["C"]), [ball_s[i]])[0]
            floor = post.ball_on_floor(bx, [p["xyxy"] for p in ps])
            # the floor projection is only right when the ball is on the floor
            bxy = apply_h(G, [((bx[0] + bx[2]) / 2, bx[3])])[0].round(2).tolist() if G is not None and floor else None
            ball = {"box": norm_box(bx, W, Hh), "court": bxy}
        frames.append({"t": r["t"], "players": players, "ball": ball})

    out = d / "tracks.json"
    write_tracks(out, a.fps, court, frames)
    # debug sidecar for render_debug.py / replay.py (not part of C2): image->court H and pan C
    (d / "render" / "cv-homography.json").write_text(json.dumps(
        [{"t": r["t"], "H": G.tolist() if G is not None else None, "C": r["C"].tolist()} for r, G in zip(raw, Gs)]))
    nd = [r["n_det"] for r in raw]
    stats = {
        "frames": n, "t": [ts[0], ts[-1]], "detect_or_load_s": round(det_s, 1),
        "total_s": round(time.time() - t_start, 1),
        "person_dets_per_frame": [min(nd), round(float(np.mean(nd)), 1), max(nd)],
        "players_kept_per_frame": round(float(np.mean([len(f["players"]) for f in frames])), 1),
        "homography_valid_pct": round(100 * sum(G is not None for G in Gs) / n, 1),
        "anchored_frames": n_anchor,
        "ball_raw_frames_pct": round(100 * sum(bool(r["balls"]) for r in raw) / n, 1),
        "ball_frames_pct": round(100 * sum(f["ball"] is not None for f in frames) / n, 1),
        "ball_court_pct": round(100 * sum(bool(f["ball"] and f["ball"]["court"]) for f in frames) / n, 1),
        "before": before, "after": after,
        "teams": Counter(team_s.values()),
    }
    print(json.dumps(stats, default=str))
    print(out)


if __name__ == "__main__":
    main()
