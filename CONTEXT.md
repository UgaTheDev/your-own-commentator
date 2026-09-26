# Your Own Commentator: Hackathon Context

Everything we know about the hackathon and the idea, verified 2026-09-26. Re-check the
Devpost page before submitting, because rules can change.

## The hackathon

**Build, Ship, Shape: Amazon Developer Hackathon**
https://amazonappdev2026.devpost.com/ (rules: /rules)

| | |
|---|---|
| Submission window | Aug 31, 2026 10:15 AM PT to **Oct 23, 2026 12:00 PM PT** |
| Judging | Nov 9 to 20, 2026 |
| Winners | ~Dec 3, 2026 |
| Our track | **Fire TV** |
| Fire TV prizes | 1st $25K cash + $15K AWS credits + Amazon meeting; 2nd $15K + $5K; 3rd $4K + $1K |
| Mini challenges | AWS Builder ($5K + $5K credits), Open Source ($5K + $5K credits) |
| Prize limit | One track prize **and** one mini-challenge prize per project |
| AWS credits | $150 promo credits by form, request before **Oct 21 noon PT** |

### Fire TV track requirements
- "Launch a demo-ready app that works on **Fire OS or Vega OS**."
- Priority areas: AI-enhanced viewing, **sports**, fitness, family entertainment, multi-modal
  UX, computer vision. We hit sports, AI-enhanced viewing, multi-modal and family.
- **The demo video must show the app running on an actual Fire TV device or the Fire TV/Vega
  simulator.**

### Alexa+ (for the "ask about this play" feature)
The Alexa+ track itself requires "a working Agent Skill or a self-hosted MCP server
(MCP spec version 2025-11-25 minimum)," actually imported and called at runtime. We are
entering Fire TV, not Alexa+, but if the voice feature is built the same way (a self-hosted MCP
server Alexa+ calls), judges see real ecosystem depth. A project can only win one track, so
this is extra credit, not a second entry.

### Submission checklist (from the rules)
- [ ] Code repo: public with an open-source license (also qualifies us for the **Open Source**
      mini challenge), or private and shared with testing@devpost.com plus Amazon GitHub users
      chris-trag, knmeiss, giolaq, anishamalde, mosesroth, emersonsklar
- [ ] Demo video **under 3 minutes**, public on YouTube or Vimeo, showing the app on a Fire TV
      or the simulator
- [ ] **No unauthorized third-party trademarks or copyrighted music or footage in the video**
      (see "Footage rights" below; this constrains the whole demo)
- [ ] Text description of features
- [ ] Product feedback on the tools used (what worked, what needs work, onboarding)
- [ ] Feature requests (optional)
- [ ] **Friction log** (optional, worth up to a **10% bonus**): keep it from day one, see
      FRICTION-LOG.md
- [ ] It must be new work, or significantly updated after Aug 31, 2026

### Judging (four criteria, equal weight)
1. **Tech Implementation:** how effectively it uses the required APIs and SDKs
2. **Design:** a complete, intuitive product experience
3. **Potential Impact:** credible customer need beyond the hackathon
4. **Quality of Idea:** creative, shows genuine understanding of the ecosystem

Judges may use expert panels, peer review, **automated AI-driven analysis**, or a mix. So the
README and description must be explicit and easy for a machine to scan: say plainly which
Amazon APIs are used, where, and why.

## Platform facts
- **Vega OS** is Fire TV's new OS. Apps are **React Native** (or web) built with Vega
  Developer Tools, which handle setup, build, packaging and debugging. A Vega simulator exists.
  Start here: https://developer.amazon.com/apps-and-games/blogs/2026/07/guide-to-building-for-fire-tv-on-vega-os
- **Fire OS** is the older Android-based OS (Kotlin/Java, or React Native for Android).
- Alexa+ on Fire TV and expanded Alexa+ search support were announced for 2026 (Amazon dev
  news, Aug 24, 2026). Whether third-party apps can route "ask about this play" through Alexa+
  on Fire TV is **unverified**. That is a Week 1 spike (see PLAN.md).

## The idea
**Problem:** live sports are confusing if you are new, and one broadcast commentary has to
serve everyone. Casual fans, brand-new fans, kids, fantasy players and families who speak
another language all get the same track.

**Product:** pick your own commentator on Fire TV.
- **Rookie:** explains the rule at the moment it matters ("that's a false start, here's why")
- **Fantasy:** follows your players and what each play did to your matchup
- **Kid:** high energy, simple words, fun facts
- **Your language:** the same game narrated in Spanish, Hindi, Mandarin and so on
- Mid-game, ask "why was that a penalty?" and get the answer about **that** play.

**Why Amazon cares:** Amazon streams Thursday Night Football on Prime Video and has NBA rights
from the 2025-26 season. Personal commentary is a real feature for their own business, which
is what "genuine ecosystem understanding" rewards.

### Existence check (2026-09-26)
- Voice tools (ElevenLabs sports voices, Resemble) and data feeds (Stats Perform) exist.
  Articles describe personalized commentary as a concept.
- Prime Vision on TNF adds stats overlays, not commentary made for you.
- **No shipped, TV-native, personal commentary product was found.** Novel as a product.
- Already taken (do not pivot to these): language learning from TV (Lingopie on Fire TV, and
  "lingo" is literally another entry in this hackathon:
  https://github.com/moiz-lakkadkutta/lingo).

## Footage rights: the constraint that shapes the demo
The rules forbid third-party copyrighted material and trademarks in the video. **No NFL, NBA
or ESPN footage, logos or team marks.**

**Decision (2026-09-26): we will not film a game.** We use licensed footage found online.
- **License must allow reuse and modification** (we overlay audio and graphics): CC-BY or
  CC-BY-SA (attribute in the video description), CC0, or US-government public domain
  (e.g. DVIDS / DoD works). Not ND or NC, not the standard YouTube license, and no fair-use
  reasoning.
- **Avoid visible trademarks:** NBA/NCAA/pro team logos, sponsor boards, broadcast graphics.
  Amateur, pickup, rec-league or military footage is ideal. It also backs the Impact story:
  amateur games have no commentary at all.
- **2 to 5 minutes of continuous play** with teachable moments (fouls, travels, 3s, free
  throws). Basketball is the default; switch sport only if the only good licensed footage is
  another sport.
- **Where to look:** Wikimedia Commons video categories, YouTube with the Creative Commons
  filter, the Internet Archive (check the license field), DVIDS.
- Every clip gets its source URL, license, uploader and attribution string in SOURCES.md.
  Raw downloads go in data/raw/ (gitignored).

The play-by-play data and rules knowledge are ours to generate, so there's no rights problem there.
