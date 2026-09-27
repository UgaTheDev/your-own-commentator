"""Assemble manifest.json (C3 manifest v2, the pipeline <-> app contract) and publish it with the renders.

Also reads (when present) questions.json (why.py) and recaps.json (recap.py), whose `audio` files
are uploaded under audio/ and referenced as audioUrl / src; personas.json marks booth tracks.

python pipeline/publish.py <clip_id> [--local] [--multitrack]
  --local       relative URLs; serve data/<clip>/ with `python -m http.server`
  (default)     upload to s3://$YOC_BUCKET/published/<clip>/, URLs on https://$YOC_CDN/<clip>/ (origin path /published)
  --multitrack  one multi.mp4 with audioTrackIndex per track (mix.py --mode multitrack)
  --allow-unreviewed  DEV ONLY: put unaccepted events in the manifest (default: accepted only, CONTRACTS.md C3)
"""
import argparse
import os
import shutil
from pathlib import Path

from common import ROOT, aws, clip_dir, load, save
from mix import track_order
from write import speakable


def audio_key(path):
    return f"audio/{Path(path).name}"  # Polly cache names are content hashes: stable, collision-free


def build_manifest(clip_id, clip, events, states, voiced, rules, questions, base_url="", multitrack=False,
                   personas=None, recaps=None, allow_unreviewed=False):
    """Only speakable events reach the manifest: the watch party settles predictions from them as accepted."""
    events = speakable(events, allow_unreviewed)
    tids = track_order(x["trackId"] for x in voiced)  # same order as mix.py's audio streams; tracks[0] is videoUrl
    and_one = {s["eventId"] for s in states if s.get("andOne")}
    tracks = []
    for k, tid in enumerate(tids):
        persona, lang = tid.rsplit("-", 1)
        tracks.append({"id": tid, "persona": persona, "lang": lang, "label": f"{persona.title()} ({lang.upper()})",
                       **({"audioTrackIndex": k} if multitrack else {"src": f"{base_url}render/{tid}.mp4"})})
        p = (personas or {}).get(tid, {})
        if p.get("kind") == "booth":
            tracks[-1] |= {"kind": "booth", "voices": [{"role": r, "voice": p[r]["voice"]} for r in ("pbp", "analyst")]}

    def rule_card(e):
        if e["id"] in and_one and "and_one" in rules:
            return "and_one"
        return e.get("ruleCardId") or (e["type"] if e["type"] in rules else None)

    m = {
        "clipId": clip_id,
        "videoUrl": f"{base_url}render/multi.mp4" if multitrack else (tracks[0]["src"] if tracks else None),
        "tracks": tracks,
        "events": sorted(({"id": e["id"], "t": e["t"], "type": e["type"], "team": e.get("team"),
                           "jersey": e.get("jersey"), "ruleCardId": rule_card(e)} for e in events), key=lambda e: e["t"]),
        "cues": {tid: sorted(({"t": x["start"], "eventId": x["eventId"], "text": x["text"],
                               **({"role": x["role"]} if "role" in x else {})}
                              for x in voiced if x["trackId"] == tid), key=lambda c: c["t"]) for tid in tids},
        "ruleCards": rules,
        "state": sorted(states, key=lambda s: s["t"]),  # superset of {t,score,fantasy}; the panel uses fantasyDelta
        "questions": {eid: [{"q": q["q"], "answers": {tid: {"text": a["text"], "audioUrl": base_url + audio_key(a["audio"])}
                                                   for tid, a in q["answers"].items()}} for q in qs]
                      for eid, qs in questions.items()},
        "roster": clip.get("roster", []),
    }
    if recaps:
        m["recaps"] = [{"t": r["t"], "src": base_url + audio_key(r["audio"]), "text": r["text"]}
                       for r in sorted(recaps, key=lambda r: r["t"])]
    return m


def audio_files(questions, recaps):
    """{published key: local path} for every answer and recap mp3."""
    paths = [a["audio"] for qs in questions.values() for q in qs for a in q["answers"].values()]
    return {audio_key(p): Path(p) for p in paths + [r["audio"] for r in recaps or []]}


