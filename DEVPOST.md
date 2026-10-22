# Devpost submission text

Paste each section into the matching Devpost field. Numbers are from `eval/*.md` and README.md.

## Tagline
Pick your own sports commentator on Fire TV, and ask it "why?" out loud.

## Inspiration
One broadcast commentary has to serve everyone: brand-new fans, kids, fantasy players, and families who speak
another language. And most amateur and high-school games have no commentary at all. We wanted every viewer
to get their own broadcast, without the commentator ever making things up.

## What it does
- **Seven commentators for one game** on Fire TV (Vega OS): Rookie (explains each rule as it happens), Kid,
  a two-voice Booth (play-by-play plus analyst), Fantasy, and Rookie in **Spanish, Hindi and Mandarin**. You switch
  between them with the remote, mid-play.
- **Ask "why?"** Pause, and the Why card offers questions about the play on screen. Or hold a button on your
  phone and ask out loud. The commentator answers about *that* play, in its own voice, in about 3 seconds.
- **Catch me up:** minute-mark recaps of what you missed.
- **Replays and minimap:** slow-motion replays of key plays with every tracked player marked, and a live court minimap,
  both from our own computer-vision engine.
- **Highlight reel:** a 64-second reel of every verified basket, narrated.
- **Watch party:** friends in other homes join with a code, each with their own commentator, and call the next
  basket. Predictions are settled only by verified events.
- **Three real games** (licensed CC BY high-school basketball) in a game picker.

## The rule that makes it trustworthy: no invented facts
A commentator may only say what is in the verified event and game-state data, plus a rules card we wrote. Every
spoken line goes through gates in code before it is voiced:
1. **Number gate:** every number, including spelled-out numbers in English, Spanish and Mandarin, must be in the facts.
2. **Play gate:** every play the line names must match a verified play, credited to the right team.
3. **Style gate:** players are referred to only by jersey number and team colour (they are minors).
   A number said as a jersey ("number 13", "नंबर १३", "13号") must be that play's verified jersey, even when the
   same number is a real score. This caught three Hindi lines that turned the score into a player.
4. **Bedrock judge** (Nova 2 Lite). If a line fails twice, it is dropped. Spoken answers fall back to a sentence
   built only from the facts, so the viewer always gets an answer and it never invents anything.

We measured why this matters. Before the play gate, 20 of 300 lines invented a play. After it, **0 of 494** did.
In an A/B test, the Bedrock judge on its own caught 0 of 2 invented plays.

## How we built it
- **Vega OS app** (React Native, `@amazon-devices/react-native-w3cmedia`): D-pad focus, commentator switching by
  swapping the source and seeking, a second AudioPlayer for spoken answers, and a WebSocket for talk-back and the
  watch party.
- **Amazon Bedrock:**
  - **Nova Pro** reads the video (events in 20-second windows) and reads the broadcast score graphic as an image.
  - **Nova 2 Lite** writes every commentary line, answer and recap, and is the grounding judge.
  - **Nova 2 Sonic** (bidirectional streaming) is the speech recognizer for spoken questions.
- **Amazon Polly:** a distinct neural or generative voice per persona and language (Danielle, Tiffany, Matthew, Ruth,
  Stephen, Lupe, Kajal, Zhiyu).
- **Talk-back relay:** Amazon ECS on Fargate behind an ALB and CloudFront, with an origin-secret header. A phone page
  on CloudFront captures the mic.
- **Watch party:** API Gateway WebSocket, Lambda and DynamoDB.
- **Media:** S3 and CloudFront with Origin Access Control. Vega's media player only accepts HTTPS.
- **Infrastructure:** CloudFormation for both services.
- **Computer vision:** RF-DETR (Apache-2.0) and ByteTrack, team colour clustering, and court homography from a
  calibrated keyframe. All open-licensed; we avoided AGPL models.
- **Review step:** a review page where proposed events are accepted, fixed or added. Only accepted events are
  ever spoken.

