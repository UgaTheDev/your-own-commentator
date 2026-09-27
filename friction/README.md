# Per-stream friction rows

Each v2 stream appends rows to `friction/<stream>.md` (same columns as FRICTION-LOG.md:
Date | Tool / doc | What I was doing | What went wrong (exact error / link) | Time lost | Suggested fix).
The integrator folds them into FRICTION-LOG.md at each checkpoint, so parallel branches never
conflict on one file. Never put URLs with credentials or tokens in a row.
