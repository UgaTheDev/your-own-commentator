"""Shared paths, AWS clients, model IDs and a content-hash cache for every pipeline step."""
import hashlib
import json
import os
import re
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = DATA / ".cache"

# ponytail: minimal .env loader (KEY=VALUE lines); real env vars win
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        k, sep, v = line.partition("=")
        if sep and not k.strip().startswith("#"):
            os.environ.setdefault(k.strip(), v.strip())
REGION = os.environ.get("AWS_REGION", "us-east-1")  # Polly generative voices + Nova live here

# Bedrock inference profile IDs. Verify with:
#   aws bedrock list-inference-profiles --region us-east-1 --query "inferenceProfileSummaries[].inferenceProfileId"
MODELS = {
    "extract": os.environ.get("MODEL_EXTRACT", "us.amazon.nova-2-lite-v1:0"),
    "write": os.environ.get("MODEL_WRITE", "us.amazon.nova-2-lite-v1:0"),
    "judge": os.environ.get("MODEL_JUDGE", "us.amazon.nova-2-lite-v1:0"),
}

CLIP_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def clip_dir(clip_id):
    """Validated data/<clip_id> path. Rejects traversal and unknown clips."""
    if not CLIP_ID.match(clip_id or ""):
        raise ValueError(f"bad clip id {clip_id!r}")
    d = DATA / clip_id
    if not d.is_dir():
        raise FileNotFoundError(d)
    return d


def load(path):
    return json.loads(Path(path).read_text())


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False))


def cache_path(kind, key, ext="json"):
    """Deterministic cache file for `key` (any JSON-able object). Caller checks .exists()."""
    digest = hashlib.sha256(json.dumps(key, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    p = CACHE / kind / f"{digest}.{ext}"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@cache
def aws(service):
    import boto3  # lazy: tests of pure logic never need boto3 or credentials

    return boto3.client(service, region_name=REGION)


def converse(model_key, prompt, system=None, content=None, max_tokens=1024, temperature=0.3):
    """One Bedrock Converse call, cached on (model, prompt, system, content hash).

    `content` is extra content blocks placed before the prompt (e.g. a video block);
    bytes inside it are hashed, not stored, in the cache key.
    """
    model = MODELS[model_key]
    content = content or []
    key = {"model": model, "prompt": prompt, "system": system, "max_tokens": max_tokens, "temperature": temperature,
           "content": [_hashable(c) for c in content]}
    p = cache_path("converse", key)
    if p.exists():
        return load(p)["text"]
    resp = aws("bedrock-runtime").converse(
        modelId=model,
        messages=[{"role": "user", "content": [*content, {"text": prompt}]}],
        **({"system": [{"text": system}]} if system else {}),
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
    save(p, {"text": text, "usage": resp.get("usage")})
    return text


def _hashable(obj):
    if isinstance(obj, bytes):
        return "sha256:" + hashlib.sha256(obj).hexdigest()
    if isinstance(obj, dict):
        return {k: _hashable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_hashable(v) for v in obj]
    return obj


def parse_json(text):
    """Extract the first JSON array/object from a model reply (models wrap JSON in prose or ``` fences)."""
    m = re.search(r"[\[{].*[\]}]", text, re.S)
    if not m:
        raise ValueError(f"no JSON in model reply: {text[:200]!r}")
    return json.loads(m.group(0))
