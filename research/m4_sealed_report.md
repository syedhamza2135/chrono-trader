# Sealed report (M4)

- PREREG.md SHA-256: `97e15094684e1b40e4a8d967cba55ec79e92b7f2ac55b3a55b21e3a5681d92ca`
- seal.lock: `{"commit": "8c683f566c8126982282d6713dc3f78007973f20", "prereg": "97e15094684e1b40e4a8d967cba55ec79e92b7f2ac55b3a55b21e3a5681d92ca", "sealed_end": "2026-10-28", "sealed_start": "2020-01-02", "settings": {"main": "755dcf398dcb34975ae84fa65518190d9504d591057ff80591b79f5ac74ee3a5", "older_vintage": "380ebc4f7809de2f15b4f117d1a016514978a0ba0b2233a05dea656dbada0941"}, "written_at": "2026-11-23T12:31:11"}`
- Run log: `{"again": false, "commit": "423a9c2a557fae5f5b428d29a6d15593798b0dd5", "n": 1, "part": "main", "settings_hash": "755dcf398dcb34975ae84fa65518190d9504d591057ff80591b79f5ac74ee3a5", "started_at": "2026-11-23T12:33:20"}`
- Run log: `{"again": false, "commit": "423a9c2a557fae5f5b428d29a6d15593798b0dd5", "n": 1, "part": "older_vintage", "settings_hash": "380ebc4f7809de2f15b4f117d1a016514978a0ba0b2233a05dea656dbada0941", "started_at": "2026-11-23T21:20:52"}`
- Sealed ledger row: `{"agents": "live live_long_only price_only placebo_1 placebo_2 placebo_3 placebo_4 placebo_5 random_1 random_2 random_3 random_4 random_5 momentum reversal equal_weight live_frozen_2016 live_frozen_2017 live_frozen_2018 live_frozen_2019 live_frozen_2020 live_frozen_2021 live_frozen_2022 live_frozen_2023 live_frozen_2024 live_frozen_2025", "commit": "423a9c2a557fae5f5b428d29a6d15593798b0dd5", "dirty": "False", "first": "2016-01-04", "last": "2026-10-28", "logged_at": "2026-11-23T21:20:16", "out_dir": "D:\\chrono-data\\runs\\m4_sealed\\main", "run_id": "20261123T212016_755dcf39", "settings_hash": "755dcf398dcb34975ae84fa65518190d9504d591057ff80591b79f5ac74ee3a5", "status": "run", "trial": ""}`
- Sealed ledger row: `{"agents": "live_older_vintage", "commit": "423a9c2a557fae5f5b428d29a6d15593798b0dd5", "dirty": "False", "first": "2016-01-04", "last": "2026-10-28", "logged_at": "2026-11-23T22:05:12", "out_dir": "D:\\chrono-data\\runs\\m4_sealed\\older_vintage", "run_id": "20261123T220512_380ebc4f", "settings_hash": "380ebc4f7809de2f15b4f117d1a016514978a0ba0b2233a05dea656dbada0941", "status": "run", "trial": ""}`
- Main part complete: yes. Older-vintage part complete: yes.

## Outcome

**Failure: H2 or H3 does not hold.**

## The pre-registered tests (PREREG.md section 3)

One-sided, Newey-West with lag 6, on the sealed IC days. Holm over H1, H2 and H3 at a family level of 5%. H3's p is the larger of its two tests' p-values.

| test | days | mean | se | t | p |
|---|---|---|---|---|---|
| H1 | 1714 | 0.0104 | 0.0046 | 2.2735 | 0.0115 |
| H2 | 1714 | 0.0040 | 0.0050 | 0.8005 | 0.2117 |
| H3 vs price-only | 1714 | 0.0049 | 0.0058 | 0.8414 | 0.2001 |
| H3 vs placebo mean | 1714 | 0.0047 | 0.0040 | 1.1654 | 0.1219 |

| hypothesis | p | holds after Holm |
|---|---|---|
| H1 | 0.0115 | yes |
| H2 | 0.2117 | no |
| H3 | 0.2001 | no |

Robustness, not tested (t-statistics only):

| series | t lag 7 | t lag 21 | t monthly means |
|---|---|---|---|
| H1 | 2.2826 | 2.4244 | 2.2897 |
| H2 | 0.7993 | 0.8563 | 0.8264 |
| H3 vs price-only | 0.8530 | 0.9256 | 0.9046 |
| H3 vs placebo mean | 1.1735 | 1.2394 | 1.2184 |

## The switch-day check (PREREG section 5)

| year | first20_days | other_days | first20_mean | other_mean | difference | se | above_by_two_se |
|---|---|---|---|---|---|---|---|
| 2020 | 20 | 233 | -0.0306 | -0.0122 | -0.0184 | 0.0630 | no |
| 2021 | 20 | 232 | -0.0135 | 0.0014 | -0.0148 | 0.0362 | no |
| 2022 | 20 | 231 | 0.0308 | 0.0150 | 0.0158 | 0.0428 | no |
| 2023 | 20 | 230 | -0.0041 | 0.0009 | -0.0050 | 0.0498 | no |
| 2024 | 20 | 232 | 0.0984 | 0.0059 | 0.0925 | 0.0451 | yes |
| 2025 | 20 | 230 | 0.0508 | 0.0160 | 0.0348 | 0.0549 | no |

| difference | se | t | p | first20_days | other_days |
|---|---|---|---|---|---|
| 0.0175 | 0.0214 | 0.8168 | 0.2070 | 120 | 1388 |

Years counted: 6. (a): no. (b): no. **no warning**.

2026, shown apart and outside the rule:

