# Spaulding event review (claude, from video frames)

Method: ffmpeg contact sheets (0.6-2 fps) over each cluster of proposals, read frame by frame; 2 fps re-checks for close calls.
Scoreboard t is the graphic update minus 1.5 s; nudged to the visible release when clear.
Result: 14 accepted (11 scoreboard, 3 nova, all nova ones fixed), 91 rejected. All Nova proposals were reviewed (21 sheets plus 2 re-checks).

| id | t (proposed -> reviewed) | type / team | decision | reason |
|---|---|---|---|---|
| e1 | 10.5 -> 8.3 | ft_made white | accept (t nudged) | white free throw released at ~8.3 s; graphic 38->39 at ~10.8. |
| e2 | 11.5 | missed_shot white | reject | after the FT, 11-22 s is transition then a maroon half-court set. No white shot, steal, travel or rebound is visible (a 1-2 s looping reply). |
| e3 | 13.6 | rebound maroon | reject | after the FT, 11-22 s is transition then a maroon half-court set. No white shot, steal, travel or rebound is visible (a 1-2 s looping reply). |
| e4 | 15.0 | steal white | reject | after the FT, 11-22 s is transition then a maroon half-court set. No white shot, steal, travel or rebound is visible (a 1-2 s looping reply). |
| e5 | 15.1 | travel maroon | reject | after the FT, 11-22 s is transition then a maroon half-court set. No white shot, steal, travel or rebound is visible (a 1-2 s looping reply). |
| e6 | 16.1 | rebound maroon | reject | after the FT, 11-22 s is transition then a maroon half-court set. No white shot, steal, travel or rebound is visible (a 1-2 s looping reply). |
| e7 | 17.8 | missed_shot maroon | reject | after the FT, 11-22 s is transition then a maroon half-court set. No white shot, steal, travel or rebound is visible (a 1-2 s looping reply). |
| e8 | 19.9 | rebound white | reject | after the FT, 11-22 s is transition then a maroon half-court set. No white shot, steal, travel or rebound is visible (a 1-2 s looping reply). |
| e9 | 20.0 | missed_shot maroon | reject | after the FT, 11-22 s is transition then a maroon half-court set. No white shot, steal, travel or rebound is visible (a 1-2 s looping reply). |
| e10 | 30.0 | missed_shot white | reject | five events within 0.4 s (looping reply). White half-court then transition, no readable shot, travel or steal. |
| e11 | 30.1 | rebound maroon | reject | five events within 0.4 s (looping reply). White half-court then transition, no readable shot, travel or steal. |
| e12 | 30.2 | travel maroon | reject | five events within 0.4 s (looping reply). White half-court then transition, no readable shot, travel or steal. |
| e13 | 30.3 | turnover maroon | reject | five events within 0.4 s (looping reply). White half-court then transition, no readable shot, travel or steal. |
| e14 | 30.4 | steal white | reject | five events within 0.4 s (looping reply). White half-court then transition, no readable shot, travel or steal. |
| e15 | 60.0 | timeout None | reject | play is live at mid court. Not a timeout. |
| e16 | 78.1 | timeout None | reject | dead ball with the referee holding the ball and players standing on court. No bench huddle, not a timeout. |
| e17 | 91.0 | steal white | reject | 1 s evenly spaced loop. A loose-ball scramble at ~93 is not readable. No clear steal, shot or travel. |
| e18 | 92.0 | missed_shot white | reject | 1 s evenly spaced loop. A loose-ball scramble at ~93 is not readable. No clear steal, shot or travel. |
| e19 | 93.0 | rebound maroon | reject | 1 s evenly spaced loop. A loose-ball scramble at ~93 is not readable. No clear steal, shot or travel. |
| e20 | 94.0 | travel maroon | reject | 1 s evenly spaced loop. A loose-ball scramble at ~93 is not readable. No clear steal, shot or travel. |
| e21 | 95.0 | steal white | reject | 1 s evenly spaced loop. A loose-ball scramble at ~93 is not readable. No clear steal, shot or travel. |
| e22 | 103.0 -> 100.5 | missed_shot white -> missed_shot maroon | accept (fixed) | the shot at ~100.5 is by maroon at the near-basket side, not white; ball hits the rim area and the score stays 39-30. |
| e23 | 132.5 | ft_made white | accept | white free-throw sequence; graphic 39->40 at ~134. Release not visible (camera on the baseline), t kept. |
| e24 | 149.5 -> 147.5 | ft_made white | accept (t nudged) | white free throw in the air at ~147.5; graphic 40->41 at ~151. |
| e25 | 151.0 | steal white | reject | 1 s evenly spaced loop. Maroon brings the ball up after the FT. Nothing visible. |
| e26 | 152.0 | missed_shot white | reject | 1 s evenly spaced loop. Maroon brings the ball up after the FT. Nothing visible. |
| e27 | 153.0 | rebound maroon | reject | 1 s evenly spaced loop. Maroon brings the ball up after the FT. Nothing visible. |
| e28 | 154.0 | travel maroon | reject | 1 s evenly spaced loop. Maroon brings the ball up after the FT. Nothing visible. |
| e29 | 155.0 | steal white | reject | 1 s evenly spaced loop. Maroon brings the ball up after the FT. Nothing visible. |
| e30 | 156.0 | missed_shot white | reject | 1 s evenly spaced loop. Maroon brings the ball up after the FT. Nothing visible. |
| e31 | 157.0 | rebound maroon | reject | 1 s evenly spaced loop. Maroon brings the ball up after the FT. Nothing visible. |
| e32 | 158.0 | travel maroon | reject | 1 s evenly spaced loop. Maroon brings the ball up after the FT. Nothing visible. |
| e33 | 180.0 | steal white | reject | transition play with motion blur. No steal, travel, shot or rebound visible. |
| e34 | 180.1 | travel maroon | reject | transition play with motion blur. No steal, travel, shot or rebound visible. |
| e35 | 181.0 | missed_shot white | reject | transition play with motion blur. No steal, travel, shot or rebound visible. |
| e36 | 181.1 | rebound maroon | reject | transition play with motion blur. No steal, travel, shot or rebound visible. |
| e37 | 184.0 | rebound white | reject | transition play with motion blur. No steal, travel, shot or rebound visible. |
| e38 | 188.5 -> 188.0 | made_3 white | accept (t nudged) | white three from the right wing, referee signals three at ~188; graphic 41->44 at ~190. |
| e39 | 195.1 | rebound maroon | reject | maroon in transition and a half-court set. No shot is visible. |
| e40 | 196.0 | missed_shot maroon | reject | maroon in transition and a half-court set. No shot is visible. |
| e41 | 228.1 | timeout None | reject | the game clock sits at 1:53 during a dead-ball stretch but players stay on court and nobody goes to a bench. Not a timeout. |
| e42 | 232.3 | timeout None | reject | the game clock sits at 1:53 during a dead-ball stretch but players stay on court and nobody goes to a bench. Not a timeout. |
| e43 | 236.5 | missed_shot white | reject | dead-ball stretch (clock stopped). No shots or rebounds. |
| e44 | 238.6 | rebound maroon | reject | dead-ball stretch (clock stopped). No shots or rebounds. |
| e45 | 240.7 | missed_shot maroon | reject | dead-ball stretch (clock stopped). No shots or rebounds. |
| e46 | 241.0 | timeout white | reject | the game clock sits at 1:53 during a dead-ball stretch but players stay on court and nobody goes to a bench. Not a timeout. |
| e47 | 242.8 | rebound white | reject | dead-ball stretch (clock stopped). No shots or rebounds. |
| e48 | 244.9 | timeout None | reject | the game clock sits at 1:53 during a dead-ball stretch but players stay on court and nobody goes to a bench. Not a timeout. |
| e49 | 258.1 | missed_shot white | reject | half-court set, no clear white shot at ~258. |
| e50 | 258.2 | rebound maroon | reject | half-court set, no clear white shot at ~258. |
| e51 | 269.5 -> 267.3 | made_2 maroon | accept (t nudged) | shot at the rim at ~267.3 followed by a maroon inbound/transition; graphic Guest 30->32 at ~271. |
| e52 | 272.8 | missed_shot white | reject | white brings the ball up after the maroon basket. No shot. |
| e53 | 274.9 | rebound maroon | reject | white brings the ball up after the maroon basket. No shot. |
| e54 | 288.1 | missed_shot white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e55 | 290.2 | rebound white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e56 | 292.3 | missed_shot white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e57 | 296.5 | missed_shot white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e58 | 298.6 | rebound white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e59 | 300.7 | missed_shot white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e60 | 302.8 | rebound white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e61 | 305.2 | missed_shot white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e62 | 307.3 | rebound white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e63 | 309.4 | missed_shot white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e64 | 311.5 | rebound white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e65 | 313.6 | missed_shot white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e66 | 315.7 | rebound white | reject | evenly spaced 2.1 s loop (13 white shot/rebound pairs). The checked sheet (286-298) shows a dead ball and a maroon sideline inbound. |
| e67 | 321.5 -> 320.0 | made_2 maroon | accept (t nudged) | maroon put-back at the far basket at ~319-320; graphic 32->34 at ~323. |
| e68 | 325.0 | steal white | reject | transition with motion blur at ~325. No steal visible. |
| e69 | 330.1 | timeout white | reject | live half-court play, then players standing on court during a stoppage. No bench huddle, not a timeout. |
| e70 | 334.9 | timeout None | reject | live half-court play, then players standing on court during a stoppage. No bench huddle, not a timeout. |
| e71 | 350.2 | timeout None | reject | free-throw lineup at ~346-354. Not a timeout. |
| e72 | 359.5 -> 358.0 | ft_made white | accept (t nudged) | white shooter at the line at ~358; graphic 44->45 at ~359. |
| e73 | 371.5 | ft_made white | accept | white free-throw lineup at ~364-369; graphic 45->46 at ~373. Release not clear enough to nudge. |
| e74 | 375.0 | steal white | reject | four events within 0.3 s (looping reply) during transition. Nothing visible. |
| e75 | 375.1 | travel maroon | reject | four events within 0.3 s (looping reply) during transition. Nothing visible. |
| e76 | 375.2 | missed_shot white | reject | four events within 0.3 s (looping reply) during transition. Nothing visible. |
| e77 | 375.3 | rebound maroon | reject | four events within 0.3 s (looping reply) during transition. Nothing visible. |
| e78 | 395.5 -> 394.3 | made_2 white | accept (t nudged) | white shot from the left block reaches the rim at ~394.3; graphic 46->48 at ~397. |
| e79 | 430.0 | steal white | reject | white holds the ball through this whole possession (it ends in the e87 three). No maroon travel, shot or steal. |
| e80 | 430.3 | travel maroon | reject | white holds the ball through this whole possession (it ends in the e87 three). No maroon travel, shot or steal. |
| e81 | 431.5 | missed_shot white | reject | white holds the ball through this whole possession (it ends in the e87 three). No maroon travel, shot or steal. |
| e82 | 432.0 | rebound maroon | reject | white holds the ball through this whole possession (it ends in the e87 three). No maroon travel, shot or steal. |
| e83 | 433.0 | travel maroon | reject | white holds the ball through this whole possession (it ends in the e87 three). No maroon travel, shot or steal. |
| e84 | 434.0 | missed_shot maroon | reject | white holds the ball through this whole possession (it ends in the e87 three). No maroon travel, shot or steal. |
| e85 | 435.2 | travel maroon | reject | white holds the ball through this whole possession (it ends in the e87 three). No maroon travel, shot or steal. |
| e86 | 435.3 | steal white | reject | white holds the ball through this whole possession (it ends in the e87 three). No maroon travel, shot or steal. |
| e87 | 438.5 -> 436.0 | made_3 white | accept (t nudged) | white bench celebrates the three at ~436; graphic 48->51 at ~440. |
| e88 | 469.9 -> 466.3 | timeout None -> ft_missed maroon | accept (fixed) | not a timeout. A maroon free throw is released at ~466 and hits the rim, and the score stays 51-34. |
| e89 | 472.3 | timeout None | reject | players lined up between free throws. Not a timeout. |
| e90 | 481.0 | steal white | reject | ~1 s evenly spaced loop. The real play here is the missed maroon free throw (e91 fixed) then white transition. |
| e91 | 482.0 -> 482.0 | missed_shot white -> ft_missed maroon | accept (fixed) | not a white shot. A maroon free throw released at ~482 is missed and white rebounds; score stays 51-34. |
| e92 | 483.1 | rebound maroon | reject | ~1 s evenly spaced loop. The real play here is the missed maroon free throw (e91 fixed) then white transition. |
| e93 | 484.2 | steal maroon | reject | ~1 s evenly spaced loop. The real play here is the missed maroon free throw (e91 fixed) then white transition. |
| e94 | 485.2 | missed_shot maroon | reject | ~1 s evenly spaced loop. The real play here is the missed maroon free throw (e91 fixed) then white transition. |
| e95 | 486.3 | rebound white | reject | ~1 s evenly spaced loop. The real play here is the missed maroon free throw (e91 fixed) then white transition. |
| e96 | 487.3 | missed_shot white | reject | ~1 s evenly spaced loop. The real play here is the missed maroon free throw (e91 fixed) then white transition. |
| e97 | 488.4 | rebound maroon | reject | ~1 s evenly spaced loop. The real play here is the missed maroon free throw (e91 fixed) then white transition. |
| e98 | 495.0 | steal white | reject | maroon transition make (e100). No steal, travel, white miss or rebound. |
| e99 | 495.1 | travel maroon | reject | maroon transition make (e100). No steal, travel, white miss or rebound. |
| e100 | 495.5 -> 491.0 | made_2 maroon | accept (t nudged) | maroon #10 layup in transition at ~491, ball through at ~492; graphic 34->36 at ~495. |
| e101 | 496.0 | missed_shot white | reject | maroon transition make (e100). No steal, travel, white miss or rebound. |
| e102 | 496.1 | rebound maroon | reject | maroon transition make (e100). No steal, travel, white miss or rebound. |
| e103 | 510.1 | timeout white | reject | stoppages with players on court and the referee signalling. No bench huddle, not a timeout. |
| e104 | 513.0 | timeout white | reject | stoppages with players on court and the referee signalling. No bench huddle, not a timeout. |
| e105 | 526.0 | timeout white | reject | stoppages with players on court and the referee signalling. No bench huddle, not a timeout. |
