# Handoff: Your Own Commentator — Visual System (Fire TV + phone companion)

## Overview
"Your Own Commentator" is a Fire TV app (Amazon Vega OS, React Native) where a viewer picks an AI sports commentator for a basketball game, asks "why?" out loud from their phone, and gets grounded, fact-checked answers. This bundle defines the brand, tokens, every TV screen/overlay, the phone companion page, demo-video graphics and Devpost gallery images.

Brand feel: a live-sports broadcast control room. Near-black surfaces, hairline borders, ONE hot accent (yellow), team colours carry meaning only for teams.

## About the Design Files
The files in this bundle are **design references created in HTML** — they show intended look and behaviour, not production code. Recreate them in the target environment: **React Native for Vega OS** (TV) and whatever stack serves the phone companion page (a plain responsive web page is fine). Use the codebase's existing patterns (focus management, spatial navigation, Animated API, etc.). Do not ship the HTML.

Open any `.dc.html` file directly in a browser (keep `support.js` alongside). Each is a pan/zoom canvas of artboards at true pixel size. Each TV file has a **"Focus order"** toggle (teal numbered arrows = spec annotation, not UI).

## Fidelity
**High-fidelity.** Final colours, type, spacing, radii, states and copy. Recreate pixel-accurately at 1920×1080 (TV) and 390×844 (phone). Court/video imagery is a placeholder (see Assets).

---

## Design Tokens

### Colour
| Token | Value | Use |
|---|---|---|
| bg | `#070b10` | Base surface, accentInk |
| panel | `#0c1218` | Cards, rails |
| panel2 | `#111922` | Buttons, inputs, chips |
| panelFocus | `#16202b` / `#1a2532` | Card / button bg while focused |
| line | `#1c2733` | 1px hairlines, dividers |
| lineStrong | `#2a3847` | 1px borders on interactive chrome |
| text | `#e6edf3` | Primary text (16.6:1 on bg) |
| textSoft | `#c4ced8` | Body copy on panels / video |
| muted | `#8c99a8` | Secondary text, eyebrows (6.8:1 on bg) |
| accent | `#FFD400` | Focus ring, live state, the ONE primary action per screen |
| accentInk | `#070b10` | Text/icons on accent (13.7:1) |
| glass | `rgba(9,14,20,0.88–0.94)` + `backdrop-filter: blur(24px)` + 1px `rgba(230,237,243,0.14)` inner border | All overlays on video. Opacity is high enough to stay AA without blur. |
| scrim | linear-gradient 0 → `rgba(7,11,16,.92)`, 260–460px tall from bottom | Behind captions / strip only |
| annotation | `#2ee6d6` | Spec-only (focus arrows). Never in product UI. |

**Team colours** (chip ink in brackets):
- Pink `#d6247a` (`#ffffff`, 4.8:1)
- Blue `#1f5fd6` (`#ffffff`, 5.7:1)
- White `#e6edf3` (`#070b10`, 16.6:1)
- Maroon `#8c1d40` (`#ffffff`, 8.9:1)
- Green `#1a7d44` (`#ffffff`, 5.2:1) — **changed from #1f8a4c** (white on old green = 4.4:1, fails AA)

