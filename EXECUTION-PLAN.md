# Execution plan: Your Own Commentator (Fire TV / Vega)

## Context
The repo holds only planning docs (CONTEXT.md, PLAN.md, FRICTION-LOG.md, LICENSE). We have to ship a demo-ready Vega OS app plus a demo video under 3 minutes by **Oct 22** (hard deadline Oct 23, 12:00 PM PT), with code freeze on the night of **Oct 20**. This plan turns PLAN.md's architecture into build steps, using facts verified on 2026-09-26 and your answers:
- **Simulator only.** The Vega Virtual Device (VVD) on your Mac. The rules accept simulator footage.
- **Footage not booked yet.** Build everything on a CC-BY clip now and swap in our own BU game when it's filmed (target Oct 10).
- **Why button first.** Add an MCP server only if time is left after Oct 17. Spend 2 hours checking Alexa+ access in week 1.
- **No AWS account.** Account setup happens on day 1.

### Verified facts that shape the design
- **Vega app stack:** React Native with `@amazon-devices/react-native-w3cmedia` (`VideoPlayer`, `KeplerVideoView`). You must call `initialize()` before `src`. The API supports `currentTime`, `timeupdate` and `volume`. Plain MP4 plays directly; HLS/DASH needs Shaka. The docs don't say whether **two players can run at once**, so a spike has to answer that.
- **Reference app:** `AmazonAppDev/vega-video-sample` (MIT-0). We copy its `FocusableElement` and D-pad focus pattern, not the whole app, which also carries IAP and Redux.
- **Nova 2 Lite video input:** samples at 1 fps, squashes every frame to 672×672, ignores audio, reads small text poorly and can't identify people. It will miss jersey numbers and travels. So Nova only **proposes** events, and human review is what makes them true, which the plan already assumed.
- **Polly voices:** Matthew (en-US neural newscaster style), Kevin or Justin (en-US child neural voices, for Kid), Lupe or Pedro (es-US generative), Kajal (hi-IN neural), Zhiyu (cmn-CN neural).
- **Alexa+:** MCP integrations are in "Preview." Nothing documents Fire TV app context. So we build the Why button.

## Key design decisions
1. **All commentary is rendered ahead of time, with no runtime backend.** The pipeline writes a static manifest plus media to S3/CloudFront, and the app only reads it. Live-replay mode is **cut**: it doesn't fit before the Oct 20 freeze.
2. **Audio switching needs no mixing on the device.** ffmpeg mixes each commentary track into the game audio offline, ducking the crowd sound under each line. The app switches tracks in one of three ways. Spike S2 tries them in order and we take the first that works:
   a. one MP4 with N audio tracks, switched through `audioTracks[i].enabled`
   b. HLS with alternate audio renditions through Shaka
   c. **fallback that always works:** one MP4 per track, switched by setting `src` and seeking to the saved `currentTime` (about a 1 s rebuffer, which reads as a channel change)