## Challenges we ran into
- **Raw video understanding mostly hallucinates on amateur footage.** Nova Pro's video-only events were right
  5 times out of 182 (precision 0.03) across three games. It once implied 60 points in a 13-point stretch.
  - **What we did:** anchored scoring to the broadcast score graphic, which Nova Pro reads well as an image.
    We detect pixel changes and keep only readings where the score goes up plausibly.
  - **Result:** points exact on all three games, with no retuning between them.
- **Nova 2 Lite refused basketball video** with no reason given. We moved video extraction to Nova Pro.
- **The judge passed wrong spelled-out scores** ("forty" when the score was 39), so we added a spelled-number gate.
- **Translation moved numbers into new roles.** A Hindi line said "with number 13" when 13 was the team's score, not
  a player. The judge passed it, so jersey wording is now checked against the play's verified jersey.
- **Sonic in Python needed a second, experimental SDK** with a CRT transport, a manual credential resolver and
  trailing silence before it would transcribe (details in the friction log).

## Accomplishments we're proud of
- Grounding that holds up when measured: 0 invented plays in 494 published lines, and every number checked against
  the verified score.
- Talk-back: from the end of speech to the answer's audio in **3.4 seconds** through the public relay.
- **Three games** processed by the same pipeline, each game's computed final score matching the broadcast.

## What we learned
On amateur footage, an LLM judge isn't enough to check facts. Deterministic gates plus a verified fact store are
what make AI commentary safe to put on a TV.

## What's next
- Live games: the live-replay mode already narrates score-graphic changes in real time (7.6 s latency).
- An Alexa+ add-on: the MCP server is built (`services/mcp/`), and "Alexa, why was that a foul?" is next.
- More sports and languages, and native-speaker review of the Hindi and Mandarin wording.

## Built with
vega-os, react-native, amazon-bedrock, amazon-nova, nova-sonic, amazon-polly, aws-fargate, amazon-ecs,
api-gateway, aws-lambda, amazon-dynamodb, amazon-s3, amazon-cloudfront, aws-cloudformation, python, typescript,
rf-detr, opencv, ffmpeg

## Product feedback (what worked, what needs work, onboarding)
**Worked well**
- Nova Pro reading images: the score graphic was read exactly on every game.
- Polly's language coverage: one API gave us 7 voices in 4 languages.
- Vega's W3C media API: switching by source and seeking behaves the same as on the web. A second AudioPlayer worked
  first time.
- The Vega Virtual Device and `vega device run-cmd` for scripted remote presses.

**Needs work** (full detail with exact errors in FRICTION-LOG.md, 40+ entries)
- Nova 2 Sonic from Python needs `aws-sdk-bedrock-runtime` 0.11 (experimental), and its getting-started
  sample doesn't match the 0.11 API.
  - A missing credential resolver hangs for over 90 seconds with no error.
  - Ending the audio content does not trigger a transcript; you have to send trailing silence.
- Nova 2 Lite refuses some sports video without saying why.
- Nova Premier is listed ACTIVE but returns end-of-life.
- New accounts: Bedrock is unavailable while the account is "being verified", and Transcribe is blocked on the
  Free plan. Neither restriction is shown up front.
- `aws login` credentials need the extra `botocore[crt]` dependency, and they expire mid-run with
  `LoginRefreshRequired`.
- Vega CLI:
  - `vega project generate` overwrote our `.gitignore`.
  - The `copy-to` help text describes its arguments backwards.
  - There's no screenshot command for the VVD.
  - Remote-key injection (`inputd-cli`) isn't mentioned in `--help`.
- Vega media players are HTTPS only. That's fine, but say it in the getting-started docs: plain `http://` fails
  with no clear error.
- Alexa+ MCP docs don't say whether an add-on can learn what a Fire TV app is playing (the playhead).

## Feature requests
1. A `vega device screenshot` / `screenrecord` command for the VVD, to record demos and run visual tests.
2. A per-app microphone capture API on Vega (we had to use the phone as the mic).
3. Bidirectional streaming in boto3, so Nova Sonic works with the standard SDK.
4. A transcription-only mode for Nova Sonic that returns the transcript as soon as speech ends.
5. Passing Fire TV app context (content ID and playhead) to Alexa+ add-ons.
6. Nova models returning a reason code when they refuse a video.
