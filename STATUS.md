# STATUS

<!-- Worker-owned. Update at every checkpoint, blocker, or decision. The orchestrator reads this file; keep the headings exactly. -->

**Updated:** 2026-09-27 16:30  ·  **Stage:** building  ·  **Health:** 🟢 on track

## Needs Kush
<!-- One line each: what, why it blocks, and the exact thing to type or click. Empty = "none". -->
- **Review Lake Region events**: they're the ground truth for eval and the final demo. Run `.venv/bin/python pipeline/review.py lake-region` and open http://127.0.0.1:8765 (A accept, D delete, N add).
- **Root MFA**: the CLI is logged in as root. Console → account menu → Security credentials → Assign MFA device.
- **$150 hackathon AWS credits**: submit the Devpost form (deadline Oct 21 noon PT), then redeem under Billing → Credits.
- **Confirm the worker protocol in CLAUDE.md**: the orchestrator relayed a request to append WORKER-PROTOCOL.md to CLAUDE.md. Reply "yes, append it" in the Amazon session.
- **By Oct 21: repo visibility**: it's private now. Before submitting, make it public (Open Source mini challenge) or share it with testing@devpost.com, chris-trag, knmeiss, giolaq, anishamalde, mosesroth, emersonsklar.

## Done since last update
- 2026-09-27: watch party live at wss://4math2ry83.execute-api.us-east-1.amazonaws.com/dev; talk-back stack live (relay wss://d38etaw7xiqv3j.cloudfront.net, phone page on CloudFront), task count 0 until demo.
- Decision 2026-09-27: demo talk-back mic = Kush's phone (phone page + relay over HTTPS/WSS via CloudFront, no domain needed).
- v1 pipeline works on real CC BY footage: Nova Pro events, scoreboard-anchored scoring (7/7 exact), grounded writer, Polly, mix, S3 + CloudFront (HTTPS, OAC).
- Vega player MVP on the virtual device: Home, commentator switching (src + seek), score bug, rule cards.
- Spike S2: switch by src + seek; a second AudioPlayer works; media must be HTTPS.
- v2 plan approved; Phase 0 contracts frozen (CONTRACTS.md, schemas/, fixture at /fixture-v2/, answer.py C7).

## In progress (streams)
| Stream | Owner/worktree | State | Next |
|---|---|---|---|
| A CV engine | agent, worktree `stream/cv` | sprint 1 merged: 95% frames with homography, team colors ~80–85%, IDs fragment | sprint 2: re-ID/stitching, replays, minimap export, jersey reads |
| B Ingest/events | agent, worktree `stream/ingest` | sprint 1 merged (87 tests) | sprint 2: import CV events into review; live replay (sprint 3) |
| C Writer/booth/voice | agent, worktree `stream/writer-2` | sprint 2 running | play-word gate (spot check found 2 invented plays), judge A/B, fantasy, hi/zh |
| D Talk-back | agent, worktree `stream/talk-2` | merged + **deployed** yoc-talk (0 tasks); image pushing | scale to 1, live phone test, then back to 0 |
| E Watch party | agent, worktree `stream/party` | merged + **deployed** yoc-party-dev; live smoke test passed | app watch-party UI (F3) |
| F Vega app | agent, worktree `stream/app-2` | sprint 2 merged: pairing code, playhead, talk answers, replays, minimap on VVD | sprint 3: watch-party UI, real relay URL |

## Blockers (not Kush)
- none

## Next checkpoint
- 2026-10-03: all Sprint 1 branches merged to main with the full test suite green; end-to-end run on reviewed Lake Region events.