3. **Track matrix (MVP):** `rookie-en`, `kid-en`, `rookie-es`. Stretch: `fantasy-en`, `rookie-hi`, `rookie-zh`. Languages apply to Rookie only. Five personas × five languages would be 25 tracks for the same demo value.
4. **Fantasy commentary doesn't depend on the roster.** The voice covers the fantasy points of the players in each play. The on-screen panel highlights *your* roster and is computed on the device from the game state. That means no rendering per user.
5. **"Why?" answers are pre-generated.** Each teachable event (foul, travel, turnover, and-one) gets up to 3 suggested questions, and each question gets an answer per track. Pressing Why pauses the video and shows an answer card. The answer audio plays in a second player if spike S2 shows two players can run at once. Otherwise it's a text card only.
6. **The grounding rule is enforced in code.** The writer's allowed facts are `event + game state + rules.json entry`. The rules file is a rules knowledge base we write by hand, so Rookie's rule explanations count as grounded input and don't break the rule in CLAUDE.md. The writer is told to write numbers as digits. A check then rejects any line containing a digit sequence that isn't in the allowed facts. That catches invented scores and jerseys in every language. Invented names and claims, and numbers spelled out as words (like "tres"), can't be caught by a regex across languages, so a second Bedrock call judges them. The two checks together make the gate. Failed lines are regenerated once and dropped after that.
7. **Players are named only with consent.** `clip.json`'s `roster` maps jersey numbers to the first names the players agreed to. Signed consent forms stay **out of the repo**.
8. **Models and region:** Nova 2 Lite for event extraction, and Nova for writing (it counts as Amazon ecosystem depth). Everything runs in `us-east-1`, where Polly's generative voices exist; Nova 2 availability there gets checked during S0. Model IDs sit in one constant and are checked in the Bedrock console, not taken from memory.
9. **Clip metadata is entered by hand** in `data/<clip>/clip.json`: `start_score` (clips start mid-game), `final_score`, teams and a license/attribution line. `state.py` **asserts** that the computed final score equals `final_score`, so a basket missed in review fails loudly instead of the commentary stating a wrong score.
10. **Dropped from PLAN.md:** the DynamoDB profile, Lambda and QR companion. The persona defaults to Rookie on launch, and the fantasy roster is picked on the TV from the clip's roster list. The AWS Builder stack is Bedrock (Nova) + Polly + S3 + CloudFront.

## Repo layout (create only what's listed)
```
pipeline/                 Python 3.11, requirements.txt (boto3 only); system deps: ffmpeg (brew)
  common.py               paths, model IDs, S3 helpers, content-hash cache (avoids repeat Bedrock/Polly spend)
  extract.py              ffmpeg 20s chunks (720p, <25 MB, sent inline as bytes, so extraction needs no S3) with 5s overlap -> Nova -> events.proposed.json (dedupe across overlap: same type within ±2s)
  review.py + review.html stdlib http.server on 127.0.0.1: <video> + event table + running score; keyboard accept/edit/add; saves events.reviewed.json (clip id checked against existing data dirs, no path traversal)
  state.py                deterministic: events -> per-event game state (score, team fouls, per-player fantasy pts)
  write.py                persona x event -> line; word budget = gap to next event; grounding check + judge
  voice.py                Polly per line; measure real duration; if it overruns the gap, regenerate shorter or drop by priority
  mix.py                  ffmpeg: loudnorm voices, adelay + amix + sidechain duck -> output format picked by S2; always `-movflags +faststart` so seeking works
  publish.py              upload to S3, write manifest.json, CloudFront invalidation
  eval.py                 precision/recall per event type (±2s) vs reviewed; faithfulness counts -> eval/results.md
  rules.json personas.json
  tests/test_state.py tests/test_grounding.py
app/                      Vega RN app (from `vega` CLI template)
  src/screens/Home.tsx    clip card + persona/language picker (D-pad)
  src/screens/Player.tsx  video, quick-switch overlay, rule-card overlay, fantasy panel, Why button + answer card
  src/manifest.ts         types + fetch + cue lookup (binary search on sorted t) + one jest test for the lookup
  src/FocusableElement.tsx  adapted from vega-video-sample
data/<clip>/              raw media gitignored; small reviewed JSON committed
README.md ATTRIBUTION.md FRICTION-LOG.md
```

**Manifest (the single contract between pipeline and app):**
`{clipId, videoUrl, tracks:[{id,persona,lang,label,src|audioTrackIndex}], events:[{id,t,type,team,jersey,ruleCardId}], cues:{trackId:[{t,eventId,text}]}, ruleCards:{id:{title,body}}, state:[{t,score,fantasy:{jersey:pts}}], questions:{eventId:[{q,answers:{trackId:{text,audioUrl}}}]}, roster:[{jersey,team,name}]}`

**Event types (kept small):** `made_2, made_3, ft_made, ft_missed, missed_shot, foul, travel, turnover, steal, block, rebound, timeout`. `and_one` isn't extracted; `state.py` derives it from a made shot plus a foul within 1 s. There's no shot-clock event because intramural games often don't have a shot clock. Fantasy scoring uses only these types: points ×1, rebound 1.2, steal/block 3, turnover −1.

