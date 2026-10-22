"""Ask the TV a spoken question exactly as the phone page does (C5), with a Polly voice instead of a person.

  .venv/bin/python scripts/demo/ask.py <TV code> "Wait, why did blue just get a point?" [--voice Joey]

Synthesizes 16 kHz mono PCM with Polly, joins the relay with the TV's code, streams it in real time, adds the
trailing silence Nova Sonic needs to finish the transcript, and prints the transcript and the answer.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import websockets

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline import common  # noqa: E402

RELAY = "wss://d38etaw7xiqv3j.cloudfront.net"
CHUNK = 3200  # 100 ms of 16 kHz s16le


async def ask(code, pcm, relay):
    async with websockets.connect(relay, max_size=None) as ws:
        await ws.send(json.dumps({"type": "join", "code": code}))
        await ws.send(json.dumps({"type": "start"}))
        audio = pcm + b"\0" * 32000  # 1 s of trailing silence
        for i in range(0, len(audio), CHUNK):
            await ws.send(audio[i:i + CHUNK])
            await asyncio.sleep(0.1)
        await ws.send(json.dumps({"type": "stop"}))
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), 30))
            print(msg.get("type"), msg.get("text", ""), flush=True)
            if msg.get("type") in ("answer", "error"):
                return msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code")
    ap.add_argument("question")
    ap.add_argument("--voice", default="Joey")
    ap.add_argument("--relay", default=RELAY)
    a = ap.parse_args()
    r = common.aws("polly").synthesize_speech(Text=a.question, VoiceId=a.voice, Engine="neural",
                                              OutputFormat="pcm", SampleRate="16000")
    msg = asyncio.run(ask(a.code.upper(), r["AudioStream"].read(), a.relay))
    sys.exit(0 if msg.get("type") == "answer" else 1)


if __name__ == "__main__":
    main()
