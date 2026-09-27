"""Alexa+-style MCP server over the grounded answer path (MCP 2025-11-25 handshake, official `mcp` SDK 2.x).

python services/mcp/server.py            # stdio
python services/mcp/server.py --http     # streamable HTTP on http://127.0.0.1:8790/mcp (localhost only)

Every sentence a tool returns comes from answer.answer() (digit gate + Bedrock judge, facts-only fallback)
or is built directly from the verified manifest (accepted events, state). No free-form model output.
"""
import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError  # message reaches the client; other exceptions are masked
from mcp.types import ToolAnnotations

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
import answer as answer_mod  # noqa: E402
from common import CLIP_ID  # noqa: E402

CDN = "https://d2og06dnam3owj.cloudfront.net"
PERSONAS = json.loads((ROOT / "pipeline" / "personas.json").read_text())
MAX_T = 7200.0
MAX_Q = 300
DEFAULT_GAMES = [{"clipId": "lake-region", "title": "lake-region"}]
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)

mcp = MCPServer(
    "your-own-commentator",
    title="Your Own Commentator",
    instructions="Answers questions about the basketball game on the viewer's Fire TV. Answers are short and "
                 "spoken, and only state facts from the reviewed game record.",
)


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read())


@lru_cache(maxsize=32)  # ponytail: cached until restart; add a TTL when manifests are republished mid-demo
def manifest(clip_id):
    return fetch_json(f"{CDN}/{clip_id}/manifest.json")


def check_clip(clip_id):
    if not isinstance(clip_id, str) or not CLIP_ID.match(clip_id):
        raise ToolError("Unknown game id. Ask for the list of games first.")
    try:
        return manifest(clip_id)
    except (urllib.error.URLError, ValueError, TimeoutError):
        raise ToolError(f"I couldn't find the game {clip_id}.") from None


def check_t(t):
    t = float(t)
    if not math.isfinite(t) or not 0 <= t <= MAX_T:
        raise ToolError(f"The time must be between 0 and {int(MAX_T)} seconds into the game.")
    return t


def score_text(score):
    """'The pink team leads 11 to 3.' from verified state only."""
    if not score:
        return "There is no score yet."
    (a, sa), *rest = sorted(score.items(), key=lambda kv: -kv[1])
    if not rest:
        return f"The {a} team has {sa}."
    b, sb = rest[0]
    return f"It's tied at {sa}." if sa == sb else f"The {a} team leads {sa} to {sb}."


def play_text(facts):
    """'Last play: three-pointer by the blue team.' from the accepted event and its rule card only
    (answer.fallback says 'by the ? team' for team-less events like a timeout, which reads badly aloud)."""
    ev = facts["event"]
    if not ev:
        return "Nothing has happened yet."
    what = ((facts.get("rule") or {}).get("title") or ev["type"].replace("_", " ")).lower()
    return f"Last play: {what}" + (f" by the {ev['team']} team." if ev.get("team") else ".")


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_games() -> dict[str, Any]:
    """List the games you can ask about. Use this first when the viewer hasn't said which game, or says
    "what games are there", "what can I watch". Returns up to 5 games, each with a clipId to pass to the other tools."""
    try:
        games = [{"clipId": c["clipId"], "title": c.get("title") or c["clipId"]}
                 for c in fetch_json(f"{CDN}/clips.json")["clips"] if CLIP_ID.match(c.get("clipId", ""))]
    except (urllib.error.URLError, ValueError, KeyError, TypeError, TimeoutError):
        games = []
    games = (games or DEFAULT_GAMES)[:5]
    return {"text": "You can ask about " + ", ".join(g["title"] for g in games) + ".", "games": games}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def get_current_play(clip_id: str, t: float) -> dict[str, Any]:
    """What just happened: the latest reviewed play at the viewer's playhead and the score.
    Use for "what happened", "what was that", "what just happened", "catch me up on that play".
    clip_id: the game id from list_games (e.g. "lake-region"). t: seconds into the video at the playhead (0-7200)."""
    facts = answer_mod.facts_at(check_t(t), check_clip(clip_id))
    score = (facts["state"] or {}).get("score")
    return {"text": play_text(facts) + " " + score_text(score), "event": facts["event"], "score": score}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def whos_winning(clip_id: str, t: float) -> dict[str, Any]:
    """The score at the viewer's playhead, from the verified game record only.
    Use for "who's winning", "what's the score", "who's ahead", "is it close".
    clip_id: the game id from list_games. t: seconds into the video at the playhead (0-7200)."""
    facts = answer_mod.facts_at(check_t(t), check_clip(clip_id))
    score = (facts["state"] or {}).get("score")
    return {"text": score_text(score), "score": score}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def explain_play(clip_id: str, t: float, question: str, persona: str = "rookie-en") -> dict[str, Any]:
    """Answer the viewer's question about the play at the playhead in one or two short spoken sentences, grounded
    in the reviewed game record (rule explanations included). Use for "why was that a foul", "what's a free throw",
    "why did they get 3 points", "explain that".
    clip_id: the game id from list_games. t: seconds into the video (0-7200). question: the viewer's words (max 300
    characters). persona: commentator style id from list_commentators (default "rookie-en": beginner-friendly English;
    also kid-en, fantasy-en, rookie-es Spanish, rookie-hi Hindi, rookie-zh Mandarin).
    Returns text plus gated (always true: the answer passed the fact checks) and fallback (true when the fact checks
    rejected the model twice and a plain facts-only sentence was used instead)."""
    man, t = check_clip(clip_id), check_t(t)
    if not isinstance(question, str) or not question.strip() or len(question) > MAX_Q:
        raise ToolError(f"The question must be 1 to {MAX_Q} characters.")
    if "style" not in PERSONAS.get(persona, {}):  # booth-en is a two-voice track, not an answer persona
        raise ToolError("Unknown commentator. Ask for the list of commentators.")
    return answer_mod.answer(question.strip(), answer_mod.facts_at(t, man), PERSONAS[persona])


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_commentators(clip_id: str) -> dict[str, Any]:
    """The commentator tracks available for a game (styles and languages the viewer can switch to).
    Use for "what commentators are there", "can I hear it in Spanish", "change the commentator".
    clip_id: the game id from list_games."""
    tracks = [{k: tr.get(k) for k in ("id", "label", "persona", "lang")} for tr in check_clip(clip_id)["tracks"]]
    names = [tr["label"] or tr["id"] for tr in tracks]
    more = f", and {len(names) - 5} more" if len(names) > 5 else ""
    return {"text": "Commentators: " + ", ".join(names[:5]) + more + ".", "commentators": tracks}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--http", action="store_true", help="streamable HTTP instead of stdio")
    p.add_argument("--port", type=int, default=8790)
    a = p.parse_args()
    if a.http:
        # 127.0.0.1 only: the SDK then enables Host/Origin (DNS-rebinding) checks. Stateless + JSON: no sessions, Lambda-friendly.
        mcp.run("streamable-http", host="127.0.0.1", port=a.port, stateless_http=True, json_response=True)
    else:
        mcp.run()
