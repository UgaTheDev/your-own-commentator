# Demo video: shot list (under 3:00, target 2:45)

The rules require the app running on a Fire TV or the simulator. We use the **Vega Virtual Device (VVD)**.

## Recording setup (about 10 min, one time)
- **Capture: OBS** (free). Add a source: "macOS Screen Capture" → Window → the VVD window, with **Capture
  audio** ticked. QuickTime and Cmd+Shift+5 don't record the Mac's own audio, and we need the commentary.
  Record a 10 s test and play it back to check the commentary is audible before the real take.
- **Voiceover:** record it separately afterwards, in your own voice, and lay it over in any editor.
  **No music.** The only background sound is the CC0 crowd bed already in the tracks.
- **Phone shot:** iPhone screen recording (Control Centre → Record) of the phone page while you ask. Overlay
  it picture-in-picture next to the TV.
- **Driving the TV:** use the VVD's on-screen remote or the arrow keys. Or tell me "drive it" and I send the key
  presses from here while you record.
- **Talk-back:** say "ready for phone test" first. I scale the relay up (takes about 1 min) and the TV shows
  the code. This needs a fresh `! aws login`, because the session expired.

## Shots (Lake Region game: verified events at 0:31 FT, 1:03 blue three, 1:38 pink two, 2:11 FT, 4:24 timeout)
| Time | On screen | Voiceover (yours) |
|---|---|---|
| 0:00–0:15 | Phone: hold, ask "why did they stop?". The TV pauses and answers out loud | "My friend has never watched basketball. They asked my TV a question, and it answered." |
| 0:15–0:30 | Home: game picker (3 games) → Lake Region → pick **Rookie** | "This is Your Own Commentator on Fire TV. Pick a game, then pick your commentator." |
| 0:30–0:55 | Play from 0:25: the free throw at 0:31 and the three at 1:03. Rookie explains the free-throw rule | "Rookie explains each rule the moment it matters." |
| 0:55–1:20 | Same moment, switch with the D-pad: **Kid** → **Spanish** → **Hindi** | "Same game, same play, a different commentator. Seven of them, in four languages." |
| 1:20–1:35 | **Booth** (two voices), then **Fantasy** after the three | "A two-voice booth, or a fantasy analyst tracking points." |
| 1:35–1:50 | **Why?** → pick a question → spoken answer card. Then **Replay** (slow motion, tracked players marked) and **Map** | "Pause and ask why. Replays and the minimap come from our own computer vision." |
| 1:50–2:00 | **Catch me up** → recap. **Watch party** code shown | "Missed a minute? Catch up. Friends join from their own homes and call the next basket." |
| 2:00–2:30 | Screen recording of README diagram + accuracy table (or slides): Nova Pro → score graphic → review → gates → Polly | "Under the hood: Amazon Nova Pro reads the game, Nova 2 Lite writes, Nova Sonic hears your question, Polly speaks. Every line passes fact gates in code. Video-only AI was right 5 times in 182, so we anchor every score to the broadcast graphic. Zero invented plays in 494 lines." |
| 2:30–2:45 | Highlights reel playing | "Most amateur games have no commentary at all. Now every viewer gets their own broadcast." |

End card: "Footage: Hardwick Community Television, CC BY 4.0, via Wikimedia Commons. Original audio removed."

## Upload
YouTube or Vimeo, **Public** (or Unlisted if Devpost accepts it). Put the attribution line from SOURCES.md in the
description. Paste the link into Devpost.
