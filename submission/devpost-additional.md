# Devpost "Additional info" page: one answer per field

**Upload a File:** leave empty (everything is in the repo).

**Submitter Type:** Individual  ·  **Organization Name:** N/A  ·  **Country:** United States  ·  **Canada province:** N/A

**Primary Track:** Fire TV

**Code repository URL:** https://github.com/UgaTheDev/your-own-commentator

**New or existing prior to August 31, 2026?** New (first commit 2026-09-26). Leave the "existing project" box empty.

**AWS Builder Mini Challenge?** Yes

**AWS Builder: which AWS services did you incorporate and how?**
Amazon Bedrock, with three Nova models:
- **Nova Pro** reads the game video (events in 20-second windows) and reads the broadcast score graphic as an image. Scoring is anchored to the score graphic.
- **Nova 2 Lite** writes every commentary line, Why answer and recap in seven personas and four languages. It also acts as a grounding judge, behind deterministic number, play and jersey gates written in code.
- **Nova 2 Sonic** (bidirectional streaming) is the speech recognizer for questions spoken into the phone.

Other AWS services:
- **Amazon Polly** voices each persona: generative Danielle, Tiffany, Matthew, Ruth, Stephen and Lupe; neural Kajal and Zhiyu.
- **Amazon ECS on Fargate** runs the talk-back relay (phone audio → Sonic → grounded answer → Polly → TV), behind an ALB and CloudFront. It uses a task role, with no keys.
- **API Gateway WebSocket, AWS Lambda and DynamoDB** run the watch party.
- **Amazon S3 and CloudFront** (Origin Access Control) serve the media, because Vega's player is HTTPS-only.
- **CloudFormation** defines both services.

The code is in `pipeline/` (Bedrock and Polly), `services/talk/` (Fargate relay) and `services/party/` (Lambda). The README has a table of every service and where it is used.

**Open Source Mini Challenge?** Yes. The project itself is a new open-source repo (Apache-2.0, detected by GitHub) created during the hackathon window.
- **Contribution URL:** https://github.com/UgaTheDev/your-own-commentator
- **Project repository URL:** https://github.com/UgaTheDev/your-own-commentator
- **GitHub username:** UgaTheDev
- **What you did, how it works, and why it matters:**
  > A complete, open-source (Apache-2.0) reference for AI sports commentary that never invents facts, plus a Vega OS Fire TV app that plays it.
  >
  > The pipeline turns a licensed game video into a verified play log: Nova Pro reads the score graphic, and a human review step follows. It then writes, voices and mixes commentary tracks in seven personas and four languages. Every line passes deterministic gates in code: numbers, plays, and jersey wording must each match the verified facts. A Bedrock judge sits behind those gates, and lines that fail twice are dropped.
  >
  > The repo also includes:
  > - a computer-vision engine built only on permissively licensed models (RF-DETR Apache-2.0, ByteTrack MIT; no AGPL models), used for replays and the minimap
  > - a Nova 2 Sonic talk-back relay
  > - a watch-party backend
  > - Vega-specific patterns other developers can reuse: commentary switching by swapping the source and seeking, a one-shot `hasTVPreferredFocus` fix, an SVG remount workaround, and scripted demo recording through the emulator console
  >
  > It matters because amateur and youth games rarely have commentary, and LLM commentary on amateur footage hallucinates. We measured video-only events at 5 correct of 182. The repo shows a measured way to make it safe: 0 invented plays in 494 published lines. It has 48 friction-log entries for other Vega and Bedrock developers.

**Feature Requests (optional):**
1. **Important:** a `vega device screenshot` / `screenrecord` command. The emulator console on port 5554 has `screenrecord`, but nothing documents it. Window capture of the VVD drops below 1 fps whenever another window covers it. It would let developers record demos and run visual tests.
2. **Important:** a per-app microphone capture API on Vega OS. Without one we had to use a phone as the mic for voice questions.
3. **Important:** bidirectional streaming in boto3, so Nova 2 Sonic works with the standard SDK instead of the experimental `aws-sdk-bedrock-runtime` with a CRT transport.
4. **Nice-to-have:** a transcription-only mode for Nova Sonic that returns the transcript as soon as speech ends, without needing trailing silence.
5. **Nice-to-have:** passing Fire TV app context (content ID and playhead) to Alexa+ add-ons, so "Alexa, why was that a foul?" knows the moment.
6. **Nice-to-have:** a reason code when a Nova model refuses a video.

**Friction Log URL:** https://github.com/UgaTheDev/your-own-commentator/blob/main/FRICTION-LOG.md

**Project Testing Link (optional):** https://github.com/UgaTheDev/your-own-commentator#run-it

**Testing instructions:**
> No credentials are needed. Clone the repo and follow README "Run it":
>
> `cd app && npm install && npm run build:release`, then `vega virtual-device start` and `vega run-app build/aarch64-release/commentator_aarch64.vpkg`. On x86_64 hosts, use `build/x86_64-release/commentator_x86_64.vpkg`.
>
> The three games, their commentary tracks, replays and minimap stream from our CloudFront distribution.
>
> Remote controls: arrows and OK. On Home, pick a game and a commentator. In the Player, the strip has Why?, Catch me up, the commentator tray, Map, Highlights, and Replay (near a play that has one). The remote's rewind key goes back 10 s.
>
> Phone talk-back needs the Fargate relay, which we scale to zero between demos to keep costs down. Contact us and we will turn it on for testing. `services/talk/deploy.md` covers deploying your own.
>
> The pipeline tests run offline: `pip install -r pipeline/requirements.txt && python -m pytest pipeline/tests`.

