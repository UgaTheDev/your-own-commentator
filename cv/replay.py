"""Telestration replays + minimap for a dev clip (contract C3 `replays` / `minimap` data).

    ~/.venvs/yoc-cv/bin/python cv/replay.py lake-region lake-region-dev --stills e3 e6 e42

Per scoring event: 6 s of source ending 1 s after the event, every source frame written at
half rate (60 fps -> 30 fps = 0.5x), 1080p H.264 +faststart with a quiet crowd bed. Draws only
what tracks.json shows: a team-coloured ellipse under each tracked player, and a ring plus a
1 s arrow trail on the 1-2 players nearest the ball in the second before the event. No jersey
numbers, names or text beyond "REPLAY". Upload/URLs: cv/publish_replays.py.
"""
import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

import post
from track import DATA, HERE, apply_h

SCORING = ("made_2", "made_3", "ft_made")
COL = {"pink": (180, 60, 255), "blue": (255, 150, 30), None: (210, 210, 210)}
PRE, POST, SLOW = 5.0, 1.0, 0.5


def interp(samples, t, max_gap=0.35):
    """samples: sorted [(t, value array)]. Linear value at t between bracketing samples no more
    than max_gap apart, the nearest one within 0.06 s, else None."""
    ts = [s[0] for s in samples]
    j = int(np.searchsorted(ts, t))
    if 0 < j < len(ts) and ts[j] - ts[j - 1] <= max_gap:
        w = (t - ts[j - 1]) / (ts[j] - ts[j - 1])
        return (1 - w) * samples[j - 1][1] + w * samples[j][1]
    near = [s for s in samples[max(0, j - 1):j + 1] if abs(s[0] - t) <= 0.06]
    return near[0][1] if near else None


def nearest_to_ball(frames, t0, t1, W, H, k=2, max_px=260):
    """Ids of up to k players nearest the ball (box centre to ball centre, mean px) over tracks
    frames in [t0, t1]; only players seen with the ball in >= 3 of those frames."""
    d = {}
    for f in frames:
        if not (t0 <= f["t"] <= t1) or not f["ball"]:
            continue
        bx, by, bw, bh = f["ball"]["box"]
        bc = np.array([(bx + bw / 2) * W, (by + bh / 2) * H])
        for p in f["players"]:
            x, y, w, h = p["box"]
            d.setdefault(p["id"], []).append(np.hypot(*(np.array([(x + w / 2) * W, (y + h / 2) * H]) - bc)))
    best = sorted((np.mean(v), i) for i, v in d.items() if len(v) >= 3 and np.mean(v) <= max_px)
    return [i for _, i in best[:k]]


def render(ev, tracks, Cs, src, out, W=1920, H=1080, audio=None, stills=None):
    te = ev["t"]
    t0, t1 = te - PRE, te + POST
    fr = [f for f in tracks["frames"] if t0 - 0.5 <= f["t"] <= t1 + 0.5]
    ts = np.array([f["t"] for f in fr])
    px = lambda b: np.array([b[0] * W, b[1] * H, (b[0] + b[2]) * W, (b[1] + b[3]) * H])  # noqa: E731
    per, team = {}, {}
    for f in fr:
        for p in f["players"]:
            per.setdefault(p["id"], []).append((f["t"], px(p["box"])))
            team[p["id"]] = p["team"]
    hi = nearest_to_ball(fr, te - 1.0, te, W, H)
    Csamp = [(f["t"], Cs[round(f["t"], 3)]) for f in fr if round(f["t"], 3) in Cs]

    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t0 * fps))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
           "-r", str(fps * SLOW), "-i", "-"]
    if audio:
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-af", "volume=0.25", "-c:a", "aac", "-b:a", "96k",
                "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = round((t1 - t0) * fps)
    for k in range(n):
        ok, img = cap.read()
        if not ok:
            break
        t = t0 + k / fps
        C = interp(Csamp, t, max_gap=0.2)
        for tid, s in per.items():
            b = interp(s, t)
            if b is None:
                continue
            x1, y1, x2, y2 = b
            cx, cy, w = int((x1 + x2) / 2), int(y2), x2 - x1
            if tid in hi:
                cv2.ellipse(img, (cx, cy), (int(w * .85), int(w * .3)), 0, 0, 360, (255, 255, 255), 5, cv2.LINE_AA)
                if C is not None:  # 1 s trail: past feet -> pan-stable px -> today's px
                    Cinv = np.linalg.inv(C)
                    pts = [apply_h(Cinv @ Cs[round(st, 3)], [((q[0] + q[2]) / 2, q[3])])[0]
                           for st, q in s if t - 1.0 <= st < t and round(st, 3) in Cs] + [np.array([cx, cy])]
                    pts = np.array(pts, np.int32)
                    if len(pts) >= 3 and np.hypot(*(pts[-1] - pts[0])) > 12:
                        cv2.polylines(img, [pts[:-1]], False, (255, 255, 255), 4, cv2.LINE_AA)
                        cv2.arrowedLine(img, tuple(map(int, pts[-2])), tuple(map(int, pts[-1])), (255, 255, 255), 4,
                                        cv2.LINE_AA, tipLength=0.6)
            cv2.ellipse(img, (cx, cy), (int(w * .6), int(w * .2)), 0, 0, 360, COL[team[tid]], 3, cv2.LINE_AA)
        cv2.rectangle(img, (32, 32), (212, 84), (20, 20, 20), -1)
        cv2.putText(img, "REPLAY", (46, 72), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
        if stills and k == round((PRE - 0.5) * fps):
            cv2.imwrite(str(stills), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError(f"ffmpeg failed for {ev['id']}")
    return {"eventId": ev["id"], "frames": n, "duration": round(n / (fps * SLOW), 2), "highlighted": hi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("track_clip")
    ap.add_argument("dev_clip")
    ap.add_argument("--stills", nargs="*", default=[])
    ap.add_argument("--stills-dir", default=str(HERE.parent / ".playwright-mcp"))
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    tracks = json.loads((DATA / a.track_clip / "tracks.json").read_text())
    Cs = {round(x["t"], 3): np.array(x["C"]) for x in
          json.loads((DATA / a.track_clip / "render" / "cv-homography.json").read_text())}
    dev = DATA / a.dev_clip
    (dev / "minimap.json").write_text(json.dumps(post.minimap(tracks["frames"]), separators=(",", ":")))
    print(dev / "minimap.json")
    out_dir = dev / "render" / "replays"
    out_dir.mkdir(parents=True, exist_ok=True)
    events = [e for e in json.loads((dev / "events.reviewed.json").read_text()) if e["type"] in SCORING]
    audio = DATA / "ambience" / "crowd.flac"
    rows = []
    for e in events:
        if a.only and e["id"] not in a.only:
            continue
        still = Path(a.stills_dir) / f"replay-{e['id']}.jpg" if e["id"] in a.stills else None
        r = render(e, tracks, Cs, DATA / a.track_clip / "source.mp4", out_dir / f"{e['id']}.mp4",
                   audio=audio if audio.exists() else None, stills=still)
        rows.append(r)
        print(json.dumps(r), still or "")
    (out_dir / "index.json").write_text(json.dumps(rows))


if __name__ == "__main__":
    main()
