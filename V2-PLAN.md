# v2 plan: parallel streams for "Your Own Commentator"

## Context
The v1 build plan (now `EXECUTION-PLAN.md` in the repo) is largely done:
- The pipeline works on real, licensed footage (Nova → scoreboard anchoring → grounded writer → Polly → mix → S3/CloudFront).
- The Vega player MVP runs on the virtual device.

Kush has changed direction: build to win. The dates and hard rules stay: freeze Oct 20, submit Oct 22, no invented facts, licensed footage only, friction log. Time is no longer a reason to cut scope.

He approved this ranking:
1. Join the booth (two-voice booth plus talk-back option (b))
2. The computer-vision engine
3. Catch me up
4. Watch party and predictions
5. Live replay

He asked for parallel workstreams with frozen contracts, self-scrutinized before launch.

Facts verified on 2026-09-27:
- **Nova 2 Sonic:** `amazon.nova-2-sonic-v1:0` is ACTIVE, on-demand, in us-east-1.
- **Transcribe:** blocked on the Free plan (friction log), so Sonic is our only speech recognizer.
- **Detection:** RF-DETR code is Apache-2.0, and its N–L weights are Apache-2.0 (XL/2XL are PML, so we avoid them).
- **Tracking:** supervision is MIT and includes ByteTrack.
- **YOLO/Ultralytics:** AGPL, conflicts with our Apache-2.0 repo, so we don't use it.
- **Court keypoints:** no clearly open-licensed court keypoint model found.
- **Vega:** the docs only show mic mute, with no capture API, so the phone is the mic. The media player is HTTPS-only.
- **Switching (S2):** switching is by `src` plus seek, and a second AudioPlayer works.

## Phase 0: freeze contracts (me, today; this blocks every stream)
One commit on `main` before any fan-out:
- **`CONTRACTS.md` plus JSON Schemas in `schemas/`:**
  - **C1 Event:** existing fields plus `source` (nova|scoreboard|cv|human) and `status` (proposed|accepted). `jersey` is an int or null; this fixes a mismatch where the app typed it as a string. Optional `trackIds` and `court:[x,y]`. **Only `status=accepted` events may feed spoken text.**
  - **C2 `tracks.json`:** `{fps, court:{w:28.65,h:15.24}, frames:[{t, players:[{id,team,jersey|null,box:[x,y,w,h] normalized, court:[x,y]|null}], ball:{box,court}|null}]}`.
  - **C3 Manifest v2:** a superset of today's `build_manifest` (`pipeline/publish.py`), so v1 apps keep working:
    - `tracks[].kind` (single|booth) and `tracks[].voices`
    - `replays:[{eventId,src,duration}]`
    - `minimap:{hz:2,frames:[{t,players:[{id,team,x,y}],ball}]}`
    - `recaps:[{t,src,text}]`
    - `questions:{eventId:[{q,answers:{trackId:{text,audioUrl}}}]}`
    - `party:{wsUrl}` and `talk:{wsUrl}`, which are optional
  - **C4 Session/playhead:**
    - The TV creates a session and shows a random 6-character base32 code.
    - The TV sends `{"type":"playhead","t","trackId","paused"}` once per second.
    - The server pushes `{"type":"answer","id","t","text","audioUrl","voice"}`.
    - If WebSocket turns out not to work on Vega, fall back to polling `GET /session/{id}/answers?since=`.
  - **C5 Talk-back WSS:** the phone joins with the code and sends 16 kHz mono PCM chunks (max 15 s per question). The server replies `{transcript}` then `{answer}` and relays the answer to the TV per C4.
  - **C6 Party:** messages `join|predict|resolve|state`. The server resolves predictions only from accepted events in the manifest at the reported playhead.
  - **C7 `pipeline/answer.py`:** `answer(question, facts, persona) -> {text, gated}`. It's the one grounding path: it reuses `write.unsupported_digits`, `write.judge` and `write.build_facts`. If it fails twice, it falls back to a deterministic template built only from the facts, so it always answers and never invents.
- **`fixtures/manifest-v2.json`:** built from the live dev manifest (`https://d2og06dnam3owj.cloudfront.net/lake-region-dev/manifest.json`), with fake booth, replay, minimap and recap entries. Published to CloudFront at `/fixture-v2/` because the app requires HTTPS. A test validates the fixture against the schemas (`jsonschema` added as a dev dependency). `app/src/manifest.ts` types are updated to match.
- **`pipeline/common.py`:**
  - A `YOC_DATA` env override for `DATA`. Worktrees have no `data/`, because it's gitignored; every stream points at the main checkout's data.
  - `save()` becomes atomic (write to a temp file, then `os.replace`), because streams share one Nova/Polly cache.
