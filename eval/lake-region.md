# Eval: lake-region

Events matched on type and |dt| <= 2.0s, one-to-one.

| type | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|
| ft_made | 2 | 1 | 1 | 0.67 | 0.67 | 0.67 |
| made_2 | 1 | 1 | 1 | 0.50 | 0.50 | 0.50 |
| made_3 | 1 | 1 | 1 | 0.50 | 0.50 | 0.50 |
| missed_shot | 1 | 10 | 0 | 0.09 | 1.00 | 0.17 |
| rebound | 0 | 7 | 0 | 0.00 | 0.00 | 0.00 |
| steal | 0 | 4 | 0 | 0.00 | 0.00 | 0.00 |
| timeout | 0 | 8 | 1 | 0.00 | 0.00 | 0.00 |
| travel | 0 | 3 | 0 | 0.00 | 0.00 | 0.00 |
| turnover | 0 | 2 | 0 | 0.00 | 0.00 | 0.00 |
| overall | 5 | 37 | 4 | 0.12 | 0.56 | 0.20 |

## By source

| source | TP | FP | FN | precision | recall | window |
|---|---|---|---|---|---|---|
| nova | 1 | 34 | 1 | 0.03 | 0.50 | 2s |
| scoreboard | 7 | 0 | 0 | 1.00 | 1.00 | 6s |

Reviewed by: claude (AI review: spot-check welcome)
