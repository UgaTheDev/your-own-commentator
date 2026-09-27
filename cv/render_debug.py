"""Evidence for tracks.json: debug MP4, annotated stills and a top-down minimap.

    ~/.venvs/yoc-cv/bin/python cv/render_debug.py lake-region --t0 55 --t1 65 \
        --stills 40 63 80 --stills-dir .playwright-mcp
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from track import DATA, apply_h

COL = {"pink": (180, 60, 255), "blue": (255, 140, 0), None: (200, 200, 200)}
PX = 30  # minimap px per metre


def court_lines(w, h):
    """Court outline, both lanes and the half-court line as polylines in metres."""
    lanes = [[(0, 5.79), (5.79, 5.79), (5.79, 9.45), (0, 9.45)],
             [(w, 5.79), (w - 5.79, 5.79), (w - 5.79, 9.45), (w, 9.45)]]
    return [[(0, 0), (w, 0), (w, h), (0, h), (0, 0)], [(w / 2, 0), (w / 2, h)]] + lanes


def draw_frame(img, fr, H, court):
    Hh, W = img.shape[:2]
    if H is not None:  # projected court lines show how good the homography is
        Hinv = np.linalg.inv(np.array(H))
        for line in court_lines(court["w"], court["h"]):
            dense = np.concatenate([np.linspace(a, b, 20) for a, b in zip(line, line[1:])])
            pts = apply_h(Hinv, dense).astype(np.int32)
            cv2.polylines(img, [pts], False, (0, 255, 255), 2)
    for p in fr["players"]:
        x, y, w, h = p["box"]
        cx, by = int((x + w / 2) * W), int((y + h) * Hh)
        c = COL[p["team"]]
        cv2.ellipse(img, (cx, by), (int(w * W * .6), int(w * W * .2)), 0, 0, 360, c, 3)
        cv2.putText(img, str(p["id"]), (cx - 10, int(y * Hh) - 6), 0, .7, c, 2)
    if fr["ball"]:
        x, y, w, h = fr["ball"]["box"]
        cv2.circle(img, (int((x + w / 2) * W), int((y + h / 2) * Hh)), 16, (0, 255, 0), 3)
    cv2.putText(img, f"t={fr['t']:.1f}  H={'ok' if H is not None else 'none'}", (20, 40), 0, 1.1, (255, 255, 255), 3)
    return img


def minimap(fr, court):
    w, h = court["w"], court["h"]
    m = np.full((int(h * PX) + 40, int(w * PX) + 40, 3), (60, 110, 160), np.uint8)
    for line in court_lines(w, h):
        cv2.polylines(m, [(np.array(line) * PX + 20).astype(np.int32)], False, (255, 255, 255), 2)
    for p in fr["players"]:
        if p["court"]:
            q = tuple(int(v * PX + 20) for v in p["court"])
            cv2.circle(m, q, 9, COL[p["team"]], -1)
            cv2.putText(m, str(p["id"]), (q[0] + 10, q[1]), 0, .5, (255, 255, 255), 1)
    if fr["ball"] and fr["ball"]["court"]:
        cv2.circle(m, tuple(int(v * PX + 20) for v in fr["ball"]["court"]), 6, (0, 255, 0), -1)
    cv2.putText(m, f"t={fr['t']:.1f}", (25, 18), 0, .5, (255, 255, 255), 1)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--t0", type=float, default=55)
    ap.add_argument("--t1", type=float, default=65)
    ap.add_argument("--stills", type=float, nargs="*", default=[])
    ap.add_argument("--stills-dir", default=".playwright-mcp")
    a = ap.parse_args()
    d = DATA / a.clip
    tr = json.loads((d / "tracks.json").read_text())
    Hs = {round(x["t"], 3): x["H"] for x in json.loads((d / "render" / "cv-homography.json").read_text())}
    cap = cv2.VideoCapture(str(d / "source.mp4"))
    src_fps = cap.get(cv2.CAP_PROP_FPS)

    def grab(fr):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(fr["t"] * src_fps))
        return cap.read()[1]

    out = d / "render" / "cv-debug.mp4"
    vw = None
    for fr in tr["frames"]:
        if a.t0 <= fr["t"] <= a.t1:
            img = draw_frame(grab(fr), fr, Hs.get(round(fr["t"], 3)), tr["court"])
            if vw is None:
                vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), tr["fps"], img.shape[1::-1])
            vw.write(img)
    if vw:
        vw.release()
        print(out)
    sd = Path(a.stills_dir)
    sd.mkdir(exist_ok=True)
    for t in a.stills:
        fr = min(tr["frames"], key=lambda f: abs(f["t"] - t))
        p = sd / f"cv-{int(t)}.jpg"
        cv2.imwrite(str(p), draw_frame(grab(fr), fr, Hs.get(round(fr["t"], 3)), tr["court"]))
        cv2.imwrite(str(sd / f"cv-minimap-{int(t)}.jpg"), minimap(fr, tr["court"]))
        print(p)


if __name__ == "__main__":
    main()
