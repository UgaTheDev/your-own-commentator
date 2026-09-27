# Lake Region event review (claude, from video frames)

Method: ffmpeg contact sheets (about 1 fps, 2 fps for close checks) around each proposal, read frame by frame.
No human decisions existed in the previous events.reviewed.json (it was an unreviewed copy of the proposals).
Result: 9 accepted (7 scoreboard, 2 nova), 33 rejected. state.py final 20-6 matches clip.json.

| id | t (proposed -> reviewed) | type / team | decision | reason |
|---|---|---|---|---|
| e1 | 0.0 | timeout pink | reject | Players are live on court. Nobody gathers at a bench. |
| e2 | 34.5 -> 31.0 | ft_made blue | accept (t nudged) | A blue shooter is at the line with the lane lined up, and the ball is released at ~31 s. The graphic reads 2->3 at ~35.8. |
| e3 | 63.5 | made_3 blue | accept | Scoreboard. The graphic reads 3->6 at ~64.8. The release is not clear enough to nudge t. |
| e4 | 90.0 | steal pink | reject | This is a fast transition with motion blur. No steal is visible. |
| e5 | 90.1 | turnover blue | reject | This is a twin of e4. No turnover is visible. |
| e6 | 103.5 -> 98.0 | made_2 pink | accept (t nudged) | The pink shot at the baseline goes in at ~98 s and players celebrate. The graphic reads 11->13 at ~104. |
| e7 | 124.9 | timeout blue | reject | Players are lined up for a free throw. This is not a timeout. |
| e8 | 130.0 | timeout null | reject | This is the same free-throw sequence, and play continues. |
| e9 | 131.5 | ft_made pink | accept | Pink free throws are taken at ~121-130 and the graphic reads 13->14 at ~131. |
| e10 | 151.0 | steal pink | reject | Pink brings the ball up in transition. No steal is visible. |
| e11 | 227.0 | timeout null | reject | Play is live half court. |
| e12 | 240.1 | rebound blue | reject | A pink shot goes up at ~240 and the scramble that follows is not readable. The rebounder's team can't be told. |
| e13 | 257.5 | made_2 pink | accept | The pink make at the far basket shows on the graphic as 14->16 at ~258-259. |
| e14 | 258.1 | missed_shot pink | reject | This is a hallucination. The shot at this moment was the made basket e13. |
| e15 | 260.2 | rebound blue | reject | This is a hallucination. Blue inbounds after the make. |
| e16 | 262.3 | missed_shot blue | reject | This is a hallucination. No shot is taken, and play stops at ~263 (the timeout). |
| e17 | 264.4 | rebound pink | reject | This is a hallucination. The game is stopped and players walk to the benches. |
| e18 | 266.5 | missed_shot pink | reject | This is a hallucination, during the timeout. |
| e19 | 268.6 | rebound blue | reject | This is a hallucination, during the timeout. |
| e20 | 270.7 | missed_shot blue | reject | This is a hallucination, during the timeout. |
| e21 | 272.8 | rebound pink | reject | This is a hallucination, during the timeout. |
| e22 | 295.0 -> 264.0 | timeout pink -> null | accept (fixed) | A real timeout. Blue walks to its bench at ~263-267 and pink huddles at its bench from ~270 to ~297. t was moved to the start of the stoppage. Which team called it can't be seen, so team is null. |
| e23 | 298.6 | timeout blue | reject | This duplicates e22. Players are returning to the court at this point. |
| e24 | 303.1 | steal pink | reject | Blue has the ball after the restart. No steal is visible. |
| e25 | 303.2 | turnover blue | reject | This is a twin of e24. Nothing is visible. |
| e26 | 304.9 | timeout pink | reject | Play is live right after the timeout ends. |
| e27 | 316.0 | missed_shot blue | reject | There is a scramble at ~312 and then a blue half-court set. No shot is visible. |
| e28 | 316.1 | rebound pink | reject | This is a twin of e27. Nothing is visible. |
| e29 | 346.0 -> 347.0 | missed_shot pink | accept | A pink shot goes up at ~347 and the score stays 16-6. |
| e30 | 346.1 | rebound blue | reject | The rebound is not visible in the frames after the shot. |
| e31 | 385.2 | travel blue | reject | Pink has the ball, with a pink shot at ~383. No blue travel and no whistle stoppage are visible. |
| e32 | 423.1 | travel pink | reject | This is transition play. No travel call is visible. |
| e33 | 425.2 | travel pink | reject | A player is on the floor in transition. A travel can't be confirmed. |
| e34 | 474.5 | ft_made pink | accept | The free-throw lineup shows at ~468-471 and the graphic later reads 16->17. |
| e35 | 495.0 | steal pink | reject | This is transition play. No steal is visible (Nova confidence 0.5). |
| e36 | 513.1 | missed_shot pink | reject | Blue has the ball in the backcourt. There is no pink shot. |
| e37 | 521.5 | missed_shot blue | reject | No clear shot is visible. |
| e38 | 525.7 | missed_shot pink | reject | No clear shot is visible. |
| e39 | 530.0 | missed_shot pink | reject | Action happens in the paint, but no clear shot is visible. |
| e40 | 555.0 | timeout blue | reject | Play is live half court. |
| e41 | 573.1 | missed_shot pink | reject | No clear shot is visible in the window. |
| e42 | 580.5 -> 578.0 | made_3 pink | accept (t nudged) | Release at ~577 and the referee signals three at ~578. The in-gym board reads 20 at ~580. |
