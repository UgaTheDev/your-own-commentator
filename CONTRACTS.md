# Contracts (frozen 2026-09-27)

Every v2 stream builds against these. **A stream never changes a contract**; ask the integrator,
who changes the schema, the fixture and this file in one commit on `main`.

Machine-checked schemas are in `schemas/`; `pipeline/tests/test_contracts.py` validates
`fixtures/manifest-v2.json` against them. The fixture is also served over HTTPS at
`https://d2og06dnam3owj.cloudfront.net/fixture-v2/manifest.json` (Vega media is HTTPS-only).

## The grounding rule, in contract form
- Only events with `status: "accepted"` may feed anything spoken.
- Everything spoken (track lines, booth lines, recaps, Why answers, talk-back answers,
  prediction results) goes through `write.write_line()` or `answer.answer()`, which run the
  digit gate and the Bedrock judge. Computer-vision output may drive visuals (minimap,
  telestration) but is spoken only after a human accepts it in review.

## C1 Event (`schemas/event.schema.json`)
`events.proposed.json` / `events.reviewed.json` are arrays of:
```json
{"id": "e7", "t": 63.5, "type": "made_3", "team": "blue", "jersey": 23,
 "confidence": 1.0, "source": "scoreboard", "status": "accepted",
 "trackIds": [4], "court": [21.3, 7.1]}
```
- `type`: `state.EVENT_TYPES` (`made_2 made_3 ft_made ft_missed missed_shot foul travel turnover steal block rebound timeout`).
- `team`: one of `clip.json` `teams`, or null (only `timeout` may be null after review).
- `jersey`: integer or null. `source`: `nova | scoreboard | cv | human`. `status`: `proposed | accepted`.
- `trackIds`, `court` (meters, origin at a corner, x along the length): optional, from CV.

## C2 Tracks (`schemas/tracks.schema.json`), `data/<clip>/tracks.json`
```json
{"fps": 10, "court": {"w": 28.65, "h": 15.24},
 "frames": [{"t": 12.3, "players": [{"id": 4, "team": "pink", "jersey": null,
   "box": [0.41, 0.33, 0.04, 0.16], "court": [9.2, 5.5]}],
   "ball": {"box": [0.5, 0.4, 0.01, 0.01], "court": null}}]}
```
`box` is normalized `[x, y, w, h]` (top-left origin). `court` is null when that frame has no homography.

## C3 Manifest v2 (`schemas/manifest.schema.json`)
A superset of v1 (`pipeline/publish.py build_manifest`), so the v1 app keeps working. **`events` in a published
manifest are only speakable events** (status accepted, or every event of a dev clip published with
`--allow-unreviewed`), so consumers like the watch party treat them as accepted. New optional keys:
- `tracks[].kind`: `single` (default) or `booth`; `tracks[].voices`: `[{role: "pbp"|"analyst", voice}]`.
- `replays`: `[{eventId, src, duration}]`: pre-rendered slow-motion telestration MP4s.
- `minimap`: `{hz: 2, frames: [{t, players: [{id, team, x, y}], ball: {x, y} | null}]}`, in meters.
- `recaps`: `[{t, src, text}]`: the voiced catch-up to play when the viewer returns at time >= `t`.
- `questions`: `{eventId: [{q, answers: {trackId: {text, audioUrl}}}]}`: pre-rendered Why answers.
- `talk`: `{wsUrl}`, `party`: `{wsUrl}`: present only when those services are deployed.

## C4 Session and playhead (TV <-> backend, WebSocket; JSON text frames)
- TV -> `{"type": "hello", "clipId"}`; server -> `{"type": "session", "code": "K7Q2MX"}` (6-char base32, expires in 2 h).
- TV -> `{"type": "playhead", "t": 63.2, "trackId": "rookie-en", "paused": false}` every 1 s.
- server -> `{"type": "answer", "id", "t", "text", "audioUrl", "voice"}` (play in the second AudioPlayer, duck the video).
- Fallback if WebSocket fails on Vega: `POST /session/{code}/playhead` and `GET /session/{code}/answers?since=<id>` polled each second.

## C5 Talk-back (phone <-> relay, WSS)
- phone -> `{"type": "join", "code"}`, then per question: `{"type": "start"}`, binary frames of 16 kHz mono
  signed 16-bit PCM (max 15 s), `{"type": "stop"}`.
- relay -> `{"type": "transcript", "text"}`, then `{"type": "answer", "text", "audioUrl"}`; the same answer
  goes to the paired TV as a C4 `answer`.
- Limits: 20 questions per session; audio is never stored.

## C6 Watch party (WebSocket)
- client -> `{"type": "join", "code", "name", "trackId", "clipId"}`. `clipId` (added 2026-09-27) tells the room which manifest settles predictions; the first joiner's clipId wins.
- client -> `{"type": "predict", "kind": "next_score_team", "value": "pink"}`
- server -> `{"type": "resolve", "predictionId", "correct", "eventId"}`: only from an **accepted** event
  after the prediction's playhead.
- server -> `{"type": "state", "members": [{name, trackId, points}]}`

## C7 `pipeline/answer.py`
```python
answer(question: str, facts: dict, persona: dict) -> {"text": str, "gated": bool, "fallback": bool}
facts_at(t: float, manifest_or_dir) -> dict   # event + state + rule card at the playhead, plus the last 30 s of events
```
Same gates as `write.write_line`. If both attempts fail, it returns a deterministic template built only from
`facts` (`fallback: true`). It never returns an ungated model sentence.

## Shared environment for worktrees
`source <main checkout>/scripts/stream-env.sh` sets `YOC_DATA` (the main `data/`, since worktrees have none),
`PY` (the main `.venv` python) and copies `.env` in if missing. Friction rows go to `friction/<stream>.md`,
never `FRICTION-LOG.md`.
