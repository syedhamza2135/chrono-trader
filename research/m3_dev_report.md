# M3 dev report (2017 to 2019)
Dev years 2017-01-03 to 2019-12-31. Costs 5 bps per side unless a table says otherwise. Sharpe ratios are over zero, no cash rate (the store has none; the owner, 23 Nov). Every number below comes from `eval/report.py` over the runs named here. H1 to H3 are tested on the sealed years only (PLAN 9.10), so this report tests none of them. p-values use the normal distribution, which is slightly liberal for a quarter of about 63 days. The Newey-West lag follows the number of days (6 for 754), which is shorter than a 20-day first-20 block, so those errors may be low.
- The frozen trial plan's SHA-256: `4a9a45a1238aad3b704a18f27c9bac046e13bbadf981ff642fc3d78986861e2f` (`research/m3_kickoff.md`).
- Stage 1 (highest mean daily rank IC; within 0.001, the earlier trial) chose T01. Stage 2 (highest long-short Sharpe after 5 bps; within 0.05, the lower daily turnover) chose T09: {"band": 15, "hold": 5}. "live" below is that configuration.
- IC days run from 2017-01-03 to 2019-12-30, so every label ends by 2019-12-31. Book returns run to 2019-12-31. Nothing from 2020 on is read.
- The baselines hold as long as the chosen trial; equal weight rebalances every session.

## Trials

8 trials in `C:/Users/syedh/dev/chrono-trader/.claude/worktrees/m3-kickoff-56264f/runs/trials.csv` (19 rows).

| trial | status | run_id | commit | dirty | settings_hash | agents |
|---|---|---|---|---|---|---|
| T01 | planned | 20261122T172112_9d54d2d3 | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 9d54d2d3c6beafc2834047758b47a7e017a96558ba529cee577044fc04f60671 | live |
| T02 | planned | 20261122T172112_07986034 | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 079860344f3df6a7a65746bce4aa55e59684e91ce004600e1b81dd90d2419dfb | live |
| T03 | planned | 20261122T172112_6ba5ce7f | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 6ba5ce7f92a406b9688260459d81d1e8c98e74c408040f9165eae922936f855a | live |
| T04 | planned | 20261122T172112_6a4d4a1e | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 6a4d4a1e474a7eb3ec99968df970417e6f55beda74e3e1b48c8d4a99a9e1103d | live |
| T05 | planned | 20261122T172113_21123e7c | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 21123e7ca241930153a04facfd220bb18322558cb6d77a6faa157e06d66e3d74 | live |
| T06 | planned | 20261122T172113_23a15566 | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 23a155665aa9dd088e7df0d5f4c2046e29694628c95832daedaececd29844e22 | live |
| T07 | planned | 20261122T172113_5b07791d | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 5b07791d1d06001a0498a964a261d849cb777d710caca349d0b90eb8df738974 | live |
| T08 | planned | 20261122T172113_77390a3d | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 77390a3d8281df353e2ef50f20238aa3bcfbe8691d0e404d736441cf6f6840f3 | live |
| T09 | planned | 20261122T172113_beef5e4d | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | beef5e4dbff9858a790628f4e791812aa46e8a95064cf29529b191811d955f5a | live |
| T04 | dropped | 20261122T173958_275e73bd | 9a17c8a691c19690c2b035764d5e4b600f9d598a | True | 275e73bd7a7d8833a5ffea6b4f83b139c39cea2ac34128ed2d471326b08e9aca | live |
| T01 | run | 20261122T191552_d305229a | 83a35cd73d3876fe2635557b414fc22d137e9cdf | False | d305229ab25b6c50d0346e13176c6398211216cfda343d52fabf27308b30d831 | live |
| T02 | run | 20261122T192557_c9e4c5a6 | 83a35cd73d3876fe2635557b414fc22d137e9cdf | True | c9e4c5a6ba4285b6dec5f585f84ac7664fbf0acdacc0ba50ba4e16171804b818 | live |
| T03 | run | 20261122T193632_f8b87d8a | 83a35cd73d3876fe2635557b414fc22d137e9cdf | True | f8b87d8a35af4c1a4451046528c84285502fa936945f3245906d64c263090d1b | live |
| T05 | run | 20261122T194728_48510e88 | 83a35cd73d3876fe2635557b414fc22d137e9cdf | True | 48510e88d133f5eae86cef4e357ddde9312a478896d14be9a51015df06cab17a | live |
| T06 | run | 20261122T195725_5fba9256 | 83a35cd73d3876fe2635557b414fc22d137e9cdf | True | 5fba92568673e916458dd0442bfafd179c3807e35b4bd816dafe8d8d651dfcbe | live |
| T07 | run | 20261122T200724_3dd39aa8 | 83a35cd73d3876fe2635557b414fc22d137e9cdf | True | 3dd39aa8fadb87e7423d609034102f61dac2a345f9541c6252170561a5549ca9 | live |
| T08 | run | 20261122T201728_9d6bce51 | 83a35cd73d3876fe2635557b414fc22d137e9cdf | True | 9d6bce519ca1fd3bcd228ff8a4413e8b813542e029924eb29ddd1ed9cec58e5c | live |
| T09 | run | 20261122T202727_eed2890b | 83a35cd73d3876fe2635557b414fc22d137e9cdf | True | eed2890bbe3f3581ee894f5010bda77c801d7d0fa6f8abccacc9e6d266f377ff | live |
|  | run | 20261122T215557_b9fab902 | 83a35cd73d3876fe2635557b414fc22d137e9cdf | True | b9fab902e46e01b5b2d32b11c062f21601e9069c9e3a8dd521df8d02d93b09ee | live live_long_only price_only placebo_1 placebo_2 placebo_3 placebo_4 placebo_5 random_1 random_2 random_3 random_4 random_5 momentum reversal equal_weight live_frozen_2016 live_frozen_2017 live_frozen_2018 |