| year | first20_days | other_days | first20_mean | other_mean | difference | se | above_by_two_se |
|---|---|---|---|---|---|---|---|
| 2026 | 20 | 186 | 0.0026 | -0.0029 | 0.0056 | 0.0339 | no |

## The older-vintage check (PREREG section 5)

| series | days | mean | t | p |
|---|---|---|---|---|
| news effect, the rule's vintage | 1714 | 0.0049 | 0.8530 |  |
| news effect, the older vintage | 1714 | 0.0059 | 1.0068 |  |
| live minus live_older_vintage | 1714 | -0.0010 | -0.3227 | 0.6265 |

Gate open (the rule's news effect has a mean above zero): yes. (a): no. (b): no. **no warning**.

Power note: the rule's news effect has a t below 1.645, so the check could not have seen a small leak.

## Deflated Sharpe (PREREG section 4)

| version | sr | sr_annual | skew | kurt | n | n_trials | var_trials | sr0 | dsr |
|---|---|---|---|---|---|---|---|---|---|
| after costs, after-cost trial variance (the result) | -0.0303 | -0.4803 | -0.5056 | 7.2120 | 1715 | 8.0000 | 0.0013 | 0.0523 | 0.0003 |
| after costs, before-cost trial variance (shown) | -0.0303 | -0.4803 | -0.5056 | 7.2120 | 1715 | 8.0000 | 0.0004 | 0.0290 | 0.0067 |
| before costs, before-cost trial variance (shown) | -0.0126 | -0.1994 | -0.5038 | 7.2286 | 1715 | 8.0000 | 0.0004 | 0.0290 | 0.0420 |

## The sealed years, described (not tested)
Sealed years 2020-01-02 to 2026-10-28, described only: nothing in this part is a test (PREREG.md section 3). Costs 5 bps per side unless a table says otherwise. Sharpe ratios are over zero, with no cash rate, borrow fee or short rebate. Every number below comes from `eval/report.py` over the runs named here.

## Trials

8 trials in `runs/trials.csv` (21 rows).

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
|  | run | 20261123T061536_0f452837 | 001d01cda33f2a12548c4c063b9f571d1ab2d35d | True | 0f4528375f0f9676deda8eed9a8f0aa89526f2f93b031650bfcc07f50821e7e8 | live_older_vintage |
|  | run | 20261123T105249_c7780628 | 6401ee7375372d68dfb02c14e0658bbc5d611e54 | True | c7780628deb8afd69726535c05afe102a26d2ac8bb02dbac3a5156517a52a8b2 | live |

## Daily rank IC by quarter (live)

| quarter | days | mean | se | t |
|---|---|---|---|---|
| 2020Q1 | 62 | 0.0325 | 0.0215 | 1.5139 |
| 2020Q2 | 63 | -0.0064 | 0.0249 | -0.2564 |
| 2020Q3 | 64 | 0.0810 | 0.0228 | 3.5453 |
| 2020Q4 | 64 | 0.0226 | 0.0302 | 0.7474 |
| 2021Q1 | 61 | 0.0135 | 0.0256 | 0.5270 |
| 2021Q2 | 63 | 0.0125 | 0.0258 | 0.4839 |
| 2021Q3 | 64 | 0.0138 | 0.0247 | 0.5598 |
| 2021Q4 | 64 | -0.0140 | 0.0180 | -0.7745 |
| 2022Q1 | 62 | -0.0061 | 0.0303 | -0.2001 |
| 2022Q2 | 62 | 0.0142 | 0.0188 | 0.7576 |
| 2022Q3 | 64 | 0.0417 | 0.0223 | 1.8684 |
| 2022Q4 | 63 | -0.0104 | 0.0271 | -0.3831 |
| 2023Q1 | 62 | -0.0414 | 0.0212 | -1.9583 |
| 2023Q2 | 62 | 0.0209 | 0.0169 | 1.2380 |
| 2023Q3 | 63 | 0.0169 | 0.0256 | 0.6576 |
| 2023Q4 | 63 | 0.0049 | 0.0225 | 0.2172 |
| 2024Q1 | 61 | -0.0014 | 0.0211 | -0.0641 |
| 2024Q2 | 63 | 0.0388 | 0.0217 | 1.7896 |
| 2024Q3 | 64 | -0.0064 | 0.0272 | -0.2351 |
| 2024Q4 | 64 | 0.0052 | 0.0194 | 0.2694 |
| 2025Q1 | 60 | 0.0050 | 0.0208 | 0.2382 |
| 2025Q2 | 62 | -0.0135 | 0.0234 | -0.5758 |
| 2025Q3 | 64 | 0.0219 | 0.0220 | 0.9946 |
| 2025Q4 | 64 | -0.0048 | 0.0212 | -0.2248 |
| 2026Q1 | 61 | 0.0262 | 0.0248 | 1.0563 |
| 2026Q2 | 62 | 0.0131 | 0.0215 | 0.6088 |
| 2026Q3 | 64 | 0.0194 | 0.0249 | 0.7798 |
| 2026Q4 | 19 | -0.0577 | 0.0506 | -1.1415 |
| all | 1714 | 0.0104 | 0.0046 | 2.2826 |

## Frozen-twin gaps (live minus twin, paired daily IC)

| twin | year | days | mean | se | t |
|---|---|---|---|---|---|
| end of 2016 | 2017 | 251 | 0.0172 | 0.0122 | 1.4095 |
| end of 2016 | 2018 | 251 | 0.0292 | 0.0123 | 2.3735 |
| end of 2016 | 2019 | 252 | 0.0063 | 0.0104 | 0.6042 |
| end of 2016 | 2020 | 253 | 0.0401 | 0.0155 | 2.5775 |
| end of 2016 | 2021 | 252 | 0.0009 | 0.0157 | 0.0601 |
| end of 2016 | 2022 | 251 | 0.0129 | 0.0175 | 0.7384 |
| end of 2016 | 2023 | 250 | -0.0027 | 0.0169 | -0.1622 |
| end of 2016 | 2024 | 252 | 0.0048 | 0.0142 | 0.3361 |
| end of 2016 | 2025 | 250 | -0.0026 | 0.0140 | -0.1847 |
| end of 2016 | 2026 | 206 | 0.0123 | 0.0171 | 0.7170 |
| end of 2016 | all | 2468 | 0.0119 | 0.0047 | 2.5451 |
| end of 2017 | 2018 | 251 | 0.0092 | 0.0103 | 0.8894 |
| end of 2017 | 2019 | 252 | 0.0029 | 0.0096 | 0.2992 |
| end of 2017 | 2020 | 253 | 0.0136 | 0.0151 | 0.9006 |
| end of 2017 | 2021 | 252 | -0.0034 | 0.0132 | -0.2575 |
| end of 2017 | 2022 | 251 | 0.0115 | 0.0172 | 0.6665 |
| end of 2017 | 2023 | 250 | 0.0051 | 0.0136 | 0.3785 |
| end of 2017 | 2024 | 252 | -0.0147 | 0.0124 | -1.1846 |
| end of 2017 | 2025 | 250 | -0.0130 | 0.0132 | -0.9889 |
| end of 2017 | 2026 | 206 | 0.0232 | 0.0197 | 1.1741 |
| end of 2017 | all | 2217 | 0.0034 | 0.0046 | 0.7353 |
| end of 2018 | 2019 | 252 | -0.0149 | 0.0085 | -1.7597 |
| end of 2018 | 2020 | 253 | 0.0176 | 0.0108 | 1.6304 |
| end of 2018 | 2021 | 252 | -0.0020 | 0.0112 | -0.1800 |
| end of 2018 | 2022 | 251 | -0.0038 | 0.0126 | -0.3011 |
| end of 2018 | 2023 | 250 | 0.0162 | 0.0136 | 1.1943 |
| end of 2018 | 2024 | 252 | 0.0031 | 0.0144 | 0.2159 |
| end of 2018 | 2025 | 250 | -0.0032 | 0.0147 | -0.2152 |
| end of 2018 | 2026 | 206 | 0.0113 | 0.0167 | 0.6722 |
| end of 2018 | all | 1966 | 0.0029 | 0.0046 | 0.6239 |
| end of 2019 | 2020 | 253 | 0.0127 | 0.0106 | 1.1893 |
| end of 2019 | 2021 | 252 | -0.0065 | 0.0101 | -0.6381 |
| end of 2019 | 2022 | 251 | -0.0048 | 0.0124 | -0.3830 |
| end of 2019 | 2023 | 250 | 0.0231 | 0.0141 | 1.6347 |
| end of 2019 | 2024 | 252 | 0.0048 | 0.0144 | 0.3308 |
| end of 2019 | 2025 | 250 | -0.0025 | 0.0149 | -0.1649 |
| end of 2019 | 2026 | 206 | 0.0007 | 0.0154 | 0.0474 |
| end of 2019 | all | 1714 | 0.0040 | 0.0050 | 0.7993 |
| end of 2020 | 2021 | 252 | 0.0005 | 0.0104 | 0.0498 |
| end of 2020 | 2022 | 251 | 0.0362 | 0.0199 | 1.8165 |
| end of 2020 | 2023 | 250 | -0.0009 | 0.0099 | -0.0885 |
| end of 2020 | 2024 | 252 | -0.0169 | 0.0100 | -1.6991 |
| end of 2020 | 2025 | 250 | -0.0025 | 0.0107 | -0.2312 |
| end of 2020 | 2026 | 206 | 0.0233 | 0.0190 | 1.2288 |
| end of 2020 | all | 1461 | 0.0061 | 0.0056 | 1.0969 |
| end of 2021 | 2022 | 251 | 0.0179 | 0.0174 | 1.0282 |
| end of 2021 | 2023 | 250 | 0.0145 | 0.0110 | 1.3121 |
| end of 2021 | 2024 | 252 | -0.0083 | 0.0106 | -0.7797 |
| end of 2021 | 2025 | 250 | 0.0077 | 0.0109 | 0.7095 |
| end of 2021 | 2026 | 206 | 0.0051 | 0.0148 | 0.3434 |
| end of 2021 | all | 1209 | 0.0074 | 0.0059 | 1.2708 |
| end of 2022 | 2023 | 250 | 0.0279 | 0.0132 | 2.1119 |
| end of 2022 | 2024 | 252 | 0.0083 | 0.0126 | 0.6608 |
| end of 2022 | 2025 | 250 | 0.0032 | 0.0125 | 0.2538 |
| end of 2022 | 2026 | 206 | 0.0145 | 0.0163 | 0.8911 |
| end of 2022 | all | 958 | 0.0134 | 0.0066 | 2.0191 |
| end of 2023 | 2024 | 252 | 0.0071 | 0.0072 | 0.9888 |
| end of 2023 | 2025 | 250 | 0.0075 | 0.0118 | 0.6413 |
| end of 2023 | 2026 | 206 | 0.0207 | 0.0172 | 1.2036 |
| end of 2023 | all | 708 | 0.0112 | 0.0069 | 1.6222 |
| end of 2024 | 2025 | 250 | 0.0036 | 0.0082 | 0.4354 |
| end of 2024 | 2026 | 206 | 0.0126 | 0.0171 | 0.7345 |
| end of 2024 | all | 456 | 0.0076 | 0.0089 | 0.8521 |
| end of 2025 | 2026 | 206 | -0.0125 | 0.0122 | -1.0293 |
| end of 2025 | all | 206 | -0.0125 | 0.0122 | -1.0293 |

## Matched baselines

Long-short, against cash (zero) and the long-short baselines:

| book | annual_return | annual_vol | sharpe_after_costs | sharpe_before_costs | annual_return_before_costs | max_drawdown | daily_turnover | days | mean_ic |
|---|---|---|---|---|---|---|---|---|---|
| live | -0.1112 | 0.2025 | -0.4803 | -0.1994 | -0.0592 | -0.6244 | 0.4513 | 1715 | 0.0104 |
| momentum | -0.0218 | 0.3124 | 0.0864 | 0.1460 | -0.0034 | -0.6449 | 0.1478 | 1715 | 0.0202 |
| reversal | -0.1330 | 0.2843 | -0.3599 | -0.0689 | -0.0581 | -0.6781 | 0.6565 | 1715 | 0.0060 |
| random_1 | -0.1358 | 0.1419 | -0.9566 | -0.3626 | -0.0593 | -0.6631 | 0.6721 | 1715 | 0.0040 |
| random_2 | -0.0989 | 0.1386 | -0.6819 | -0.0730 | -0.0195 | -0.6055 | 0.6693 | 1715 | 0.0015 |
| random_3 | 0.0222 | 0.1403 | 0.2268 | 0.8286 | 0.1120 | -0.2680 | 0.6680 | 1715 | 0.0040 |
| random_4 | -0.0768 | 0.1420 | -0.4918 | 0.1027 | 0.0045 | -0.4591 | 0.6694 | 1715 | 0.0020 |
| random_5 | -0.1054 | 0.1479 | -0.6791 | -0.1107 | -0.0268 | -0.6227 | 0.6679 | 1715 | 0.0059 |
| cash | 0.0000 | 0.0000 |  |  | 0.0000 | 0.0000 | 0.0000 | 0 |  |

Long-only, against SPY buy-and-hold and all picks equally:

| book | annual_return | annual_vol | sharpe_after_costs | sharpe_before_costs | annual_return_before_costs | max_drawdown | daily_turnover | days |
|---|---|---|---|---|---|---|---|---|
| live_long_only | 0.1267 | 0.2522 | 0.5996 | 0.7090 | 0.1582 | -0.3808 | 0.2190 | 1715 |
| equal_weight | 0.1782 | 0.2106 | 0.8846 | 0.8933 | 0.1804 | -0.3187 | 0.0145 | 1715 |
| spy_buy_and_hold | 0.1523 | 0.1905 | 0.8397 |  |  | -0.3205 |  | 1714 |

## Costs (bps per side)

live:

| cost | annual_return | annual_vol | sharpe | max_drawdown | total |
|---|---|---|---|---|---|
| 0 bps | -0.0592 | 0.2025 | -0.1994 | -0.5151 | -0.3396 |
| 5 bps | -0.1112 | 0.2025 | -0.4803 | -0.6244 | -0.5518 |
| 10 bps | -0.1605 | 0.2028 | -0.7602 | -0.7336 | -0.6959 |
| 20 bps | -0.2511 | 0.2041 | -1.3137 | -0.8674 | -0.8603 |

live_long_only:

| cost | annual_return | annual_vol | sharpe | max_drawdown | total |
|---|---|---|---|---|---|
| 0 bps | 0.1582 | 0.2522 | 0.7090 | -0.3689 | 1.7163 |
| 5 bps | 0.1267 | 0.2522 | 0.5996 | -0.3808 | 1.2514 |
| 10 bps | 0.0960 | 0.2523 | 0.4901 | -0.3927 | 0.8659 |
| 20 bps | 0.0371 | 0.2525 | 0.2711 | -0.4171 | 0.2811 |


## Exposures

Market beta against SPY's open-to-open returns (Newey-West):

| book | beta | se | t | alpha_daily | days |
|---|---|---|---|---|---|
| live | 0.0872 | 0.0448 | 1.9464 | -0.0004 | 1715 |
| live_long_only | 1.1369 | 0.0283 | 40.2183 | -0.0001 | 1715 |

Sector tilt of live's targets (net weight; sectors are Wikipedia's list as of each date, see `research/audit/benchmarks.md`):

