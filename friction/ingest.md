# Stream B (ingest) friction

Date | Tool / doc | What I was doing | What went wrong (exact error / link) | Time lost | Suggested fix
---|---|---|---|---|---
2026-09-27 | Claude Code worktree sandbox | `git checkout -b stream/ingest && source scripts/stream-env.sh` chained in one command | Sandbox refused: "command names git in a form too complex to verify that it stays inside the worktree" for any compound command containing `&&`/`source` alongside `git` | ~2 min | Run `git checkout -b` alone, then export `PY`/`YOC_DATA` as plain env vars per-command instead of `source`-ing `stream-env.sh` (shell state doesn't persist across tool calls anyway)
