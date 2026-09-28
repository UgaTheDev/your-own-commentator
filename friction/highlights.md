# Stream H (highlight reel + game picker) friction

Amazon-tool snags only.

| Date | Tool / doc | What I was doing | What went wrong (exact error / link) | Time lost | Suggested fix |
|---|---|---|---|---|---|
| 2026-09-27 | Amazon Nova 2 Lite (Bedrock, `write` model) through the digit gate | Short highlight line for e3 (blue made 3, score pink 11 blue 6) | Both attempts put a `9` in the line (`numbers not in facts: ['9']`), a number that is nowhere in the facts, even with the score spelled out in the prompt's example format. The other 6 events passed first time. Recovered through `answer.answer()` over the same facts ("Blue makes a three-pointer, score is pink 11, blue 6."). | 5 min | None needed on the model side for us (the gate caught it); worth noting that short, number-dense prompts are where Nova 2 Lite most often invents a digit |
