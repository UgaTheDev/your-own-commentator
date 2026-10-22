# Your Own Commentator

**Pick your own sports commentator on Fire TV.** One game, narrated for everyone: a **Rookie**
commentator who explains each rule the moment it matters, a **Kid** commentator, a two-voice
**Booth** (play-by-play + analyst), a **Fantasy** analyst, and the same game in **Spanish, Hindi
and Mandarin**. Hold a button on your phone and ask *"wait, why did blue just get a point?"*, and the
commentator answers about **that** play, out loud, in seconds. Friends in other homes can join a
**watch party**, each with their own commentator, and call the next basket.

Built for the **Fire TV track** of the Amazon Developer Hackathon 2026, on **Vega OS**.

> **The rule that makes it trustworthy: no invented facts.** A commentator may only say what is
> in the verified event and game-state data, plus a rules card we wrote. Every spoken line passes
> three gates in code before it is voiced (see [Grounding](#grounding)).

## Amazon services used

| Service | Where | Why |
|---|---|---|
| **Vega OS + Vega SDK** (React Native, `@amazon-devices/react-native-w3cmedia`) | `app/`: the Fire TV app | Amazon's new Fire TV platform; W3C media player, D-pad focus, second AudioPlayer for spoken answers |
| **Amazon Bedrock: Nova 2 Sonic** (`amazon.nova-2-sonic-v1:0`, bidirectional streaming) | `services/talk/sonic_asr.py` | Speech recognition for viewer questions from the phone |
| **Amazon Bedrock: Nova Pro** | `pipeline/extract.py`, `pipeline/scoreboard.py` | Video understanding (events in 20 s windows) and reading the broadcast score graphic as an image |
| **Amazon Bedrock: Nova 2 Lite** | `pipeline/write.py`, `answer.py`, `booth.py`, `why.py`, `recap.py` | Writing commentary, answers and recaps, and the grounding judge |
| **Amazon Polly** (neural + generative) | `pipeline/voice.py`, `services/talk/relay.py` | A distinct voice per persona and language: Danielle, Tiffany, Matthew, Ruth, Stephen (en-US, generative), Lupe (es-US, generative), Kajal (hi-IN), Zhiyu (cmn-CN) |
| **Amazon S3 + CloudFront** (Origin Access Control) | `pipeline/publish.py` | Private storage; HTTPS delivery of tracks, audio and manifests (Vega's media player is HTTPS-only) |
| **Amazon ECS on AWS Fargate + ALB + CloudFront** | `services/talk/template.yaml` | The talk-back relay (secure WebSocket), locked so only our CloudFront can reach the ALB |
| **Amazon ECR** | `services/talk/Dockerfile` | The relay's container image |
| **Amazon API Gateway (WebSocket) + AWS Lambda + Amazon DynamoDB** | `services/party/` | Watch-party rooms and predictions, settled only by verified events |
| **AWS CloudFormation** | `services/*/template.yaml` | Infrastructure as code for both services |

## How it works

```
licensed game video
  │  Nova Pro: events per 20 s window          scoreboard.py: score-graphic changes → Nova Pro reads digits
  ▼                                            (authoritative for baskets: +1 FT, +2, +3)
proposed events ──► review page (accept / fix / add) ──► verified events
                                                                  │  state.py: score, fouls, fantasy (deterministic,
                                                                  ▼  must equal the broadcast's final score)
                     Nova 2 Lite writer per persona × event ──► 3 grounding gates ──► Polly ──► ffmpeg mix
                                                                                                  │ (crowd ducked)
                                                                  S3 + CloudFront: tracks, audio, manifest v2
                                                                                                  ▼
   phone (hold to talk) ─wss─► Fargate relay: Nova Sonic ASR ─► answer() gates ─► Polly ─► Fire TV (Vega app)
   friends ───────────────wss─► API Gateway + Lambda + DynamoDB watch party ◄──────────── playhead every 1 s
```

## Grounding

Every spoken line goes through `write.gate()`:
1. **Digit gate:** any number in the line must appear in the facts, in any script (Devanagari and full-width digits normalized).
2. **Play-word gate:** every play the line names (steal, foul, rebound, three, free throw…, in English and Spanish, with starter lists for Hindi and Mandarin) must match a play in the facts, credited to the right team. Team-less plays can't be given to a team.
3. **Bedrock judge** (Nova 2 Lite) for names and claims. If both attempts fail, the line is dropped. Viewer answers fall back to a sentence built only from the facts, so they never invent anything.

Only events accepted in review are spoken (`write.speakable()`), and published manifests contain only those.

## Measured so far (2026-09-28, three 10-minute CC BY high-school games)

| What | Result |
|---|---|
| Scoring events from the score graphic | **7 of 7 exact** (type, team, time), computed final score = broadcast (20–6) |
| Nova Pro video-only baskets (why we anchor to the graphic) | 131 raw proposals implying 60 points vs 13 real; periodic hallucinations filtered |
| Grounding: invented plays in live lines | 20 of 300 before the play-word gate → **0 of 494** after |
| Bedrock judge alone (A/B, 30 lines) | Nova 2 Lite and Nova Pro each caught **0 of 2** invented plays, so a deterministic gate is required |
| Talk-back latency (end of speech → answer audio ready) | **2.9 s mean** (local, 6 runs); **3.4 s** through the public relay; transcripts exact |
| Computer vision (RF-DETR + ByteTrack, 60 s) | 95% of frames with court homography; team colour ~80–85%; ball 42% of frames |
| Vega | WebSocket works; media must be HTTPS; switching commentators by source swap + seek ≈ 1–1.5 s to playing |

**Event extraction vs reviewed ground truth, across 3 games** (30 min of play, `eval/*.md`):

| Proposer | Lake Region | Spaulding | Montpelier | All 3 games |
|---|---|---|---|---|
| Score-graphic reader (Nova Pro reads the broadcast graphic) | 7/7 | 11/11 | 14 events, points exact* | **points exact on every game; 18/18 matched on the two clean games** |
| Nova Pro video-only (fouls, rebounds, steals, timeouts…) | 1 of 35 | 0 of 94 | 4 of 53 | **5 of 182 correct (precision 0.03)** |

\* On Montpelier the operator sometimes ticked one basket up in two +1 steps and recorded free throws during a
dead ball, so review corrected 3 types. The per-event match score (0.64 in `eval/hctv-boys-montpelier.md`) counts
those corrections as misses, but the scoreboard's point totals equal the graphic exactly (+11/+11).

The score-graphic reader needed no retuning between games (same crop, same code). Raw video understanding on
amateur footage mostly hallucinates, which is why the product anchors facts to the broadcast graphic plus a
review step. Ground truth was produced by an AI reviewer (Claude) looking at frames around every proposal, with
every decision explained in `data/<clip>/review-notes.md` and each game's computed final score checked against the
broadcast. Human spot-checks are welcome; nothing is spoken unless it is in a reviewed file.

**Jerseys:** Nova Pro reading shooters' jerseys named the wrong player in 3 of 5 proposals on Lake Region, so a
jersey is used only after the reviewer confirms it in the frames (3 of 7 shooters verified; `jersey-notes.md`).

## Repo map
- `app/`: Vega OS Fire TV app (Home, Player, Why card, Catch me up, booth captions, pairing code, replays, minimap, watch party)
- `pipeline/`: extract → review → state → write/booth/why/recap → voice → mix → publish
- `services/talk/`: Nova Sonic relay (Fargate), phone push-to-talk page, runbook (`deploy.md`)
- `services/party/`: watch-party WebSocket backend (Lambda + DynamoDB)
- `cv/`: computer-vision engine (tracking, court mapping, replays, minimap)
- `CONTRACTS.md` + `schemas/`: the frozen interfaces between all parts
- `FRICTION-LOG.md`: every tooling snag we hit, with exact errors and suggested fixes

## Footage and licensing
Code: Apache-2.0. Demo footage: Hardwick Community Television (HCTV), "Girls Varsity Basketball v.
Lake Region - February 11, 2026", [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), via
Wikimedia Commons; original audio removed, commentary and CC0 crowd ambience (SSE Library) added.
Players are referred to only by jersey number and team colour. Details: `SOURCES.md`. Not affiliated
with or endorsed by Amazon.