| sector | mean_net | mean_abs_net |
|---|---|---|
| Communication Services | 0.0046 | 0.1246 |
| Consumer Discretionary | -0.0288 | 0.0991 |
| Consumer Staples | -0.0626 | 0.1028 |
| Energy | -0.0222 | 0.0781 |
| Financials | 0.0059 | 0.1234 |
| Health Care | -0.0157 | 0.1236 |
| Industrials | 0.0047 | 0.0864 |
| Information Technology | 0.1148 | 0.2318 |
| all | 0.0007 | 0.9699 |

Sector tilt of live_long_only's targets (net weight; sectors are Wikipedia's list as of each date, see `research/audit/benchmarks.md`):

| sector | mean_net | mean_abs_net |
|---|---|---|
| Communication Services | 0.1280 | 0.1280 |
| Consumer Discretionary | 0.0832 | 0.0832 |
| Consumer Staples | 0.0510 | 0.0510 |
| Energy | 0.0350 | 0.0350 |
| Financials | 0.1319 | 0.1319 |
| Health Care | 0.1125 | 0.1125 |
| Industrials | 0.0583 | 0.0583 |
| Information Technology | 0.3996 | 0.3996 |
| all | 0.9995 | 0.9995 |


## Seed spread

placebo:

| seed | mean_ic | t | sharpe_after_costs |
|---|---|---|---|
| 1 | 0.0041 | 1.0413 | -0.5560 |
| 2 | 0.0038 | 1.0512 | -0.5356 |
| 3 | 0.0079 | 2.0762 | -0.2002 |
| 4 | 0.0071 | 1.7036 | -0.3159 |
| 5 | 0.0058 | 1.5479 | -0.9244 |
| min | 0.0038 | 1.0413 | -0.9244 |
| max | 0.0079 | 2.0762 | -0.2002 |
| mean | 0.0057 | 1.4841 | -0.5064 |
| std | 0.0018 | 0.4434 | 0.2775 |