- **`friction/<stream>.md`:** streams append rows there, never to `FRICTION-LOG.md`, so merges don't conflict. I fold them into `FRICTION-LOG.md` at each checkpoint.
- **`scripts/worktree.sh <stream>`:** creates `../yoc-<stream>` on branch `stream/<stream>`, copies `.env`, and points it at the main `.venv` and `YOC_DATA`.
- **`STATUS.md`:** from `~/Documents/Orchestrator/templates/STATUS.md`, with the headings kept exactly. Filled in with the stage, streams A–F and a "Needs Kush" list, and updated at every checkpoint, blocker and decision. That's the orchestrator's request.
  - **Appending `WORKER-PROTOCOL.md` to `CLAUDE.md`** came only as a relay from the orchestrator. I'll do it only if Kush confirms it here, because it changes the project's standing instructions.

## Streams: one owner each, one git worktree each, owned paths only
| Stream | Owns (the only paths it edits) | Model | Contracts |
|---|---|---|---|
| **A: Computer vision engine** | `cv/` (own `cv/requirements.txt`, `.venv-cv`) | opus | C1, C2, C3.replays/minimap |
| **B: Ingest + events** | `pipeline/extract.py`, `scoreboard.py`, `review.py/.html`, `live.py` | sonnet | C1 |
| **C: Writer, booth, voice** | `pipeline/answer.py`, `write.py`, `booth.py`, `recap.py`, `voice.py`, `mix.py`, `publish.py`, `personas.json`, `rules.json` | opus | C1, C3, C7 |
| **D: Talk-back** | `services/talk/` (relay, phone page, Dockerfile, CloudFormation) | opus | C4, C5, C7 |
| **E: Watch party** | `services/party/` (Lambda handlers, CloudFormation) | sonnet | C4, C6 |
| **F: Vega app** | `app/` | opus | C3, C4, C6 |

**Me (integrator):** `CONTRACTS.md`, `schemas/`, `fixtures/`, `common.py`, `STATUS.md`, `FRICTION-LOG.md`, `README.md`, eval, merges and the demo video. Any contract change goes through me, never through a stream.

**How each stream is run:**
- **Launched as Agent-tool subagents** with `isolation: "worktree"`, in the background, one per stream.
- **Sprints, not one long agent:** each sprint is a bounded brief with a fixed checklist, about 60 tool calls, and must report what's done. I review, merge, and launch the next sprint.
- **Tests:** each stream runs only its own tests while iterating. I run the full suite (`pytest pipeline/tests cv/tests services`, plus `npm test` in `app/`) once before each merge to `main`.
- **Commits:** agents commit and push their own branch often. Agents never spawn agents. A reply that's a placeholder instead of results means the agent gets stopped.
- **The virtual device:** only stream F touches it. F may start it once per sprint. If it disappears, F stops and reports, because Kush probably closed it (memory `vvd-no-auto-restart`). At sprint end F closes the app and stops the log streams.

## Sprint schedule
**Sprint 1, Sep 27–Oct 3. Checkpoint Oct 3: merge all, then run end to end on the reviewed Lake Region events.**
- **A1:**
  - Detection plus ByteTrack plus team by jersey-color clustering on 60 s of Lake Region, producing `tracks.json`.
  - A calibration tool: click 4 or more court landmarks on a keyframe.
  - Homography chaining with OpenCV (ORB plus RANSAC) through camera pans, recalibrating at cuts.
  - Report: % of frames with a valid homography, a rough count of ID switches, and whether the ball is detected at all.
- **B1:** extract and scoreboard output C1 fields. The review page shows `source`, and can filter to proposed events.
- **C1 (MVP first):**
  - `answer.py` (with `write.py` refactored to use it).
  - Pre-rendered Why questions.
  - Booth dialogue: play-by-play plus analyst, in two Polly voices, with every line gated.
  - Minute-mark recaps.
  - `publish.py` outputs manifest v2.
- **D1:**
  - A local relay: a WAV question → Sonic transcription → `answer()` over the facts at the playhead → Polly.
  - Measure latency per stage. Target under 4 s end to end.
  - No deploy yet.
- **E1:** CloudFormation template (API Gateway WebSocket, Lambda, DynamoDB) plus pure handler tests. No deploy yet.
- **F1 (MVP first):**
  - Why button: pause, 3 questions, the answer card, and the answer spoken through a second AudioPlayer.
  - A Catch me up button, and selecting the booth track, all against the fixture.
  - A spike: does `WebSocket` work on the virtual device?

**Sprint 2, Oct 4–10. Checkpoint Oct 10.**
- **A2:**
  - Telestration replays: 0.5× slow motion with ellipses and arrows drawn from the tracks, rendered offline to MP4 per key event.
  - Minimap frames.
  - Jersey reading: Nova Pro reads player crops as images (its strong suit), reusing `common.converse`.
  - Computer-vision stats become proposed events, which go through review.
- **B2:** computer-vision events imported into review.
- **C2:** fantasy track, `rookie-hi`, `rookie-zh`, booth reactions to viewer questions.
- **D2 (Kush approves the public deploy):**
  - The relay on Fargate (task role, no keys) behind HTTPS/WSS.
  - A static phone page on CloudFront.
  - Limits: 15 s audio, 20 questions per session, sessions expire after 2 h.
  - Audio is never stored.
