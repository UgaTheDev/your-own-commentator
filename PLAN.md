# Your Own Commentator: Build Plan

> **2026-09-26:** EXECUTION-PLAN.md is the approved step-by-step plan and wins where the two conflict. It drops DynamoDB, Lambda, the QR companion and live mode, and adds pre-rendered audio tracks and the Why button first.

**Deadline: Oct 23, 2026, 12:00 PM PT (3:00 PM ET). Internal target: submit Oct 22.**
This is built in parallel with ../NVIDIA (Waze for Floods, due Oct 30). This one is due
first, so it gets priority through Oct 22.

## 1. What the demo must prove (work backwards from the video)
A viewer on a Fire TV picks **Rookie**, watches 30 seconds of a real game, and hears the
commentator explain the rule the instant it matters. They flip to **Kid**, then to **Spanish**,
and it's the same play told three ways. They ask "why was that a foul?" and get an answer
about *that* foul. A fantasy user sees what the last play did to their roster.
**Everything below exists to make those 3 minutes true, running on a Vega simulator or a
real Fire TV.**

## 2. Decisions to make first (by Sep 28)
| Decision | Recommendation | Why |
|---|---|---|
| Sport | **Basketball** | One camera in a BU gym can film it; frequent teachable rules (travel, shot clock, fouls, 3 vs 2, and-one); legal footage is easy to get |
| Footage | **Film a BU intramural or club game** with written OK from players | Zero rights risk; also proves the amateur-sports angle (no commentary exists there at all) |
| OS | **Vega OS** (React Native) | It's Amazon's new platform (judges notice), and you know React and TypeScript |
| Pipeline language | Python (FastAPI) | Fastest for you; boto3 for Bedrock and Polly |
| Mini challenge to target | **AWS Builder** (Bedrock + Polly + S3/CloudFront + DynamoDB + Lambda) | The repo will be public with a license anyway, but only one mini prize can be won, and AWS Builder fits the stack better |

## 3. Architecture
```
 recorded or "live-replayed" game video
          |
  [1] Event extraction  -- Amazon Nova (Bedrock) video understanding over 10-20s chunks
          |               -> timestamped events: {t, type: foul|made_3|travel|..., team,
          |                  jersey, confidence}
          |               -> human review screen: accept/fix each event (ground truth)
          v
  [2] Game state       -- running score, fouls, possession, fantasy stat lines per player
          |
  [3] Persona writer   -- Bedrock LLM, one call per (event, persona), with hard constraints:
          |               length <= gap-before-next-event x 2.5 words/sec, no invented facts
          |               (may only reference fields present in the event and game state)
          v
  [4] Voice            -- Amazon Polly (neural/generative; a distinct voice per persona;
          |               languages: es, hi, zh at minimum) -> mp3 per line
          v
  [5] Track manifest   -- S3 + CloudFront: {t, eventId, text, audioUrl, ruleCardId}
          |
  [6] Fire TV app (Vega, React Native)
          - video player + commentary audio synced to the playhead (duck crowd audio)
          - persona picker (D-pad friendly), language picker
          - Rookie "rule cards" overlay synced to events
          - Fantasy panel: your roster, fantasy points delta per play
          - "Ask about this play": see section 5
  [7] Profile           -- DynamoDB: persona, language, fantasy roster (set up on the phone
                           via QR code, never by typing on a TV)
```
**The anti-hallucination rule is the product's credibility.** The persona writer may only
narrate facts in the verified event and game state. Say this in the README and video;
it's the same evidence-grounding idea as HireBuddy's safeguards.

### Live mode (stretch, week 3)
MVP: commentary is generated ahead of time for recorded clips, and the app says "replay."
Stretch: feed the clip through the pipeline in real time (chunk every 10s) and show
commentary arriving about 5-10s behind the action. Label it honestly: "live replay:
commentary generated in real time." Real live broadcast ingestion is out of scope, and the
rights for it don't exist anyway.

## 4. Evaluation (put the numbers in the README and the video)
- **Event extraction:** precision and recall of Nova's events against your hand-verified events
  on the demo clips, per event type. Report it honestly even if it's mediocre; the human
  review step is the answer to low recall.