random:

| seed | mean_ic | t | sharpe_after_costs |
|---|---|---|---|
| 1 | 0.0040 | 1.1656 | -0.9566 |
| 2 | 0.0015 | 0.4486 | -0.6819 |
| 3 | 0.0040 | 1.1502 | 0.2268 |
| 4 | 0.0020 | 0.6240 | -0.4918 |
| 5 | 0.0059 | 1.6987 | -0.6791 |
| min | 0.0015 | 0.4486 | -0.9566 |
| max | 0.0059 | 1.6987 | 0.2268 |
| mean | 0.0035 | 1.0174 | -0.5165 |
| std | 0.0018 | 0.4955 | 0.4474 |


## Regimes and shocks (reported, not tested)

| regime | value | ic_days | mean_ic | t | book_days | sharpe |
|---|---|---|---|---|---|---|
| trend | down | 333 | 0.0129 | 1.3073 | 333 | -0.2052 |
| trend | up | 1381 | 0.0098 | 1.9420 | 1382 | -0.5441 |
| vol | high | 1111 | 0.0132 | 2.2752 | 1111 | -0.3252 |
| vol | low | 603 | 0.0053 | 0.6877 | 604 | -0.8002 |
| shock | after shock | 60 | 0.0101 | 0.5221 | 60 | 1.0062 |
| shock | none | 1654 | 0.0104 | 2.2297 | 1655 | -0.5580 |

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
| end of 2016 | 12 | 64 | -0.0202 | -1.5269 |
| end of 2016 | 13 | 62 | -0.0139 | -0.7454 |
| end of 2016 | 14 | 63 | 0.0047 | 0.1992 |
| end of 2016 | 15 | 64 | -0.0258 | -1.2401 |
| end of 2016 | 16 | 64 | 0.0051 | 0.3151 |
| end of 2016 | 17 | 61 | 0.0066 | 0.3249 |
| end of 2016 | 18 | 63 | 0.0025 | 0.1312 |
| end of 2016 | 19 | 64 | 0.0472 | 1.7689 |
| end of 2016 | 20 | 64 | -0.0347 | -2.1383 |
| end of 2016 | 21 | 62 | 0.0016 | 0.0576 |
| end of 2016 | 22 | 62 | -0.0308 | -1.5766 |
| end of 2016 | 23 | 64 | 0.0321 | 1.8074 |
| end of 2016 | 24 | 63 | -0.0153 | -0.7008 |
| end of 2016 | 25 | 62 | -0.0215 | -0.8729 |
| end of 2016 | 26 | 62 | 0.0106 | 0.5354 |
| end of 2016 | 27 | 63 | 0.0145 | 0.9151 |
| end of 2016 | 28 | 63 | 0.0086 | 0.3415 |
| end of 2016 | 29 | 61 | -0.0135 | -0.6683 |
| end of 2016 | 30 | 63 | -0.0071 | -0.3461 |
| end of 2016 | 31 | 64 | 0.0114 | 0.5594 |
| end of 2016 | 32 | 64 | 0.0254 | 1.7241 |
| end of 2016 | 33 | 60 | -0.0068 | -0.2503 |
| end of 2016 | 34 | 62 | -0.0168 | -1.1626 |
| end of 2016 | 35 | 64 | 0.0049 | 0.2123 |
| end of 2016 | 36 | 64 | 0.0366 | 2.0885 |
| end of 2016 | 37 | 61 | 0.0009 | 0.0486 |
| end of 2016 | 38 | 62 | -0.0292 | -1.4699 |
| end of 2016 | 39 | 64 | 0.0234 | 1.3967 |
| end of 2016 | 40 | 19 | 0.0149 | 0.4232 |
| end of 2017 | 1 | 61 | 0.0184 | 0.9692 |
| end of 2017 | 2 | 64 | 0.0065 | 0.3246 |
| end of 2017 | 3 | 63 | 0.0031 | 0.1855 |
| end of 2017 | 4 | 63 | -0.0070 | -0.4556 |
| end of 2017 | 5 | 61 | 0.0053 | 0.2519 |
| end of 2017 | 6 | 63 | 0.0142 | 0.6780 |
| end of 2017 | 7 | 64 | 0.0009 | 0.0614 |
| end of 2017 | 8 | 64 | -0.0133 | -0.8464 |
| end of 2017 | 9 | 62 | -0.0171 | -0.9342 |
| end of 2017 | 10 | 63 | 0.0351 | 1.5936 |
| end of 2017 | 11 | 64 | 0.0123 | 0.8161 |
| end of 2017 | 12 | 64 | 0.0448 | 2.6349 |
| end of 2017 | 13 | 61 | 0.0530 | 3.3893 |
| end of 2017 | 14 | 63 | 0.0132 | 0.5684 |
| end of 2017 | 15 | 64 | 0.0098 | 0.4613 |
| end of 2017 | 16 | 64 | -0.0349 | -1.7631 |
| end of 2017 | 17 | 62 | -0.0049 | -0.2220 |
| end of 2017 | 18 | 62 | 0.0079 | 0.2988 |
| end of 2017 | 19 | 64 | 0.0175 | 1.0960 |
| end of 2017 | 20 | 63 | -0.0265 | -1.5454 |
| end of 2017 | 21 | 62 | -0.0490 | -2.6566 |
| end of 2017 | 22 | 62 | 0.0144 | 0.8320 |
| end of 2017 | 23 | 63 | -0.0130 | -0.6758 |
| end of 2017 | 24 | 63 | 0.0281 | 1.1638 |
| end of 2017 | 25 | 61 | 0.0194 | 1.0549 |
| end of 2017 | 26 | 63 | -0.0093 | -0.5322 |
| end of 2017 | 27 | 64 | 0.0417 | 2.1275 |
| end of 2017 | 28 | 64 | 0.0427 | 2.4746 |
| end of 2017 | 29 | 60 | 0.0251 | 0.9289 |
| end of 2017 | 30 | 62 | 0.0066 | 0.3333 |
| end of 2017 | 31 | 64 | 0.0124 | 0.5789 |
| end of 2017 | 32 | 64 | 0.0173 | 0.9960 |
| end of 2017 | 33 | 61 | -0.0103 | -0.4198 |
| end of 2017 | 34 | 62 | -0.0245 | -0.9746 |
| end of 2017 | 35 | 64 | 0.0069 | 0.3701 |
| end of 2017 | 36 | 19 | -0.0265 | -0.7249 |
| end of 2018 | 1 | 61 | 0.0154 | 0.9049 |
| end of 2018 | 2 | 63 | 0.0105 | 0.5759 |
| end of 2018 | 3 | 64 | 0.0256 | 1.4511 |
| end of 2018 | 4 | 64 | 0.0261 | 1.6453 |
| end of 2018 | 5 | 62 | 0.0162 | 0.8158 |
| end of 2018 | 6 | 63 | 0.0060 | 0.2887 |
| end of 2018 | 7 | 64 | 0.0096 | 0.5507 |
| end of 2018 | 8 | 64 | 0.0279 | 1.4064 |
| end of 2018 | 9 | 61 | 0.0449 | 2.7337 |
| end of 2018 | 10 | 63 | 0.0151 | 0.6480 |
| end of 2018 | 11 | 64 | 0.0093 | 0.4574 |
| end of 2018 | 12 | 64 | -0.0340 | -1.6085 |
| end of 2018 | 13 | 62 | 0.0153 | 0.6662 |
| end of 2018 | 14 | 62 | 0.0121 | 0.6942 |
| end of 2018 | 15 | 64 | 0.0276 | 1.9303 |
| end of 2018 | 16 | 63 | 0.0001 | 0.0087 |
| end of 2018 | 17 | 62 | -0.0524 | -2.7991 |
| end of 2018 | 18 | 62 | 0.0016 | 0.0892 |
| end of 2018 | 19 | 63 | -0.0022 | -0.1305 |
| end of 2018 | 20 | 63 | -0.0106 | -0.7544 |
| end of 2018 | 21 | 61 | -0.0206 | -1.6811 |
| end of 2018 | 22 | 63 | 0.0013 | 0.0749 |
| end of 2018 | 23 | 64 | 0.0145 | 0.6811 |
| end of 2018 | 24 | 64 | 0.0273 | 1.3169 |
| end of 2018 | 25 | 60 | 0.0290 | 1.8509 |
| end of 2018 | 26 | 62 | -0.0250 | -1.1894 |
| end of 2018 | 27 | 64 | 0.0174 | 0.7370 |
| end of 2018 | 28 | 64 | 0.0006 | 0.0262 |
| end of 2018 | 29 | 61 | -0.0105 | -0.5629 |
| end of 2018 | 30 | 62 | 0.0155 | 0.6862 |
| end of 2018 | 31 | 64 | 0.0104 | 0.4933 |
| end of 2018 | 32 | 19 | -0.0393 | -1.4892 |
| end of 2019 | 1 | 62 | 0.0097 | 0.4183 |
| end of 2019 | 2 | 63 | -0.0002 | -0.0084 |
| end of 2019 | 3 | 64 | 0.0383 | 2.5224 |
| end of 2019 | 4 | 64 | 0.0313 | 1.7295 |
| end of 2019 | 5 | 61 | 0.0395 | 2.2042 |
| end of 2019 | 6 | 63 | 0.0318 | 1.6495 |
| end of 2019 | 7 | 64 | 0.0015 | 0.0741 |
| end of 2019 | 8 | 64 | -0.0200 | -0.8158 |
| end of 2019 | 9 | 62 | 0.0242 | 1.0786 |
| end of 2019 | 10 | 62 | 0.0100 | 0.4852 |
| end of 2019 | 11 | 64 | 0.0173 | 1.1423 |
| end of 2019 | 12 | 63 | 0.0077 | 0.3983 |
| end of 2019 | 13 | 62 | -0.0565 | -2.6476 |
| end of 2019 | 14 | 62 | -0.0256 | -1.5152 |
| end of 2019 | 15 | 63 | 0.0010 | 0.0523 |
| end of 2019 | 16 | 63 | -0.0103 | -0.6400 |
| end of 2019 | 17 | 61 | -0.0028 | -0.1695 |
| end of 2019 | 18 | 63 | 0.0047 | 0.2125 |
| end of 2019 | 19 | 64 | 0.0056 | 0.3111 |
| end of 2019 | 20 | 64 | 0.0094 | 0.4239 |
| end of 2019 | 21 | 60 | 0.0146 | 0.9806 |
| end of 2019 | 22 | 62 | -0.0060 | -0.2819 |
| end of 2019 | 23 | 64 | 0.0200 | 0.7953 |
| end of 2019 | 24 | 64 | -0.0096 | -0.4853 |
| end of 2019 | 25 | 61 | 0.0076 | 0.3508 |
| end of 2019 | 26 | 62 | 0.0179 | 0.8944 |
| end of 2019 | 27 | 64 | 0.0191 | 0.9861 |
| end of 2019 | 28 | 19 | -0.0203 | -0.5923 |
| end of 2020 | 1 | 61 | -0.0144 | -0.4815 |
| end of 2020 | 2 | 63 | 0.0247 | 0.9800 |
| end of 2020 | 3 | 64 | 0.0126 | 0.5313 |
| end of 2020 | 4 | 64 | -0.0002 | -0.0099 |
| end of 2020 | 5 | 62 | -0.0091 | -0.3004 |
| end of 2020 | 6 | 62 | -0.0604 | -1.9544 |
| end of 2020 | 7 | 64 | -0.0069 | -0.2219 |
| end of 2020 | 8 | 63 | -0.0287 | -0.9997 |
| end of 2020 | 9 | 62 | -0.0358 | -1.9049 |
| end of 2020 | 10 | 62 | 0.0315 | 2.0125 |
| end of 2020 | 11 | 63 | 0.0005 | 0.0214 |
| end of 2020 | 12 | 63 | 0.0088 | 0.3680 |
| end of 2020 | 13 | 61 | 0.0404 | 1.7914 |
| end of 2020 | 14 | 63 | 0.0267 | 1.1905 |
| end of 2020 | 15 | 64 | 0.0204 | 0.7994 |
| end of 2020 | 16 | 64 | 0.0171 | 0.9126 |
| end of 2020 | 17 | 60 | -0.0088 | -0.4397 |
| end of 2020 | 18 | 62 | 0.0233 | 0.9038 |
| end of 2020 | 19 | 64 | -0.0030 | -0.1859 |
| end of 2020 | 20 | 64 | 0.0072 | 0.4043 |
| end of 2020 | 21 | 61 | -0.0115 | -0.3803 |
| end of 2020 | 22 | 62 | -0.0226 | -0.8410 |
| end of 2020 | 23 | 64 | 0.0089 | 0.4295 |
| end of 2020 | 24 | 19 | -0.0374 | -1.3517 |
| end of 2021 | 1 | 62 | 0.0171 | 0.4851 |
| end of 2021 | 2 | 62 | -0.0437 | -1.4150 |
| end of 2021 | 3 | 64 | 0.0189 | 0.6964 |
| end of 2021 | 4 | 63 | -0.0244 | -0.9080 |
| end of 2021 | 5 | 62 | -0.0353 | -2.0033 |
| end of 2021 | 6 | 62 | -0.0218 | -1.1244 |
| end of 2021 | 7 | 63 | -0.0015 | -0.0704 |
| end of 2021 | 8 | 63 | 0.0018 | 0.1097 |
| end of 2021 | 9 | 61 | 0.0404 | 2.0060 |
| end of 2021 | 10 | 63 | 0.0116 | 0.5024 |
| end of 2021 | 11 | 64 | 0.0088 | 0.4724 |
| end of 2021 | 12 | 64 | 0.0095 | 0.4977 |
| end of 2021 | 13 | 60 | -0.0189 | -0.8462 |
| end of 2021 | 14 | 62 | -0.0043 | -0.1975 |
| end of 2021 | 15 | 64 | -0.0009 | -0.0471 |
| end of 2021 | 16 | 64 | 0.0013 | 0.0552 |
| end of 2021 | 17 | 61 | 0.0212 | 0.7334 |
| end of 2021 | 18 | 62 | -0.0049 | -0.2064 |
| end of 2021 | 19 | 64 | 0.0221 | 1.0710 |
| end of 2021 | 20 | 19 | -0.0471 | -2.7049 |
| end of 2022 | 1 | 62 | -0.0503 | -2.6506 |
| end of 2022 | 2 | 62 | -0.0245 | -1.3491 |
| end of 2022 | 3 | 63 | 0.0045 | 0.1734 |
| end of 2022 | 4 | 63 | -0.0398 | -2.2636 |
| end of 2022 | 5 | 61 | 0.0057 | 0.2193 |
| end of 2022 | 6 | 63 | 0.0203 | 1.1639 |
| end of 2022 | 7 | 64 | -0.0214 | -1.1595 |
| end of 2022 | 8 | 64 | -0.0011 | -0.0746 |
| end of 2022 | 9 | 60 | 0.0031 | 0.1453 |
| end of 2022 | 10 | 62 | -0.0377 | -1.9886 |
| end of 2022 | 11 | 64 | -0.0025 | -0.1415 |
| end of 2022 | 12 | 64 | 0.0325 | 1.3752 |
| end of 2022 | 13 | 61 | 0.0067 | 0.3484 |
| end of 2022 | 14 | 62 | -0.0252 | -1.0695 |
| end of 2022 | 15 | 64 | 0.0189 | 0.9784 |
| end of 2022 | 16 | 19 | -0.0257 | -1.0754 |
| end of 2023 | 1 | 61 | -0.0063 | -0.2952 |
| end of 2023 | 2 | 63 | 0.0283 | 1.4758 |
| end of 2023 | 3 | 64 | -0.0071 | -0.3466 |
| end of 2023 | 4 | 64 | -0.0069 | -0.3826 |
| end of 2023 | 5 | 60 | 0.0021 | 0.0897 |
| end of 2023 | 6 | 62 | -0.0321 | -1.3401 |
| end of 2023 | 7 | 64 | -0.0106 | -0.4587 |
| end of 2023 | 8 | 64 | 0.0191 | 0.8411 |
| end of 2023 | 9 | 61 | 0.0093 | 0.4641 |
| end of 2023 | 10 | 62 | -0.0450 | -2.2132 |
| end of 2023 | 11 | 64 | 0.0210 | 1.1996 |
| end of 2023 | 12 | 19 | -0.0431 | -1.6694 |
| end of 2024 | 1 | 60 | 0.0078 | 0.4010 |
| end of 2024 | 2 | 62 | -0.0087 | -0.3361 |
| end of 2024 | 3 | 64 | 0.0002 | 0.0102 |
| end of 2024 | 4 | 64 | -0.0042 | -0.2800 |
| end of 2024 | 5 | 61 | 0.0197 | 0.8147 |
| end of 2024 | 6 | 62 | -0.0433 | -2.2286 |
| end of 2024 | 7 | 64 | 0.0309 | 1.5086 |
| end of 2024 | 8 | 19 | -0.0275 | -0.9229 |
| end of 2025 | 1 | 61 | 0.0418 | 1.7052 |
| end of 2025 | 2 | 62 | 0.0015 | 0.0677 |
| end of 2025 | 3 | 64 | 0.0515 | 2.6291 |
| end of 2025 | 4 | 19 | -0.0421 | -1.6034 |

