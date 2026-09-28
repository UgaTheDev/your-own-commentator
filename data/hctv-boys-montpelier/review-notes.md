# Montpelier event review (claude, from video frames)

Method: ffmpeg contact sheets (1.6 fps, 5 s around each proposal), plus denser (2-3 fps) and wider (0.5 fps) sheets for the free-throw sequences, the timeout and the final minute. Looping Nova replies were checked on one sheet per run.
Result: 18 accepted (14 scoreboard incl. the e16b split, 4 nova), 50 rejected. Scoreboard points still total +11/+11 (23-22 -> 34-33).

| id | t (proposed -> reviewed) | type / team | source | decision |
|---|---|---|---|---|
| e1 | 10.5 -> 3.5 | made_2 green -> made_2 green | scoreboard | accept (t nudged): green shot at the far basket released ~3.3 s, ball at rim ~3.8; graphic 22->24 at ~6 s. |
| e2 | 57.5 -> 55.0 | ft_made white -> ft_made white | scoreboard | accept (t nudged): white shooter at the line, ball at the rim ~55 s; in-gym board 23->24 by ~56.4. |
| e3 | 63.1 | missed_shot green | nova | reject: green brings the ball up half court; no shot. |
| e4 | 69.4 | missed_shot green | nova | reject: the shot at this moment is the green make e5; no miss. |
| e5 | 69.5 -> 67.0 | ft_made green -> made_2 green | scoreboard | accept (fixed ft_made -> made_2): green layup at the far basket goes in at ~67 s during live play (no free-throw lineup anywhere 64-75 s); the graphic ticks 24->25->26 in two 1-point steps, so this is one made 2, not two free throws. |
| e6 | 72.5 | ft_made green | scoreboard | reject: duplicate: second 1-point tick of the same green made 2 (e5); no free throw is taken. |
| e7 | 73.6 -> 74.5 | missed_shot green -> missed_shot white | nova | accept (fixed team green -> white): a white player shoots at the near basket at ~74.5 s and a white putback follows at ~75.8; score stays 24. |
| e8 | 75.1 | rebound green | nova | reject: white keeps the ball after its miss (putback ~75.8); no green rebound readable. |
| e9 | 77.8 | missed_shot green | nova | reject: green transition after the white miss; no green shot visible. |
| e10 | 81.5 -> 80.5 | made_2 green -> made_2 green | scoreboard | accept (t nudged): green layup at the far basket ~80.4 s; graphic 26->28 at ~83. |
| e11 | 93.5 -> 93.5 | made_2 white -> made_2 white | scoreboard | accept: scoreboard 24->26 at ~94.3; the make is not visible in transition, t kept. |
| e12 | 105.0 | rebound green | nova | reject: a white shot at ~104.5 and a player on the floor; the rebound team is not readable. |
| e13 | 108.1 | timeout None | nova | reject: stoppage after the collision; players stay on court, no bench huddle. Not a timeout. |
| e14 | 115.0 | timeout None | nova | reject: same stoppage, close-ups of players standing on court. Not a timeout. |
| e15 | 120.7 | ft_missed white | nova | reject: close-ups of players waiting; no white free throw visible (#15 is a green player). |
| e16 | 130.5 -> 128.5 | made_2 green -> ft_made green | scoreboard | accept (fixed made_2 -> ft_made, split into e16 + e16b): play is dead from the collision at ~105 s until ~150 s (close-ups, then a free-throw lineup); no field goal is possible, so the 28->30 graphic update at ~129 must be two green free throws. Exact releases are hidden by the close-up camera. |
| e17 | 139.9 | timeout None | nova | reject: green free-throw lineup; not a timeout. |
| e18 | 148.5 -> 148.5 | ft_made green -> ft_made green | scoreboard | accept: green shooter at the line ~134-148 s during the lineup; graphic 30->31 at ~150. Release not clear, t kept. |
| e19 | 161.5 | foul white | nova | reject: a collision near the basket and a white player on the floor at ~161; which team fouled is not readable. |
| e20 | 163.6 | foul white | nova | reject: twin of e19; no second foul visible. |
| e21 | 198.1 | missed_shot white | nova | reject: the shot at ~198 is the white make e22; not a miss. |
| e22 | 200.5 -> 198.0 | made_2 white -> made_2 white | scoreboard | accept (t nudged): white shot at the near basket ~197.5-198 s; in-gym board shows 28 by ~199.4, graphic 26->28 at ~201. |
| e23 | 225.0 | missed_shot white | nova | reject: a loose-ball scramble near the sideline; no shot. |
| e24 | 225.1 | rebound green | nova | reject: twin of e23; no rebound. |
| e25 | 254.5 -> 254.5 | made_2 white -> made_2 white | scoreboard | accept: scoreboard 28->30 at ~255; the make is not visible in transition, t kept. |
| e26 | 275.2 -> 274.0 | missed_shot white -> missed_shot white | nova | accept (t nudged): a white player goes up at the near rim at ~274 s; score stays 30 until the free throw at ~331. |
| e27 | 279.4 | missed_shot white | nova | reject: dead ball, players jog back; no shot. |
| e28 | 288.0 | missed_shot green | nova | reject: green inbounds and brings the ball up; no shot. |
| e29 | 333.1 | timeout None | nova | reject: white free-throw lineup; not a timeout. |
| e30 | 335.2 | timeout None | nova | reject: same free-throw lineup; not a timeout. |
| e31 | 340.5 -> 331.5 | ft_made white -> ft_made white | scoreboard | accept (t nudged): white #11 free throw released ~331 s; in-gym board 30->31 by ~334, graphic catches up at ~341. |
| e32 | 348.1 | missed_shot white | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e33 | 350.2 | rebound green | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e34 | 352.3 | missed_shot green | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e35 | 354.4 | rebound white | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e36 | 356.5 | missed_shot white | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e37 | 358.6 | rebound green | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e38 | 360.7 | missed_shot green | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e39 | 361.0 | timeout None | nova | reject: free-throw lineup; not a timeout. |
| e40 | 362.8 | rebound white | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e41 | 363.1 | missed_shot green | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e42 | 365.2 | rebound white | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e43 | 367.3 | missed_shot white | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e44 | 367.5 -> 362.0 | ft_made white -> ft_made white | scoreboard | accept (t nudged): second white free throw released ~362 s in the same lineup; in-gym board reads 32 by ~366. |
| e45 | 369.4 | rebound green | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e46 | 371.5 | missed_shot green | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e47 | 373.6 | rebound white | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e48 | 375.7 | missed_shot white | nova | reject: looping reply (2.1 s spacing, alternating teams) during the white free-throw lineup 331-363 s; no live shots or rebounds. |
| e49 | 421.0 -> 423.0 | timeout green -> timeout None | nova | accept (fixed team green -> null, t 421 -> 423): real timeout; green huddles at its bench from ~424 and white at its bench, play resumes ~468. Who called it is not visible, so team is null. |
| e50 | 421.5 -> 421.5 | made_2 green -> made_2 green | scoreboard | accept: scoreboard 31->33 at ~422; the camera shows close-ups of green players, the make is not visible, t kept. |
| e51 | 454.9 | timeout None | nova | reject: duplicate of the e49 timeout. |
| e52 | 460.0 | timeout None | nova | reject: duplicate of the e49 timeout (white huddle visible). |
| e53 | 466.0 | timeout None | nova | reject: duplicate of the e49 timeout; players returning. |
| e54 | 470.2 | missed_shot white | nova | reject: looping reply (2.1 s spacing) at the restart after the timeout; white inbounds, no shots or rebounds. |
| e55 | 472.3 | rebound green | nova | reject: looping reply (2.1 s spacing) at the restart after the timeout; white inbounds, no shots or rebounds. |
| e56 | 476.5 | missed_shot green | nova | reject: looping reply (2.1 s spacing) at the restart after the timeout; white inbounds, no shots or rebounds. |
| e57 | 478.6 | rebound white | nova | reject: looping reply (2.1 s spacing) at the restart after the timeout; white inbounds, no shots or rebounds. |
| e58 | 480.7 | missed_shot white | nova | reject: looping reply (2.1 s spacing) at the restart after the timeout; white inbounds, no shots or rebounds. |
| e59 | 482.8 | rebound green | nova | reject: looping reply (2.1 s spacing) at the restart after the timeout; white inbounds, no shots or rebounds. |
| e60 | 495.0 | timeout None | nova | reject: live play; no timeout. |
| e61 | 510.0 | timeout None | nova | reject: live play; no timeout. |
| e62 | 510.5 -> 505.0 | made_2 white -> made_2 white | scoreboard | accept (t moved earlier): the graphic already reads 34 at ~506 s, after a white possession at the far basket ~502-504; the release is not clear. |
| e63 | 540.0 | missed_shot white | nova | reject: looping reply (4.2 s spacing); white half-court set, no shot at ~540. |
| e64 | 545.2 -> 545.0 | missed_shot white -> missed_shot green | nova | accept (fixed team white -> green): a green player shoots at the far rim ~545 s; score stays 33 to the end. |
| e65 | 549.4 | missed_shot white | nova | reject: looping reply; white inbounds from the sideline at ~549. |
| e66 | 553.6 | missed_shot white | nova | reject: looping reply; white inbound/backcourt, no shot. |
| e67 | 555.1 | rebound white | nova | reject: white brings the ball up; no rebound. |