## Daily rank IC by quarter (live)

| quarter | days | mean | se | t | p |
|---|---|---|---|---|---|
| 2017Q1 | 62 | 0.0160 | 0.0186 | 0.8608 | 0.1947 |
| 2017Q2 | 63 | -0.0291 | 0.0203 | -1.4313 | 0.9238 |
| 2017Q3 | 63 | -0.0179 | 0.0207 | -0.8642 | 0.8063 |
| 2017Q4 | 63 | 0.0465 | 0.0188 | 2.4668 | 0.0068 |
| 2018Q1 | 61 | 0.0394 | 0.0162 | 2.4310 | 0.0075 |
| 2018Q2 | 64 | 0.0189 | 0.0188 | 1.0065 | 0.1571 |
| 2018Q3 | 63 | -0.0016 | 0.0245 | -0.0638 | 0.5254 |
| 2018Q4 | 63 | 0.0013 | 0.0199 | 0.0659 | 0.4737 |
| 2019Q1 | 61 | 0.0165 | 0.0154 | 1.0723 | 0.1418 |
| 2019Q2 | 63 | -0.0014 | 0.0178 | -0.0770 | 0.5307 |
| 2019Q3 | 64 | 0.0211 | 0.0137 | 1.5451 | 0.0612 |
| 2019Q4 | 63 | -0.0173 | 0.0137 | -1.2623 | 0.8966 |
| all | 753 | 0.0076 | 0.0055 | 1.3803 | 0.0838 |

## Frozen-twin gaps (live minus twin, paired daily IC)

