"""Talk-back relay server: C4 (TV session + playhead) and C5 (phone push-to-talk), one asyncio WebSocket port.

python services/talk/server.py [--host 127.0.0.1] [--port 8765]

TV:    hello{clipId} -> session{code}; playhead{t, trackId, paused} every 1 s; receives answer{id, t, text, audioUrl, voice}
Phone: join{code}; per question start, binary 16 kHz mono s16le PCM (<= 15 s), stop -> transcript{text}, answer{text, audioUrl}
Errors close the socket with 1008 and a reason (the contracts define no error message).
Audio is never stored: PCM goes straight from the socket into Sonic.
"""
import asyncio
import json
import os
import re
import secrets
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "messages.schema.json").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # RFC 4648 base32, matches ^[A-Z2-7]{6}$
CLIP_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")  # same rule as pipeline/common.CLIP_ID
TTL_S = 2 * 3600
MAX_QUESTIONS = 20
MAX_AUDIO_BYTES = 15 * 16000 * 2  # 15 s of 16 kHz s16le
MAX_FRAME = 64 * 1024             # any single WebSocket message
MAX_TEXT = 1024                   # any JSON text message
MAX_SESSIONS = 500
MAX_JOIN_FAILS = 10               # per client IP per JOIN_WINDOW_S: 32^6 codes can't be guessed at this rate
JOIN_WINDOW_S = 600
ASR_TIMEOUT_S = 30.0


class Reject(Exception):
    """Close the connection with 1008 and this reason."""


def parse(raw):
    if len(raw) > MAX_TEXT:
        raise Reject("message too large")
    try:
        msg = json.loads(raw)
    except ValueError:
        raise Reject("not JSON") from None
    if not isinstance(msg, dict) or not VALIDATOR.is_valid(msg):
        raise Reject("invalid message")
    return msg


@dataclass
class Session:
    code: str
    clip: str
    expires: float
    t: float = 0.0
    track: str = "rookie-en"
    paused: bool = False
    questions: int = 0
    answers: int = 0
    tv: object = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # one question at a time per session

    def expired(self, now=None):
        return (now or time.time()) >= self.expires


