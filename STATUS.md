# STATUS

<!-- Worker-owned. Update at every checkpoint, blocker, or decision. The orchestrator reads this file; keep the headings exactly. -->

**Updated:** 2026-09-27 14:10  ·  **Stage:** building  ·  **Health:** 🟢 on track

## Needs Kush
<!-- One line each: what, why it blocks, and the exact thing to type or click. Empty = "none". -->
- **Review Lake Region events**: they're the ground truth for eval and the final demo. Run `.venv/bin/python pipeline/review.py lake-region` and open http://127.0.0.1:8765 (A accept, D delete, N add).
- **Root MFA**: the CLI is logged in as root. Console → account menu → Security credentials → Assign MFA device.
- **$150 hackathon AWS credits**: submit the Devpost form (deadline Oct 21 noon PT), then redeem under Billing → Credits.
- **Confirm the worker protocol in CLAUDE.md**: the orchestrator relayed a request to append WORKER-PROTOCOL.md to CLAUDE.md. Reply "yes, append it" in the Amazon session.
- **Approve public deploys when asked** (~Oct 4–10): the Fargate talk-back relay (stream D) and the watch-party WebSocket API (stream E).
- **By Oct 21: repo visibility**: it's private now. Before submitting, make it public (Open Source mini challenge) or share it with testing@devpost.com, chris-trag, knmeiss, giolaq, anishamalde, mosesroth, emersonsklar.

## Done since last update
- v1 pipeline works on real CC BY footage: Nova Pro events, scoreboard-anchored scoring (7/7 exact), grounded writer, Polly, mix, S3 + CloudFront (HTTPS, OAC).
- Vega player MVP on the virtual device: Home, commentator switching (src + seek), score bug, rule cards.
- Spike S2: switch by src + seek; a second AudioPlayer works; media must be HTTPS.
- v2 plan approved; Phase 0 contracts frozen (CONTRACTS.md, schemas/, fixture at /fixture-v2/, answer.py C7).

## In progress (streams)
| Stream | Owner/worktree | State | Next |
|---|---|---|---|
| A CV engine | agent, worktree `stream/cv` | running (sprint 1) | detection + ByteTrack + team colors + homography on 60 s |
| B Ingest/events | agent, worktree `stream/ingest` | sprint 1 merged (87 tests) | sprint 2: import CV events into review; live replay (sprint 3) |
| C Writer/booth/voice | agent, worktree `stream/writer` | sprint 1 merged: live manifest v2 (booth, 10 Why events, 9 recaps) | sprint 2: fantasy, hi/zh, booth reacts to viewer questions |
| D Talk-back | agent, worktree `stream/talk` | sprint 1 merged: question→answer 2.9 s mean, 0 fallbacks, exact transcripts | sprint 2: Fargate WSS deploy (needs Kush), phone page |
| E Watch party | agent, worktree `stream/party` | sprint 1 merged (22 tests, template validated) | sprint 2: use join.clipId, deploy after Kush approves |
| F Vega app | agent, worktree `stream/app` | running (sprint 1) | Why button + second AudioPlayer, recap, booth, WebSocket spike |

## Blockers (not Kush)
- none

## Next checkpoint
- 2026-10-03: all Sprint 1 branches merged to main with the full test suite green; end-to-end run on reviewed Lake Region events.