CONTENT_TYPES = {".json": "application/json", ".mp4": "video/mp4", ".mp3": "audio/mpeg"}


def unchanged(s3, bucket, key, f):
    # ponytail: same size and uploaded after the last local write = skip; saves re-sending 366 MB renders
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
    except s3.exceptions.ClientError:
        return False
    return head["ContentLength"] == f.stat().st_size and head["LastModified"].timestamp() > f.stat().st_mtime


def upload(clip_id, files):
    """files: {path relative to published/<clip>/: local file}, uploaded in order."""
    bucket = os.environ["YOC_BUCKET"]
    s3 = aws("s3")
    for rel, f in files.items():
        key = f"published/{clip_id}/{rel}"
        if f.suffix != ".json" and unchanged(s3, bucket, key, f):
            print(f"unchanged s3://{bucket}/{key}")
            continue
        # ponytail: short max-age on the manifest instead of a CloudFront invalidation
        extra = {"ContentType": CONTENT_TYPES[f.suffix], **({"CacheControl": "max-age=60"} if f.suffix == ".json" else {})}
        s3.upload_file(str(f), bucket, key, ExtraArgs=extra)
        print(f"s3://{bucket}/{key}")


def extras(d, clip):
    """Optional v2 sections made by other streams: CV replays/minimap files and the deployed service URLs in clip.json."""
    out = {name: load(d / f"{name}.json") for name in ("replays", "minimap") if (d / f"{name}.json").exists()}
    out |= {k: clip[k] for k in ("talk", "party") if clip.get(k)}
    return out


def validate(m):
    import jsonschema  # dev dependency; a manifest that breaks C3 must never go live
    jsonschema.validate(m, load(ROOT / "schemas" / "manifest.schema.json"))


def main(clip_id, local, multitrack, allow_unreviewed=False):
    d = clip_dir(clip_id)
    rules_path = ROOT / "pipeline" / "rules.json"
    optional = {name: load(d / f"{name}.json") if (d / f"{name}.json").exists() else None for name in ("questions", "recaps")}
    if local:
        base = ""
    else:
        if not os.environ.get("YOC_BUCKET") or not os.environ.get("YOC_CDN"):
            raise SystemExit("set YOC_BUCKET and YOC_CDN, or pass --local")
        base = f"https://{os.environ['YOC_CDN']}/{clip_id}/"  # the CloudFront origin path is /published
    m = build_manifest(clip_id, load(d / "clip.json"), load(d / "events.reviewed.json"), load(d / "state.json"),
                       load(d / "voiced.json"), load(rules_path) if rules_path.exists() else {},
                       optional["questions"] or {}, base, multitrack, load(ROOT / "pipeline" / "personas.json"),
                       optional["recaps"], allow_unreviewed)
    m |= extras(d, load(d / "clip.json"))
    if not local:
        validate(m)
    renders = [d / "render/multi.mp4"] if multitrack else [d / f"render/{t['id']}.mp4" for t in m["tracks"]]
    missing = [str(p) for p in renders if not p.exists()]
    if missing:
        raise SystemExit(f"missing renders (run mix.py first): {missing}")
    save(d / "manifest.json", m)
    if local:
        for rel, f in audio_files(optional["questions"] or {}, optional["recaps"]).items():
            (d / rel).parent.mkdir(exist_ok=True)
            shutil.copyfile(f, d / rel)
        print(f"wrote {d / 'manifest.json'}; serve with: python3 -m http.server -d {d}")
    else:
        media = {r.relative_to(d).as_posix(): r for r in renders} | audio_files(optional["questions"] or {}, optional["recaps"])
        upload(clip_id, media | {"manifest.json": d / "manifest.json"})  # manifest last: never points at missing media


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--multitrack", action="store_true")
    ap.add_argument("--allow-unreviewed", action="store_true", help="DEV ONLY: publish events not yet accepted in review")
    a = ap.parse_args()
    main(a.clip_id, a.local, a.multitrack, a.allow_unreviewed)
