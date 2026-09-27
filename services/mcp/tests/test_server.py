"""Pure tests: tools called through the SDK's in-process client; manifest fetch and answer() are patched."""
import asyncio
import sys
from pathlib import Path

import pytest
from mcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402

MAN = {
    "tracks": [{"id": "rookie-en", "label": "Rookie (EN)", "persona": "rookie", "lang": "en"},
               {"id": "booth-en", "label": "Booth (EN)", "persona": "booth", "lang": "en", "kind": "booth"}],
    "events": [{"id": "e1", "t": 10.0, "type": "made_2", "team": "blue", "jersey": None, "ruleCardId": None},
               {"id": "e2", "t": 60.0, "type": "made_3", "team": "pink", "jersey": None, "ruleCardId": "made_3"}],
    "state": [{"eventId": "e1", "score": {"pink": 0, "blue": 2}}, {"eventId": "e2", "score": {"pink": 3, "blue": 2}}],
    "ruleCards": {"made_3": {"title": "a three-pointer"}},
}


@pytest.fixture(autouse=True)
def patched(monkeypatch):
    calls = []
    monkeypatch.setattr(server, "manifest", lambda clip: MAN)
    monkeypatch.setattr(server, "fetch_json", lambda url: (_ for _ in ()).throw(server.urllib.error.URLError("403")))

    def fake_answer(q, facts, persona):
        calls.append((q, facts, persona))
        return {"text": "grounded", "gated": True, "fallback": False}
    monkeypatch.setattr(server.answer_mod, "answer", fake_answer)
    return calls


def call(name, **args):
    async def go():
        async with Client(server.mcp) as c:
            return await c.call_tool(name, args)
    r = asyncio.run(go())
    return r.is_error, r.structured_content, r.content[0].text if r.content else ""


def test_list_games_falls_back_to_lake_region():
    err, out, _ = call("list_games")
    assert not err and out["games"] == [{"clipId": "lake-region", "title": "lake-region"}]


def test_list_games_reads_clips_json(monkeypatch):
    monkeypatch.setattr(server, "fetch_json", lambda url: {"clips": [{"clipId": "g1", "title": "Game 1"}, {"clipId": "../x"}]})
    assert call("list_games")[1]["games"] == [{"clipId": "g1", "title": "Game 1"}]


def test_current_play_and_score_from_verified_state():
    _, out, _ = call("get_current_play", clip_id="lake-region", t=65)
    assert out["event"]["id"] == "e2" and out["score"] == {"pink": 3, "blue": 2}
    assert out["text"] == "Last play: a three-pointer by the pink team. The pink team leads 3 to 2."
    assert call("get_current_play", clip_id="lake-region", t=5)[1]["text"] == "Nothing has happened yet. There is no score yet."
    assert call("whos_winning", clip_id="lake-region", t=65)[1]["text"] == "The pink team leads 3 to 2."
    assert call("whos_winning", clip_id="lake-region", t=5)[1]["text"] == "There is no score yet."


def test_score_text():
    assert server.score_text({"a": 4, "b": 4}) == "It's tied at 4."


def test_explain_play_goes_through_answer(patched):
    _, out, _ = call("explain_play", clip_id="lake-region", t=65, question="  why 3?  ", persona="rookie-es")
    assert out == {"text": "grounded", "gated": True, "fallback": False}
    q, facts, persona = patched[0]
    assert q == "why 3?" and facts["event"]["id"] == "e2" and persona["lang"] == "es"


def test_commentators():
    _, out, _ = call("list_commentators", clip_id="lake-region")
    assert [c["id"] for c in out["commentators"]] == ["rookie-en", "booth-en"]
    assert out["text"] == "Commentators: Rookie (EN), Booth (EN)."


@pytest.mark.parametrize("name,args", [
    ("whos_winning", {"clip_id": "../etc", "t": 1}),
    ("whos_winning", {"clip_id": "lake-region", "t": -1}),
    ("whos_winning", {"clip_id": "lake-region", "t": 7201}),
    ("explain_play", {"clip_id": "lake-region", "t": 1, "question": "x" * 301}),
    ("explain_play", {"clip_id": "lake-region", "t": 1, "question": "   "}),
    ("explain_play", {"clip_id": "lake-region", "t": 1, "question": "why", "persona": "nope"}),
    ("explain_play", {"clip_id": "lake-region", "t": 1, "question": "why", "persona": "booth-en"}),
])
def test_bad_input_is_a_tool_error(name, args, patched):
    err, _, text = call(name, **args)
    assert err and not patched and text.startswith(f"Error executing tool {name}: ")  # our message kept, not masked
