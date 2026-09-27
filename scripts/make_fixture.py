"""Build fixtures/manifest-v2.json from the live dev manifest plus fake v2 sections, and publish it.

Usage: .venv/bin/python scripts/make_fixture.py [--publish]
The fake sections exist only so the app and services can be built before the real streams land.
Fixture text is marked [fixture] so it can never be mistaken for real commentary.
"""
import json
import math
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import common  # noqa: E402

CDN = "https://d2og06dnam3owj.cloudfront.net"
DEV = f"{CDN}/lake-region-dev/manifest.json"
BASE = f"{CDN}/fixture-v2/"
OUT = common.ROOT / "fixtures" / "manifest-v2.json"
AUDIO = {  # name -> (text, voice)
    "why-e2.mp3": ("[fixture] That was a free throw: after certain fouls, the player shoots unguarded for 1 point.", "Matthew"),
    "why-e3.mp3": ("[fixture] A shot from behind the arc is worth 3 points instead of 2.", "Matthew"),
    "recap-120.mp3": ("[fixture] You missed a free throw and a three for blue, then a basket for pink.", "Matthew"),
}


def build(dev):
    m = dict(dev, clipId="fixture-v2")
    rookie = next(t for t in m["tracks"] if t["id"] == "rookie-en")
    m["tracks"] = [*m["tracks"], {**rookie, "id": "booth-en", "persona": "booth", "label": "Booth (EN)", "kind": "booth",
                                  "voices": [{"role": "pbp", "voice": "Matthew"}, {"role": "analyst", "voice": "Ruth"}]}]
    m["cues"]["booth-en"] = [{**c, "role": "pbp" if i % 2 == 0 else "analyst"} for i, c in enumerate(m["cues"]["rookie-en"])]
    m["questions"] = {
        "e2": [{"q": "Why did they get a free shot?", "answers": {"rookie-en": {"text": AUDIO["why-e2.mp3"][0], "audioUrl": BASE + "why-e2.mp3"}}}],
        "e3": [{"q": "Why is that worth 3?", "answers": {"rookie-en": {"text": AUDIO["why-e3.mp3"][0], "audioUrl": BASE + "why-e3.mp3"}}}],
    }
    m["replays"] = [{"eventId": "e3", "src": rookie["src"], "duration": 6.0}]  # fake: real ones come from stream A
    m["recaps"] = [{"t": 120.0, "src": BASE + "recap-120.mp3", "text": AUDIO["recap-120.mp3"][0]}]
    m["minimap"] = {"hz": 2, "frames": [
        {"t": k / 2, "players": [{"id": p, "team": "pink" if p < 5 else "blue",
                                  "x": 14.3 + 10 * math.sin(k / 20 + p), "y": 7.6 + 5 * math.cos(k / 25 + p)} for p in range(10)],
         "ball": {"x": 14.3 + 12 * math.sin(k / 15), "y": 7.6}} for k in range(240)]}
    return m


def publish(m):
    s3, bucket = common.aws("s3"), __import__("os").environ["YOC_BUCKET"]
    polly = common.aws("polly")
    for name, (text, voice) in AUDIO.items():
        audio = polly.synthesize_speech(Text=text, VoiceId=voice, Engine="neural", OutputFormat="mp3")["AudioStream"].read()
        s3.put_object(Bucket=bucket, Key=f"published/fixture-v2/{name}", Body=audio, ContentType="audio/mpeg")
    s3.put_object(Bucket=bucket, Key="published/fixture-v2/manifest.json", Body=json.dumps(m).encode(),
                  ContentType="application/json", CacheControl="max-age=60")


if __name__ == "__main__":
    dev = json.load(urllib.request.urlopen(DEV))
    m = build(dev)
    OUT.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(f"wrote {OUT}")
    if "--publish" in sys.argv:
        publish(m)
        print(f"published {BASE}manifest.json")
