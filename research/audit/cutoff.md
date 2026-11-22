# The cutoff check (M2 step 2)

Does each ChronoBERT vintage stop learning at its cutoff? The method is `research/m2_kickoff.md` section 5, built as
`reader/cutoff.py`. This file holds counts, losses, intervals and probe ids only: no headline text and no prices.
Every number here comes from a command named next to it. The outputs are in `D:\chrono-data\reader\cutoff`.

**What decides.** On 21 Nov 2026 the owner chose to settle each vintage's cutoff on stronger probes ("Stronger
probes"). Sections 1 to 7 (the masked-word loss check, the first 22 probes and the redesign sizing) stay as the
record, unchanged. They do not decide any vintage's cutoff. Section 8 holds the rules that decide, written and
frozen before any score of the new probes, and its results.

## 1. The rules, fixed before any result (21 Nov 2026, 07:00 New York)

Written before the pilot and before any loss was computed. At that time `reader/cutoff.py` had SHA-256
`4fc3a4cf8f064160e085c109f1b97c5387be5cbe965c507f06915afcd7212e29` and `reader/probes.csv` had SHA-256
`7c3d31611a6c5964c4cb7ac55aaa1469ef231bbc4b50a310bcdc3189b4ab2c65` (22 probes, frozen from here on).

**The sample.** For each New York year from 2015 to 2026, the stories in `story_entities` whose headline has at
least one token besides [CLS] and [SEP], in `story_id` order, then put in a random order seeded by (20151231, year).
The run uses the first N of each year. Each headline's masks are 15% of its inner tokens, rounded half up, at least
one, at positions drawn from a generator seeded by (15, story_id). Every vintage sees the same headlines and masks.

**The measure.** L(v, y) is vintage v's mean over year y's headlines of each headline's mean cross-entropy on its
masked tokens. G(v, y) = L(v-1, y) - L(v, y). There are 41 cells: years V-1 to V+2 for each vintage 2014 to 2024,
inside 2015 to 2026.

**The checks**, for each vintage V that reads news:
- Check A, for V from 2015 to 2023: G(V+1, V+1) - G(V+1, V). Its power gate is G(V+1, V+1).
- Check B, for V from 2015 to 2024: G(V, V) - G(V, V+1). Its power gate is G(V, V), V's gain on its own year.
- Every gain and check gets a 95% percentile interval from 10,000 bootstrap resamples of the headlines. Each year
  has one set of resamples, shared by every vintage, so the differences stay paired. Years are resampled
  independently. The bootstrap seed is (10000, year).

**The outcomes** (review finding M-4: the owner has not ruled on "too weak", so this is the default until they do):
- A gate is open when its interval lies above zero.
- A check whose interval lies above zero passes if its gate is open, and is too weak if not.
- A check whose interval lies below zero fails, gate or no gate.
- A check whose interval holds zero fails if its gate is open, and is too weak if not.
- A vintage fails when any of its checks fails. Otherwise it is too weak when any check is too weak. Otherwise it
  passes. The 2014 vintage reads no news and only serves as 2015's predecessor, so it has no outcome.
- Why the gates differ: a vintage V that knew year V+1 leaves V+1 little to gain there, which shrinks check A's gate.
  It doesn't shrink G(V, V), so check B still fails such a vintage with its gate open.
- A failing or too-weak vintage is reported to the owner. It is **not** replaced in `reader/vintage.py` in this
  step: the note's replacement rule waits for the owner's yes.

**The pilot and N.** The 2015 and 2016 vintages on the first 300 headlines of 2015, 2016 and 2017. From the 2016
vintage's per-headline gains on 2016 and 2017, predict check B's 95% half-width at N as 1.96 times the square root of
(var 2016 + var 2017) / N. N is the smallest of 1,000 and 2,000 whose half-width is at most half the pilot's
G(2016, 2016), else 2,000. The pilot's headlines are the start of the full sample; the pilot sets N only.

**The probes** (`reader/probes.csv`, two per year for events from 2015 to 2025). Each sentence has one blank. Each
candidate (the answer and four wrong answers) fills it in turn, all its tokens masked at once, and gets the summed
log-probability of its tokens. A probe's score for a vintage is the answer's log share among the candidates. For an
event in year E, the vintages from E on could know the answer. With lo the 2014 vintage's score and hi the median
score of the vintages from E on, a vintage before E is flagged when its score is at least (lo + hi) / 2. If hi is
not above lo, the probe is uninformative. For the 2025 events no vintage comes after, so a vintage is flagged when its
score is above lo and the answer's share is above one half. A flag alone fails nothing: it gets a closer look, and
the owner decides.

## 2. The sample

`python -m reader.cutoff sample` (output `sample.parquet` and `sample.json`). 534,619 stories in `story_entities`.
Eligible headlines by year (at least one inner token), each with 2,000 drawn:

| Year | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Eligible | 31,907 | 33,251 | 23,908 | 27,012 | 28,807 | 36,455 | 47,607 | 58,380 | 65,544 | 65,110 | 63,553 | 53,082 |

Sample SHA-256 `c4421876a1ee56a542e5995f1ebe965c55a55636d23ba76c0616de3bfaf45cd6` (over year, rank, story_id and
token count). 2017 and 2018 have 2 and 1 fewer than the M2 note's counts: those headlines have no inner token.

## 3. The pilot