| twin | year | days | mean | se | t | p |
|---|---|---|---|---|---|---|
| end of 2016 | 2017 | 251 | 0.0172 | 0.0122 | 1.4095 | 0.0793 |
| end of 2016 | 2018 | 251 | 0.0292 | 0.0123 | 2.3735 | 0.0088 |
| end of 2016 | 2019 | 251 | 0.0071 | 0.0106 | 0.6757 | 0.2496 |
| end of 2016 | all | 753 | 0.0179 | 0.0069 | 2.6051 | 0.0046 |
| end of 2017 | 2018 | 251 | 0.0092 | 0.0103 | 0.8894 | 0.1869 |
| end of 2017 | 2019 | 251 | 0.0030 | 0.0096 | 0.3072 | 0.3794 |
| end of 2017 | all | 502 | 0.0061 | 0.0070 | 0.8688 | 0.1925 |
| end of 2018 | 2019 | 251 | -0.0150 | 0.0085 | -1.7581 | 0.9606 |
| end of 2018 | all | 251 | -0.0150 | 0.0085 | -1.7581 | 0.9606 |

## Reading: the price-only twin and the placebo (live minus each, paired daily IC)

| against | days | mean | se | t | p |
|---|---|---|---|---|---|
| price_only | 753.0000 | 0.0069 | 0.0093 | 0.7356 | 0.2310 |
| placebo_1 | 753.0000 | 0.0142 | 0.0078 | 1.8192 | 0.0344 |
| placebo_2 | 753.0000 | 0.0147 | 0.0076 | 1.9431 | 0.0260 |
| placebo_3 | 753.0000 | 0.0039 | 0.0072 | 0.5332 | 0.2969 |
| placebo_4 | 753.0000 | 0.0068 | 0.0075 | 0.9055 | 0.1826 |
| placebo_5 | 753.0000 | -0.0054 | 0.0076 | -0.7161 | 0.7630 |

## Matched baselines

Long-short, against cash (zero) and the long-short baselines:

| book | annual_return | annual_vol | sharpe_after_costs | sharpe_before_costs | annual_return_before_costs | max_drawdown | daily_turnover | days | mean_ic |
|---|---|---|---|---|---|---|---|---|---|
| live | -0.0341 | 0.1153 | -0.2432 | 0.1825 | 0.0145 | -0.1679 | 0.3895 | 754 | 0.0076 |
| momentum | 0.0540 | 0.1630 | 0.4045 | 0.4997 | 0.0705 | -0.2689 | 0.1229 | 754 | 0.0218 |
| reversal | -0.0750 | 0.1517 | -0.4378 | 0.0957 | 0.0030 | -0.2944 | 0.6415 | 754 | 0.0053 |
| random_1 | -0.0979 | 0.1022 | -0.9571 | -0.1432 | -0.0195 | -0.2974 | 0.6612 | 754 | -0.0081 |
| random_2 | -0.0705 | 0.0978 | -0.6988 | 0.1541 | 0.0103 | -0.2307 | 0.6617 | 754 | -0.0056 |
| random_3 | -0.1082 | 0.0998 | -1.0971 | -0.2722 | -0.0315 | -0.3206 | 0.6537 | 754 | -0.0062 |
| random_4 | -0.1788 | 0.0932 | -2.0674 | -1.1752 | -0.1066 | -0.4477 | 0.6679 | 754 | 0.0011 |
| random_5 | -0.0401 | 0.0943 | -0.3872 | 0.5100 | 0.0444 | -0.1634 | 0.6697 | 754 | -0.0083 |
| cash | 0.0000 | 0.0000 |  |  | 0.0000 | 0.0000 | 0.0000 | 0 |  |

Long-only, against SPY buy-and-hold and all picks equally:

| book | annual_return | annual_vol | sharpe_after_costs | sharpe_before_costs | annual_return_before_costs | max_drawdown | daily_turnover | days |
|---|---|---|---|---|---|---|---|---|
| live_long_only | 0.1389 | 0.1752 | 0.8306 | 0.9699 | 0.1669 | -0.2538 | 0.1930 | 754 |
| equal_weight | 0.1576 | 0.1395 | 1.1192 | 1.1292 | 0.1592 | -0.1979 | 0.0110 | 754 |
| spy_buy_and_hold | 0.1456 | 0.1251 | 1.1491 |  |  | -0.1902 |  | 753 |

## Every trial, winners and losers

