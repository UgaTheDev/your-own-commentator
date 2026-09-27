"""Live smoke run (not collected by pytest): the SDK client against a running `yoc_mcp.py --http`, real CDN + Bedrock.

python services/mcp/tests/live_http.py [http://127.0.0.1:8790/mcp]
mode="legacy" forces the initialize handshake, which negotiates 2025-11-25: the version Alexa+ supports.
"""
import asyncio
import json
import sys
import time

from mcp import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790/mcp"
CLIP = "lake-region"


async def main():
    async with Client(URL, mode="legacy") as c:
        print("protocol", c.protocol_version)
        print("tools", [t.name for t in (await c.list_tools()).tools])
        calls = [("list_games", {}), ("list_commentators", {"clip_id": CLIP})]
        for t in (65, 300):
            calls += [("get_current_play", {"clip_id": CLIP, "t": t}), ("whos_winning", {"clip_id": CLIP, "t": t}),
                      ("explain_play", {"clip_id": CLIP, "t": t, "question": "Why did that count?"})]
        calls.append(("whos_winning", {"clip_id": "../etc", "t": 1}))
        for name, args in calls:
            s = time.perf_counter()
            r = await c.call_tool(name, args)
            ms = (time.perf_counter() - s) * 1000
            body = r.structured_content if r.structured_content is not None else r.content[0].text
            print(f"{name} {json.dumps(args)} {ms:.0f}ms error={r.is_error}\n  {json.dumps(body, ensure_ascii=False)}")


asyncio.run(main())
