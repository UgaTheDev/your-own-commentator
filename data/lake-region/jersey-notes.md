# Lake Region jersey review (claude, from video frames)

Method: `cv/jersey.py` proposes a shooter from tracks.json and asks Nova Pro to read torso crops
(`events.jersey.json`, sheets in `data/lake-region/jersey/`, not committed). I then checked each scoring event on my own
wide 2x2 frame strips and 2x full-res zoom strips (`jersey/<id>w.jpg`, `jersey/<id>z.jpg`). A jersey went into
events.reviewed.json only if I could read the number on the player who actually took the shot. No names: jersey + colour only.

Result: 3 of 7 scoring events have a jersey. Nova's proposal matched my read on 1 of them (e34).

| id | type / team | Nova proposal (top track) | decision | evidence |
|---|---|---|---|---|
| e2 | ft_made blue | none (1 vote). The 2nd track read "3" 5/5, but #3 stands on the lane and is not the shooter | **blue #5** | The free-throw shooter has her back to the camera. The "5" is clear at t=31.0 (release) and partly visible at t=30.2 (e2z.jpg) |
| e3 | made_3 blue | none (15/11/1/5 split) | null | The release at ~60.2-60.5 is on the far side. The shooter's number is blurred ("10"/"13" can't be told apart) |
| e6 | made_2 pink | 1 (3 votes) | null | The layup at ~97.1 is taken by a dark-haired pink player. Her number is not visible. Pink #1 is a teammate trailing the play, and the track swaps to blue #2 at the release |
| e9 | ft_made pink | 1 (2 votes, 1 vote "11") | **pink #11** | The shooter follows through at t=126.6 and 126.9 with "11" on her back. At t=128.8 the same player shows "HAZEN 11" on the front (e9z.jpg). Nova dropped a digit |
| e13 | made_2 pink | 3 (3 votes) | null | The make is at ~249-250 (the in-gym board reads 16 by 254.5), not in the tracked window. The shooter can't be identified in the frames. #3 is only nearby |
| e34 | ft_made pink | 3 (3 of 5 votes) | **pink #3** | Pink #3 is at the line holding the ball, with "3" on her back at t=469.0, 469.8, 470.4 and 471.0 (e34z.jpg) |
| e42 | made_3 pink | 5 (3 votes) | null | The shooter is in the right corner by the bench (release ~576.1-576.6). Her back number is motion-blurred. #5 is a different player, at the top of the key |

Takeaway: Nova proposed a number for 5 events. 3 were the wrong player (e6, e13, e42), 1 had the right player but a
dropped digit (e9), and 1 was correct (e34). On e2, the second track's confident "3" was also a non-shooter.
The ball track is sparse and IDs swap in traffic. So Nova votes are only a pointer to where to look, never evidence.