| trial | stage | mean_ic | ic_t | sharpe_before_costs | sharpe_after_costs | max_drawdown | daily_turnover | won |
|---|---|---|---|---|---|---|---|---|
| T01 | 1 | 0.0076 | 1.3803 | 0.1118 | -1.7387 | -0.4848 | 1.7869 | stage 1 |
| T02 | 1 | -0.0026 | -0.4569 | 0.1020 | -1.4408 | -0.4351 | 1.5072 |  |
| T03 | 1 | 0.0083 | 1.4208 | 0.1056 | -1.8201 | -0.4897 | 1.8189 |  |
| T05 | 2 | 0.0076 | 1.3803 | -0.5305 | -1.2505 | -0.3904 | 0.7130 |  |
| T06 | 2 | 0.0076 | 1.3803 | 0.0534 | -0.4597 | -0.2612 | 0.4953 |  |
| T07 | 2 | 0.0076 | 1.3803 | 0.3047 | -0.8622 | -0.3030 | 1.1506 |  |
| T08 | 2 | 0.0076 | 1.3803 | -0.5085 | -1.0601 | -0.3578 | 0.5353 |  |
| T09 | 2 | 0.0076 | 1.3803 | 0.1825 | -0.2432 | -0.1679 | 0.3895 | stage 2 (chosen) |

## Variants (each a trial)

| variant | annual_return | annual_vol | sharpe_after_costs | sharpe_before_costs | annual_return_before_costs | max_drawdown | daily_turnover | days | mean_ic |
|---|---|---|---|---|---|---|---|---|---|
| T01 | -0.1967 | 0.1217 | -1.7387 | 0.1118 | 0.0062 | -0.4848 | 1.7869 | 754 | 0.0076 |
| T02 | -0.1689 | 0.1231 | -1.4408 | 0.1020 | 0.0050 | -0.4351 | 1.5072 | 754 | -0.0026 |
| T03 | -0.2006 | 0.1190 | -1.8201 | 0.1056 | 0.0055 | -0.4897 | 1.8189 | 754 | 0.0083 |
| T05 | -0.1508 | 0.1245 | -1.2505 | -0.5305 | -0.0709 | -0.3904 | 0.7130 | 754 | 0.0076 |
| T06 | -0.0613 | 0.1215 | -0.4597 | 0.0534 | -0.0008 | -0.2612 | 0.4953 | 754 | 0.0076 |
| T07 | -0.1085 | 0.1243 | -0.8622 | 0.3047 | 0.0306 | -0.3030 | 1.1506 | 754 | 0.0076 |
| T08 | -0.1280 | 0.1222 | -1.0601 | -0.5085 | -0.0671 | -0.3578 | 0.5353 | 754 | 0.0076 |

## Costs (bps per side)

live:

| cost | annual_return | annual_vol | sharpe | max_drawdown | total |
|---|---|---|---|---|---|
| 0 bps | 0.0145 | 0.1150 | 0.1825 | -0.1496 | 0.0440 |
| 5 bps | -0.0341 | 0.1153 | -0.2432 | -0.1679 | -0.0986 |
| 10 bps | -0.0804 | 0.1159 | -0.6653 | -0.2556 | -0.2218 |
| 20 bps | -0.1666 | 0.1179 | -1.4858 | -0.4372 | -0.4203 |

live_long_only:

| cost | annual_return | annual_vol | sharpe | max_drawdown | total |
|---|---|---|---|---|---|
| 0 bps | 0.1669 | 0.1751 | 0.9699 | -0.2480 | 0.5871 |
| 5 bps | 0.1389 | 0.1752 | 0.8306 | -0.2538 | 0.4759 |
| 10 bps | 0.1116 | 0.1754 | 0.6913 | -0.2595 | 0.3725 |
| 20 bps | 0.0589 | 0.1760 | 0.4133 | -0.2708 | 0.1867 |


## Exposures

Market beta against SPY's open-to-open returns (Newey-West):

