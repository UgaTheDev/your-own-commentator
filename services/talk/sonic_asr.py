"""Nova 2 Sonic as a speech recognizer only (design option b).

We stream 16 kHz mono s16le PCM in and keep only the USER transcript (the ASR textOutput). The session is closed
as soon as that arrives, so Sonic's own spoken reply is never generated to completion and never played: it can't
be gated before speaking. The answer comes from pipeline/answer.py instead.

python services/talk/sonic_asr.py q.pcm   ->  prints the transcript and timing
"""
import asyncio
import base64
import json
import os
import sys
import time
import uuid

MODEL_ID = "amazon.nova-2-sonic-v1:0"
REGION = os.environ.get("AWS_REGION", "us-east-1")
RATE = 16000
CHUNK = 1024          # 32 ms of 16 kHz s16le, the frame size the Sonic docs use
TAIL_SILENCE_S = 3.0  # silence after speech so Sonic's turn detection fires; we stop as soon as the transcript lands
TIMEOUT_S = 20.0
DEBUG = bool(os.environ.get("YOC_SONIC_DEBUG"))
TAIL_PACE = float(os.environ.get("YOC_SONIC_TAIL_PACE", "0.25"))  # 4x real time: halves ASR latency vs 1


class Boto3Credentials:
    """The smithy SDK can't read `aws login` credentials; boto3 can (and refreshes them). Nothing touches disk."""

    def __init__(self):
        import boto3
        self._creds = boto3.Session().get_credentials()
        if self._creds is None:
            raise RuntimeError("no AWS credentials (run `aws login`)")

    async def get_identity(self, *, properties=None, **_):
        from smithy_aws_core.identity import AWSCredentialsIdentity
        c = self._creds.get_frozen_credentials()
        return AWSCredentialsIdentity(access_key_id=c.access_key, secret_access_key=c.secret_key, session_token=c.token)


_client = None


async def client():
    """One client per process (connection reuse is the 'warm' case). Config must be built with resolve() in 0.11."""
    global _client
    if _client is None:
        from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient
        from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig
        overrides = {} if os.environ.get("YOC_SONIC_SDK_CREDS") else {"aws_credentials_identity_resolver": Boto3Credentials()}
        from smithy_http.aio.crt import AWSCRTHTTPClient  # the default aiohttp transport has no duplex streaming
        _client = AsyncBedrockRuntimeClient(config=await AsyncBedrockRuntimeConfig.resolve(
            region=REGION, transport=AWSCRTHTTPClient(), **overrides))
    return _client


def _events(prompt, audio):
    """The input events around the audio, in the order the docs require."""
    start = [
        {"sessionStart": {"inferenceConfiguration": {"maxTokens": 256, "topP": 0.9, "temperature": 0.0},
                          "turnDetectionConfiguration": {"endpointingSensitivity": "HIGH"}}},
        {"promptStart": {"promptName": prompt, "textOutputConfiguration": {"mediaType": "text/plain"},
                         "audioOutputConfiguration": {"mediaType": "audio/lpcm", "sampleRateHertz": 16000,
                                                      "sampleSizeBits": 16, "channelCount": 1, "voiceId": "matthew",
                                                      "encoding": "base64", "audioType": "SPEECH"}}},
        {"contentStart": {"promptName": prompt, "contentName": "sys", "type": "TEXT", "interactive": False,
                          "role": "SYSTEM", "textInputConfiguration": {"mediaType": "text/plain"}}},
        {"textInput": {"promptName": prompt, "contentName": "sys",
                       "content": "A viewer is asking about a basketball game. Reply in one short sentence."}},
        {"contentEnd": {"promptName": prompt, "contentName": "sys"}},
        {"contentStart": {"promptName": prompt, "contentName": audio, "type": "AUDIO", "interactive": True,
                          "role": "USER", "audioInputConfiguration": {
                              "mediaType": "audio/lpcm", "sampleRateHertz": RATE, "sampleSizeBits": 16,
                              "channelCount": 1, "audioType": "SPEECH", "encoding": "base64"}}},
    ]
    end = [{"contentEnd": {"promptName": prompt, "contentName": audio}},
           {"promptEnd": {"promptName": prompt}}, {"sessionEnd": {}}]
    return start, end


