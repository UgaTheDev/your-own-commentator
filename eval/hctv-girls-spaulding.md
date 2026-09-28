# Eval: hctv-girls-spaulding

Events matched on type and |dt| <= 2.0s, one-to-one.

| type | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|
| ft_made | 4 | 1 | 1 | 0.80 | 0.80 | 0.80 |
| ft_missed | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| made_2 | 2 | 2 | 2 | 0.50 | 0.50 | 0.50 |
| made_3 | 1 | 1 | 1 | 0.50 | 0.50 | 0.50 |
| missed_shot | 0 | 28 | 1 | 0.00 | 0.00 | 0.00 |
| rebound | 0 | 26 | 0 | 0.00 | 0.00 | 0.00 |
| steal | 0 | 14 | 0 | 0.00 | 0.00 | 0.00 |
| timeout | 0 | 14 | 0 | 0.00 | 0.00 | 0.00 |
| travel | 0 | 11 | 0 | 0.00 | 0.00 | 0.00 |
| turnover | 0 | 1 | 0 | 0.00 | 0.00 | 0.00 |
| overall | 7 | 98 | 7 | 0.07 | 0.50 | 0.12 |

## By source

| source | TP | FP | FN | precision | recall | window |
|---|---|---|---|---|---|---|
| nova | 0 | 94 | 3 | 0.00 | 0.00 | 2s |
| scoreboard | 11 | 0 | 0 | 1.00 | 1.00 | 6s |

Reviewed by: claude (AI review: spot-check welcome)