| book | beta | se | t | alpha_daily | days |
|---|---|---|---|---|---|
| live | 0.2757 | 0.0547 | 5.0378 | -0.0003 | 754.0000 |
| live_long_only | 1.2385 | 0.0388 | 31.9042 | -0.0001 | 754.0000 |

Sector tilt of live's targets (net weight; sectors are Wikipedia's list as of each date, see `research/audit/benchmarks.md`):

| sector | mean_net | mean_abs_net |
|---|---|---|
| Communication Services | -0.0005 | 0.0509 |
| Consumer Discretionary | 0.0005 | 0.1358 |
| Consumer Staples | -0.0232 | 0.0882 |
| Energy | -0.0439 | 0.0858 |
| Financials | 0.0728 | 0.1086 |
| Health Care | -0.1097 | 0.1442 |
| Industrials | -0.0305 | 0.0836 |
| Information Technology | 0.1434 | 0.2023 |
| Materials | -0.0198 | 0.0264 |
| Telecommunication Services | 0.0113 | 0.0338 |
| all | 0.0004 | 0.9595 |

Sector tilt of live_long_only's targets (net weight; sectors are Wikipedia's list as of each date, see `research/audit/benchmarks.md`):

| sector | mean_net | mean_abs_net |
|---|---|---|
| Communication Services | 0.0668 | 0.0668 |
| Consumer Discretionary | 0.1517 | 0.1517 |
| Consumer Staples | 0.0617 | 0.0617 |
| Energy | 0.0358 | 0.0358 |
| Financials | 0.1523 | 0.1523 |
| Health Care | 0.1168 | 0.1168 |
| Industrials | 0.0443 | 0.0443 |
| Information Technology | 0.3389 | 0.3389 |
| Materials | 0.0033 | 0.0033 |
| Telecommunication Services | 0.0279 | 0.0279 |
| all | 0.9995 | 0.9995 |


## Deflated Sharpe (the chosen version)

