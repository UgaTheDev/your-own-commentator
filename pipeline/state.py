"""Deterministic game state from reviewed events.

Usage: python pipeline/state.py <clip_id>
Reads clip.json + events.reviewed.json, writes state.json (one entry per event).
Every number the commentary may say comes from here, so it must be exact.
"""
import json
import sys

import common

POINTS = {"made_2": 2, "made_3": 3, "ft_made": 1}
FANTASY = {"rebound": 1.2, "steal": 3, "block": 3, "turnover": -1}  # plus 1 per point
EVENT_TYPES = set(POINTS) | set(FANTASY) | {"ft_missed", "missed_shot", "foul", "travel", "timeout"}
NEEDS_TEAM = EVENT_TYPES - {"timeout"}
AND_ONE_WINDOW = 1.0  # seconds between a made shot and the foul on it


def compute(clip, events):
    teams = clip["teams"]
    score = {team: clip["start_score"][team] for team in teams}
    fouls = {team: 0 for team in teams}
    fantasy = {}
    events = sorted(events, key=lambda e: e["t"])

    for e in events:
        if e["type"] not in EVENT_TYPES:
            raise ValueError(f"event {e['id']}: unknown type {e['type']!r}")
        if e["type"] in NEEDS_TEAM and e.get("team") not in teams:
            raise ValueError(f"event {e['id']}: team {e.get('team')!r} not in {teams}")

    states = []
    for i, e in enumerate(events):
        kind, team = e["type"], e.get("team")
        player = f"{team}#{e['jersey']}" if e.get("jersey") is not None else None
        if kind in POINTS:
            score[team] += POINTS[kind]
        if kind == "foul":
            fouls[team] += 1
        delta = POINTS.get(kind, 0) + FANTASY.get(kind, 0)
        if player and delta:
            fantasy[player] = round(fantasy.get(player, 0) + delta, 1)  # round: 1.2 accumulates float error
        states.append({
            "eventId": e["id"],
            "t": e["t"],
            "score": dict(score),
            "teamFouls": dict(fouls),
            "fantasy": dict(fantasy),
            "fantasyDelta": {player: delta} if player and delta else {},
            "andOne": kind in ("made_2", "made_3") and _fouled_on_shot(events, i),
        })
    final = clip.get("final_score")
    if final is not None and score != final:
        raise ValueError(f"computed final score {score} != clip final_score {final}; an event is missing or wrong in review")
    return states


def _fouled_on_shot(events, i):
    # ponytail: O(n^2) scan, fine for a few hundred events per clip
    shot = events[i]
    for other in events:
        if other["type"] == "foul" and other.get("team") != shot["team"] and abs(other["t"] - shot["t"]) <= AND_ONE_WINDOW:
            return True
    return False


if __name__ == "__main__":
    clip_dir = common.clip_dir(sys.argv[1])
    clip = json.loads((clip_dir / "clip.json").read_text())
    events = json.loads((clip_dir / "events.reviewed.json").read_text())
    states = compute(clip, events)
    (clip_dir / "state.json").write_text(json.dumps(states, indent=2, ensure_ascii=False))
    print(f"{len(states)} states, final {states[-1]['score'] if states else clip['start_score']}")
