"""C4/C5 protocol tests with a fake ASR and a fake answer(): no AWS, no network beyond 127.0.0.1."""
import asyncio
import json
import sys
from pathlib import Path

import pytest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402


class Clock:
    now = 1_000_000.0

    def __call__(self):
        return self.now


def make_relay():
    calls = []

    async def fake_asr(chunks):
        n = 0
        async for c in chunks:
            n += len(c)
        return "who is winning" if n else ""

    def fake_respond(text, t, clip, track):
        calls.append((text, t, clip, track))
        return {"text": f"At {t} the pink team leads.", "audioUrl": "https://cdn.example/a.mp3", "voice": "Matthew"}

    clock = Clock()
    return server.Relay(fake_asr, fake_respond, clock=clock), calls, clock


def run(scenario):
    async def main():
        relay, calls, clock = make_relay()
        async with serve(relay.handler, "127.0.0.1", 0, max_size=server.MAX_FRAME) as srv:
            url = f"ws://127.0.0.1:{srv.sockets[0].getsockname()[1]}"
            await asyncio.wait_for(scenario(url, relay, calls, clock), 10)
    asyncio.run(main())


def valid(msg):
    assert server.VALIDATOR.is_valid(msg), msg
    return msg


async def recv(ws):
    return valid(json.loads(await ws.recv()))


async def pair(url):
    tv = await connect(url)
    await tv.send(json.dumps({"type": "hello", "clipId": "lake-region-dev"}))
    code = (await recv(tv))["code"]
    phone = await connect(url)
    await phone.send(json.dumps({"type": "join", "code": code}))
    return tv, phone, code


async def ask(phone, pcm=b"\0" * 3200):
    await phone.send(json.dumps({"type": "start"}))
    await phone.send(pcm)
    await phone.send(json.dumps({"type": "stop"}))
    return await recv(phone), await recv(phone)


async def closed_with(ws, code=1008):
    with pytest.raises(ConnectionClosed) as e:
        while True:
            await ws.recv()
    assert e.value.rcvd.code == code, e.value.rcvd
    return e.value.rcvd.reason


def test_pairing_code_format_and_expiry():
    async def s(url, relay, calls, clock):
        tv, phone, code = await pair(url)
        assert len(code) == 6 and set(code) <= set(server.ALPHABET)
        assert relay.sessions[code].expires == clock.now + 2 * 3600
        clock.now += 2 * 3600
        late = await connect(url)
        await late.send(json.dumps({"type": "join", "code": code}))
        assert "expired" in await closed_with(late)
    run(s)


def test_question_round_trip_uses_playhead_and_reaches_tv():
    async def s(url, relay, calls, clock):
        tv, phone, code = await pair(url)
        await tv.send(json.dumps({"type": "playhead", "t": 63.2, "trackId": "kid-en", "paused": False}))
        await asyncio.sleep(0.05)
        assert relay.sessions[code].t == 63.2
        transcript, answer = await ask(phone)
        assert transcript == {"type": "transcript", "text": "who is winning"}
        assert answer["type"] == "answer" and answer["audioUrl"].startswith("https://")
        assert calls == [("who is winning", 63.2, "lake-region-dev", "kid-en")]
        tv_answer = await recv(tv)
        assert tv_answer =={"type": "answer", "id": "a1", "t": 63.2, "text": answer["text"],
                                  "audioUrl": answer["audioUrl"], "voice": "Matthew"}
    run(s)


def test_empty_transcript_gets_no_answer():
    async def s(url, relay, calls, clock):
        tv, phone, _ = await pair(url)
        await phone.send(json.dumps({"type": "start"}))
        await phone.send(json.dumps({"type": "stop"}))
        assert await recv(phone) == {"type": "transcript", "text": ""}
        assert calls == []
    run(s)


def test_question_limit():
    async def s(url, relay, calls, clock):
        tv, phone, _ = await pair(url)
        for _ in range(server.MAX_QUESTIONS):
            await ask(phone)
        await phone.send(json.dumps({"type": "start"}))
        assert "limit" in await closed_with(phone)
    run(s)


def test_audio_cap():
    async def s(url, relay, calls, clock):
        tv, phone, _ = await pair(url)
        await phone.send(json.dumps({"type": "start"}))
        chunk = b"\0" * 32000  # 1 s
        for _ in range(16):
            await phone.send(chunk)
        assert "15 s" in await closed_with(phone)
        assert calls == []
    run(s)


def test_oversized_frame_rejected():
    async def s(url, relay, calls, clock):
        tv, phone, _ = await pair(url)
        await phone.send(json.dumps({"type": "start"}))
        await phone.send(b"\0" * (server.MAX_FRAME + 1))
        await closed_with(phone, 1009)
    run(s)


@pytest.mark.parametrize("first", [
    "not json", json.dumps({"type": "nope"}), json.dumps({"type": "join", "code": "lower1"}),
    json.dumps({"type": "hello", "clipId": "../etc"}), json.dumps({"type": "start"}), b"\0\0",
    json.dumps({"type": "hello", "clipId": "x" * 2000}),
])
def test_bad_first_message_rejected(first):
    async def s(url, relay, calls, clock):
        ws = await connect(url)
        await ws.send(first)
        await closed_with(ws)
        assert relay.sessions == {} or all(v.tv is None for v in relay.sessions.values())
    run(s)


def test_role_confusion_rejected():
    async def s(url, relay, calls, clock):
        tv, phone, _ = await pair(url)
        await tv.send(json.dumps({"type": "start"}))
        assert "playhead" in await closed_with(tv)
        await phone.send(b"\0" * 10)
        assert "start/stop" in await closed_with(phone)
    run(s)


def test_join_guessing_rate_limited():
    async def s(url, relay, calls, clock):
        for _ in range(server.MAX_JOIN_FAILS):
            ws = await connect(url)
            await ws.send(json.dumps({"type": "join", "code": "AAAAAA"}))
            assert "unknown" in await closed_with(ws)
        tv, phone, _ = await pair(url)  # even a right code is refused while the IP is locked out
        assert "too many" in await closed_with(phone)
        clock.now += server.JOIN_WINDOW_S
        tv, phone, _ = await pair(url)
        await ask(phone)
    run(s)