## Schedule (NVIDIA work stays in the background)
| Dates | Work | Exit criterion |
|---|---|---|
| **Sep 27 (Sun)** | **S0 setup:** create the AWS account, turn on MFA, create an IAM user limited to Bedrock, Polly, S3 and CloudFront, set a $20 budget alarm, **request the $150 credits**, enable Bedrock model access. Write the consent form and message the BU intramural/club contacts. Ask the BU rec center for permission to film at the venue. Find the CC-BY basketball clip and record its license in ATTRIBUTION.md. | Credits requested; a `bedrock converse` hello works from the CLI |
| **Sep 28 (Mon)** | **S1:** install the Vega tools (prerequisites: Rosetta 2, Java 21+, Node 18–20, latest SDK, since older builds had Apple Silicon VVD crashes) and run the `vega` template on the VVD. Check that the VVD can reach an HTTP server on the host Mac. If it can't, use S3 + CloudFront from day 1. **Test recording the VVD with audio** (macOS screen capture, plus BlackHole if system audio isn't captured) so Oct 21 isn't the first try. **S2 audio spike:** test options 2a, 2b and 2c, and whether two players can run at once. Update PLAN.md's decisions table (basketball, Vega, AWS Builder, Why button, live mode cut). | Video plays on the VVD; S2 result written into PLAN.md |
| Sep 29–Oct 1 | **S3:** extract.py on the CC-BY clip plus a rough review.py. **S4:** 2-hour Alexa+ for Builders access check, logged in the friction log. | `events.proposed.json` for a 2-minute clip; first precision/recall numbers |
| Oct 2–3 | state.py plus tests; rules.json for all event types; personas.json | `pytest pipeline/tests` passes |
| **Oct 4–7** | write.py with grounding check plus judge; voice.py; mix.py; publish.py (a local `python -m http.server` stands in for CloudFront during development) | **End-to-end on one clip:** `rookie-en` and `kid-en` play synced on the VVD |
| Oct 8–10 | Player: rule-card overlay, quick switch, Home picker, 10-foot styling. **Film the BU game** (players' consent and venue permission in hand) and run it through the pipeline plus review. Record a 30-second rehearsal of the video. | Three MVP tracks on our own footage |
| Oct 11–14 | Why button: questions in write.py, answer card and audio. Fantasy panel plus `fantasy-en`. | Demo script sections 0:15–1:35 can be performed end to end |
| Oct 15–17 | `rookie-hi` and `rookie-zh`; eval.py run on the final clip; switch to S3 + CloudFront with OAC; README with an "Amazon services used, where, why" table | Numbers in eval/results.md; app loads the manifest from CloudFront |
| Oct 18–20 | Stretch, only if everything above is green: an MCP server exposing `get_current_play`, `explain_play` and `fantasy_impact`, reading manifest.json. Otherwise polish. **Freeze the night of Oct 20.** | Tagged `v1.0` |
| Oct 21 | Record the video on the VVD (screen capture plus our own voiceover, no music); write the description, product feedback, feature requests and final friction log | Video under 3:00, public on YouTube |
| **Oct 22** | Submit on Devpost; re-read the rules page first | Confirmation email |

**Cut order if we slip:** MCP server → hi/zh → fantasy → Why audio (keep the text card) → Home screen polish. The MVP floor is Rookie + Kid + Spanish + Why text card.

## Risks and holes addressed
- **Nova recall is low (expected).** Human review is where the ground truth comes from, and we report the real precision/recall per event type anyway.
- **Voice lines overrun the next play.** Measure the actual Polly duration, not an estimated word count. Spanish, Hindi and Mandarin speak at different rates, so a fixed 2.5 words/sec budget would get them wrong.
- **Two plays close together.** A line is placed at `t+0.4s`. A lower-priority event's line gets dropped if it would overlap a higher one (priority: score > foul/violation > rest).
- **Translation drift.** Lines are generated directly in the target language from the same allowed facts. The grounding check compares numerals and jerseys across languages.
- **Rebuffer on switch (option 2c).** The UI shows the persona label during the ~1 s gap and saves `currentTime` before the swap.
- **Filming slips past Oct 10.** Ship on the CC-BY clip with attribution. That's already the development path, so nothing breaks.
- **Security.** No keys in the repo (`.env` is gitignored, and the pipeline uses the AWS profile). The S3 bucket stays private and CloudFront reads it through OAC, serving only `published/`. Consent forms and full player names stay out of git. review.py binds to 127.0.0.1 only.
- **Cost.** The content-hash cache means an unchanged input never re-calls Bedrock or Polly. The budget alarm is $20.
- **Friction log.** Every snag gets logged the day it happens (the VVD, S2 and Alexa+ access are the likely ones).

## Verification
- `pytest pipeline/tests`: state math (score, fouls, fantasy, and-one, the `final_score` assertion) and grounding check cases (an invented digit, a wrong jersey, a digit in a Spanish or Mandarin line must be rejected; the judge prompt gets a separate spot-check for names).
- App: `npm test` covers cue lookup (before the first cue, exactly on t, after the last cue, empty list).
- `python pipeline/eval.py <clip>`: precision/recall table plus faithfulness (`0 unsupported / N lines` is the target), with 20 lines spot-checked by hand.
- On the VVD: `vega virtual-device start` → `vega run-app build/aarch64-release/*.vpkg`. Walk through the demo script with only the D-pad. Voice sync is built into the mixed audio and can't drift. Check that the overlays driven by `timeupdate` (rule cards, fantasy ticks) stay within 0.5 s of their event over the full clip, persona switching works mid-play, Why pauses and answers about *that* play, and fantasy points change after a made 3.
- Before submitting: check against CONTEXT.md's submission checklist; confirm the video has no third-party marks or music; confirm the repo is public with Apache-2.0 and no secrets (`git log -p | grep -iE 'aws_secret|AKIA'` returns nothing).

## Self-scrutiny (one pass; issues found → fix)
- **Grounding check claimed to catch names**, but spotting names with a regex doesn't work in Spanish, Hindi or Mandarin. → The deterministic check now covers digits only (numbers must be written as digits), and the Bedrock judge handles names, claims and spelled-out numbers.
- **The score could be wrong because of a missed review event,** which would put a false fact on air. → `clip.json` holds `start_score` and `final_score`, `state.py` asserts they match, and the review page shows the running score.
- **The clip starts mid-game,** so the initial score is unknown. → `start_score` goes in `clip.json`.
- **Seeking in option 2c** fails on MP4s without faststart. → `-movflags +faststart` on every render.
- **"Cue drift" test was misdirected:** the voice is mixed into the audio and can't drift. → The test now targets the `timeupdate` overlays.
- **Recording the VVD with audio hadn't been checked** until Oct 21. → Tested during S1, rehearsed Oct 8–10.
- **The VVD might not reach localhost.** → Tested during S1, with CloudFront from day 1 as the fallback.
- **Apple Silicon VVD crashes** in older SDKs, plus unlisted prerequisites. → S1 now lists Rosetta, Java 21 and Node 18–20 and requires the latest SDK.
- **Extraction didn't need S3:** 20 s chunks fit Nova's 25 MB inline limit. → Chunks are sent inline, so there's one fewer IAM and bucket dependency in week 1.
- **FastAPI was overkill** for a local review page. → stdlib `http.server`, and boto3 is the only Python dependency. The page is bound to 127.0.0.1 and checks clip ids against existing dirs.
- **Shot clock event** doesn't fit intramural games. → Dropped. Fantasy scoring defined over only the event types we extract (no assists).
- **PLAN.md conflicts** (DynamoDB, QR, Lambda, live mode). → Dropped explicitly (decision 10), and PLAN.md gets updated Sep 28.
- **Region:** Polly generative voices exist only in some regions. → Pinned to `us-east-1`, with Nova 2 availability checked during S0.
- **Venue permission** was missing next to the players' consent. → Added to S0.
- **Untested non-trivial app logic** (cue binary search). → One jest test.
- A second pass found nothing new.