Trials counted: 8 (the larger of the ledger's 8 trials and the 8 trials shown).

| sr | sr_annual | skew | kurt | n | n_trials | var_trials | sr0 | dsr |
|---|---|---|---|---|---|---|---|---|
| -0.0153 | -0.2432 | -0.2506 | 7.1519 | 754 | 8 | 0.0013 | 0.0523 | 0.0315 |

## Seed spread

placebo:

| seed | mean_ic | t | sharpe_after_costs |
|---|---|---|---|
| 1 | -0.0066 | -1.2569 | -0.3777 |
| 2 | -0.0071 | -1.4005 | -0.5891 |
| 3 | 0.0038 | 0.7305 | -0.0617 |
| 4 | 0.0008 | 0.1498 | -1.0756 |
| 5 | 0.0130 | 2.4729 | -0.1488 |
| min | -0.0071 | -1.4005 | -1.0756 |
| max | 0.0130 | 2.4729 | -0.0617 |
| mean | 0.0008 | 0.1392 | -0.4506 |
| std | 0.0083 | 1.5902 | 0.4054 |

random:

| seed | mean_ic | t | sharpe_after_costs |
|---|---|---|---|
| 1 | -0.0081 | -1.5415 | -0.9571 |
| 2 | -0.0056 | -1.1744 | -0.6988 |
| 3 | -0.0062 | -1.1217 | -1.0971 |
| 4 | 0.0011 | 0.2302 | -2.0674 |
| 5 | -0.0083 | -1.6336 | -0.3872 |
| min | -0.0083 | -1.6336 | -2.0674 |
| max | 0.0011 | 0.2302 | -0.3872 |
| mean | -0.0054 | -1.0482 | -1.0415 |
| std | 0.0038 | 0.7486 | 0.6341 |


## Regimes and shocks (reported, not tested)

| regime | value | ic_days | mean_ic | t | book_days | sharpe |
|---|---|---|---|---|---|---|
| trend | down | 71 | 0.0282 | 1.7970 | 71 | 0.5127 |
| trend | up | 682 | 0.0055 | 0.9363 | 683 | -0.3778 |
| vol | high | 367 | 0.0033 | 0.4337 | 367 | -0.2814 |
| vol | low | 386 | 0.0117 | 1.3896 | 387 | -0.2001 |
| shock | after shock | 40 | 0.0649 | 4.0088 | 40 | 3.1424 |
| shock | none | 713 | 0.0044 | 0.7917 | 714 | -0.4364 |

## Coefficient life (reported, not tested)

Each frozen twin's mean daily IC by quarter since its snapshot:

| twin | quarter | days | mean_ic | t |
|---|---|---|---|---|
| end of 2016 | 1 | 62 | 0.0119 | 0.6477 |
| end of 2016 | 2 | 63 | -0.0163 | -0.7903 |
| end of 2016 | 3 | 63 | -0.0282 | -1.4619 |
| end of 2016 | 4 | 63 | -0.0207 | -1.1340 |
| end of 2016 | 5 | 61 | 0.0042 | 0.2387 |
| end of 2016 | 6 | 64 | -0.0091 | -0.5698 |
| end of 2016 | 7 | 63 | -0.0356 | -2.0506 |
| end of 2016 | 8 | 63 | -0.0184 | -0.8280 |
| end of 2016 | 9 | 61 | 0.0491 | 3.7971 |
| end of 2016 | 10 | 63 | -0.0105 | -0.6594 |
| end of 2016 | 11 | 64 | -0.0232 | -1.3836 |
| end of 2016 | 12 | 63 | -0.0232 | -1.6922 |
| end of 2017 | 1 | 61 | 0.0184 | 0.9692 |
| end of 2017 | 2 | 64 | 0.0065 | 0.3246 |
| end of 2017 | 3 | 63 | 0.0031 | 0.1855 |
| end of 2017 | 4 | 63 | -0.0070 | -0.4556 |
| end of 2017 | 5 | 61 | 0.0053 | 0.2519 |
| end of 2017 | 6 | 63 | 0.0142 | 0.6780 |
| end of 2017 | 7 | 64 | 0.0009 | 0.0614 |
| end of 2017 | 8 | 63 | -0.0133 | -0.8313 |
| end of 2018 | 1 | 61 | 0.0154 | 0.9049 |
| end of 2018 | 2 | 63 | 0.0105 | 0.5759 |
| end of 2018 | 3 | 64 | 0.0256 | 1.4511 |
| end of 2018 | 4 | 63 | 0.0269 | 1.6791 |

## The switch-day check (`research/audit/cutoff.md` 10.2)

| year | first20_days | other_days | first20_mean | other_mean | difference | se | above_by_two_se |
|---|---|---|---|---|---|---|---|
| 2017 | 20 | 231 | -0.0686 | 0.0223 | -0.0909 | 0.0533 | no |
| 2018 | 20 | 231 | 0.0326 | -0.0050 | 0.0375 | 0.0371 | no |
| 2019 | 20 | 231 | 0.0273 | 0.0059 | 0.0214 | 0.0664 | no |

| difference | se | t | p | first20_days | other_days |
|---|---|---|---|---|---|
| -0.0107 | 0.0345 | -0.3088 | 0.6213 | 60 | 693 |

Years counted: 3. Warning (a), the pooled difference above zero at one-sided 5%: no. Warning (b), at least half the years above by more than two standard errors: no.

## Charts

- IC over time: `D:/chrono-data/runs/m3_dev_report_charts/ic.svg`
- Frozen-twin gaps: `D:/chrono-data/runs/m3_dev_report_charts/twin_gaps.svg`
- Long-short equity against the baselines: `D:/chrono-data/runs/m3_dev_report_charts/equity_long_short.svg`
- Long-only equity against SPY and equal weight: `D:/chrono-data/runs/m3_dev_report_charts/equity_long_only.svg`
- Cost sensitivity: `D:/chrono-data/runs/m3_dev_report_charts/costs.svg`