async def paced(pcm, realtime=True):
    """Yield a PCM buffer as 32 ms chunks, at real-time pace like a live mic (or as fast as possible)."""
    for i in range(0, len(pcm), CHUNK):
        yield pcm[i:i + CHUNK]
        if realtime:
            await asyncio.sleep(CHUNK / (2 * RATE))


async def transcribe(chunks, timings=None):
    """Stream PCM chunks (async iterable of bytes) into Sonic; return the user's final transcript ("" if none)."""
    from aws_sdk_bedrock_runtime.models import (BidirectionalInputPayloadPart,
                                                InvokeModelWithBidirectionalStreamInputChunk,
                                                InvokeModelWithBidirectionalStreamOperationInput)
    timings = {} if timings is None else timings
    prompt, audio = str(uuid.uuid4()), str(uuid.uuid4())
    start, end = _events(prompt, audio)
    t0 = time.perf_counter()
    stream = await (await client()).invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(model_id=MODEL_ID))

    async def send(ev):
        await stream.input_stream.send(InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps({"event": ev}).encode())))

    async def audio_in(pcm):
        await send({"audioInput": {"promptName": prompt, "contentName": audio,
                                   "content": base64.b64encode(pcm).decode()}})

    done = asyncio.get_running_loop().create_future()

    async def read():
        roles, parts = {}, []
        _, out = await stream.await_output()
        async for event in out:
            raw = getattr(getattr(event, "value", None), "bytes_", None)
            if not raw:
                if DEBUG:
                    print("sonic:", type(event).__name__, event, file=sys.stderr)
                if not isinstance(event, type(None)) and "Exception" in type(event).__name__:
                    raise RuntimeError(f"Sonic error: {event}")
                continue
            ev = json.loads(raw)["event"]
            kind = next(iter(ev))
            body = ev[kind]
            if DEBUG and kind != "audioOutput":
                print("sonic:", json.dumps(ev)[:300], file=sys.stderr)
            if kind == "contentStart":
                roles[body.get("contentId")] = (body.get("role"), body.get("type"))
                if body.get("role") == "ASSISTANT" and parts:  # the model moved on: the user turn is complete
                    break
            elif kind == "textOutput" and roles.get(body.get("contentId"), ("",))[0] == "USER":
                parts.append(body["content"])
                timings.setdefault("asr_first_text", time.perf_counter() - t0)
            elif kind == "contentEnd" and parts and roles.get(body.get("contentId"), ("",))[0] == "USER":
                break
        if not done.done():
            done.set_result(" ".join(p.strip() for p in parts).strip())

    reader = asyncio.create_task(read())
    reader.add_done_callback(lambda t: done.done() or t.cancelled() or done.set_exception(
        t.exception() or RuntimeError("Sonic stream ended without a transcript")))
    try:
        for ev in start:
            await send(ev)
        async for pcm in chunks:
            if done.done():
                break
            await audio_in(pcm)
        timings["audio_end"] = time.perf_counter() - t0
        silence = bytes(CHUNK)
        for _ in range(int(TAIL_SILENCE_S * RATE * 2 / CHUNK)):
            if done.done():
                break
            await audio_in(silence)
            await asyncio.sleep(TAIL_PACE * CHUNK / (2 * RATE))
        text = await asyncio.wait_for(done, TIMEOUT_S)
        timings["asr_after_audio"] = time.perf_counter() - t0 - timings["audio_end"]
        return text
    finally:
        reader.cancel()
        try:
            for ev in end:
                await send(ev)
            await stream.input_stream.close()
        except Exception as e:  # ponytail: best-effort close; the service times the session out anyway
            if DEBUG:
                print("sonic close:", repr(e), file=sys.stderr)


async def transcribe_pcm(pcm, realtime=True, timings=None):
    return await transcribe(paced(pcm, realtime), timings)


if __name__ == "__main__":
    t = {}
    text = asyncio.run(transcribe_pcm(open(sys.argv[1], "rb").read(), timings=t))
    print(repr(text), {k: round(v, 2) for k, v in t.items()})
