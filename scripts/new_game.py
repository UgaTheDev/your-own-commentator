"""Checklist runner for adding a licensed game (a clip) end to end. Not magic: review stays a human/AI step.

Run from the main checkout with YOC_DATA set (see CONTRACTS.md "Shared environment"). Steps, in order:

  1. license  "File:Boys Varsity Basketball v. Montpelier - February 21, 2026.webm"
       Commons API: prints license, size, uploader, URL. Exits 1 unless the license is CC BY 4.0.
  2. download <commons title> <out.webm>      one request with a User-Agent (Wikimedia 429s parallel/seek-heavy clients)
  3. sheet <video> <outdir> <step_s> <end_s> [start_s] [crop]
       Contact sheet (full frames + score-bug crop) to pick the 10-min segment with the most visible scoring,
       read team colors and the score at the segment edges, and later to review each proposal.
       Frame k of a sheet is at start_s + k*step_s, row-major.
  4. cut <video> <clip_id> <start_s> [dur_s=600]   -> data/<clip>/source.mp4 (1080p h264, audio stripped: HCTV has a human commentator)
  5. Write data/<clip>/clip.json by hand (copy data/lake-region/clip.json: teams, start/final score, scoreBug, audioBed, attribution, talk/party).
  6. python pipeline/extract.py <clip>   -> events.proposed.json (score graphic + Nova)
  7. REVIEW (by eye, see data/lake-region/review-notes.md): events.reviewed.json holds only accepted events tagged reviewedBy;
       write review-notes.md. `python pipeline/state.py <clip>` must pass its final-score assertion.
  8. pipeline <clip>   runs state, write, booth, why, recap, voice, mix, publish, eval in order; stops at the first failure.
  9. index <clip_id>="<title>" ...   builds clips.json (C8) from the live manifests, validates it, uploads it to
       s3://$YOC_BUCKET/published/clips.json and checks https://$YOC_CDN/clips.json returns 200.
Then add the SOURCES.md row with the exact CC BY attribution line.
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import common  # noqa: E402  (loads .env, resolves YOC_DATA)

UA = "YOC-hackathon/1.0 (github.com/kushzingade; commons footage for a CC BY demo)"
PY = sys.executable
STEPS = ["state", "write", "booth", "why", "recap", "voice", "mix", "publish", "eval"]


def commons_info(title):
    q = urllib.parse.urlencode({"action": "query", "prop": "imageinfo", "format": "json", "titles": title,
                                "iiprop": "url|size|user|extmetadata",
                                "iiextmetadatafilter": "LicenseShortName|Artist"})
    req = urllib.request.Request(f"https://commons.wikimedia.org/w/api.php?{q}", headers={"User-Agent": UA})
    page = next(iter(json.load(urllib.request.urlopen(req))["query"]["pages"].values()))
    info = page["imageinfo"][0]
    return {"title": page["title"], "license": info["extmetadata"]["LicenseShortName"]["value"],
            "user": info["user"], "width": info["width"], "height": info["height"],
            "minutes": round(info.get("duration", 0) / 60, 1), "bytes": info["size"], "url": info["url"].split("?")[0]}


def run(*cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), check=True)


def sheet(video, out, step, end, start=0.0, crop="iw*0.2:ih*0.1:0:ih*0.9"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    t, k = float(start), 0
    while t < float(end):
        for kind, vf in (("full", "scale=480:-2"), ("bug", f"crop={crop},scale=384:-2")):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf", vf,
                            str(out / f"{kind}_{k:03d}.png")], check=False)
        t, k = t + float(step), k + 1
    for kind, cols in (("full", 5), ("bug", 4)):
        run("ffmpeg", "-v", "error", "-y", "-i", out / f"{kind}_%03d.png", "-vf", f"tile={cols}x{-(-k // cols)}",
            "-frames:v", "1", out / f"{kind}_sheet.png")
    print(f"{k} frames, frame i at {start}+i*{step}s -> {out}/full_sheet.png, bug_sheet.png")


def cut(video, clip_id, start, dur=600):
    d = common.DATA / clip_id
    d.mkdir(parents=True, exist_ok=True)
    run("ffmpeg", "-v", "error", "-y", "-ss", start, "-i", video, "-t", dur, "-an", "-vf", "scale=-2:1080",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-movflags", "+faststart", d / "source.mp4")


def pipeline(clip_id, steps=STEPS):
    for step in steps:  # no --allow-unreviewed anywhere: only accepted events are spoken
        run(PY, ROOT / "pipeline" / f"{step}.py", clip_id)


def index(pairs):
    import jsonschema
    bucket, cdn = os.environ["YOC_BUCKET"], os.environ["YOC_CDN"]
    clips = []
    for pair in pairs:
        clip_id, title = pair.split("=", 1)
        clip = common.load(common.clip_dir(clip_id) / "clip.json")
        reviewed = common.load(common.clip_dir(clip_id) / "events.reviewed.json")
        assert reviewed and all(e["status"] == "accepted" and e.get("reviewedBy") for e in reviewed), \
            f"{clip_id}: only reviewed clips go in the games index (C8)"
        url = f"https://{cdn}/{clip_id}/manifest.json"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        assert urllib.request.urlopen(req).status == 200, url
        clips.append({"clipId": clip_id, "title": title, "manifestUrl": url, "attribution": clip["attribution"]})
    doc = {"clips": clips}
    jsonschema.validate(doc, common.load(ROOT / "schemas" / "clips.schema.json"))
    out = common.DATA / "clips.json"
    common.save(out, doc)
    run("aws", "s3", "cp", out, f"s3://{bucket}/published/clips.json", "--content-type", "application/json",
        "--cache-control", "max-age=60")
    req = urllib.request.Request(f"https://{cdn}/clips.json", headers={"User-Agent": UA})
    print(f"https://{cdn}/clips.json ->", urllib.request.urlopen(req).status)


def main(argv):
    cmd, args = argv[0], argv[1:]
    if cmd == "license":
        info = commons_info(args[0])
        print(json.dumps(info, indent=2))
        sys.exit(0 if info["license"] == "CC BY 4.0" else 1)
    elif cmd == "download":
        run("curl", "-sSfL", "--retry", "5", "--retry-delay", "30", "-A", UA, "-o", args[1], commons_info(args[0])["url"])
    elif cmd == "sheet":
        sheet(*args)
    elif cmd == "cut":
        cut(*args)
    elif cmd == "pipeline":
        pipeline(args[0], args[1].split(",") if len(args) > 1 else STEPS)
    elif cmd == "index":
        index(args)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:] or ["help"])
