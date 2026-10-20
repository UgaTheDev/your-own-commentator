"""Upload rendered replays and write the C3 `replays` list. Needs boto3 + AWS credentials, so
run it with the main .venv, not the CV one:

    .venv/bin/python cv/publish_replays.py lake-region-dev

Reads data/<clip>/render/replays/index.json (from replay.py), uploads each MP4 to
s3://$YOC_BUCKET/published/<clip>/replays/<eventId>.mp4, writes data/<clip>/replays.json and
checks that every CloudFront URL answers 200 with video/mp4.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

DATA = Path(os.environ.get("YOC_DATA", Path(__file__).resolve().parents[1] / "data"))
BUCKET = os.environ.get("YOC_BUCKET", "yoc-media-817210752334")
CDN = "https://" + os.environ.get("YOC_CDN", "d2og06dnam3owj.cloudfront.net")  # bare host, like pipeline/publish.py


def replays_doc(rows, clip, cdn=CDN):
    """C3 `replays`: [{eventId, src, duration}] with https src."""
    return [{"eventId": r["eventId"], "src": f"{cdn}/{clip}/replays/{r['eventId']}.mp4", "duration": r["duration"]}
            for r in rows]


def main():
    import boto3
    clip = sys.argv[1]
    d = DATA / clip
    rows = json.loads((d / "render" / "replays" / "index.json").read_text())
    s3 = boto3.client("s3")
    for r in rows:
        s3.upload_file(str(d / "render" / "replays" / f"{r['eventId']}.mp4"), BUCKET,
                       f"published/{clip}/replays/{r['eventId']}.mp4",
                       ExtraArgs={"ContentType": "video/mp4", "CacheControl": "max-age=300"})
    doc = replays_doc(rows, clip)
    (d / "replays.json").write_text(json.dumps(doc, indent=1))
    for x in doc:
        with urllib.request.urlopen(urllib.request.Request(x["src"], method="HEAD")) as resp:
            print(resp.status, resp.headers.get("Content-Type"), resp.headers.get("Content-Length"), x["src"])
            assert resp.status == 200 and resp.headers.get("Content-Type") == "video/mp4"
    print(d / "replays.json")


if __name__ == "__main__":
    main()
