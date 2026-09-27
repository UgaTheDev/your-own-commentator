# STATUS

<!-- Worker-owned. Update at every checkpoint, blocker, or decision. The orchestrator reads this file; keep the headings exactly. -->

**Updated:** 2026-09-27 18:00  ·  **Stage:** building  ·  **Health:** 🟢 on track

## Needs Kush
<!-- One line each: what, why it blocks, and the exact thing to type or click. Empty = "none". -->
- **$20 credit: Bedrock playground**: Bedrock console → Playgrounds → Chat → Nova 2 Lite → send any message.
- **Phone talk-back test**: say "ready for phone test" in the Amazon session; I scale the relay up and send a code.
- **Review Lake Region events**: they're the ground truth for eval and the final demo. Run `.venv/bin/python pipeline/review.py lake-region` and open http://127.0.0.1:8765 (A accept, D delete, N add).
- **Root MFA**: the CLI is logged in as root. Console → account menu → Security credentials → Assign MFA device.
- **$150 hackathon AWS credits**: submit the Devpost form (deadline Oct 21 noon PT), then redeem under Billing → Credits.
- **Confirm the worker protocol in CLAUDE.md**: the orchestrator relayed a request to append WORKER-PROTOCOL.md to CLAUDE.md. Reply "yes, append it" in the Amazon session.
- **By Oct 21: repo visibility**: it's private now. Before submitting, make it public (Open Source mini challenge) or share it with testing@devpost.com, chris-trag, knmeiss, giolaq, anishamalde, mosesroth, emersonsklar.

## Done since last update
- 2026-09-27: README with the Amazon services table and measured numbers; EC2 + RDS credit activities done and cleaned up; ECS scale-only permission.
- 2026-09-27: watch party live at wss://4math2ry83.execute-api.us-east-1.amazonaws.com/dev; talk-back stack live (relay wss://d38etaw7xiqv3j.cloudfront.net, phone page on CloudFront), task count 0 until demo.
- Decision 2026-09-27: demo talk-back mic = Kush's phone (phone page + relay over HTTPS/WSS via CloudFront, no domain needed).
- v1 pipeline works on real CC BY footage: Nova Pro events, scoreboard-anchored scoring (7/7 exact), grounded writer, Polly, mix, S3 + CloudFront (HTTPS, OAC).
- Vega player MVP on the virtual device: Home, commentator switching (src + seek), score bug, rule cards.
- Spike S2: switch by src + seek; a second AudioPlayer works; media must be HTTPS.
- v2 plan approved; Phase 0 contracts frozen (CONTRACTS.md, schemas/, fixture at /fixture-v2/, answer.py C7).

## In progress (streams)
| Stream | Owner/worktree | State | Next |
|---|---|---|---|
| A CV engine | agent, worktree `stream/cv-2` | sprint 2 running | full-clip tracks, ID stitching, ball filter, minimap.json, telestration replays on CloudFront |
| B Ingest/events | agent, worktree `stream/ingest-2` | sprint 2 running | CV events in review, accept-all-scoreboard, live replay (score-graphic facts only) |
| C Writer/booth/voice | done through sprint 2 | merged: play-word gate (0/494 invented plays), 7 tracks, speakable-only manifests | integrator added team-less-actor gate |
| D Talk-back | deployed yoc-talk | live e2e passed (3.4 s answer via public relay); scaled to 0 | Kush phone test |
| E Watch party | agent, worktree `stream/party` | merged + **deployed** yoc-party-dev; live smoke test passed | app watch-party UI (F3) |
| F Vega app | agent, worktree `stream/app-3` | sprint 3 running | watch-party UI, real relay on VVD, 7 track labels, focus leftovers |

## Blockers (not Kush)
- none

## Next checkpoint
- 2026-10-03: all Sprint 1 branches merged to main with the full test suite green; end-to-end run on reviewed Lake Region events.