`python -m reader.cutoff pilot` (log `pilot.log`; cells in `pilot\`). 300 headlines a year.

| Cell | L | | Gain | Value | Per-headline sd | Standard error |
|---|---|---|---|---|---|---|
| (2015, 2015) | 4.2028 | | G(2016, 2015) | 0.0504 | 0.6480 | 0.0374 |
| (2015, 2016) | 4.1105 | | G(2016, 2016) | -0.0187 | 0.5325 | 0.0307 |
| (2015, 2017) | 4.1544 | | G(2016, 2017) | 0.0005 | 0.7280 | 0.0420 |
| (2016, 2015) | 4.1524 | | | | | |
| (2016, 2016) | 4.1292 | | | | | |
| (2016, 2017) | 4.1539 | | | | | |

- G(2016, 2016) is not above zero, so the rule picks N = 2,000.
- The paired per-headline spread is 0.53 to 0.73, against gains of a few hundredths. At N = 2,000 a gain's
  standard error is about 0.012 to 0.016, so a yearly gain under about 0.03 may not be told from zero. The check
  may end too weak for some vintages; that would be a result, not a pass.
- Speed: 12.8 to 18.7 headlines a second, so the 82,000 passes of the full run take about 1.2 to 1.8 hours.

## 4. The judge, before the full run

One `chrono-judge` (Opus, high) checked the method against the spec: `research/audit/cutoff_judge.md`. It found the
code does what the spec and section 1 say, and that a vintage which fully learned its reading year fails. Its
findings, and what was done with each, before any full-run result:
- **1, high, in the spec:** a partial leak can pass (in its synthetic run, a 2018 vintage that knew 25% or 50% of
  2019 passed check B). Done: the report adds each vintage's spillover, G(V, V+1) / G(V, V), as a description only.
  It changes no outcome. The judge's other idea, a January-to-March split, needs months in the sample and is left
  for the owner.
- **2, medium:** a fully leaky vintage whose yearly gain is too small to measure ends too weak, and too weak was not
  replaced. Done: until the owner rules on M-4, a too-weak vintage blocks the reader run (step 4) like a fail.
- **3, medium:** the N rule sizes power on G(2016, 2016), not on check B. No change: the pilot already picked the
  largest N, 2,000.
- **4 to 6, low:** 2015's probes can never flag (only the 2014 vintage comes before them); no check covers 2026,
  which the 2024 vintage also reads; a repeated story_id would make the sample depend on row order. Done for the
  last one: the sample now stops on a repeated story_id instead of dropping it. The redrawn sample has the same
  SHA-256.
- After these changes `reader/cutoff.py` has SHA-256
  `8fb546e0ceb4977437292fca0013c3f3b8577de5a8c5ee4906491cf586770741`. The rules in section 1 did not change.

## 5. Results (21 Nov 2026)

Run: `python -m reader.cutoff run 2000` (log `run_n2000.log`; 41 cells at 11.0 to 19.8 headlines a second, then
the probes). Every number below comes from `python -m reader.cutoff report 2000`, which reads the saved cells in
`n2000\` and loads no model (its output is saved as `report_n2000.md` and `n2000\report.json`). Sample SHA-256
`c4421876...45cd6`, N 2,000 a year, 41 cells, 10,000 resamples.

### The outcomes, by the rules in section 1

| Vintage | Own-year gain G(V, V) | Check A | A | Check B | B | Outcome |
|---|---|---|---|---|---|---|
| 2015 | +0.0349 [+0.0061, +0.0633] | +0.0073 [-0.0315, +0.0467] | too weak | -0.0180 [-0.0561, +0.0207] | fail | fail |
| 2016 | -0.0049 [-0.0322, +0.0227] | -0.0120 [-0.0515, +0.0273] | fail | -0.0146 [-0.0533, +0.0238] | too weak | fail |
| 2017 | +0.1036 [+0.0759, +0.1305] | -0.0471 [-0.0831, -0.0114] | fail | +0.0103 [-0.0274, +0.0478] | fail | fail |
| 2018 | -0.0120 [-0.0369, +0.0135] | +0.0216 [-0.0149, +0.0585] | fail | +0.0147 [-0.0206, +0.0504] | too weak | fail |
| 2019 | +0.0552 [+0.0293, +0.0815] | +0.0183 [-0.0261, +0.0615] | too weak | -0.0398 [-0.0774, -0.0024] | fail | fail |
| 2020 | -0.0951 [-0.1275, -0.0636] | +0.0496 [+0.0026, +0.0966] | pass | -0.0066 [-0.0532, +0.0389] | too weak | too weak |
| 2021 | +0.1343 [+0.0996, +0.1681] | +0.0580 [+0.0136, +0.1036] | too weak | +0.0373 [-0.0109, +0.0840] | fail | fail |
| 2022 | -0.0154 [-0.0483, +0.0187] | +0.0264 [-0.0138, +0.0667] | fail | -0.0035 [-0.0495, +0.0426] | too weak | fail |
| 2023 | +0.1127 [+0.0838, +0.1411] | +0.0220 [-0.0009, +0.0450] | fail | +0.0152 [-0.0219, +0.0520] | fail | fail |
| 2024 | +0.0650 [+0.0497, +0.0804] | none | | +0.0005 [-0.0213, +0.0226] | fail | fail |

**No vintage passes.** Nine fail and 2020 is too weak. By section 1 none is replaced, and the reader run (step 4)
waits for the owner.

### What the numbers show (a reading, not part of the rules)

- **The vintages differ in general quality far more than year by year.** A vintage's gain over its predecessor is
  nearly the same on every year it is measured on: the 2017 vintage gains +0.116, +0.104 and +0.093 on 2016, 2017
  and 2018. The 2016, 2018, 2020 and 2022 vintages are no better than the one before them on their own year and the
  next (2020 is worse on all three of its years: -0.113, -0.095, -0.089). The cause is not known.
- **So the gates do not measure what they were meant to.** G(V, V) was meant as V's yearly update. It is mostly
  the vintage-wide shift, so a gate can open with no measurable year-specific gain (2017, 2021, 2023, 2024) or shut
  for a vintage that may have learned its year (2016, 2018, 2020, 2022).
- **The year-specific part is within the noise.** The checks remove the vintage-wide shift, and what is left is a
  few hundredths with 95% half-widths of 0.02 to 0.05. Four of the 19 check intervals exclude zero: check A for
  2020 and 2021 (above; 2021's gate is shut) and check A for 2017 and check B for 2019 (below).
- **The fails are mostly "holds zero with an open gate".** Two are below zero: check A for 2017 (the 2018 vintage
  gains less on 2018 than on 2017) and check B for 2019 (the 2019 vintage gains more over 2018 on 2020 than on 2019).
  The second is the leak's direction, but the COVID probe (p2020a) gives the 2019 vintage -18.22 against -4.60 for
  2020, so it did not know that 2020 name.
- **Spillover** G(V, V+1) / G(V, V), where G(V, V) is above zero (description only, judge finding 1): 2015 +1.52,
  2017 +0.90, 2019 +1.72, 2021 +0.72, 2023 +0.86, 2024 +0.99. Near 1 means the gain is not specific to year V, which
  fits the vintage-wide shift above. A full leak would also give 1, so this measure cannot tell the two apart.

### Mean masked-word loss L(v, y)

| Vintage | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2014 | 4.2084 | 4.1011 |  |  |  |  |  |  |  |  |  |  |
| 2015 | 4.1735 | 4.0481 | 4.1468 |  |  |  |  |  |  |  |  |  |
| 2016 | 4.1857 | 4.0531 | 4.1372 | 3.8214 |  |  |  |  |  |  |  |  |
| 2017 |  | 3.9375 | 4.0336 | 3.7281 | 3.7850 |  |  |  |  |  |  |  |
| 2018 |  |  | 3.9985 | 3.7401 | 3.8117 | 3.8276 |  |  |  |  |  |  |
| 2019 |  |  |  | 3.7065 | 3.7565 | 3.7326 | 3.8036 |  |  |  |  |  |
| 2020 |  |  |  |  | 3.8698 | 3.8277 | 3.8921 | 3.8016 |  |  |  |  |
| 2021 |  |  |  |  |  | 3.7429 | 3.7578 | 3.7046 | 3.6284 |  |  |  |
| 2022 |  |  |  |  |  |  | 3.8312 | 3.7200 | 3.6403 | 3.6533 |  |  |
| 2023 |  |  |  |  |  |  |  | 3.6337 | 3.5276 | 3.5558 | 3.4757 |  |
| 2024 |  |  |  |  |  |  |  |  | 3.4846 | 3.4908 | 3.4112 | 3.4739 |

### Every gain G(v, y)

| G(v, y) | value [95% interval] |
|---|---|
| G(2015, 2015) | +0.0349 [+0.0061, +0.0633] |
| G(2015, 2016) | +0.0529 [+0.0265, +0.0791] |
| G(2016, 2015) | -0.0122 [-0.0408, +0.0166] |
| G(2016, 2016) | -0.0049 [-0.0322, +0.0227] |
| G(2016, 2017) | +0.0097 [-0.0165, +0.0359] |
| G(2017, 2016) | +0.1156 [+0.0866, +0.1443] |
| G(2017, 2017) | +0.1036 [+0.0759, +0.1305] |
| G(2017, 2018) | +0.0933 [+0.0668, +0.1200] |
| G(2018, 2017) | +0.0351 [+0.0098, +0.0606] |
| G(2018, 2018) | -0.0120 [-0.0369, +0.0135] |
| G(2018, 2019) | -0.0267 [-0.0518, -0.0021] |
| G(2019, 2018) | +0.0336 [+0.0074, +0.0604] |
| G(2019, 2019) | +0.0552 [+0.0293, +0.0815] |
| G(2019, 2020) | +0.0951 [+0.0685, +0.1225] |
| G(2020, 2019) | -0.1134 [-0.1420, -0.0839] |
| G(2020, 2020) | -0.0951 [-0.1275, -0.0636] |
| G(2020, 2021) | -0.0885 [-0.1201, -0.0556] |
| G(2021, 2020) | +0.0847 [+0.0547, +0.1157] |
| G(2021, 2021) | +0.1343 [+0.0996, +0.1681] |
| G(2021, 2022) | +0.0970 [+0.0650, +0.1295] |
| G(2022, 2021) | -0.0734 [-0.1042, -0.0430] |
| G(2022, 2022) | -0.0154 [-0.0483, +0.0187] |
| G(2022, 2023) | -0.0119 [-0.0436, +0.0195] |
| G(2023, 2022) | +0.0864 [+0.0583, +0.1146] |
| G(2023, 2023) | +0.1127 [+0.0838, +0.1411] |
| G(2023, 2024) | +0.0975 [+0.0740, +0.1212] |
| G(2024, 2023) | +0.0430 [+0.0257, +0.0600] |
| G(2024, 2024) | +0.0650 [+0.0497, +0.0804] |
| G(2024, 2025) | +0.0645 [+0.0485, +0.0804] |

### The probes

`reader/probes.csv` had the same SHA-256 at the run as when frozen (`7c3d3161...b2c65`). Scores are the answer's log
share among the five candidates (0 is certain).

| Probe | Event year | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | Kind | Flagged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p2015a | 2015 | -19.13 | -19.52 | -19.22 | -15.65 | -11.50 | -10.62 | -8.87 | -7.76 | -7.37 | -7.14 | -6.89 | informative | none |
| p2015b | 2015 | -9.95 | -8.75 | -9.69 | -10.39 | -9.87 | -8.65 | -9.20 | -9.98 | -9.93 | -10.68 | -9.64 | informative | none |
| p2016a | 2016 | -3.00 | -2.30 | -1.25 | -1.88 | -0.85 | -0.34 | -0.13 | -0.49 | -0.39 | -1.34 | -1.02 | informative | none |
| p2016b | 2016 | -11.02 | -8.49 | -2.58 | -0.73 | -0.99 | -0.89 | -0.49 | -0.59 | -1.64 | -1.09 | -1.08 | informative | none |
| p2017a | 2017 | -12.56 | -14.78 | -13.66 | -11.21 | -13.26 | -11.87 | -13.07 | -11.56 | -11.65 | -9.64 | -9.29 | informative | none |
| p2017b | 2017 | -3.27 | -3.61 | -4.82 | -4.09 | -4.97 | -4.47 | -5.40 | -5.29 | -3.76 | -3.98 | -4.14 | uninformative | none |
| p2018a | 2018 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | uninformative | none |
| p2018b | 2018 | -4.19 | -4.24 | -4.83 | -5.07 | -3.29 | -5.51 | -5.42 | -3.77 | -5.59 | -4.20 | -4.36 | uninformative | none |
| p2019a | 2019 | -7.10 | -7.35 | -7.37 | -7.20 | -7.49 | -3.17 | -1.34 | -0.20 | -0.08 | -0.36 | -0.58 | informative | none |
| p2019b | 2019 | -21.74 | -19.16 | -21.40 | -21.05 | -17.76 | -17.68 | -18.49 | -17.98 | -19.32 | -17.58 | -18.26 | informative | 2015, 2018 |
| p2020a | 2020 | -19.76 | -20.34 | -22.19 | -19.22 | -21.29 | -18.22 | -4.60 | -2.31 | -0.71 | -1.33 | -1.58 | informative | none |
| p2020b | 2020 | -3.61 | -3.15 | -3.62 | -3.81 | -5.58 | -3.84 | -1.06 | -0.18 | -0.52 | -0.93 | -0.59 | informative | none |
| p2021a | 2021 | -16.98 | -17.00 | -17.81 | -19.85 | -20.41 | -20.65 | -21.08 | -18.07 | -17.45 | -16.60 | -16.78 | uninformative | none |
| p2021b | 2021 | -4.57 | -5.46 | -4.99 | -5.20 | -4.09 | -5.68 | -5.91 | -6.58 | -1.89 | -1.02 | -1.03 | informative | none |
| p2022a | 2022 | -1.34 | -1.00 | -0.94 | -1.68 | -1.48 | -2.08 | -2.11 | -1.41 | -1.58 | -0.95 | -0.61 | informative | 2015, 2016 |
| p2022b | 2022 | -11.53 | -11.25 | -11.08 | -13.57 | -15.24 | -15.65 | -16.04 | -15.91 | -15.24 | -11.08 | -9.86 | informative | 2015, 2016 |
| p2023a | 2023 | -12.86 | -15.62 | -16.16 | -12.21 | -11.33 | -12.38 | -11.46 | -11.85 | -11.09 | -10.81 | -11.52 | informative | 2018, 2020, 2021, 2022 |
| p2023b | 2023 | -10.28 | -10.19 | -13.52 | -11.79 | -10.04 | -18.00 | -14.92 | -10.94 | -11.61 | -12.07 | -10.40 | uninformative | none |
| p2024a | 2024 | -4.24 | -5.86 | -6.68 | -7.57 | -9.16 | -8.51 | -7.69 | -4.66 | -4.06 | -3.94 | -2.80 | informative | none |
| p2024b | 2024 | -2.11 | -2.20 | -1.50 | -1.42 | -1.39 | -1.14 | -2.82 | -1.06 | -3.25 | -2.79 | -2.48 | uninformative | none |
| p2025a | 2025 | -2.76 | -1.95 | -1.25 | -2.58 | -1.70 | -1.27 | -1.82 | -3.20 | -2.57 | -5.45 | -3.22 | no later vintage | none |
| p2025b | 2025 | -9.25 | -11.89 | -12.43 | -11.67 | -13.84 | -11.54 | -9.74 | -13.07 | -11.75 | -10.41 | -11.69 | no later vintage | none |

- **Flags, for the owner (a flag alone fails nothing):** p2019b (vintages 2015 and 2018), p2022a (2015, 2016),
  p2022b (2015, 2016), p2023a (2018, 2020, 2021, 2022).
- A reading of the flags, not part of the rules. The gap hi minus lo is 3.61 for p2019b, 0.39 for p2022a, 0.45 for
  p2022b and 1.69 for p2023a. In p2022a and p2022b the gap is under 0.5, inside the spread between neighbouring
  vintages, so a vintage crosses the halfway line by noise. In p2019b the 2014 score is the lowest, and the
  vintages from 2018 on score alike (-17.58 to -19.32), with no step at 2019. In p2023a the vintages from 2017 on
  score alike (-10.81 to -12.38), with no step at 2023. The rule has no margin, which the owner may want to add.
- **Steps**, where a probe's score rises by more than 3 from one vintage to the next. The gaps and rises are the
  last table that `report 2000` prints, added after the run as a reading only (it changes no flag):
  - At the event's own vintage: p2016b at 2016 (+5.91), p2019a at 2019 (+4.32), p2020a at 2020 (+13.62), p2021a
    at 2021 (+3.01, though that probe's later median is below the 2014 score, so it is uninformative).
  - Later than the event: p2015a at 2017 and 2018 (+3.57, +4.15), p2021b at 2022 (+4.70; Meta, October 2021),
    p2022b at 2023 (+4.16; ChatGPT, 30 November 2022).
  - Before the event: p2019b at 2018 (+3.29, flagged above), p2020a at 2019 (+3.08, to -18.22, still far below the
    2020 vintage's -4.60), p2023a at 2017 (+3.95, back from a dip to about the 2014 level), p2023b at 2020 and 2021
    (+3.08, +3.98, back from a dip at 2019 to about the 2014 level), p2024a at 2021 (+3.03, to -4.66, about the
    2014 level of -4.24; Harris was already vice president then).
- After the run, `cmd_report` gained that last table; no other line of `reader/cutoff.py` changed after the run.
  The final file has SHA-256 `f38c814daa78fd644b3ec6fb3ec5ca08e3cfc12d49fea93210ab0f527a03d652`.
- Checked by a `chrono-checker`: every table above matches a fresh `report 2000`, and the full test suite printed
  "279 passed, 2 skipped, 6 warnings in 309.96s".

## 6. What waits for the owner

1. **M-4 and M2's done-when.** No vintage passes. Under section 1 nine fail and one is too weak, and nothing is
   replaced. The replacement rule could not help in any case: it needs an earlier vintage that passes.
2. **Whether this check can decide anything.** The reading in section 5 is that the loss check is dominated by
   vintage-wide quality shifts and cannot tell a leak from a yearly update too small to see. Options, none done:
   rule the loss check too weak for every vintage and decide on the probes; or redesign the measure (several mask
   draws per headline, larger N, or a contrast that removes each vintage's overall shift).
3. **The four probe flags** above, and whether to add a margin to the flag rule.
4. **Judge finding 1** (the January-to-March split) and finding 5 (no check covers 2026).

## 7. The redesign (21 Nov 2026): no design within 10 hours can decide

The owner chose "redesign the check". Sections 1 to 6 stay as they were. This section sizes a redesign from the
first run's saved cells, before any new loss is computed. Command: `python research/cutoff_design.py` (reads the
per-headline losses in `n2000\` and the speeds in `run_n2000.log`; output saved as `design.log`). The conclusion is
that nothing under 10 hours of laptop time can decide, so no new rules were written, no judge ran and nothing ran.

**The noise.** Each check is a difference of means over independent headlines, so its 95% half-width shrinks as
one over the square root of N. At N = 2,000 the bootstrap standard errors are 0.0118 to 0.0237 for check A (median
0.0202, a half-width of 0.0396) and 0.0112 to 0.0244 for check B (median 0.0194).

**The effect worth detecting.** A full leak in vintage V takes a check's true value from V's honest year-specific
effect down to zero. So the effect to detect is the honest year-specific effect. Pooled over vintages (the mean of
the check values, with the paired bootstrap):
- check A, 9 vintages: +0.0160 [+0.0005, +0.0309].
- check B, 10 vintages: -0.0004 [-0.0147, +0.0136].
Check B's honest value is indistinguishable from zero, which is also what a full leak gives. More data can't make
it tell the two apart. Only check A has an effect to detect, about 0.016.

**The arithmetic, for check A at E = 0.016** (28 cells; median speed 16.4 headlines a second, range 11.0 to 19.8):
- A half-width of at most E / 2 needs N = 2,000 x (0.0396 / 0.008)^2 = 49,005 a year: 28 x 49,005 / 16.4 =
  23.2 hours. It also needs more headlines than 2017 has (23,908 eligible), and 2017 enters checks A for 2016
  and 2017.
- 10 hours buys N = 10 x 3,600 x 16.4 / 28 = 21,086 a year, a half-width of 0.0122. An honest vintage with a true
  effect of 0.016 then passes with probability about 0.73, so all 9 honest vintages pass with probability about
  0.06. Almost every such run would fail an honest vintage.
- At the largest pool, 23,908, the half-width is still 0.0115.

**Several mask draws per headline don't help.** With K draws on each of N headlines, a mean's variance is
s_h^2 / N + s_m^2 / (N K), where s_h is the spread between headlines and s_m the spread between mask draws. Each
draw costs one pass, like a new headline. For a fixed number of passes N K, the variance is smallest at K = 1
unless s_h is zero, and even then it only equals that of N K new headlines. The 10-hour limit binds before the
pools run out, so extra draws can't beat more headlines. (This holds whatever the two spreads are, so they were
not measured.)

**No extra contrast is needed.** Checks A and B already remove each vintage's overall shift: each is a difference
between two gains of the same pair of vintages. What is left is sampling noise against a small effect, not the
shift. A contrast over more years would add cells without adding signal for the one question, whether V knew year
V+1. Pooling over vintages would detect year-specific learning in general, but a leak in one vintage moves the pool
by about a ninth, so it can't find that vintage.

**So, for the owner:** masked-word loss on headlines can't settle the cutoff on this laptop. Check B never can,
and check A needs about 23 hours and more headlines than 2017 has. What remains: (a) decide on the named-event
probes (section 5), perhaps with more probes and a margin in the flag rule; (b) run check A alone, above 10 hours
or on a GPU, and accept that 2016 and 2017 can't reach the target; (c) accept the vintages as published on the
probes' evidence. Judge findings 1 and 5 were not folded in, since no new run is designed.

## 8. The stronger probes (21 Nov 2026): the rules that decide

The owner chose "Stronger probes". Each vintage's cutoff is settled here, on named-event probes, not on the
masked-word loss check. This section was written before any vintage scored a single new probe, and the file and the
rules below were frozen at that point. Code: `reader/cutoff.py` (`probe2_cell`, `probe2_last`, `probe2_outcomes`,
commands `probes2` and `report-probes2`). Tests: `tests/test_cutoff.py`.

### 8.1 Why the first probes were weak

Two things, both from the first run's saved scores (`n2000\probes.parquet`), used here only as a pilot for the
design. The new probes are new events, so none of their scores was seen.

- **Unequal lengths.** In 17 of the 22 first probes the answer had a different number of tokens from some wrong
  answer (count by `candidate_inputs` with the pinned tokenizer). A candidate's score is the sum of its tokens'
  log-probabilities, so a longer answer starts far behind and drifts with each vintage's overall habits. The
  flags that read as noise in section 5 (p2019b, p2022b, p2021a's drift) are all on answers longer than every wrong
  answer. p2018a scored -0.00 for every vintage for the opposite reason.
- **No margin.** A probe counted as informative when the later vintages scored above the earlier ones by any amount,
  so a gap of 0.4 could flag a vintage.

### 8.2 The probes

`reader/probes2.csv`: 80 events, 8 in each year from 2016 to 2025. Each event:
- is public, named and dated (the New York date the news first came out), with a Wikipedia article to check it;
- has an answer that was not public before 1 January of the event's year, the day after the cutoff of the vintage
  just before: a deal, a result, a name or a number nobody could predict (news earlier in the same year does no harm);
- comes with four wrong answers of the same kind, none of which also makes the sentence true;
- has the same number of tokens in the answer and in each wrong answer (the pinned tokenizer, shared by every
  vintage; `test_probes2_candidates_have_the_answers_token_count` checks every candidate).

How the list was made. Events were written by year from public knowledge, each with a pool of wrong answers in a
fixed order; the four kept are the first in the pool with the answer's token count, with hand fixes where a pool
ran short. Before freezing, these were dropped or replaced: every event of the first set (their scores were seen);
events whose answer may already have been in the news the year before, dropped as a precaution on the writer's
memory, not checked (Synopsys and Ansys, Paramount and Skydance, Seagen as a takeover target, Stargate as a
Microsoft and OpenAI plan, Windsurf as Codeium's editor, Cambridge Analytica's use of Facebook data, PG&E's
bankruptcy of 2001); wrong answers that were also true at another time (for example Arroyo and Estrada for a
May election in the Philippines, Theresa May for "in July became prime minister", Symantec for "Broadcom agreed
to buy"); and events whose answer and wrong answers could not be matched in length (WannaCry, two online brokers).
A `chrono-checker` then checked every row against its Wikipedia article (8.6).

The 2014 vintage reads no news, so the 2015 events would test nothing and there are none. No probe covers 2026,
which the 2024 vintage also reads (judge finding 5 of 21 Nov stands).

| Probe | Date | Answer | Wrong answers | Check against |
|---|---|---|---|---|
| q2016a | 2016-02-07 | Broncos | Panthers, Patriots, Steelers, Packers | Super Bowl 50 |
| q2016b | 2016-04-03 | Panama | Pentagon, Swiss, Jersey, Delaware | Panama Papers |
| q2016c | 2016-05-02 | Leicester | Watford, Burnley, Norwich, Southampton | 2015–16 Leicester City F.C. season |
| q2016d | 2016-06-13 | LinkedIn | Monster, Indeed, Twitter, Facebook | LinkedIn |
| q2016e | 2016-09-22 | Yahoo | Twitter, eBay, Facebook, Google | Yahoo data breaches |
| q2016f | 2016-09-02 | 7 | 5, 4, 3, 2 | Samsung Galaxy Note 7 |
| q2016g | 2016-07-10 | Portugal | Germany, Spain, Italy, England | UEFA Euro 2016 final |
| q2016h | 2016-09-14 | Monsanto | Pioneer, KWS, Sakata, Bunge | Monsanto (Bayer deal announced September 2016) |
| q2017a | 2017-02-17 | Unilever | Mondelez, Reckitt, Diageo, ConAgra | Unilever (Kraft Heinz bid of February 2017) |
| q2017b | 2017-03-13 | Mobileye | Innoviz, Elbit, Valens, Argus | Mobileye (Intel deal announced March 2017) |
| q2017c | 2017-09-20 | Maria | Sandy, Andrew, Matthew, Rita | Hurricane Maria |
| q2017d | 2017-04-09 | United | American, Southwest, Spirit, Alaska | United Express Flight 3411 incident |
| q2017e | 2017-08-25 | Harvey | Allison, Rita, Andrew, Ivan | Hurricane Harvey |
| q2017f | 2017-09-07 | Equifax | Experian, TransUnion, Moody's, FICO | 2017 Equifax data breach |
| q2017g | 2017-11-06 | Qualcomm | NXP, Nvidia, Micron, Marvell | Qualcomm (Broadcom bid of November 2017) |
| q2017h | 2017-12-03 | Aetna | Cigna, Magellan, Premera, Assurant | Aetna (CVS deal announced December 2017) |
| q2018a | 2018-01-03 | Meltdown | Heartbleed, Stagefright, Poodle, Dirty Cow | Meltdown (security vulnerability) |
| q2018b | 2018-03-18 | Uber | Tesla, Google, Cruise, Intel | Death of Elaine Herzberg |
| q2018c | 2018-05-09 | Flipkart | Tata Cliq, BigBazaar, Lenskart, Fabfurnish | Flipkart (Walmart deal announced May 2018) |
| q2018d | 2018-06-12 | Singapore | Beijing, Seoul, Geneva, Tokyo | 2018 North Korea–United States Singapore Summit |
| q2018e | 2018-07-10 | Thailand | Vietnam, Cambodia, Malaysia, Myanmar | Tham Luang cave rescue |
| q2018f | 2018-10-02 | Istanbul | Cairo, Paris, London, Dubai | Assassination of Jamal Khashoggi |
| q2018g | 2018-10-28 | Red Hat | SUSE, Canonical, MongoDB, GitLab | Red Hat (IBM deal announced October 2018) |
| q2018h | 2018-11-08 | Paradise | Auburn, Lincoln, Chester, Concord | Camp Fire (2018) |
| q2019a | 2019-01-03 | Celgene | Biogen, Amgen, Alexion, Vertex | Celgene (Bristol-Myers Squibb deal announced January 2019) |
| q2019b | 2019-10-30 | Nationals | Brewers, Rays, Padres, Mariners | 2019 World Series |
| q2019c | 2019-06-18 | Libra | Ripple, Monero, Zcash, Stellar | Diem (digital currency) |
| q2019d | 2019-06-25 | Allergan | Gilead, Regeneron, Perrigo, Incyte | Allergan (AbbVie deal announced June 2019) |
| q2019e | 2019-07-24 | Boris Johnson | Jeremy Hunt, Philip Hammond, David Davis, Liam Fox | 2019 Conservative Party leadership election |
| q2019f | 2019-09-23 | Thomas Cook | TUI, Jet2, EasyJet, Ryanair | Thomas Cook Group (collapse September 2019) |
| q2019g | 2019-06-10 | Tableau | Qlik, Domo, Spotfire, MicroStrategy | Tableau Software (Salesforce deal announced June 2019) |
| q2019h | 2019-11-25 | Tiffany | Harry Winston, Signet, Zales, Blue Nile | Tiffany & Co. (LVMH deal announced November 2019) |
| q2020a | 2020-01-13 | Plaid | Stripe, Venmo, Robinhood, Chime | Plaid Inc. (Visa deal announced January 2020) |
| q2020b | 2020-03-08 | Russia | Iran, Qatar, Venezuela, Norway | 2020 Russia–Saudi Arabia oil price war |
| q2020c | 2020-04-20 | zero | twenty, thirty, fifty, forty | 2020 Russia–Saudi Arabia oil price war (WTI futures negative on 20 April 2020) |
| q2020d | 2020-09-10 | Nikola | Rivian, Workhorse, Navistar, Arrival | Nikola Corporation |
| q2020e | 2020-10-27 | Xilinx | Microsemi, Synaptics, Qorvo, Rambus | Xilinx (AMD deal announced October 2020) |
| q2020f | 2020-08-04 | Beirut | Piraeus, Mersin, Aqaba, Tartus | 2020 Beirut explosion |
| q2020g | 2020-12-01 | Slack | Zoom, Dropbox, Asana, Twilio | Slack Technologies (Salesforce deal announced December 2020) |
| q2020h | 2020-12-13 | SolarWinds | Symantec, McAfee, NetScout, Infoblox | 2020 United States federal government data breach |
| q2021a | 2021-02-15 | Texas | California, Florida, Ohio, Michigan | 2021 Texas power crisis |
| q2021b | 2021-03-11 | Beeple | Hockney, Basquiat, Kusama, Murakami | Everydays: the First 5000 Days |
| q2021c | 2021-03-23 | Given | Green, Golden, Grace, Lucky | 2021 Suez Canal obstruction |
| q2021d | 2021-03-26 | Archegos | Baupost, Coatue, Maverick, Appaloosa | Archegos Capital Management |
| q2021e | 2021-05-07 | Colonial | Dakota, Trans, Alaska, Atlantic | Colonial Pipeline ransomware attack |
| q2021f | 2021-05-17 | Discovery | Netflix, Disney, CBS, Sony | Warner Bros. Discovery |
| q2021g | 2021-06-09 | El Salvador | Estonia, South Korea, Lithuania, Honduras | Bitcoin in El Salvador |
| q2021h | 2021-11-10 | Rivian | Nikola, Lordstown, Lucid, Canoo | Rivian |
| q2022a | 2022-01-18 | Activision Blizzard | Bandai Namco, CD Projekt, Take-Two Interactive, Sega Sammy | Acquisition of Activision Blizzard by Microsoft |
| q2022b | 2022-03-08 | Mandiant | Fortinet, Sophos, Rapid7, Tenable | Mandiant (Google deal announced March 2022) |
| q2022c | 2022-05-09 | TerraUSD | Paxos, FRAX, Neutrino, Gemini Dollar | Terra (blockchain) |
| q2022d | 2022-05-26 | VMware | Citrix, Salesforce, ServiceNow, Workday | VMware (Broadcom deal announced May 2022) |
| q2022e | 2022-08-16 | Reduction | Control, Relief, Protection, Recovery | Inflation Reduction Act |
| q2022f | 2022-03-27 | Will Smith | Eddie Murphy, Kevin Hart, Tom Cruise, Mel Gibson | Will Smith–Chris Rock slapping incident |
| q2022g | 2022-09-15 | Figma | Canva, Sketch, Framer, Miro | Figma (Adobe deal announced September 2022) |
| q2022h | 2022-11-11 | FTX | Binance, Coinbase, Kraken, Gemini | Bankruptcy of FTX |
| q2023a | 2023-01-24 | Adani | Tata, Reliance, Wipro, Essar | Adani Group (Hindenburg Research report of January 2023) |
| q2023b | 2023-02-06 | Bard | Alexa, Watson, Tay, Zo | Gemini (chatbot) (announced as Bard in February 2023) |
| q2023c | 2023-08-01 | Fitch | Moody's, DBRS, Kroll, Morningstar | United States federal government credit-rating downgrades (Fitch, August 2023) |
| q2023d | 2023-02-03 | Palestine | Liverpool, Cleveland, Dayton, Columbus | East Palestine, Ohio, train derailment |
| q2023e | 2023-05-01 | JPMorgan | Bank of America, Barclays, Comerica, M&T | First Republic Bank (failure May 2023) |
| q2023f | 2023-06-09 | Modelo | Coors, Corona, Michelob, Stella | Modelo Especial (overtook Bud Light; first reported June 2023) |
| q2023g | 2023-10-11 | Pioneer | Diamondback, EOG, Coterra, Matador | Pioneer Natural Resources (Exxon deal announced October 2023) |
| q2023h | 2023-12-18 | Nippon Steel | Hyundai Steel, Jindal Steel, Voestalpine, Dongkuk Steel | U.S. Steel (Nippon Steel deal announced December 2023) |
| q2024a | 2024-01-05 | Alaska | United, Delta, American, Southwest | Alaska Airlines Flight 1282 |
| q2024b | 2024-01-09 | Juniper | Arista, Extreme, Riverbed, Gigamon | Juniper Networks (HPE deal announced January 2024) |
| q2024c | 2024-08-06 | Walz | Whitmer, Newsom, Polis, Inslee | Tim Walz 2024 vice presidential campaign |
| q2024d | 2024-02-19 | Capital One | JPMorgan, Wells Fargo, Goldman Sachs, Barclays | Discover Financial (Capital One deal announced February 2024) |
| q2024e | 2024-07-23 | Wiz | Orca, Okta, Sysdig, Tanium | Wiz (company) (Google offer reported July 2024) |
| q2024f | 2024-07-19 | CrowdStrike | Kaspersky, F-Secure, Netskope, Palo Alto Networks | 2024 CrowdStrike-related IT outages |
| q2024g | 2024-08-13 | Chipotle | Papa John's, Domino's, Dunkin, Qdoba | Brian Niccol |
| q2024h | 2024-08-24 | Telegram | WhatsApp, Viber, WeChat, Discord | Pavel Durov (arrested in France August 2024) |
| q2025a | 2025-01-07 | Palisades | Skirball, Sesnon, La Tuna, Kincade | Palisades Fire |
| q2025b | 2025-01-10 | Calpine | NRG, Talen, Entergy, Dominion | Calpine (Constellation deal announced January 2025) |
| q2025c | 2025-04-28 | Spain | France, Italy, Morocco, Greece | 2025 Iberian Peninsula blackout |
| q2025d | 2025-07-16 | Astronomer | Snowflake, Databricks, Datadog, Confluent | Kiss cam (Coldplay concert at Gillette Stadium, July 2025) |
| q2025e | 2025-08-25 | Cook | Barr, Jefferson, Fischer, Williams | Lisa Cook (attempted removal August 2025) |
| q2025f | 2025-02-21 | Bybit | Binance, Coinbase, Kraken, OKX | Bybit (hack of February 2025) |
| q2025g | 2025-07-29 | Norfolk Southern | CSX, Canadian National, Canadian Pacific, Conrail | Norfolk Southern Railway (Union Pacific deal announced July 2025) |
| q2025h | 2025-08-22 | Intel | AMD, Arm, Samsung, IBM | Intel (US government stake August 2025) |

### 8.3 Scoring

As in section 1. Each candidate fills the blank in turn, all its tokens masked at once, and gets the summed
log-probability of its tokens. A probe's score for a vintage is the answer's log share among its five candidates
(0 is certain, log(1/5) = -1.61 is no preference). With equal lengths, the shares compare like with like.

### 8.4 The flag rule, with its margin

These are the rules as changed after the judge (8.8 lists what changed from the first freeze in 8.7).

For a probe of year E from 2016 to 2024, and a vintage V from 2015 to E-1:
- lo is the median score of V's three nearest predecessors, the vintages from V-3 to V-1 (from 2014 on). It leaves
  V out, so a leak in V can't raise its own baseline. It leaves older vintages out, so slow honest growth in what
  vintages know about an answer over the years isn't read as a leak. For V = 2015 it is the 2014 vintage alone.
- hi is the median score of the vintages from E to 2024.
- The probe is **informative for V** when hi - lo is at least 3, the margin. A gap of 3 is a factor of about 20 in
  the answer's share.
- T is the least rise over lo that can flag. It is the 95th percentile of score minus lo over every honest cell, and
  never below 1.5. An honest cell is a probe of year E (2016 to 2025) and a vintage from 2015 to E-2, a full year
  or more before the event, which can't know the answer. So T is measured on the run's own drift, and an honest
  vintage clears it on about 1 probe in 20.
- V is **flagged** by the probe when the probe is informative for V and V's score is at least both (lo + hi) / 2
  and lo + T.

For a 2025 probe no vintage comes after the event, so hi can't be measured. lo is the median of the 2021, 2022 and
2023 vintages. The probe is **usable** when lo is -3 or lower, the room a gap of 3 needs, since a score is at most
0. The 2024 vintage is flagged when the probe is usable and its score is at least lo + T.

Why a margin of 3. On the first run's scores (`python research/probe_margin_pilot.py`, which applies
`probe2_cell` with T at its floor of 1.5 to `n2000\probes.parquet`), a margin of 2, 3 or 4 finds 11, 8 or 4 cells
informative for the vintage just before the event, with 2, 1 and 0 flags among them (p2019b on 2018, p2023b on
2022). A margin of 3 keeps most of the signal; 4 keeps too little. The same script tries the 2024 rule with lo + 1.5
on the earlier years: 15 usable and 4 flagged (p2016b on 2015, p2019b on 2018, p2020a on 2019, p2023b on 2022), far
too many for honest vintages. That is why T is calibrated. On the first set, the honest cells' 95th percentile is
3.04, heavy-tailed because of its unequal lengths, and with it the 2024 rule still flags 3 of 15. The first set is
only a rough guide to the new set's drift, which is why T is measured on the run itself.

### 8.5 The outcomes, for each vintage

Each vintage V from 2015 to 2024 is judged on the 8 probes of year V+1, the year it reads first. It is the year a
leak past the cutoff would show. f is the number of those probes that flag V.
- **V from 2015 to 2023.** n is the number of those probes informative for V.
- **V = 2024.** A 2025 probe's informativeness can't be measured, so n is q times the number of usable 2025
  probes, where q is the share of the 72 probes of 2016 to 2024 informative for the vintage just before their
  event. The power is borrowed from the other years.
- V **fails** when f is 2 or more. Otherwise it **passes** when n is 3 or more. Otherwise it is **too weak**.
- One flag is tolerated, since one probe can be flagged by chance or by a fact that leaked into the news early.
- Reported for the owner, deciding nothing: T and q; flags on the probes of later years (V+2 to 2024); and which of
  V's flags fall on events from January to March, where a leak of a few weeks past the cutoff would show first.
- The 2014 vintage has no outcome. A vintage that fails or is too weak is reported, not replaced. Only the owner
  replaces a vintage.

How often the rules are wrong, on synthetic scores (`python research/probe_rules_sim.py`, 200 seeds; -5 for a
vintage that doesn't know, -0.5 for one that does, normal noise; a share of events that no vintage ever learns;
the leaky case has 2018 know 2019 and 2024 know 2025):

| Noise (sd) | Share of events learned | Honest vintage fails | Honest vintage too weak | Leaky 2018 or 2024 fails |
|---|---|---|---|---|
| 0.7 | 0.5 | 0.004 | 0.141 | 0.960 |
| 0.7 | 0.8 | 0.004 | 0.000 | 1.000 |
| 1.0 | 0.5 | 0.006 | 0.174 | 0.953 |
| 1.0 | 0.8 | 0.009 | 0.002 | 1.000 |
| 1.5 | 0.5 | 0.021 | 0.238 | 0.887 |
| 1.5 | 0.8 | 0.037 | 0.013 | 0.990 |

The judge's estimate for the first freeze's rules was an honest fail rate of about 0.3 per vintage, from a flag rate
of 1 in 7 (finding 4). The calibrated T is what brings it down. Real scores need not be normal, so these rates are a
guide, not a guarantee.

What the probes can't see. A leak of a few weeks touches only the earliest events of a year, so it may flag one
probe and pass. A vintage that knows its next year's general news but none of these 8 events would pass. The 2024
vintage's power is borrowed from the other years, not measured. A gross leak far into the future would also raise
T a little, though it would show among the later-year flags. 2026 is not covered.

### 8.6 The fact check, before freezing

A `chrono-checker` (Sonnet) checked all 80 rows against their Wikipedia articles on 21 Nov 2026: whether the filled
sentence is true, the year and month, whether a wrong answer also fits, and whether the answer was public before.
It flagged 11 rows; WebFetch read only the first 100,000 characters of each article, so earlier links in long deal
articles may be missed. What was done:
- **Replaced:** q2016e, Verizon and Yahoo (a Reuters report of 7 Dec 2015 had Verizon's finance chief saying it
  could look at Yahoo's internet business). Now Yahoo's breach of at least 500 million accounts, 22 Sep 2016.
- **Reworded:** q2019f now says 150,000 British holidaymakers (about 600,000 were stranded in all); q2017d now says
  a sold-out United Express flight (Republic Airways flew it, and United said it was sold out, not overbooked);
  q2021g now says El Salvador passed the law in June (it took effect on 7 Sep 2021).
- **Re-dated:** q2024e to 23 Jul 2024, the day Wiz's refusal was reported (talks were reported on 14 Jul).
- **Wrong answer swapped:** q2024g, Taco Bell for Papa John's (Niccol ran Taco Bell from 2015 to 2018).
- **Kept, since the earlier link falls in the event's own year:** q2016h (Bayer's first bid, May 2016), q2018e
  (Comcast's first bid for Sky, Apr 2018), q2020g (talks reported 25 Nov 2020), q2025c (the name "Liberation Day"
  used on 31 Mar 2025). A vintage judged on year E stops at the end of year E-1, so news earlier in year E can't
  reach it. The rule in 8.2 means "not public before 1 January of the event's year".
- **Kept, not a problem for the score:** q2023c. S&P also cut the US rating from AAA in August (2011), but S&P is
  not a candidate, so the sentence is true of one candidate only.
- The checker could not confirm or rule out reports from the year before for 10 deals (CVS and Aetna, Walmart and
  Flipkart, Aramco and SABIC, LVMH and Tiffany, Broadcom and Qualcomm, Exxon and Pioneer, Nippon Steel and US Steel,
  HPE and Juniper, Union Pacific and Norfolk Southern, the US stake in Intel). One such leak can flag one probe,
  which the outcome rule tolerates.

### 8.7 The freeze

Frozen at 16:00 New York on 21 Nov 2026, before any vintage scored a probe of `reader/probes2.csv` (the output
folder `D:\chrono-data\reader\cutoff\probes2` did not exist). At that time:
- `reader/probes2.csv` had SHA-256 `5dac45065a39e981bad680143b44dfb967f78980f585a6f6c3f5ab00ef98b619`;
- `reader/cutoff.py` had SHA-256 `06f106d09843350ddf4474bc2e8df9bc1966cbefc2dc9c546df287bbffa709e3`;
- `tests/test_cutoff.py` passed (24 tests, among them the real-tokenizer length check).
Any change after this point, the judge's included, is listed in 8.8 with the new hashes.

### 8.8 The judge, and the changes before the run

One `chrono-judge` (Opus, high effort) checked the frozen rules and list, with no new score in existence. Its report
is `research/audit/probes2_judge.md`. Verdict: don't run as frozen. It confirmed that the hashes matched 8.7, that
the 24 tests passed with no skips, that the pilot reproduced 8.4's counts, and that the code matched 8.4 and 8.5
line for line. Its event facts came from memory, so a suspected link was taken as reason enough to replace a probe
(replacing costs nothing), and every new or changed row was checked again (below). Findings and actions:

1. **High: the 2024 rule had no margin and a far baseline.** Done: lo for 2024 is the median of 2021 to 2023, a
   2025 probe counts only when lo is -3 or lower, and 2024's n is q times the usable count. The judge's check showed
   lo + 1.5 alone flags too often. So the flag floor became T, calibrated on the run's honest cells (8.4), for every
   vintage.
2. **High: six answers tied to their sentence before the event year.** Done, all six replaced: q2016g (Wells
   Fargo), q2020f (BioNTech), q2018e (Sky), q2019b (SABIC), q2025e (Scale AI), q2023d (GPT-4).
3. **Medium: answers predictable before the year.** Done, the clearest replaced: q2016c (Duterte), q2017c
   (Macron), q2022f (Truss), q2025c ("Liberation" Day), q2025d (Signal), q2023f (Splunk). Also q2024h (Microsoft),
   so that 2024 doesn't keep two (q2024e stays). And q2016a: AlphaGo splits into "Alpha" and "Go", so the "Go" piece
   copied the sentence. Kept, one per year at most: q2017b, q2018b, q2019e, q2022c, q2023a, q2024e, q2025a.
4. **Medium: the one-flag tolerance.** Kept. lo now comes from V's three nearest predecessors, as the judge proposed,
   and the calibrated T caps the honest flag rate near 1 in 20. The simulated honest fail rates are in 8.5.
5. **Medium: wrong answers also true or nearly so.** Done: Lordstown (q2020d) to Arrival, ten (q2020c) to forty,
   Monarch (q2019f) to Ryanair, Sumitomo Metal (q2023h) to Dongkuk Steel, America (q2020b) to Norway.
6. **Low: wordings that give the answer away** (q2016d, q2018g, q2020g, q2021e, q2023e, q2021a, q2019d, q2018c).
   Not changed: they can only be uninformative, which lowers power and can't fail a vintage.
7. **Low: code gaps.** Done: `probes2` refuses to overwrite an existing `scores.parquet` and records the hashes of
   both `probes2.csv` and `cutoff.py`; `report-probes2` stops if `probes2.csv` changed; `probe2_outcomes` raises
   unless it has every probe and every vintage.
8. **Low: a weak test.** Done: `test_probe2_lo_uses_the_three_vintages_before_v_and_leaves_v_out` replaces it.
   New tests also cover the usable rule, the full-table check and T.
9. **Worth noting.** n = 3 with one flag passes. q and the usable count decide whether 2024 can pass. Equal token
   counts don't mean equal make-up ("Scale AI" is two words, others split into pieces). All stand as limits.

The replacements, all checked for equal token counts with the pinned tokenizer: q2016a Broncos (Super Bowl 50),
q2016c Leicester (the Premier League title), q2016g Portugal (Euro 2016), q2017c Maria (Puerto Rico), q2018e
Thailand (the cave rescue), q2019b Nationals (the World Series), q2020f Beirut (the port explosion), q2022f Will
Smith (the Oscars), q2023d Palestine (East Palestine, Ohio), q2023f Modelo (overtaking Bud Light), q2024h Telegram
(its founder's arrest), q2025c Spain (the Iberian blackout), q2025d Astronomer (the Coldplay concert), q2025e Cook
(the Fed governor).

A second `chrono-checker` (Sonnet) checked the 25 new or changed rows against Wikipedia. 23 had no problem. Fixed:
q2023f, which the news first reported in June 2023 (CBS, 9 June; WSJ, 13 June), so it is now dated 9 Jun 2023 and
reworded to "Sales figures showed that {} had overtaken Bud Light". q2025d's source now names the Wikipedia "Kiss
cam" article, since "Astronomer (company)" does not exist. Kept: q2020c, where WTI was also below twenty to fifty
dollars that day, but "for the first time" holds only for zero. The checker found no answer tied to its sentence
before 1 January of the event's year.

**The second freeze.** Frozen again at 16:21 New York on 21 Nov 2026, still before any vintage scored a probe of
`reader/probes2.csv` (`D:\chrono-data\reader\cutoff` held no `probes2` folder). At that time:
- `reader/probes2.csv` had SHA-256 `eed31d911b049213de6d53f71a0f56a2b38618183e3fc9bf0936d6305c1bd5bd`;
- `reader/cutoff.py` had SHA-256 `8bae55f5b4ecc5a499e2bab767c27de273f85b2cc8322da9af7dc41c3e153b3e`;
- `tests/test_cutoff.py` passed (27 tests, among them the real-tokenizer length check).
These are the files the run uses. The table in 8.2 shows the list as of this freeze.

### 8.9 Results (21 Nov 2026)

Commands: `python -m reader.cutoff probes2` (log `run_probes2.log`), then `python -m reader.cutoff report-probes2`
(output saved as `report_probes2.md`; numbers in `probes2\report.json`). Scores are in `probes2\scores.parquet`: 880
rows, 80 probes by 11 vintages. The run used the second freeze's files: `reader/probes2.csv` and `reader/cutoff.py`
had the SHA-256s in 8.8, both at the run and at the report.

**The outcomes, by the rules in 8.4 and 8.5.** T, the calibrated flag floor, came out at 1.631. q, the share of the
72 probes of 2016 to 2024 informative for the vintage just before the event, came out at 0.097 (7 of 72).

| Vintage | Reads | Probes | Informative (2024: q x usable) | Flags | Of them January to March | Later-year flags | Outcome |
|---|---|---|---|---|---|---|---|
| 2015 | 2016 | 8 | 1 | none | none | q2018b | too weak |
| 2016 | 2017 | 8 | 3 | q2017f | none | q2018b, q2019e | pass |
| 2017 | 2018 | 8 | 0 | none | none | q2019e, q2024g | too weak |
| 2018 | 2019 | 8 | 0 | none | none | none | too weak |
| 2019 | 2020 | 8 | 0 | none | none | none | too weak |
| 2020 | 2021 | 8 | 1 | none | none | none | too weak |
| 2021 | 2022 | 8 | 0 | none | none | none | too weak |
| 2022 | 2023 | 8 | 2 | q2023c | none | none | too weak |
| 2023 | 2024 | 8 | 0 | none | none | none | too weak |
| 2024 | 2025 | 8 | 0.292 (3 usable) | none | none | none | too weak |

So no vintage fails, 2016 passes, and the other nine are too weak. Nothing is replaced.

**What the numbers show (a reading, not part of the rules).**
- No vintage scores like a later vintage on two events of the year it reads. Where a probe could tell, the vintage
  before the event looks like the older ones. Examples: Hurricane Maria (q2017c) scores -8.79 at 2016 and -3.14 at
  2017; Harvey (q2017e) -12.07 at 2016 and -0.50 at 2017; Bard (q2023b) -6.96 at 2022 and -3.21 at 2023; the
  Colonial Pipeline (q2021e) -5.82 at 2020 and -3.44 at 2021.
- But the probes seldom have the power to pass a vintage. Only 7 of 72 are informative for the vintage just before
  their event (q2016b, q2017c, q2017e, q2017f, q2021e, q2023b, q2023c). In 9 probes every vintage already favours
  the answer (every score above log(1/5) = -1.61: q2018e, q2018g, q2019g, q2020c, q2020d, q2022d, q2022f, q2023h,
  q2025c). In 18, no vintage ever scores above -3. So these masked models rarely learn a named event's answer
  strongly enough, from the news of its own year, to pass a margin of 3.
- The two flags. q2017f (Equifax) flags 2016 at -4.92 against lo -7.10 and hi -3.10, but the score climbs steadily
  from 2014 (-8.23, -5.98, -4.92, -4.99), with no step at 2017. It reads as drift. q2023c (Fitch) flags 2022: it
  scores -6.23 at 2021, then -3.07 at 2022, -3.24 at 2023 and -3.76 at 2024, so the step comes a year before the
  event. Fitch put the United States on rating watch negative in May 2023 (from memory, not checked) and cut it in
  August. The 2022 vintage shows no knowledge of the other 2023 events (Bard scores -6.96 at 2022). One flag fails
  nothing under the rules. It is a lead for the owner, not a finding.
- The later-year flags (deciding nothing): q2018b (Uber's fatal crash) on 2015 and 2016, where the score climbs
  from 2014 (-8.06, -4.76, -2.76); Uber's self-driving tests were in the news from 2016. q2019e (Boris Johnson)
  on 2016 and 2017: he was a leadership contender from 2016. q2024g (Chipotle) on 2017. They read as answers that
  became likelier for other reasons, not leaks.

The full score table follows (the answer's log share; lo, hi and the flag are for the vintage just before the
event, and for 2025 probes "usable" replaces "informative").

| Probe | Event | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | lo | hi | Informative | Flags V = E-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q2016a | 2016-02-07 | -3.06 | -1.77 | -1.98 | -2.72 | -1.17 | -1.13 | -0.60 | -1.52 | -1.19 | -1.36 | -1.27 | -3.06 | -1.27 | no | no |
| q2016b | 2016-04-03 | -3.69 | -3.32 | -3.55 | -2.75 | -1.07 | -0.49 | -0.54 | -0.13 | -0.23 | -0.13 | -0.06 | -3.69 | -0.49 | yes | no |
| q2016c | 2016-05-02 | -3.22 | -1.77 | -2.55 | -2.64 | -1.81 | -2.56 | -2.39 | -1.86 | -2.48 | -1.67 | -2.12 | -3.22 | -2.39 | no | no |
| q2016d | 2016-06-13 | -2.30 | -3.05 | -2.28 | -1.71 | -2.16 | -2.18 | -2.84 | -2.63 | -2.55 | -2.65 | -1.88 | -2.30 | -2.28 | no | no |
| q2016e | 2016-09-22 | -2.86 | -3.64 | -2.97 | -2.34 | -2.28 | -1.48 | -2.36 | -2.10 | -2.09 | -1.97 | -1.91 | -2.86 | -2.10 | no | no |
| q2016f | 2016-09-02 | -2.14 | -2.38 | -3.10 | -2.19 | -4.35 | -4.41 | -5.48 | -5.58 | -6.18 | -5.48 | -5.36 | -2.14 | -5.36 | no | no |
| q2016g | 2016-07-10 | -4.44 | -3.87 | -4.13 | -3.82 | -3.82 | -3.48 | -3.32 | -3.52 | -3.81 | -3.59 | -3.68 | -4.44 | -3.68 | no | no |
| q2016h | 2016-09-14 | -1.07 | -0.72 | -1.45 | -0.52 | -0.50 | -0.60 | -1.02 | -0.99 | -1.83 | -2.19 | -3.09 | -1.07 | -1.02 | no | no |
| q2017a | 2017-02-17 | -0.34 | -0.54 | -0.38 | -0.48 | -0.31 | -0.37 | -0.21 | -0.49 | -1.62 | -1.05 | -0.92 | -0.44 | -0.49 | no | no |
| q2017b | 2017-03-13 | -1.94 | -3.33 | -2.74 | -2.98 | -2.04 | -2.36 | -1.73 | -2.62 | -3.44 | -3.32 | -2.73 | -2.64 | -2.68 | no | no |
| q2017c | 2017-09-20 | -6.93 | -6.91 | -8.79 | -3.14 | -0.23 | -0.35 | -0.12 | -0.35 | -0.28 | -0.21 | -0.12 | -6.92 | -0.25 | yes | no |
| q2017d | 2017-04-09 | -1.46 | -2.48 | -2.83 | -1.69 | -1.65 | -2.01 | -3.29 | -2.64 | -1.97 | -3.99 | -3.62 | -1.97 | -2.33 | no | no |
| q2017e | 2017-08-25 | -13.81 | -12.92 | -12.07 | -0.50 | -0.18 | -0.19 | -0.47 | -0.44 | -0.37 | -0.23 | -0.44 | -13.37 | -0.40 | yes | no |
| q2017f | 2017-09-07 | -8.23 | -5.98 | -4.92 | -4.99 | -4.70 | -2.91 | -4.12 | -2.35 | -3.28 | -2.39 | -2.91 | -7.10 | -3.10 | yes | yes |
| q2017g | 2017-11-06 | -5.69 | -6.53 | -7.39 | -5.93 | -6.10 | -4.89 | -5.58 | -4.72 | -4.34 | -5.40 | -6.75 | -6.11 | -5.49 | no | no |
| q2017h | 2017-12-03 | -3.27 | -3.03 | -3.11 | -2.84 | -1.86 | -1.51 | -1.91 | -2.10 | -2.71 | -2.13 | -1.79 | -3.15 | -2.01 | no | no |
| q2018a | 2018-01-03 | -1.66 | -1.68 | -2.36 | -2.05 | -1.99 | -1.57 | -2.26 | -2.92 | -1.70 | -1.53 | -0.96 | -1.68 | -1.70 | no | no |
| q2018b | 2018-03-18 | -8.06 | -4.76 | -2.76 | -1.86 | -1.80 | -0.71 | -1.19 | -0.67 | -2.16 | -1.83 | -1.85 | -4.76 | -1.80 | no | no |
| q2018c | 2018-05-09 | -3.72 | -6.05 | -3.70 | -4.52 | -3.83 | -4.09 | -3.20 | -4.86 | -4.39 | -2.63 | -4.61 | -3.72 | -4.09 | no | no |
| q2018d | 2018-06-12 | -3.73 | -5.57 | -4.33 | -5.49 | -5.00 | -5.60 | -5.78 | -5.41 | -5.62 | -4.27 | -4.72 | -4.33 | -5.41 | no | no |
| q2018e | 2018-07-10 | -1.05 | -1.00 | -1.01 | -1.04 | -0.98 | -1.25 | -1.14 | -1.11 | -1.27 | -1.32 | -1.13 | -1.01 | -1.14 | no | no |
| q2018f | 2018-10-02 | -3.39 | -3.37 | -3.54 | -2.56 | -3.19 | -2.99 | -3.49 | -1.97 | -2.32 | -2.52 | -2.07 | -3.39 | -2.52 | no | no |
| q2018g | 2018-10-28 | -1.47 | -0.79 | -0.37 | -0.60 | -0.61 | -0.42 | -0.64 | -0.46 | -0.56 | -0.19 | -0.09 | -0.79 | -0.46 | no | no |
| q2018h | 2018-11-08 | -0.52 | -0.89 | -1.70 | -1.94 | -0.92 | -0.39 | -0.16 | -0.30 | -0.12 | -0.19 | -0.17 | -0.89 | -0.19 | no | no |
| q2019a | 2019-01-03 | -2.01 | -1.27 | -1.18 | -0.63 | -0.74 | -0.87 | -1.93 | -2.57 | -3.09 | -3.38 | -3.13 | -1.18 | -2.83 | no | no |
| q2019b | 2019-10-30 | -1.36 | -2.50 | -3.90 | -4.24 | -2.97 | -4.73 | -2.80 | -4.74 | -5.64 | -4.06 | -3.94 | -3.90 | -4.40 | no | no |
| q2019c | 2019-06-18 | -2.86 | -1.46 | -2.69 | -2.46 | -2.97 | -3.57 | -3.32 | -3.99 | -5.27 | -4.63 | -4.70 | -2.46 | -4.31 | no | no |
| q2019d | 2019-06-25 | -0.33 | -1.02 | -1.22 | -0.98 | -1.75 | -1.77 | -1.57 | -2.23 | -1.89 | -1.24 | -1.64 | -1.02 | -1.70 | no | no |
| q2019e | 2019-07-24 | -7.24 | -6.12 | -2.42 | -1.81 | -2.54 | -0.71 | -0.00 | -0.01 | -0.00 | -0.00 | -0.00 | -2.42 | -0.00 | no | no |
| q2019f | 2019-09-23 | -0.97 | -1.31 | -0.72 | -0.82 | -1.30 | -1.21 | -1.40 | -0.93 | -2.65 | -1.30 | -1.92 | -0.82 | -1.35 | no | no |
| q2019g | 2019-06-10 | -1.16 | -0.62 | -0.53 | -0.28 | -0.57 | -0.13 | -0.31 | -0.21 | -0.13 | -0.25 | -0.11 | -0.53 | -0.17 | no | no |
| q2019h | 2019-11-25 | -0.27 | -0.19 | -0.18 | -0.05 | -0.13 | -0.23 | -0.13 | -1.66 | -0.55 | -0.21 | -0.20 | -0.18 | -0.22 | no | no |
| q2020a | 2020-01-13 | -1.47 | -2.00 | -1.53 | -0.96 | -0.55 | -0.83 | -0.80 | -0.63 | -1.70 | -1.42 | -2.00 | -0.96 | -1.42 | no | no |
| q2020b | 2020-03-08 | -2.16 | -2.74 | -1.69 | -2.82 | -2.10 | -3.68 | -3.02 | -2.50 | -2.24 | -2.01 | -2.11 | -2.10 | -2.24 | no | no |
| q2020c | 2020-04-20 | -0.00 | -0.00 | -0.00 | -0.00 | -0.01 | -0.00 | -0.00 | -0.00 | -0.01 | -0.00 | -0.01 | -0.00 | -0.00 | no | no |
| q2020d | 2020-09-10 | -0.07 | -0.19 | -0.37 | -0.61 | -0.51 | -0.40 | -0.16 | -0.32 | -0.29 | -0.30 | -0.43 | -0.51 | -0.30 | no | no |
| q2020e | 2020-10-27 | -1.22 | -1.30 | -1.91 | -3.38 | -2.95 | -3.03 | -3.18 | -2.98 | -5.00 | -4.25 | -4.89 | -2.95 | -4.25 | no | no |
| q2020f | 2020-08-04 | -4.99 | -3.68 | -5.00 | -4.19 | -4.68 | -4.11 | -4.43 | -3.82 | -3.50 | -3.54 | -3.75 | -4.68 | -3.75 | no | no |
| q2020g | 2020-12-01 | -0.86 | -0.19 | -0.38 | -0.28 | -0.59 | -0.47 | -2.55 | -2.47 | -2.02 | -1.75 | -2.02 | -0.38 | -2.02 | no | no |
| q2020h | 2020-12-13 | -2.67 | -3.94 | -4.08 | -5.18 | -5.51 | -4.45 | -3.81 | -4.80 | -4.06 | -3.67 | -4.56 | -5.18 | -4.06 | no | no |
| q2021a | 2021-02-15 | -1.85 | -1.78 | -1.73 | -1.30 | -1.16 | -1.28 | -1.31 | -0.72 | -1.08 | -1.23 | -0.90 | -1.28 | -0.99 | no | no |
| q2021b | 2021-03-11 | -4.42 | -4.76 | -5.29 | -4.90 | -6.07 | -4.36 | -4.16 | -4.93 | -4.89 | -3.80 | -4.69 | -4.90 | -4.79 | no | no |
| q2021c | 2021-03-23 | -7.26 | -8.04 | -7.28 | -7.07 | -7.46 | -7.20 | -7.61 | -5.24 | -5.19 | -4.09 | -4.21 | -7.20 | -4.70 | no | no |
| q2021d | 2021-03-26 | -6.68 | -6.41 | -6.80 | -8.04 | -7.35 | -6.33 | -6.70 | -6.93 | -8.32 | -8.30 | -8.61 | -7.35 | -8.31 | no | no |
| q2021e | 2021-05-07 | -4.82 | -4.73 | -5.73 | -6.33 | -6.43 | -6.20 | -5.82 | -3.44 | -1.20 | -0.65 | -0.58 | -6.33 | -0.93 | yes | no |
| q2021f | 2021-05-17 | -1.25 | -2.23 | -2.95 | -2.70 | -3.25 | -3.43 | -3.29 | -4.07 | -2.90 | -3.61 | -3.28 | -3.25 | -3.44 | no | no |
| q2021g | 2021-06-09 | -12.05 | -10.35 | -11.57 | -8.35 | -11.31 | -9.55 | -12.08 | -10.02 | -9.42 | -8.14 | -10.07 | -9.55 | -9.72 | no | no |
| q2021h | 2021-11-10 | -3.89 | -4.16 | -5.23 | -3.10 | -4.31 | -4.09 | -4.88 | -3.19 | -3.28 | -3.65 | -3.72 | -4.09 | -3.47 | no | no |
| q2022a | 2022-01-18 | -8.21 | -8.37 | -10.58 | -7.98 | -7.11 | -8.24 | -7.54 | -6.27 | -4.86 | -3.42 | -4.83 | -7.54 | -4.83 | no | no |
| q2022b | 2022-03-08 | -1.85 | -1.28 | -1.43 | -1.93 | -2.00 | -2.28 | -2.20 | -2.64 | -3.10 | -3.13 | -3.67 | -2.20 | -3.13 | no | no |
| q2022c | 2022-05-09 | -6.73 | -4.80 | -5.26 | -6.29 | -7.06 | -6.57 | -7.33 | -6.51 | -7.16 | -6.72 | -6.27 | -7.06 | -6.72 | no | no |
| q2022d | 2022-05-26 | -1.06 | -0.23 | -0.33 | -0.36 | -0.56 | -0.79 | -0.82 | -0.65 | -0.66 | -0.54 | -0.21 | -0.79 | -0.54 | no | no |
| q2022e | 2022-08-16 | -0.81 | -1.40 | -2.32 | -1.91 | -1.40 | -1.55 | -2.73 | -3.43 | -0.23 | -0.05 | -0.01 | -1.55 | -0.05 | no | no |
| q2022f | 2022-03-27 | -1.09 | -1.08 | -0.89 | -0.63 | -1.23 | -0.73 | -1.16 | -0.79 | -1.31 | -0.72 | -0.92 | -1.16 | -0.92 | no | no |
| q2022g | 2022-09-15 | -1.20 | -2.27 | -2.03 | -2.21 | -2.37 | -0.75 | -1.55 | -1.22 | -0.92 | -1.18 | -0.83 | -1.55 | -0.92 | no | no |
| q2022h | 2022-11-11 | -0.43 | -0.39 | -0.82 | -0.93 | -1.93 | -0.92 | -1.84 | -1.07 | -0.64 | -1.66 | -0.71 | -1.84 | -0.71 | no | no |
| q2023a | 2023-01-24 | -3.16 | -3.54 | -2.75 | -3.04 | -3.09 | -1.81 | -1.57 | -1.98 | -2.62 | -1.45 | -2.04 | -1.81 | -1.74 | no | no |
| q2023b | 2023-02-06 | -3.07 | -2.86 | -3.05 | -5.02 | -5.10 | -5.01 | -6.33 | -6.41 | -6.96 | -3.21 | -2.41 | -6.33 | -2.81 | yes | no |
| q2023c | 2023-08-01 | -6.26 | -6.17 | -7.18 | -6.69 | -7.59 | -8.14 | -7.14 | -6.23 | -3.07 | -3.24 | -3.76 | -7.14 | -3.50 | yes | yes |
| q2023d | 2023-02-03 | -8.09 | -8.03 | -8.20 | -9.21 | -11.68 | -9.55 | -9.98 | -8.07 | -8.78 | -7.83 | -7.38 | -9.55 | -7.60 | no | no |
| q2023e | 2023-05-01 | -10.86 | -9.49 | -8.39 | -9.55 | -9.91 | -9.94 | -10.89 | -10.76 | -11.81 | -12.33 | -12.31 | -10.76 | -12.32 | no | no |
| q2023f | 2023-06-09 | -1.51 | -1.86 | -1.40 | -1.71 | -0.96 | -1.40 | -1.61 | -1.95 | -2.20 | -1.97 | -2.14 | -1.61 | -2.06 | no | no |
| q2023g | 2023-10-11 | -0.89 | -1.41 | -0.97 | -1.26 | -1.02 | -1.41 | -3.05 | -2.28 | -1.45 | -1.62 | -1.78 | -2.28 | -1.70 | no | no |
| q2023h | 2023-12-18 | -0.34 | -0.27 | -0.23 | -0.18 | -0.24 | -0.19 | -0.57 | -0.21 | -0.62 | -0.25 | -0.16 | -0.21 | -0.21 | no | no |
| q2024a | 2024-01-05 | -4.53 | -2.29 | -3.73 | -4.17 | -4.50 | -3.32 | -2.37 | -2.36 | -2.54 | -2.82 | -3.03 | -2.37 | -3.03 | no | no |
| q2024b | 2024-01-09 | -1.94 | -2.82 | -2.37 | -1.39 | -0.66 | -0.43 | -0.67 | -1.80 | -0.92 | -1.21 | -0.79 | -0.92 | -0.79 | no | no |
| q2024c | 2024-08-06 | -4.39 | -4.09 | -3.87 | -5.07 | -4.26 | -4.51 | -5.62 | -3.20 | -3.57 | -4.01 | -3.03 | -3.57 | -3.03 | no | no |
| q2024d | 2024-02-19 | -6.81 | -7.52 | -7.86 | -9.02 | -8.68 | -8.31 | -7.77 | -7.38 | -7.15 | -8.21 | -6.86 | -7.38 | -6.86 | no | no |
| q2024e | 2024-07-23 | -0.63 | -0.31 | -0.74 | -0.74 | -0.48 | -0.60 | -1.13 | -1.60 | -1.93 | -1.23 | -1.45 | -1.60 | -1.45 | no | no |
| q2024f | 2024-07-19 | -10.68 | -11.05 | -11.62 | -12.51 | -12.32 | -12.23 | -11.93 | -11.08 | -10.67 | -10.23 | -10.54 | -11.08 | -10.54 | no | no |
| q2024g | 2024-08-13 | -9.07 | -8.53 | -7.65 | -6.47 | -6.59 | -6.32 | -7.03 | -6.43 | -6.55 | -4.64 | -5.13 | -6.55 | -5.13 | no | no |
| q2024h | 2024-08-24 | -0.10 | -0.23 | -0.93 | -2.88 | -4.16 | -5.14 | -5.25 | -3.51 | -4.08 | -4.28 | -3.80 | -4.08 | -3.80 | no | no |
| q2025a | 2025-01-07 | -2.62 | -3.73 | -3.81 | -3.07 | -3.19 | -3.61 | -2.99 | -3.27 | -2.32 | -1.92 | -2.97 | -2.32 | none | not usable | no |
| q2025b | 2025-01-10 | -2.86 | -4.50 | -5.48 | -5.58 | -6.30 | -7.69 | -7.46 | -6.76 | -6.17 | -6.34 | -5.73 | -6.34 | none | usable | no |
| q2025c | 2025-04-28 | -0.16 | -0.22 | -0.14 | -0.19 | -0.31 | -0.15 | -0.19 | -0.41 | -0.26 | -0.16 | -0.11 | -0.26 | none | not usable | no |
| q2025d | 2025-07-16 | -1.28 | -1.25 | -3.34 | -1.19 | -2.03 | -0.52 | -0.86 | -0.75 | -2.23 | -2.17 | -1.43 | -2.17 | none | not usable | no |
| q2025e | 2025-08-25 | -2.76 | -2.08 | -1.91 | -1.93 | -1.30 | -1.50 | -1.95 | -2.00 | -2.44 | -2.37 | -1.79 | -2.37 | none | not usable | no |
| q2025f | 2025-02-21 | -4.77 | -2.79 | -3.08 | -2.31 | -1.75 | -1.82 | -1.26 | -3.59 | -3.10 | -3.78 | -3.40 | -3.59 | none | usable | no |
| q2025g | 2025-07-29 | -5.21 | -5.38 | -3.28 | -3.67 | -4.03 | -3.35 | -6.54 | -2.66 | -3.97 | -3.76 | -2.95 | -3.76 | none | usable | no |
| q2025h | 2025-08-22 | -3.33 | -1.61 | -1.80 | -1.41 | -1.12 | -0.80 | -1.27 | -1.19 | -1.22 | -0.98 | -1.60 | -1.19 | none | not usable | no |

### 8.10 What waits for the owner

1. **The outcomes.** 2016 passes; 2015 and 2017 to 2024 are too weak; none fails. 2016 passes at the edge: exactly
   3 informative probes and 1 flag (q2017f, read as drift). Too weak means the probes could not tell, not that the
   vintage leaked. Nothing is replaced. What to do with too weak is the owner's call, for
   example accept the published vintages on this and section 5's evidence, or add a check with more power.
2. **The q2023c flag on 2022** (Fitch, one step a year early), and whether to look closer.
3. **Power.** Only 7 of 72 probes were informative. More probes would help only in the same proportion, about one
   in ten. A different measure could help more, for example events with longer coverage, or a wider choice of
   answers.
4. **2026** is still not covered (judge finding 5 of the first review).

## 9. The owner's decision (21 Nov 2026, New York; 22 Nov where the owner is)

The owner accepted all 11 vintages as published ("Accept, go on"). No vintage is replaced, and the rule in
`reader/vintage.py` stays as it is. What that rests on:
- Only the 2016 vintage is supported by evidence: it passed the stronger probes (section 8.9), at the edge.
- The other nine vintages that read news (2015 and 2017 to 2024) are too weak to judge. The probes could not tell
  whether they knew the year they read. None failed, but that is not evidence they are clean.
- The flag of q2023c (Fitch) on the 2022 vintage was seen and accepted.
- The 2014 vintage reads no news and needs no outcome.
- 2026, which the 2024 vintage also reads, was never checked.
This is a known limit of M2. It is recorded in `research/m2_kickoff.md` too.

## 10. Two planned checks downstream (21 Nov 2026; plans only, nothing run)

The owner asked for two checks that would catch a vintage leak through results ("whatever is better, your call",
via the lead). Both are fixed here, with what counts as a warning, before any result exists. Neither has run. The
metric is PLAN's primary one: daily rank IC (`eval/metrics.daily_rank_ic`). The news effect on a day is the live
agent's IC minus the price-only twin's IC that day (PLAN H3), with Newey-West standard errors as in PLAN.

### 10.1 The older-vintage rerun (after the main run; about 14 more hours on the laptop)

- **What.** Read every story again with the vintage one year older than the rule's: a story from New York year Y by
  Y-2, not Y-1 (2016's stories by 2014, the 2025 and 2026 stories by 2023). That vintage was trained a full year
  before Y, so it can't know year Y's events even if the rule's vintage leaked a few weeks or months.
- **How.** The same `reader/embed.py` with the offset, into `D:\chrono-data\reader_older` and its own table. The World
  refuses any vintage but the rule's, so this needs one planned change: a `vintage_offset` the World accepts only for
  this check, with its own test. Then rerun the M3 agent unchanged (same code, seeds and dates) on the older
  embeddings, next to the run on the rule's embeddings.
- **Warning.** Both of these: (a) the news effect with the older vintage is less than half the news effect with the
  rule's; (b) the paired daily difference in IC (the rule's run minus the older run) is above zero, one-sided at 5%.
  If the news effect isn't above zero in the first place, the check says nothing, and the report says so.
- **Expected without a leak.** A small drop, since an older model knows less recent language. That is why a drop is
  a warning, not a fail. The owner decides what a warning means.
- **Cost.** About 14 hours, like the main run. It starts only when the owner says, after M3 has a result to compare.

### 10.2 The switch-day check (in M3's evaluation; no new run)

- **What.** Each year's stories switch to a new vintage on 1 January (New York). A vintage that leaked into the
  start of the year it reads would read early-year headlines better than later ones. So the news effect would be
  larger right after each switch.
- **How.** For each year, split its sessions into the first 20 and the rest. Compute the news effect for each day.
  Then take the mean over all years' first-20 days minus the mean over all years' other days, with Newey-West
  standard errors over the pooled days.
- **Warning.** Either of these: (a) the pooled difference is above zero, one-sided at 5%; (b) in at least half of
  the years, the first-20 mean is above the rest of that year's mean by more than two of its standard errors.
- **Limits.** The news memory's half-life is 5 sessions, so the first sessions of a year still lean on late-December
  stories, read by the year before's vintage. The dev years give only a few switches, so the check has little power
  there; it is repeated on the sealed years when those open. A January effect in returns would show here too, which
  is why the measure is the news effect against the price-only twin, not IC alone.
