# Stream C (writer, booth, voice) friction

| Date | Tool / doc | What I was doing | What went wrong (exact error / link) | Time lost | Suggested fix |
|---|---|---|---|---|---|
| 2026-09-27 | Claude Code worktree isolation | Running `source scripts/stream-env.sh` then `$PY ...` in a stream worktree | Refused: "this command runs source inside a construct too complex to verify ... cannot be shown not to run git"; the same for `$PY` ("command whose name is computed at runtime") and for heredocs | 5 min | Brief agents to call the absolute interpreter path with `YOC_DATA=...` inline instead of sourcing the env script |
| 2026-09-27 | pipeline/mix.py | Rendering the booth track from a worktree | `clip.json` `audioBed` ("data/ambience/crowd.flac") was resolved against the repo root, which in a worktree has no `data/` | 2 min | Fixed: resolve it against `common.DATA.parent`, which follows `YOC_DATA` |
| 2026-09-27 | Amazon Nova 2 Lite (judge) | Gating the 60 s recaps | The judge passed "Blue led early, but pink scored 14 to blue's 6" even though FACTS held only the current score (pink 14, blue 6). I caught it reading the output by hand | 5 min | Tightened the recap prompt (the score is NOW; never say who led before or who's on a run). The judge is still the weak gate, so keep the 20-line hand spot-check at every merge |