class Relay:
    """`asr(chunks) -> str` consumes an async iterator of PCM bytes; `respond(text, t, clip, track) -> dict` returns
    {text, audioUrl, voice}. Both are injected so tests run on fakes."""

    def __init__(self, asr, respond, clock=time.time):
        self.asr, self.respond, self.clock = asr, respond, clock
        self.sessions = {}
        self.join_fails = {}  # ip -> [timestamps]

    def new_session(self, clip):
        now = self.clock()
        for code in [c for c, s in self.sessions.items() if s.expired(now)]:
            del self.sessions[code]
        if len(self.sessions) >= MAX_SESSIONS:
            raise Reject("server busy")
        while (code := "".join(secrets.choice(ALPHABET) for _ in range(6))) in self.sessions:
            pass
        s = self.sessions[code] = Session(code, clip, now + TTL_S)
        return s

    def live(self, code):
        s = self.sessions.get(code)
        if s and s.expired(self.clock()):
            del self.sessions[code]
            return None
        return s

    async def handler(self, ws):
        try:
            first = await ws.recv()
            if not isinstance(first, str):
                raise Reject("expected hello or join")
            msg = parse(first)
            if msg["type"] == "hello":
                await self.tv(ws, msg)
            elif msg["type"] == "join":
                await self.phone(ws, msg)
            else:
                raise Reject("expected hello or join")
        except Reject as e:
            await ws.close(1008, str(e))
        except ConnectionClosed:
            pass
        except Exception as e:  # ASR/Bedrock/Polly failure: tell the client, keep the server up
            print("talk: error", repr(e), file=sys.stderr)
            await ws.close(1011, "internal error")

    async def tv(self, ws, hello):
        if not CLIP_ID.match(hello["clipId"]):
            raise Reject("bad clipId")
        s = self.new_session(hello["clipId"])
        s.tv = ws
        await ws.send(json.dumps({"type": "session", "code": s.code}))
        try:
            async for raw in ws:
                if not isinstance(raw, str):
                    raise Reject("TV sends text only")
                msg = parse(raw)
                if msg["type"] != "playhead":
                    raise Reject("TV may only send playhead")
                if s.expired(self.clock()):
                    raise Reject("session expired")
                s.t, s.track, s.paused = float(msg["t"]), msg["trackId"], msg["paused"]
        finally:
            if s.tv is ws:
                s.tv = None

    async def phone(self, ws, join):
        ip = (ws.remote_address or ("?",))[0]  # ponytail: behind a load balancer use X-Forwarded-For instead
        fails = [f for f in self.join_fails.get(ip, []) if self.clock() - f < JOIN_WINDOW_S]
        if len(fails) >= MAX_JOIN_FAILS:
            raise Reject("too many bad codes, wait")
        s = self.live(join["code"])
        if s is None:
            self.join_fails[ip] = [*fails, self.clock()]
            raise Reject("unknown or expired code")
        async for raw in ws:
            if not isinstance(raw, str):
                raise Reject("audio outside start/stop")
            msg = parse(raw)
            if msg["type"] != "start":
                raise Reject("expected start")
            await self.question(ws, s)

    async def question(self, ws, s):
        if s.expired(self.clock()):
            raise Reject("session expired")
        if s.questions >= MAX_QUESTIONS:
            raise Reject("question limit reached")
        s.questions += 1
        t_at_start, track = s.t, s.track  # the viewer asks about what was on screen when they pressed talk
        q = asyncio.Queue()

        async def chunks():
            while (c := await q.get()) is not None:
                yield c

        async def recognize():  # the ASR coroutine is only created once the task runs, so a cancel never leaks it
            return await asyncio.wait_for(self.asr(chunks()), ASR_TIMEOUT_S)

        asr = asyncio.create_task(recognize())
        try:
            size = 0
            while True:
                raw = await ws.recv()
                if isinstance(raw, bytes):
                    size += len(raw)
                    if size > MAX_AUDIO_BYTES:
                        raise Reject("audio over 15 s")
                    q.put_nowait(raw)
                    continue
                if parse(raw)["type"] != "stop":
                    raise Reject("expected audio or stop")
                break
            q.put_nowait(None)
            text = (await asr).strip()
        finally:
            if not asr.done():
                asr.cancel()
        await ws.send(json.dumps({"type": "transcript", "text": text}))
        if not text:
            return
        async with s.lock:
            a = await asyncio.to_thread(self.respond, text, t_at_start, s.clip, track)
            s.answers += 1
            out = {"type": "answer", "id": f"a{s.answers}", "t": t_at_start, "text": a["text"],
                   "audioUrl": a["audioUrl"], "voice": a["voice"]}
        await ws.send(json.dumps({"type": "answer", "text": out["text"], "audioUrl": out["audioUrl"]}))
        if s.tv is not None:
            try:
                await s.tv.send(json.dumps(out))
            except ConnectionClosed:
                pass


def real_respond(text, t, clip, track):
    """Grounded answer + Polly, uploaded so the TV can play it over HTTPS (Vega media is HTTPS-only)."""
    import relay  # lazy: pulls in pipeline/ and boto3
    import common
    persona = track if track in relay.PERSONAS else "rookie-en"
    r = relay.respond(text, t, clip, persona)
    key = f"talk/{clip}/{uuid.uuid4().hex}.mp3"
    common.aws("s3").upload_file(str(r["mp3"]), os.environ["YOC_BUCKET"], f"published/{key}",
                                 ExtraArgs={"ContentType": "audio/mpeg"})
    return {"text": r["text"], "audioUrl": f"https://{os.environ['YOC_CDN']}/{key}", "voice": r["voice"],
            "fallback": r["fallback"]}


async def main(host, port):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sonic_asr
    if not (os.environ.get("YOC_BUCKET") and os.environ.get("YOC_CDN")):
        raise SystemExit("set YOC_BUCKET and YOC_CDN (answer audio must be HTTPS for the TV)")
    r = Relay(sonic_asr.transcribe, real_respond)
    async with serve(r.handler, host, port, max_size=MAX_FRAME, max_queue=64):
        print(f"talk relay on ws://{host}:{port}")
        await asyncio.Future()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args()
    asyncio.run(main(a.host, a.port))
