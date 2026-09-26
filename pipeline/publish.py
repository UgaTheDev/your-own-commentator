"""Assemble manifest.json (the pipeline <-> app contract) and publish it with the renders.

python pipeline/publish.py <clip_id> [--local] [--multitrack]
  --local       relative URLs; serve data/<clip>/ with `python -m http.server`
  (default)     upload to s3://$YOC_BUCKET/published/<clip>/, URLs on https://$YOC_CDN/<clip>/ (origin path /published)
  --multitrack  one multi.mp4 with audioTrackIndex per track (mix.py --mode multitrack)
"""
import argparse
import os

from common import ROOT, aws, clip_dir, load, save


def build_manifest(clip_id, clip, events, states, voiced, rules, questions, base_url="", multitrack=False):
    tids = sorted({x["trackId"] for x in voiced})  # same order as mix.py's audio streams
    and_one = {s["eventId"] for s in states if s.get("andOne")}
    tracks = []
    for k, tid in enumerate(tids):
        persona, lang = tid.rsplit("-", 1)
        tracks.append({"id": tid, "persona": persona, "lang": lang, "label": f"{persona.title()} ({lang.upper()})",
                       **({"audioTrackIndex": k} if multitrack else {"src": f"{base_url}render/{tid}.mp4"})})

    def rule_card(e):
        if e["id"] in and_one and "and_one" in rules:
            return "and_one"
        return e.get("ruleCardId") or (e["type"] if e["type"] in rules else None)

    return {
        "clipId": clip_id,
        "videoUrl": f"{base_url}render/multi.mp4" if multitrack else (tracks[0]["src"] if tracks else None),
        "tracks": tracks,
        "events": sorted(({"id": e["id"], "t": e["t"], "type": e["type"], "team": e.get("team"),
                           "jersey": e.get("jersey"), "ruleCardId": rule_card(e)} for e in events), key=lambda e: e["t"]),
        "cues": {tid: sorted(({"t": x["start"], "eventId": x["eventId"], "text": x["text"]}
                              for x in voiced if x["trackId"] == tid), key=lambda c: c["t"]) for tid in tids},
        "ruleCards": rules,
        "state": sorted(states, key=lambda s: s["t"]),  # superset of {t,score,fantasy}; the panel uses fantasyDelta
        "questions": questions,
        "roster": clip.get("roster", []),
    }


def upload(d, clip_id, files):
    bucket = os.environ["YOC_BUCKET"]
    s3 = aws("s3")
    for f in files:
        key = f"published/{clip_id}/{f.relative_to(d).as_posix()}"
        # ponytail: short max-age on the manifest instead of a CloudFront invalidation
        extra = {"ContentType": "application/json", "CacheControl": "max-age=60"} if f.suffix == ".json" \
            else {"ContentType": "video/mp4"}
        s3.upload_file(str(f), bucket, key, ExtraArgs=extra)
        print(f"s3://{bucket}/{key}")


def main(clip_id, local, multitrack):
    d = clip_dir(clip_id)
    rules_path = ROOT / "pipeline" / "rules.json"
    questions_path = d / "questions.json"
    if local:
        base = ""
    else:
        if not os.environ.get("YOC_BUCKET") or not os.environ.get("YOC_CDN"):
            raise SystemExit("set YOC_BUCKET and YOC_CDN, or pass --local")
        base = f"https://{os.environ['YOC_CDN']}/{clip_id}/"  # the CloudFront origin path is /published
    m = build_manifest(clip_id, load(d / "clip.json"), load(d / "events.reviewed.json"), load(d / "state.json"),
                       load(d / "voiced.json"), load(rules_path) if rules_path.exists() else {},
                       load(questions_path) if questions_path.exists() else {}, base, multitrack)
    renders = [d / "render/multi.mp4"] if multitrack else [d / f"render/{t['id']}.mp4" for t in m["tracks"]]
    missing = [str(p) for p in renders if not p.exists()]
    if missing:
        raise SystemExit(f"missing renders (run mix.py first): {missing}")
    save(d / "manifest.json", m)
    if local:
        print(f"wrote {d / 'manifest.json'}; serve with: python3 -m http.server -d {d}")
    else:
        upload(d, clip_id, [*renders, d / "manifest.json"])  # manifest last so it never points at missing media


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--multitrack", action="store_true")
    a = ap.parse_args()
    main(a.clip_id, a.local, a.multitrack)