## Note added on 24 Nov 2026, after the M4 review

This note is added below the report, as PREREG section 7 allows. Everything above it is the writer's output, unedited.
It changes no number and no outcome. The outcome stays **Failure**. The review is
`research/review_m4_2026-11-24.md`, and the owner took its six recommendations on 24 Nov ("Yes, take all six").

- **The leak-test gate was skipped before the run (review G4-1).** PREREG section 6 says the full suite, with
  `CHRONO_SLOW_LEAKS=1`, passes on the clean tree at the code-plus-PREREG commit (`8c683f5`) before `seal.lock` is
  written, and again at the lock's commit (`423a9c2`) before the sealed run starts. Neither run happened. The lock was
  written 12 seconds after `8c683f5`, and the main part started 1 minute 54 seconds after `423a9c2` (New York, 23 Nov:
  12:30:59, 12:31:11, 12:31:26 and 12:33:20). The suite takes 35 to 52 minutes. Every suite run on record before the
  seal skipped the slow leak test. The gate was run afterwards, on 24 Nov, on a clean checkout of `423a9c2`, whose code
  equals `8c683f5`'s: `CHRONO_SLOW_LEAKS=1 python -m pytest tests -q -p no:cacheprovider` printed "535 passed, 9 warnings in 2850.85s (0:47:30)", pytest exit code 0, with nothing skipped (04:35 to 05:23 New York, 24 Nov; the tree was clean before and after). A leak could only raise a result, so the gate cannot turn this Failure into
  another outcome.