- **Faithfulness:** 0 unsupported claims in N generated lines. Check every line against
  its event JSON, first automatically, then by a manual spot-check.
- **Latency** (if live mode lands): event-to-audio seconds, p50/p95.

## 5. "Ask about this play": the risky feature
- **Plan A: Alexa+.** A self-hosted **MCP server** (MCP spec >= 2025-11-25) exposing
  `get_current_play(session)`, `explain_play(play_id, persona)` and
  `fantasy_impact(play_id, user)`. The session links the Fire TV to the user with a device
  code. If Alexa+ can call it while watching, that's the best possible demo.
- **Plan B, always works:** an on-screen "Why?" button on the D-pad that shows three
  suggested questions for the current play, answered by the same backend, with the answer
  voiced in the current persona.
- **Plan C:** a phone companion (the same QR page) with a mic button.
- **Week 1 spike decides it.** If Alexa+ third-party routing on Fire TV isn't reachable
  by Oct 3, build B, keep the MCP server (it's small and still shows ecosystem depth), and log
  the blocker in the friction log (that's what the bonus is for).

## 6. Schedule (interleaved with ../NVIDIA)
| Dates | Amazon (priority) | NVIDIA (background) |
|---|---|---|
| **Sep 27-Oct 3** | Install Vega Developer Tools; simulator hello-world playing a video. **Alexa+ spike.** Book the game filming and get player consent. Run Nova event extraction on a 2-min test clip. **Request the $150 AWS credits** (deadline Oct 21, do it now). Start FRICTION-LOG.md. | Deploy Cosmos Reason 2 on Nebius AI Cloud; depth on 20 public-domain images |
| **Oct 4-10** | End to end on one clip: events, review screen, Rookie + Kid personas, Polly, manifest, app playing a synced track | Build the eval set; eval harness v1 |
| **Oct 11-17** | Spanish + Fantasy personas, rule cards, Ask (Plan A or B), QR companion, polish the TV UI (focus states, 10-foot readability) | Segment fusion + map UI |
| **Oct 18-20** | Live-replay stretch only if everything else is done. **Code freeze Oct 20 night.** | none |
| **Oct 21** | Record the video on the simulator or a device; write the description, feedback and friction log | none |
| **Oct 22** | **Submit** (a day of buffer before the Oct 23 noon PT deadline) | resume full time |

## 7. Demo video script (under 3:00, target 2:45)
- 0:00-0:15. Hook: a friend who's never watched basketball asks "wait, why did they stop?"
  The TV answers.
- 0:15-0:45. Pick Rookie on the Fire TV. The play happens, the rule card pops up, the commentator explains.
- 0:45-1:10. The same play in Kid, then Spanish. It's one game with three commentators.
- 1:10-1:35. Fantasy: roster points tick after a made 3.
- 1:35-2:00. Ask "why was that a foul?" and get the answer about that play (Alexa+ or the Why button).
- 2:00-2:30. Under the hood: Nova events, then verified, then persona writer with a no-invented-facts
  rule, then Polly. Show the faithfulness and extraction numbers.
- 2:30-2:45. Impact: amateur and college games have zero commentary today, and for Prime
  Video's TNF and NBA audiences, every viewer gets their own broadcast.
No copyrighted music. Record your own voiceover.

## 8. Risks
| Risk | Mitigation |
|---|---|
| Alexa+ third-party routing unavailable | Plan B/C button; MCP server still ships; friction log entry |
| Nova misses or mislabels events | Human review screen (it's also the ground truth); report precision and recall honestly |
| Vega tooling friction (new OS) | Spike in week 1; fallback to Fire OS with React Native for Android if blocked by Oct 3 |
| Footage rights | Only our own filmed game with consent, or CC-BY with attribution |
| Voice lines overrun the next play | Hard word budget per gap; drop low-priority lines |
| Scope creep with two hackathons | Rookie + Kid + Spanish + Why is the MVP. Fantasy and live replay are the first things cut |
| AWS cost | $150 credits; pre-render and cache all audio; Polly and Bedrock costs are small at demo scale |