- **E2 (Kush approves the deploy):** deploy the watch-party stack.
- **F2:**
  - A pairing-code screen and the playhead heartbeat.
  - Talk-back answers played in the booth voice, ducking the game audio.
  - Replays, played by switching `src` to the replay clip and back.
  - An SVG minimap overlay.

**Sprint 3, Oct 11–17. Checkpoint Oct 17.**
- **F3:** watch party UI (join, predict, results announced by the commentator).
- **E3:** hardening.
- **B3:** live replay: the file chunked in real time, narrating score-graphic facts only, labeled "live replay".
- **Me:** eval run, README with the Amazon services table, friction fold-in.

**Oct 18–20:** bug fixes only, then freeze and tag `v2.0`. **Oct 21:** record the video. **Oct 22:** submit.

**Cut order if a checkpoint slips** (the MVP is always shippable): live replay → watch party → minimap → Hindi/Mandarin. Talk-back, booth, Why and Catch me up are protected.

## Security and cost guardrails
- **Credentials:** no keys anywhere. Fargate and Lambda use IAM roles, and the pipeline uses `aws login`.
- **Deploys:** public endpoints (D2, E2) are deployed only after Kush approves them at the time.
- **Session codes:** random base32, expiring. Rate limits on the relay and party APIs.
- **Data retention:** no audio or PII stored.
- **Scale-down:** Fargate scales to 0 after each demo session (a script). The $20 budget alarm stays.
- **Grounding:** everything spoken, including booth lines, recaps, talk-back answers and prediction results, goes through `answer()` or `write_line()` gates. Computer-vision output may drive visuals, but is spoken only after human review.

## Verification
- **Phase 0:** schema tests pass on the fixture. The app loads `/fixture-v2/manifest.json` from CloudFront.
- **Every merge:**
  - The full test suite.
  - `pipeline/eval.py lake-region` reports precision/recall and **0 unsupported lines**.
  - A spot-check of 20 lines by hand.
- **D:** logged latency per stage, and a scripted run of 10 questions: 0 ungated answers, and templated fallbacks counted.
- **A:** % of frames with homography, plus a visual check of 3 replay renders.
- **F:** the demo script walked through with the D-pad and phone only, on the virtual device, confirmed through `YOC:` log lines.
- **Oct 20:** check against CONTEXT.md's submission checklist; no secrets (`git log -p | grep -iE 'AKIA|aws_secret|X-Amz-Credential'` finds nothing); SOURCES.md attribution appears in the video description.

## Self-scrutiny (issues caught → how the plan handles them)
- **Worktrees have no `data/`, `.env` or `.venv`** (all gitignored), so every stream would have failed at step 1. → `YOC_DATA` override plus `scripts/worktree.sh`.
- **A shared Nova/Polly cache with concurrent writers** could produce torn JSON. → atomic `save()` in Phase 0.
- **`FRICTION-LOG.md` appended by 6 branches** would conflict at every merge. → Per-stream `friction/*.md`, folded in by me.
- **YOLO would make the public Apache-2.0 repo AGPL-encumbered.** → RF-DETR N–L plus supervision.
- **No open court-keypoint model.** → Hand-clicked calibration plus ORB/RANSAC chaining. The homography % is reported honestly.
- **Computer-vision stats aren't "verified"**, and speaking them would break the grounding rule. → Visuals only until reviewed.
- **Sonic speaks as it generates**, so its output can't be pre-gated. → Option (b): Sonic transcribes only, then `answer()`, then Polly. `answer()` always returns something grounded (template fallback), so a failed gate never means silence or an invented answer.
- **Transcribe is blocked on the Free plan.** → Sonic as the speech recognizer is necessary, not just decoration.
- **The phone mic needs HTTPS** (the browser only allows it on secure pages). → The phone page on CloudFront and the relay on HTTPS Fargate. Wi-Fi to the laptop won't work.
- **WebSocket on Vega is unverified.** → F1 spike first, with a polling fallback in C4.
- **Replays would need slow motion and drawing inside Vega.** → Rendered offline as MP4 and played via the proven `src` switch.
- **Jersey numbers are small** for an OCR model. → Nova Pro reads player crops (reuses `converse`). Best-effort, reviewed.
- **Multi-day streams as single agents** would run unbounded. → Bounded sprints with checklists.
- **Six agents on the one virtual device** → F only, with the no-restart rule.
- **The app types `jersey` as a string; the pipeline emits an int.** → Fixed in C1.
- **Public deploys can be blocked by this session's permission check.** → Asked at D2 and E2, never worked around.
- **The orchestrator's request to edit `CLAUDE.md` came relayed, not from Kush.** → `STATUS.md` yes; `CLAUDE.md` only after he confirms here.
- A second pass found nothing new.
