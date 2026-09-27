"""Jersey-number proposals for reviewed scoring events (Stream J).

For each accepted scoring event: pick the scoring-team players nearest the ball (or the rim / free-throw
spot when the ball track is empty) in the ~1.5 s before the release, crop their torsos at full resolution,
ask Nova Pro to read the number on each crop, and majority-vote. Output is a PROPOSAL file
(events.jersey.json) plus contact sheets; a human/Claude reviewer copies a jersey into events.reviewed.json
only after reading it on the sheet. Never names: jersey + colour only.

Runs in the main venv (boto3 via pipeline/common); images are cut with ffmpeg, so no PIL/cv2 needed.
    YOC_DATA=<main>/data .venv/bin/python cv/jersey.py lake-region
"""
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import common  # noqa: E402

SCORING = {"made_2", "made_3", "ft_made"}
RIM_M, FT_M = 1.575, 5.8  # metres from the baseline: rim centre, free-throw line
W, H = 1920, 1080
CW, CH = 300, 360  # crop tile size sent to Nova and shown on the sheet
# Visible release times from review-notes.md (e2/e6/e42), else a nudge before the graphic change.
# ponytail: hand table for one clip; move to events.reviewed.json (`release`) if more clips get jerseys.
RELEASE = {"e2": 31.0, "e3": 63.0, "e6": 98.0, "e9": 127.0, "e13": 257.0, "e34": 471.0, "e42": 577.0}
PROMPT = ("Read the jersey number on this player's shirt. If you cannot clearly read every digit, say so. "
          'Reply only JSON: {"jersey": <int or null>, "legible": true/false}')


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def candidates(frames, team, t, kind, court, window=1.5, k=2):
    """Track ids of `team` that are most often the closest player to the ball (image space) or, in frames
    with no ball, to the nearest rim (free-throw spot for ft_made) in court metres. Returns up to k ids."""
    x = FT_M if kind == "ft_made" else RIM_M
    targets = [(x, court["h"] / 2), (court["w"] - x, court["h"] / 2)]
    wins = Counter()
    for f in frames:
        if not t - window <= f["t"] <= t:
            continue
        ps = [p for p in f["players"] if p.get("team") == team]
        ball = (f.get("ball") or {}).get("box")
        if ball:
            bc = (ball[0] + ball[2] / 2, ball[1] + ball[3] / 2)
            d = {p["id"]: _dist((p["box"][0] + p["box"][2] / 2, p["box"][1] + p["box"][3] / 2), bc) for p in ps}
        else:
            d = {p["id"]: min(_dist(p["court"], g) for g in targets) for p in ps if p.get("court")}
        if d:
            wins[min(d, key=d.get)] += 1
    return [i for i, _ in wins.most_common(k)]


def best_frames(frames, pid, t, window=1.5, n=5, gap=0.2):
    """Up to n (t, box) for track pid in the window, biggest boxes first, at least `gap` s apart."""
    seen = sorted(((f["t"], p["box"]) for f in frames if t - window <= f["t"] <= t
                   for p in f["players"] if p["id"] == pid), key=lambda tb: -tb[1][3])
    out = []
    for tb in seen:
        if all(abs(tb[0] - o[0]) >= gap - 1e-6 for o in out):  # 10 fps float times
            out.append(tb)
    return sorted(out[:n])


def vote(readings, min_votes=2):
    """readings: [{"jersey", "legible"}]. The number wins only if legible in >= min_votes frames and it is a
    strict majority of the legible readings (no close conflicting read). Returns (jersey or None, counts)."""
    c = Counter(r["jersey"] for r in readings if r.get("legible") and isinstance(r.get("jersey"), int))
    if not c:
        return None, {}
    (num, n), total = c.most_common(1)[0], sum(c.values())
    return (num if n >= min_votes and n * 2 > total else None), {str(j): v for j, v in c.items()}


def torso(box):
    x, y, w, h = box
    x0, x1 = max(0, (x - 0.15 * w) * W), min(W, (x + 1.15 * w) * W)
    y0, y1 = max(0, (y + 0.08 * h) * H), min(H, (y + 0.6 * h) * H)
    return int(x1 - x0) // 2 * 2, int(y1 - y0) // 2 * 2, int(x0), int(y0)


