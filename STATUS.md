# STATUS

<!-- Worker-owned. Update at every checkpoint, blocker, or decision. The orchestrator reads this file; keep the headings exactly. -->

**Updated:** 2026-10-20  ·  **Stage:** freeze  ·  **Health:** 🟢 on track

## Needs Kush
<!-- One line each: what, why it blocks, and the exact thing to type or click. Empty = "none". -->
- **Watch the demo video** (2:29): `scripts/demo/out/YourOwnCommentator-demo.mp4` (Finder has it selected). Say what to change.
- **Upload it** to YouTube (Public or Unlisted), title "Your Own Commentator: pick your own sports commentator on Fire TV", description = the attribution line in SOURCES.md.
- **Submit on Devpost (by Oct 22)**: paste DEVPOST.md sections + the video link; repo https://github.com/UgaTheDev/your-own-commentator (public).

## Done since last update
- 2026-10-20 (pm): app redesign (control-room theme, game cards, single-row controls); phone page restyle; phone talk-back test passed on the real relay; demo video recorded fully automated (ScreenCaptureKit window capture with device audio, remote keys driven by the app's playhead log, Polly narration + cards) and cut to 2:29; caught and fixed a recap that said 5 points for 4 (jersey numbers now only count as jerseys), re-audited all 3 games: 0 failures; relay scaled to 0.
- 2026-10-20: freeze pass. Full suite green (174 pipeline, 21 CV, 24 app); fixed replay CDN URL scheme bug in cv/publish_replays.py; secret scan of history clean; published game outputs committed; DEVPOST.md and VIDEO.md drafted. Dropped by Kush: root MFA, Bedrock playground credit. Worker protocol: not added (STATUS.md already serves the orchestrator).
- 2026-09-28: 3 licensed games live (games index https://d2og06dnam3owj.cloudfront.net/clips.json); score-graphic reader points-exact on all 3, Nova video-only 5/182 (P=0.03); verified jerseys (3/7), 64 s highlight reel, game picker, Alexa+ MCP server (local). Gate now checks spelled-out numbers (en/es/zh), spelled jerseys, pronouns; all 3 live manifests audited 0 mismatched numbers. Friction log 40 rows.
- 2026-09-27: all v2 streams merged. Demo manifest (reviewed events only) live with 7 tracks, 9 recaps, 7 replays, minimap, talk + party URLs. Eval: scoreboard 7/7 (P=1.00), Nova video-only P=0.03.
- 2026-09-27: Kush submitted the $150 credits form (redeem the code under Billing → Credits when it arrives). Lake Region review delegated to an AI reviewer at Kush's request; events tagged reviewedBy=claude.
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
| A CV engine | done (sprint 2 merged) | full-clip tracks 96.7% homography, 7 ellipse-only replays + minimap live in demo manifest | optional: ball model for highlight rings |
| B Ingest/events | done (sprint 2 merged) | live replay proven w/ upload (7.6 s latency), CV merge + Shift+A in review | — |
| C Writer/booth/voice | done through sprint 2 | merged: play-word gate (0/494 invented plays), 7 tracks, speakable-only manifests | integrator added team-less-actor gate |
| D Talk-back | deployed yoc-talk | live e2e passed (3.4 s answer via public relay); scaled to 0 | Kush phone test |
| E Watch party | agent, worktree `stream/party` | merged + **deployed** yoc-party-dev; live smoke test passed | app watch-party UI (F3) |
| F Vega app | done (sprint 3 merged) | watch party + real talk-back on VVD (2.4 s), defaults to demo manifest | final walkthrough |

## Blockers (not Kush)
- none

## Next checkpoint
- 2026-10-03: all Sprint 1 branches merged to main with the full test suite green; end-to-end run on reviewed Lake Region events.