- **The dev check's commit (review G4-2).** The rerun of T09 on the dev years ran at `6401ee7` on a tree with
  uncommitted changes, not at `7b9a138` as PREREG section 1 names. The code the run uses is the same in both, and the
  sealed live agent's decisions to 2019-12-31 equal M3's T09 run on all 817 days.
- **Known limits (review R4-1, R4-4).** PREREG section 6 says the report states these:
  - Only the 2016 ChronoBERT vintage has evidence for its training cutoff; the other vintages that read news were too
    weak to judge, and the 2026 vintage was never checked (`research/audit/cutoff.md`, section 9). The owner accepted
    all 11 vintages as published. This is the context for both leak checks' "no warning".
  - The sectors come from 142 monthly revisions of Wikipedia's S&P 500 list, 2014-12-29 to 2026-09-25, as of each
    date (`research/audit/benchmarks.md`). PREREG calls them "a present-day list"; that wording is wrong. They are
    close to point in time, not exact: Wikipedia's dates lag S&P's changes, and 5 of the 746 companies have no sector.
  - The store's data ends on 2026-10-28, the last sealed session.
  - Two of PLAN's known limits that PREREG did not carry: ModernBERT's tokenizer vocabulary is from 2024, and
    ChronoBERT's design was chosen in 2025 (review R4-9).
- **The baselines are compared before costs (review R4-2).** PREREG section 4 compares the baselines with live
  **before costs**, and marks the after-cost rows as not turnover-matched, since only live has the band. The section
  above is headed "Matched baselines" and leads with the after-cost Sharpe, unmarked. Its after-cost rows are **not
  turnover-matched**: live turns over 0.4513 of equity a day, the random seeds and reversal 0.66 to 0.67. Before
  costs, the comparison PREREG names, live is 7th of the 8 long-short books (live, momentum, reversal and 5 random
  seeds), with a Sharpe of -0.1994 against momentum's 0.1460. After costs it would read 4th of 8.
- **Sessions scored by neither run (review R4-3).** The sessions from 2026-10-29 to the forward test's first day are
  scored by neither the sealed run nor the forward test, as PREREG section 1 says.
- **Dev years in two descriptive tables (review R4-5).** The frozen-twin gaps and the coefficient life for the
  end-of-2016, 2017 and 2018 twins include dev-year days and quarters, though the line above them says the sealed years
  only. No test uses them: H2's twin, the end-of-2019 one, has sealed days only (1,714).
