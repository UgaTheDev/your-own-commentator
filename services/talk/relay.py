"""Talk-back relay, local CLI: spoken question -> Sonic transcript -> answer() over facts at the playhead -> Polly.

python services/talk/relay.py --wav q.pcm --clip lake-region-dev --t 65 [--repeat 2] [--no-cache]

Sonic only transcribes (option b). What gets spoken is pipeline/answer.py's gated answer (or its facts-only fallback).
"""
import argparse
import asyncio
import json
import os
import shutil
import sys
import time
import urllib.request
import uuid
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import answer as answer_mod  # noqa: E402
import common  # noqa: E402
import voice  # noqa: E402

CDN = os.environ.get("YOC_CDN", "d2og06dnam3owj.cloudfront.net")
OUT = Path(os.environ.get("YOC_TALK_OUT", "/private/tmp/claude-501/talk/answers"))
PERSONAS = json.loads((ROOT / "pipeline" / "personas.json").read_text())


@cache
def manifest(clip):
    if not common.CLIP_ID.match(clip):
        raise ValueError(f"bad clip id {clip!r}")
    with urllib.request.urlopen(f"https://{CDN}/{clip}/manifest.json", timeout=10) as r:
        return json.load(r)


def _timed_converse(timings):
    """Wrap common.converse so answer()'s write/judge calls are timed separately (answer.py stays untouched)."""
    real = common.converse

    def wrapped(key, *a, **kw):
        t = time.perf_counter()
        try:
            return real(key, *a, **kw)
        finally:
            timings.setdefault(f"answer_{key}", 0.0)
            timings[f"answer_{key}"] += time.perf_counter() - t
            timings[f"n_{key}"] = timings.get(f"n_{key}", 0) + 1
    return real, wrapped


def respond(question, t, clip, persona_id="rookie-en", timings=None):
    """Blocking: grounded answer + Polly mp3 for a transcript at playhead t. Returns {text, fallback, mp3, voice}."""
    timings = {} if timings is None else timings
    persona = PERSONAS[persona_id]
    s = time.perf_counter()
    facts = answer_mod.facts_at(t, manifest(clip))
    timings["facts"] = time.perf_counter() - s
    real, wrapped = _timed_converse(timings)
    common.converse = wrapped
    try:
        s = time.perf_counter()
        a = answer_mod.answer(question, facts, persona)
        timings["answer_total"] = time.perf_counter() - s
    finally:
        common.converse = real
    s = time.perf_counter()
    mp3 = voice.synth({"text": a["text"], "voice": persona["voice"], "engine": persona["engine"], "lang": persona["lang"]})
    timings["polly"] = time.perf_counter() - s
    return {**a, "mp3": mp3, "voice": persona["voice"]}


def no_cache():
    """Benchmark mode: every Bedrock/Polly call misses the shared cache (fresh path per call)."""
    tmp = OUT / ".nocache"
    tmp.mkdir(parents=True, exist_ok=True)
    fresh = lambda kind, key, ext="json": tmp / f"{kind}-{uuid.uuid4().hex}.{ext}"  # noqa: E731
    common.cache_path = voice.cache_path = fresh


async def run_once(pcm, clip, t, persona):
    import sonic_asr
    tm = {}
    s = time.perf_counter()
    man = asyncio.create_task(asyncio.to_thread(manifest, clip))  # overlaps the (cached-after-first) fetch with ASR
    text = await sonic_asr.transcribe_pcm(pcm, timings=tm)
    await man
    tm["asr"] = tm.pop("asr_after_audio")  # latency the viewer feels: from end of their speech to transcript
    s2 = time.perf_counter()
    r = await asyncio.to_thread(respond, text, t, clip, persona, tm)
    tm["total"] = tm["asr"] + (time.perf_counter() - s2)
    tm["wall"] = time.perf_counter() - s
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{uuid.uuid4().hex[:8]}.mp3"
    shutil.copy(r["mp3"], dest)
    return text, r, dest, tm


async def main(a):
    if a.no_cache:
        no_cache()
    for wav in a.wav:
        pcm = Path(wav).read_bytes()
        for i in range(a.repeat):
            text, r, dest, tm = await run_once(pcm, a.clip, a.t, a.persona)
            print(json.dumps({"wav": Path(wav).name, "run": "cold" if i == 0 else "warm", "transcript": text,
                              "answer": r["text"], "fallback": r["fallback"], "mp3": str(dest),
                              **{k: round(v, 2) if isinstance(v, float) else v for k, v in tm.items()}}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--wav", action="append", required=True, help="16 kHz mono s16le PCM (repeatable)")
    p.add_argument("--clip", required=True)
    p.add_argument("--t", type=float, required=True)
    p.add_argument("--persona", default="rookie-en")
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--no-cache", action="store_true")
    asyncio.run(main(p.parse_args()))