def ffmpeg(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def cut(src, t, box, out):
    cw, ch, cx, cy = torso(box)
    ffmpeg(["-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", "-vf",
            f"crop={cw}:{ch}:{cx}:{cy},scale={CW}:{CH}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={CW}:{CH}:(ow-iw)/2:(oh-ih)/2", "-q:v", "2", str(out)])


def read(path):
    content = [{"image": {"format": "jpeg", "source": {"bytes": Path(path).read_bytes()}}}]
    try:
        r = common.parse_json(common.converse("extract", PROMPT, content=content, max_tokens=60, temperature=0))
        j = r.get("jersey")
        return {"jersey": j if isinstance(j, int) else None, "legible": bool(r.get("legible")) and isinstance(j, int)}
    except (ValueError, AttributeError) as e:
        return {"jersey": None, "legible": False, "error": str(e)[:120]}


def sheet(src, t, rows, out):
    """rows: [[crop paths]] per candidate; bottom tile is the release frame with candidate boxes drawn
    (first candidate red, second yellow)."""
    ctx = out.with_suffix(".ctx.jpg")
    boxes = ",".join(f"drawbox=x={b[0]*W:.0f}:y={b[1]*H:.0f}:w={b[2]*W:.0f}:h={b[3]*H:.0f}:color={c}:t=4"
                     for (b, c) in rows["boxes"])
    ffmpeg(["-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", "-vf", f"{boxes + ',' if boxes else ''}scale=1280:720",
            "-q:v", "3", str(ctx)])
    ins, lay = [], []
    for r, crops in enumerate(rows["crops"]):
        for c, p in enumerate(crops):
            ins += ["-i", str(p)]
            lay.append(f"{c * CW}_{r * CH}")
    ins += ["-i", str(ctx)]
    lay.append(f"0_{len(rows['crops']) * CH}")
    ffmpeg([*ins, "-filter_complex", f"xstack=inputs={len(lay)}:layout={'|'.join(lay)}:fill=black", "-q:v", "3",
            str(out)])


def main(clip_id):
    d = common.clip_dir(clip_id)
    src, tracks = d / "source.mp4", common.load(d / "tracks.json")
    frames, court = tracks["frames"], tracks["court"]
    outdir = d / "jersey"
    outdir.mkdir(exist_ok=True)
    events = [e for e in common.load(d / "events.reviewed.json") if e["status"] == "accepted" and e["type"] in SCORING]
    plan = []  # (event, pid, [(t, box, crop path)])
    for e in events:
        t = RELEASE.get(e["id"], e["t"])
        for pid in candidates(frames, e["team"], t, e["type"], court):
            fr = [(ft, b, outdir / f"{e['id']}-id{pid}-{ft:.1f}.jpg") for ft, b in best_frames(frames, pid, t)]
            plan.append((e, pid, fr))
    jobs = [(ft, b, p) for _, _, fr in plan for ft, b, p in fr]
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda j: cut(src, *j), jobs))
        reads = dict(zip([p for *_, p in jobs], ex.map(read, [p for *_, p in jobs])))
    out = []
    for e in events:
        t = RELEASE.get(e["id"], e["t"])
        cands = []
        for ev, pid, fr in plan:
            if ev is e:
                rs = [reads[p] for *_, p in fr]
                j, votes = vote(rs)
                cands.append({"trackId": pid, "jersey": j, "votes": votes, "reads": rs,
                              "crops": [str(p.relative_to(d)) for *_, p in fr], "_fr": fr})
        rows = {"crops": [[p for *_, p in c["_fr"]] for c in cands if c["_fr"]],
                "boxes": [(min(c["_fr"], key=lambda f: abs(f[0] - t))[1], col)
                          for c, col in zip(cands, ("red", "yellow")) if c["_fr"]]}
        if rows["crops"]:
            sheet(src, t, rows, outdir / f"{e['id']}-sheet.jpg")
        for c in cands:
            c.pop("_fr")
        pick = cands[0] if cands and cands[0]["jersey"] is not None else None  # only the likeliest shooter counts
        out.append({"eventId": e["id"], "t": t, "team": e["team"], "jersey": pick and pick["jersey"],
                    "votes": pick["votes"] if pick else {}, "crops": pick["crops"] if pick else [],
                    "sheet": f"jersey/{e['id']}-sheet.jpg", "candidates": cands, "status": "proposed"})
    common.save(d / "events.jersey.json", out)
    for o in out:
        print(o["eventId"], o["team"], "->", o["jersey"], [(c["trackId"], c["votes"]) for c in o["candidates"]])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "lake-region")
