# Eval: hctv-boys-montpelier

Events matched on type and |dt| <= 2.0s, one-to-one.

| type | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|
| foul | 0 | 2 | 0 | 0.00 | 0.00 | 0.00 |
| ft_made | 1 | 5 | 5 | 0.17 | 0.17 | 0.17 |
| ft_missed | 0 | 1 | 0 | 0.00 | 0.00 | 0.00 |
| made_2 | 4 | 4 | 4 | 0.50 | 0.50 | 0.50 |
| missed_shot | 3 | 21 | 0 | 0.12 | 1.00 | 0.22 |
| rebound | 0 | 14 | 0 | 0.00 | 0.00 | 0.00 |
| timeout | 1 | 11 | 0 | 0.08 | 1.00 | 0.15 |
| overall | 9 | 58 | 9 | 0.13 | 0.50 | 0.21 |

## By source

| source | TP | FP | FN | precision | recall | window |
|---|---|---|---|---|---|---|
| nova | 4 | 49 | 0 | 0.08 | 1.00 | 2s |
| scoreboard | 9 | 5 | 5 | 0.64 | 0.64 | 6s |

Reviewed by: claude (AI review: spot-check welcome)

## Faithfulness

**0 unsupported / 94 lines** (a line counts as unsupported if it failed the grounding check or the judge)