Team chip ink is pure `#ffffff`, not `#e6edf3` (pink + #e6edf3 = 4.1:1, fails).

**Persona tile tints** (low-chroma, must never read as a team):
rookie `oklch(0.36 0.06 240)`, kid `oklch(0.42 0.08 80)`, booth `oklch(0.34 0.06 295)`, fantasy `oklch(0.36 0.05 180)`, novato `oklch(0.37 0.07 30)`, hindi `oklch(0.36 0.06 330)`, mandarin `oklch(0.36 0.06 130)`.

### Typography
System fonts only. Stack:
`system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, "Noto Sans", "Noto Sans Devanagari", "Nirmala UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif`

TV scale (px size / line-height · weight):
| Role | Spec |
|---|---|
| Display | 88/96 · 800 · letter-spacing −0.025em (title cards up to 120/120) |
| H1 | 56/64 · 800 · −0.02em (72/80 on full-screen pages) |
| H2 | 40/48 · 800 |
| Title | 32/40 · 700–800 |
| Body L | 28/40 · 400 (captions: 32/44 · 600) |
| Body (minimum) | 24/34 · 400 |
| Eyebrow | 24 · 700 · uppercase · +0.14em |
| Score | 42 · 800 · `font-variant-numeric: tabular-nums` |

**Nothing on TV is below 24px.** Devanagari/Han: same sizes, line-height +12%, no letter-spacing, never text-transformed.

Phone scale: Display 34/40 · 800, Title 22/30 · 800, Body 17/24, Small 15, Eyebrow 13 · 700 · +0.14em. Hit targets ≥ 44px.

### Spacing / layout
- Scale: 8, 16, 24, 32, 48, 64, 96
- TV safe area: **96px left/right, 54px top/bottom** (5%)
- 12-col grid, 120px columns, 24px gutters inside safe area
- Phone: 20px side padding, 47px status bar, 34px bottom inset

### Radii
chip/pill 999 · small chip 8–10 · button 14 · card 20 · panel 24–28 · phone screen 52 · persona tile 22%

### Elevation
Only focused elements lift: `0 28px 56px rgba(0,0,0,.65)`. Overlays: `0 24px 64px rgba(0,0,0,.5)`.

---

## Interactive states (D-pad)
Every focusable element has default / focused / selected.

- **Default button**: h72 (strip) or h80 (panels), padding 0 28–32, radius 14, bg `#111922`, 1px inset `#2a3847`, 26–28px 700.
- **Focused** (must read from across a room): bg → `#1a2532` (buttons) / `#16202b` (cards); ring `box-shadow: 0 0 0 4px #070b10, 0 0 0 10px #FFD400, 0 28px 56px rgba(0,0,0,.65)`; lift `translateY(-4…-8px) scale(1.04–1.06)`; raise z-index. Transition 160ms ease-out.
- **Selected / toggled on**: accent text, 12px accent dot, `inset 0 -5px 0 #FFD400` underline bar.
- **Selected card (on air / now showing)**: `inset 0 0 0 3px #FFD400` border + accent pill "✓ ON AIR" / "▶ NOW SHOWING" (h40, 24px 800, accentInk).
- **Primary**: accent fill + accentInk text; when focused also gets the ring.
- **Disabled**: bg `#0c1218`, 1px `#1c2733`, text muted.

Focus order per screen is drawn in each file (toggle "Focus order").

## Motion
focus 160ms ease-out · overlays in/out 240ms · control strip auto-hides after 6s · rule card max 8s with an accent progress bar · commentator switch ≈1.5s (old voice fades 300ms) · party result banner 4s · phone listening: 3 accent rings scale 1→1.7, opacity .55→0, 1.8s ease-out, staggered 0.6s · thinking: 3 dots bob 1.2s staggered 0.15s.

## Overlay zone rules
- Top-left: score bug; below it rule cards / PAUSED chip.
- Top-right: "Ask on your phone" code badge; top-centre: REPLAY / HIGHLIGHTS tag.
- Bottom: caption (left), minimap (right), control strip (full width).
- **Court centre** (middle 50%×50%): nothing for > 8s unless the game is paused (Why?, Catch me up).
- Players are minors: refer only as team colour + jersey number ("Pink #23"). No faces, no names. No third-party logos.

---

## Shared components
| Component | File | Spec |
|---|---|---|
| Mark | `YOC Mark.dc.html` | 100×100 SVG: circle r36 at (54,46) + tail triangle (27,70)(14,92)(44,80), fill accent; seams (H line, V line, two side arcs) in accentInk 4.5 stroke, clipped to the ball. `variant=ink` swaps colours. |
| Score bug | `YOC Score Bug.dc.html` | h76, radius 16, glass. Team A chip [NAME 24/700 +.12em][score 42/800], Team B mirrored, then period (24/800 accent) + clock (30/700). On a basket: scoring chip gets `inset 0 -6px 0 #FFD400` and an accent pill "+2 PINK" (h56, 26/800) appears to the right. |
| Persona icon | `YOC Persona.dc.html` | Tinted tile, 22% radius, 1px inner hairline; 62% glyph, stroke `#e6edf3` 4px round. Rookie = open book, Kid = star with eyes, Booth = two mics, Fantasy = rising chart, Novato = speech bubble "Ñ", Hindi = "न" + headline bar, Mandarin = "新" in circle. |
| Minimap | `YOC Minimap.dc.html` | 320×180 viewBox; court lines `rgba(230,237,243,.55)`; team dots r8 (r13 with jersey numbers when expanded) white 2px stroke; ball = accent dot r7 with bg stroke. |
| Court placeholder | `YOC Court.dc.html` | Stand-in for live video: blurred abstract arena + team-colour blurred silhouettes. Replace with the real video surface. |

---

## Screens

### 1. Brand (`01 Brand + Spec.dc.html`)
- Square icon: 1024 master (shown 512), radius ≈18.75%, bg radial `#16212c`→`#070b10`, 2px inner `#1c2733`, mark at 64%.
- Fire TV tile 1280×720: bg `#070b10`, mark 280px at x120 centred vertically, stacked wordmark 92/92 ("Your Own" 400 / "Commentator" 800, −0.025em), tagline "PICK WHO CALLS THE GAME" 32/700 +.14em accent. Decorative accent arcs at 10–16% opacity. Keep lockup in central 1120×560.
- Wordmark: "Your Own " 400 + "Commentator" 800. Min mark size 48 (TV) / 28 (phone). Clear space ½ mark height.

### 2. Home (`02 TV Home.dc.html`)
**2a Hero + games rail.** Header at y54: mark 56 + wordmark 30; right: language button (h64). Court image right 1320×742, faded left with `linear-gradient(90deg,#070b10 0%,rgba(7,11,16,.75) 30%,transparent 70%)` + bottom fade. Hero block at x96 y196: eyebrow "● NOW SHOWING · PINK VS BLUE" (accent), H "Pick who calls the game." 88/96 max-w 900, body 28/40 `#c4ced8`, buttons h80: **Watch with Rookie** (primary, focused default), Change commentator, Watch party. Games rail at y722: eyebrow "GAMES", cards 540×248 r20, gap 32. Poster = 115° split of the two team colours + dark gradient overlay + faint circle; bottom: title 30/800 + score chips (h44 r10 24/800, "PINK 62" "58 BLUE") + "FINAL". States: now showing (3px accent inset + pill), focused (ring+lift), default.
Focus: language → Watch → Change → Party; ▼ Game 1 → 2 → 3; ▼ commentators.

**2b Commentators grid.** Title "Choose your commentator" H2 at y150; hint right. Grid at y226: 4 cols × 414px, rows 226px, gap 24. Row 1: Rookie, Kid, **Booth (spans 2 cols)**; row 2: Fantasy, Novato, नौसिखिया, 新手. Card: padding 28, r20, bg panel, persona icon 96, name 32/800, tagline 24/32 `#c4ced8`, language chip (h40 pill, 1px lineStrong, 24/700 muted). Booth shows "PLAY-BY-PLAY", "ANALYST", "ENGLISH · 2 VOICES" chips. Rookie = selected (ON AIR). नौसिखिया = focused.
Copy: Rookie "Every call explained, zero jargon." · Kid "Big plays, big feelings, small words." · Booth "The classic two-person broadcast: one calls it, one breaks it down." · Fantasy "Stats, streaks and who’s heating up." · Novato "Cada jugada, explicada desde cero." (ESPAÑOL) · नौसिखिया "हर नियम, आसान शब्दों में।" (हिन्दी) · 新手 "每个判罚，简单讲清楚。" (中文).
Below at y764: "MORE WAYS TO WATCH": Highlights card ("12 key plays in 4 minutes, called by your commentator.") and Watch party card ("Everyone joins from their phone and calls the next basket."), each h200 in a 2-col grid.

### 3. Player overlays (`03 TV Player.dc.html`)
- **3a Live**: score bug (96,54). Code badge top-right: glass h76 r16, phone glyph, "Ask on your phone" 24/700, code chip accent h56 32/800 +.18em "4K7Q". Caption bottom-left (bottom 166, w1080): glass r24 p24/28, persona 72, role chip (h36 r8, 2px accent outline, accent 24/800 +.12em "PLAY-BY-PLAY"; ANALYST variant = `#e6edf3` fill, ink text), speaker "Booth · voice 1" muted, line 32/44 600. Minimap bottom-right 360 wide glass. **Control strip** bottom 54, full safe width, h88 r20 glass, p0 8, gap 12: Why? (primary, "?" disc), Catch me up, 7 commentators (with current persona icon 48), Map (toggled on state), Highlights, Replay; right: "● On air: Booth". Focus ◀▶ along strip, Back hides, auto-hide 6s.
- **3b Basket**: score bug flash state (+2 PINK). Rule card at (96,162) w600 glass: eyebrow "RULE" accent, title 36/800 "Free throw", body 26/38, 6px timer bar (accent on `#1c2733`). Caption with ANALYST label. Strip hidden.
- **3c Commentator tray**: above strip (bottom 166) glass r24 p16, 7-col grid, items h104 r16: persona 60 + name 26/800 + lang code 24. On-air item = 3px accent inset + "● ON AIR". Tray opens focused on on-air voice; OK switches; ▼/Back closes. Strip button "7 commentators ▲" in selected state.
- **3d Switching**: video dimmed 25%. Card bottom-left w860 glass: old persona (72, 50% opacity) overlapped by new (84), "Switching to Novato…" 40/48 800, "Cambiando a Novato · español · same game, same facts" 26 `#c4ced8`, 8px accent progress bar.
- **3e Replay + map**: 10px accent inset frame around the whole video; accent tag top-centre h76 "↺ REPLAY  Q3 · 4:12" 30/800 +.16em. Expanded map right (top 162) w704 with legend (Pink/Blue/Ball) and jersey numbers, one-line explanation 26/36.
- **3f Highlights**: outlined tag (3px accent inset on glass) "★ HIGHLIGHTS  3 of 12"; 12-segment progress bar (8px, gap 8, accent done / `#2a3847` pending). ◀▶ prev/next.

### 4. Why? / Catch me up / Watch party (`04 Why + Watch Party.dc.html`)
- **4a Why? questions** (game paused, video dim 50%, "❚❚ PAUSED" pill under score bug). Right panel: top/bottom 54, right 96, w760, p48, r28 glass. Eyebrow "? WHY? · ABOUT THIS PLAY" accent; context "Q3 · 4:12 · [PINK #23] fouled by [BLUE #4]" with team chips; H2 "What do you want to know?"; 3 question buttons h120 r16 28/36 700 with index numeral: "Why does Pink #23 get two free throws?", "Was that really a foul by Blue #4?", "Why did the clock stop?"; divider row "Or hold to ask on your phone — code 4K7Q"; bottom "▶ Resume game". Focus starts on Q1, ▼ through to Resume.
- **4b Answer**: same panel. Header: persona + "ROOKIE ANSWERS" + static/animated accent waveform (7 bars, 6px). Question echo 26 muted in quotes; answer 36/50 700; "CHECKED AGAINST" box (panel, r20, p24) with "✓ 3 of 3 facts verified" and 3 source lines (Play log · Score graphic · Rule). Buttons: **Resume** (primary, focused), Ask another, Replay play.
- **4c Catch me up**: centred card x400 y240 w1120 p48/56 r28. Eyebrow "CATCH ME UP · LAST 5 MIN", H1 56 "Pink went on a 10–2 run.", 3 rows (grid 110 / 150 / 1fr): time, team chip, sentence 28/38, hairline separators. Buttons: **Back to live** (primary, focused), Watch the run.
- **4d Party join** (full screen): header; eyebrow "WATCH PARTY · PINK VS BLUE"; H 72/80 "Join on your phone"; instructions (URL placeholder `yoc.app/join`); 4 code tiles 180×220 r24 140px 800 accent; **Start the party** (primary, focused) + Watch solo. Right "IN THE ROOM 3" list rows h80 r16 (Phone 1 ● ready …), "Up to 8 phones".
- **4e Prediction** (game keeps playing): bottom-left panel w1000 glass r28 p36/40: eyebrow "PREDICT", status "2 of 3 voted · closes in 0:08", H 48/56 "Next basket: Pink or Blue?", 2 team buttons h120 r20 in team colours (40/800 name + vote count), 8px timer bar. Focus ◀▶ Pink/Blue.
- **4f Result banner** (4s): bottom full safe width h200 r28 in scoring team colour; left 200px accent block "+2 / PINK"; "Pink scores!" 64/72 800 white; "2 of 3 phones called it. Phone 1 is on a 3-basket streak." 28/38; right pills (h64): winners on bg with accent text, others translucent.

### 5. Phone companion (`05 Phone Companion.dc.html`, 390×844)
Shared header: persona 36 + name 15/800 + status 13 muted; right status (CONNECTED / LISTENING / THINKING) 13/700.
- **5a Join**: logo row; eyebrow "STEP 1 OF 1"; "Enter the code on your TV" 34/40; 4 boxes h88 r16 (filled = accent 44/800, active = 2px accent + caret); Join TV button h56 r14 accent (40% opacity until 4 chars); footnote.
- **5b Idle**: mini score bar h52 r12 (team halves + Q3 4:12). Hold button 220px circle accent, mic glyph 84 accentInk, halo `0 0 0 10px rgba(255,212,0,.12)`. "Hold to ask" 22/800, "The game pauses while you talk". "TRY" chips (min-h44 pill).
- **5c Listening**: live transcript card ("YOU", 22/30 with accent caret). Button scale .94 + `0 0 0 6px bg, 0 0 0 12px accent` ring + 3 pulsing rings. "Listening…", "Let go to send · slide away to cancel".
- **5d Thinking**: button becomes panel2 circle with 3 bobbing dots; "Checking the play…" + checklist (✓ found foul in play log, ✓ score matches graphic, ○ writing answer).
- **5e Answer**: user bubble right (r18 18 4 18); answer card 2px accent inset r24: "ROOKIE ANSWERS", answer 20/28 700, "CHECKED AGAINST" list 15/21. Footer: 72px accent hold button + "Hold to ask again / TV resumes in 5 s".
- **5f Party result**: same language as TV banner — team-colour card with accent "+2 PINK" header, "Pink scores!" 34, "You called it. 3-basket streak."; room leaderboard rows h52; disabled Pink/Blue buttons (45%) until next prediction.

### 6. Demo video + Devpost (`06 Demo + Devpost.dc.html`, all 1920×1080)
6a Title card · 6b "Under the hood" 6-step pipeline (Nova Pro reads the game → Score graphic + human review → Nova 2 Lite writes → **Fact gates in code** (highlighted) → Polly speaks → Fire TV) · 6c Numbers (Exact score reader on 3 games · 5/182 video-only AI · 0 of 494 invented plays · 3.4 s talk-back) · 6d Lower-third "ASKED FROM THE PHONE" with 16px accent spine · 6e End card + credits (placeholders) · 6f Devpost hero TV + phone · 6g Commentator picker · 6h "No invented facts" grounding explainer.

---

## State management (app)
- `selectedGame`, `nowShowingGameId`
- `commentator` (rookie | kid | booth | fantasy | novato | hindi | mandarin), `switchingTo` (transient)
- `playback`: live | paused | replay | highlights (+ `highlightIndex`)
- `overlay`: none | strip | tray | why-questions | why-answer | catchup | rule-card | party-prediction | party-result
- `stripVisible` + 6s auto-hide timer; `mapOn` toggle
- `score {a, b, period, clock}`, `lastScored {team, pts}` (drives score-bug flash)
- `pairing {code, phonesConnected[]}`; phone: `askState` idle | listening | thinking | answered, `transcript`, `answer {text, sources[]}`
- `party {active, phones[], prediction {open, votes, closesAt}, result}`
Why?/Catch me up pause playback on open and resume on Resume/Back.

## Assets
- No raster assets. Mark, persona icons and minimap are inline SVG (in the component files).
- Court/arena imagery is a CSS placeholder for live video — replace with the real video surface. Keep any stills abstract/blurred; no faces.
- No third-party logos. Product names (Nova, Polly, Vega OS) appear only as text in demo/credit graphics.
- Placeholders to fill: credits names, join URL (`yoc.app/join`).

## Files
- `01 Brand + Spec.dc.html` — icon, tile, wordmark, tokens, type, spacing, states, overlay zones, language fit
- `02 TV Home.dc.html` — 2a, 2b
- `03 TV Player.dc.html` — 3a–3f
- `04 Why + Watch Party.dc.html` — 4a–4f
- `05 Phone Companion.dc.html` — 5a–5f
- `06 Demo + Devpost.dc.html` — 6a–6h
- `YOC Mark`, `YOC Score Bug`, `YOC Persona`, `YOC Minimap`, `YOC Court` `.dc.html` — shared components
- `support.js` — runtime needed to open the HTML references in a browser