**Feedback Q1: Which developer tools, APIs and SDKs did you use and for what?**
> - **Vega OS SDK:**
>   - the `vega` CLI, the Vega Virtual Device, and React Native for Vega (RN 0.83): the TV app
>   - `@amazon-devices/react-native-w3cmedia`: video plus a second AudioPlayer for spoken answers
>   - `@amazon-devices/react-native-svg`: logo, persona icons, minimap
>   - `useTVEventHandler`: remote rewind
>   - `inputd-cli` via `vega device run-cmd`: scripted remote presses for tests and the demo recording
> - **Amazon Bedrock:**
>   - Nova Pro: video and score-graphic reading
>   - Nova 2 Lite: commentary writer and grounding judge
>   - Nova 2 Sonic: speech recognition for spoken questions
> - **Amazon Polly:** generative and neural voices in 4 languages.
> - **AWS ECS on Fargate, ALB, CloudFront, S3, API Gateway WebSocket, Lambda, DynamoDB, CloudFormation:** the talk-back relay, the watch party, and media hosting.
> - **AWS CLI `aws login`, boto3, and the experimental `aws-sdk-bedrock-runtime`:** Sonic bidirectional streaming.

**Feedback Q2: What worked well?**
> - **Nova Pro on images:** read the broadcast score graphic exactly on all three games with no retuning. That became our ground truth.
> - **Polly:** one API gave us 8 voices in 4 languages, and the generative voices are a big step up for sports energy.
> - **Vega W3C media:** switching by source and seeking behaves like the web, and a second AudioPlayer worked first time.
> - **The VVD with `inputd-cli`:** let us script the whole remote flow for tests and an automated demo recording.
> - **React Native for Vega:** our React knowledge carried over. Focus, Pressable and SVG mostly just worked.
> - **Fargate behind CloudFront:** gave the phone page the HTTPS and WSS it needs for the mic, with no servers to manage.

**Feedback Q3: What needs work?**
> Full detail with exact errors is in FRICTION-LOG.md (48 entries). The main ones:
> - **Nova 2 Sonic from Python:**
>   - It needs the experimental `aws-sdk-bedrock-runtime` 0.11 with a CRT transport, and the getting-started sample doesn't match the 0.11 API.
>   - A missing credential resolver hangs for more than 90 s with no error.
>   - Ending the audio does not produce a transcript; you have to send trailing silence.
> - **Nova 2 Lite:**
>   - It refuses some sports video with no reason given.
>   - As a judge, it passed wrong spelled-out scores and a translated line that turned a score into a player number. We had to add deterministic gates.
> - **Nova Premier:** listed ACTIVE, but returns end-of-life.
> - **Vega:**
>   - `hasTVPreferredFocus` re-grabs focus on every re-render, which pinned the D-pad.
>   - The SVG renderer leaves removed circles on screen.
>   - Keys sent seconds after a REWIND key are dropped, and run-cmd latency varies from 1 to 7 s.
>   - `useTVEventHandler` isn't exported in the `react-native` types.
>   - The `-rn-83` svg build fails the compatibility check.
>   - The VVD has no documented screenshot or recording command.
>   - `vega project generate` overwrote our `.gitignore`.
>   - The media player is HTTPS-only with no clear error.

**Feedback Q4: How was your onboarding experience (zero to hello world)?**
> - **Vega:** hello world on the VVD took under an hour: `vega project generate`, build, `vega run-app`. Two things slowed us down. The generator silently overwrote our existing `.gitignore`. And `http://` media failed with no clear error, until we learned the player is HTTPS-only.
> - **AWS:** slower on a brand-new account.
>   - `aws login` crashed in a non-interactive terminal when no region was set.
>   - Bedrock returned "account is being verified" for the first couple of hours.
>   - Transcribe was blocked on the Free plan.
>   - boto3 needed `botocore[crt]` before it could use `aws login` credentials.
>
>   Polly worked immediately. Once Bedrock was enabled, the Converse API calls to Nova worked the same day.
> - **Nova 2 Sonic:** the slowest. Getting bidirectional streaming working from Python took about an hour of SDK, transport and credential workarounds.

**Feedback Q5: Would you build with these devices and services again?**
> Yes.
> - **Vega:** React Native on Vega let us build a full TV experience (focus navigation, two media players, SVG, WebSocket) quickly.
> - **Bedrock and Nova:** gave us vision, writing and speech recognition behind one API.
> - **Polly:** made seven distinct commentators affordable.
>
> The friction we hit is fixable with docs and small SDK changes, and the platform fits AI-enhanced viewing well.

**Eligibility checkboxes (age of majority, eligible jurisdiction, not an employee of the Promotion Entities):** your call. Tick them only if true.

**Which AI tools have you leveraged while working on this project?**
> - **Claude Code** (Anthropic, Claude Opus): planning, writing and reviewing code across the app, pipeline and services; running the build, test and demo-recording scripts; keeping the friction log.
> - **Claude Design:** the visual design system (palette, focus states, persona icons, screen layouts) that the app implements.
> - **In the product itself:** Amazon Nova (Pro, 2 Lite, 2 Sonic) and Amazon Polly.

**Level of learning / AI value for your career:** your call (dropdowns).
