# Judge: M3 books, costs and test statistics (23 Nov)

Scope: `sim/simulator.py` (`Simulator.step`, `run_many`, `replay`, `_fresh`), `eval/metrics.py`, `eval/stats.py`,
`eval/switch_day.py`, `agent/baselines.py`, the hold and band lines of `agent/track_a.py` (411-468), the placebo's
shuffle (`agent/placebo.py`), the DSR lines of `eval/report.py` (174-184), `research/audit/m3_report_judge.md`,
`research/audit/cutoff.md` 10.2, and the dev report's numbers. Data read: `D:\chrono-data\store\labels.parquet` and
the compare pass in `D:\chrono-data\runs\m3_dev\compare` (live, price_only, placebo_1 to 5, random_1 to 5,
momentum, reversal, equal_weight, the three frozen twins). Only ICs, t values, Sharpe ratios, turnover and counts
were printed. No `.env`, nothing fixed, nothing committed.

Scripts (rerun with `D:\venvs\chrono-trader\Scripts\python.exe <script>`; each takes 15 s to 2 min):
- `C:\Users\syedh\AppData\Local\Temp\claude\a742097078b03236\6cc4007d-fcb6-47d2-8b04-650f79c5109d\scratchpad\s3_ic_tstats.py`:
  daily IC, autocorrelations, t under each lag, seed SDs, the paired gaps and the switch day under each lag.
- `C:\Users\syedh\AppData\Local\Temp\claude\a742097078b03236\6cc4007d-fcb6-47d2-8b04-650f79c5109d\scratchpad\s3_books_and_null.py`:
  the cost checks, turnover on trade days and between them, a null calibration of the t (2,000 random rankings on
  live's own stock-days with the real labels), the chance of the seed SDs, the DSR's V, and the placebo's counts.
- `C:\Users\syedh\AppData\Local\Temp\claude\a742097078b03236\6cc4007d-fcb6-47d2-8b04-650f79c5109d\scratchpad\s3_seed_detail.py`:
  correlation of the seeds, month-to-month persistence of each seed's own part, IC by year, live minus the
  placebos' mean.

Result: 0 high, 2 medium, 3 low, 6 info.

## The question: are the Newey-West t values too large?

No. The t values are calibrated, and no lag or sample choice changes a dev conclusion.

1. **The label is one session.** Labels run from one official open to the next (calendar gap 1 to 4 days, median
   1, `labels.parquet`), and the ridge's target is the same one-day return, demeaned (PLAN L561). Nothing overlaps.
2. **The daily IC has no memory.** Live's autocorrelation is -0.066, -0.033, -0.003, 0.009 and 0.051 at lags 1, 5,
   10, 21 and 63. Every series checked (live, price-only, 5 placebos, 5 randoms, momentum, reversal, 3 twins) has
   |acf| at most 0.12 at those lags, and the sum of the first 63 autocorrelations lies between -0.38 and 0.32,
   which is noise for 753 days (se of one acf about 0.036).
3. **A seed's own error does not last months.** Each placebo minus the 5 placebos' mean has daily acf under 0.07 at
   lags 1 to 63. Its monthly means (36 months) have lag-1 autocorrelations 0.13, 0.06, -0.04, -0.26 and -0.12
   (se about 0.17). A monthly refit on running sums gives each seed lasting coefficients, but their effect on the
   IC is a constant offset over the whole run, not autocorrelation. No HAC lag can see a constant offset within one
   run; only the spread across seeds can.
4. **The t is calibrated on the real data.** 2,000 random rankings on live's own stock-days with the real labels
   give an SD of the lag-6 t of 1.021, with 5.3% of |t| above 1.96. Monthly means give 1.042 and 6.0%. Lag 63
   gives 1.109 and 8.1%: the long lag over-rejects, so it is the worse choice, not the safer one.
5. **The seeds are nearly independent, so an SD near 1 is the expected value, not an upper bound.** The placebos'
   daily ICs correlate 0.01 to 0.20 with each other and 0.04 to 0.14 with live; live correlates only 0.23 with
   its price-only twin. The shared price features carry little of the ranking; the (shuffled) news features carry
   most of it. For 5 independent N(0, 1) draws, P(SD >= 1.59) = 0.039 and P(SD <= 0.75) = 0.31. Pooling the two
   groups (10 seeds), the within-group SD is 1.24 and P(SD >= 1.24) = 0.14.
6. **Why seed 5 beats live.** Two causes fit the numbers, and five seeds cannot tell them apart: chance (about 1 in
   26), or real seed-to-seed differences in what each shuffle hands the ridge (the 95% interval for the true SD
   from a sample SD of 1.59 with 4 degrees of freedom is about 0.95 to 4.6). Seed 5 is ahead in all three years
   (0.0098, 0.0208, 0.0086 against live's 0.0038, 0.0143, 0.0047), so it is not one stretch. Paired against live,
   seed 5 is t -0.72 (lag 6), -0.81 (lag 63): no difference.

The t table (753 IC days, 2017-01-03 to 2019-12-30):

| series | t lag 6 (used) | t lag 21 | t lag 63 | t monthly (36) | t iid | acf 1 | acf 21 | acf 63 |
|---|---|---|---|---|---|---|---|---|
| live | 1.38 | 1.29 | 1.28 | 1.28 | 1.31 | -0.07 | 0.01 | 0.05 |
| price_only | 0.10 | 0.10 | 0.09 | 0.17 | 0.09 | -0.04 | -0.02 | 0.02 |
| placebo_1 | -1.26 | -1.28 | -1.08 | -1.26 | -1.23 | -0.04 | 0.01 | -0.02 |
| placebo_2 | -1.40 | -1.37 | -1.45 | -1.23 | -1.41 | -0.03 | -0.04 | -0.03 |
| placebo_3 | 0.73 | 0.69 | 0.61 | 0.70 | 0.69 | -0.02 | 0.02 | -0.03 |
| placebo_4 | 0.15 | 0.14 | 0.15 | 0.31 | 0.16 | -0.04 | 0.01 | -0.00 |
| placebo_5 | 2.47 | 2.82 | 3.44 | 2.83 | 2.46 | 0.02 | -0.05 | 0.00 |
| SD of 5 placebo t | 1.59 | 1.71 | 1.93 | 1.68 | 1.58 | | | |
| SD of 5 random t | 0.75 | 0.72 | 0.75 | 0.75 | 0.74 | | | |

Longer lags make the placebo spread larger, not smaller, so a too-short lag is not the cause.

The dev conclusions under each t:

| statistic | report (lag 6) | lag 21 | lag 63 | monthly means |
|---|---|---|---|---|
| live IC | 1.38 | 1.29 | 1.28 | 1.28 |
| news effect, live minus price-only | 0.74 | 0.71 | 0.67 | 0.65 |
| frozen-twin gap, end of 2016, all years | 2.61 | 2.62 | 3.17 | 2.30 |
| switch day, pooled p | 0.621 | 0.625 | 0.633 | n/a |

None changes. The report should keep the Newey-West t with the 1994 lag (6 for 753 days); a monthly-means t is a
fair robustness column. The switch day reproduces exactly (difference -0.0107, se 0.0345, p 0.6213).

## Medium

**S3-1. The "matched" baselines are not matched on turnover, so the after-cost comparison favours live.**
`research/m3_kickoff.md` L483-484 and L540-541 say the baselines hold as long as the chosen trial "so turnover is
matched"; `agent/baselines.py:16-18` says the same; `research/m3_dev_runs.py:137-138` builds them with `hold=5` and
no band (the owner ruled the band is Track A's alone). The band halves live's trades: daily turnover is live 0.39,
random 0.65 to 0.67, reversal 0.64, momentum 0.12 (report, "Matched baselines"). Over 2017 to 2019 the cost drag
in log equity is live 0.147, random_1 0.250, reversal 0.242, momentum 0.046 (`s3_books_and_null.py`, part 1). It
changes a ranking: before costs random_5 (Sharpe 0.51) beats live (0.18); after costs live (-0.24) beats every
random seed (best -0.39). Every book has about 152 trade days in 754, so the hold is matched; only the band is not.
PLAN L583-589 and L600 ("matched baselines"). Fix: give the baselines the same band 15 rank rule, or drop "so
turnover is matched", label the after-cost rows "turnover not matched", and read the baselines before costs.

**S3-2. The placebo comparison has no single rule across seeds.** The report tests live against each placebo seed
separately (5 paired t from -0.72 to 1.94, "Reading" table), and PLAN L347 and L351 do not say how seeds combine
for H3. With seed offsets that the data cannot rule out (item 6 above), "beats the placebo" depends on the seed
picked. One test against the mean of the 5 placebos gives mean 0.0068, t 1.14 (lag 6) and 1.15 (lag 63)
(`s3_seed_detail.py`). A paired Newey-West t also treats each seed's offset as fixed, so it does not carry the
between-seed variance. Severity medium because it could decide H3 on the sealed years; no dev conclusion changes.
Fix: in PREREG, test live against the daily mean of the seeds' ICs, one test, and show each seed as spread only.

## Low

**S3-3. The deflated Sharpe's V is mostly cost, not noise.** `eval/report.py:176-180` takes V from the 8 trials'
Sharpe ratios after costs. Those Sharpes track turnover (correlation -0.86 over the 8 trials), so V reflects how
much each policy trades, a known difference, not the luck of the draw that Bailey and Lopez de Prado's V stands
for. With after-cost V the bar sr0 is 0.83 a year and DSR 0.032; with before-cost V the bar is 0.46 and DSR 0.11;
live before costs against before-cost trials gives DSR 0.32 (`s3_books_and_null.py`, part 4). N = 8 is right
(T04 was dropped before any run: `m3_kickoff.md` L456, and no log names T04). The conclusion, no evidence of skill
after selection, holds under every choice. PLAN L596. Fix: say in the report which Sharpes give V and why, or take
V from the before-cost Sharpes.

**S3-4. The placebo keeps each company's number of news links.** `agent/placebo.py:42` permutes the entity column
within a decision's group, which reorders one multiset, so each company keeps exactly as many links that day
(made-up demo in `s3_books_and_null.py`, part 5: counts {A: 3, B: 1, C: 2} under every seed). `news_count` and
`news_none` (PLAN L552-553) are then nearly unchanged and only the content moves. The docstring (lines 8-10) says
"the same amount of news each day, attached to the wrong stocks", which reads as if counts move too. So the placebo
tests what the news says, not whether there is news. Not a bug if intended; it changes what H3 means. For judge 1
and the skeptic. Fix: say so in the docstring and the report, or also permute whole stories across companies.

**S3-5. Random seeds lean negative, with no mechanism found.** The 5 random-ranking seeds have mean t -1.05; their
daily ICs correlate 0.019 on average, and the t of their averaged daily IC is -2.30 (two-sided p about 0.02).
Scores come from `default_rng([seed, date])` (`agent/baselines.py:101`), independent of labels, and the null
simulation on the same stock-days (part 3) is centred and calibrated. Most likely chance. Fix: none needed; to
settle it, score 50 random seeds offline against the stored labels (cheap, no run).

## Info

**S3-6. The frozen-twin gap is the twin's loss more than live's gain.** The end-of-2016 twin has IC -0.0102 (t
-1.89) over 2017 to 2019, so most of the 0.0179 gap (t 2.61) is the twin doing badly; live alone is 0.0076 (t
1.38). Worth one sentence in the reading of H2's dev analogue.

**S3-7. "Hold 5" keeps weights, not shares.** On the 602 days between trades, `Simulator.step` re-weights each
holding to its target times equity, which costs 0.027 of equity a day, 5.5% of live's turnover (random 3.3%,
reversal 3.8%, momentum 20%). All books are charged the same way, so it is fair; PLAN L575 does not say which.

**S3-8. The earlier judge's "under 1%" is about 4%.** `m3_report_judge.md` L67-68: on iid noise the difference's se
over the first-20 mean's se is sqrt(1 + 20/231) = 1.042. The reading of "its standard errors" in 10.2 (b) is
therefore about 4% stricter. No year is near the line (largest difference/se is 1.01, 2018). No change needed.

**S3-9. Regime t values treat days far apart as neighbours.** `eval/metrics.py:236` runs `nw_mean` on the regime's
days in order, though they are not contiguous. With no IC autocorrelation (item 2) this costs nothing. Reported,
not tested (PLAN L599).

**S3-10. Sharpe is over zero with no borrow fee or short rebate.** The long-short book holds about 1.0 of equity in
cash plus short proceeds and earns nothing on it (report header, the owner's ruling of 23 Nov). Fine for the dev
report; note it next to SPY, whose Sharpe is also over zero.

**S3-11. The random-group premise.** The brief's expectation that seeds sharing price features give an SD of 1 or
less does not hold here: live's ranking correlates only 0.23 with its price-only twin, so the embeddings dominate
the ridge's scores, and differently shuffled embeddings give nearly independent rankings.

## Checked and right

- **Costs per side, both legs.** `Simulator.step` charges `abs(change) * rate` on every trade, long or short, and
  on the exit sale at the last close (`sim/simulator.py:78-79, 96-97`). In the saved runs, `cost` equals `traded`
  times the rate to 5e-18 on every row at 0, 5, 10 and 20 bps, for 8 books. The log drag is linear in the rate
  (live 0.1468, 0.1469, 0.1471 per 5 bps at 5, 10 and 20). Turnover counts buys plus sells over pre-trade equity.
- **Replay is exact.** For live, long-only, random_1, momentum, reversal, equal weight, placebo_5 and the 2016 twin,
  the run's equity rows equal the 5 bps replay exactly. The twin's replay has 754 rows and starts fresh on its join
  day. A None and an empty target both go flat, in the run and the replay alike.
- **Books.** Long-short gross 1.999 and long-only 1.000 on average from 2017; long-short holds 10 at plus and 10 at
  minus 0.1 (`track_a.py:427-431`), dollar-neutral (PLAN L573-574). Returns use the previous row's equity, so 2017
  starts from 2016-12-30.
- **Matched hold.** Baselines and T09 count sessions the same way (`baselines.py:81-85`, `track_a.py:459-466`):
  trade, then hold 4 sessions; from `trade_from` with the counter reset before it. Trade days: live 152, random_1
  151, reversal 152, momentum 146 (momentum's equal targets on some trade days show as no change).
- **Sharpe and returns.** Mean over sd (ddof 1) of daily simple returns times sqrt(252); annual return geometric
  over n/252 years (`stats.py:82-95`). Days 754 (251 + 251 + 252).
- **Lag rule.** floor(4 (753/100)^(2/9)) = 6 (`stats.py:20-22`).
- **Sample.** Every IC series in the seed spread and the paired tests covers the same 753 days, 2017-01-03 to
  2019-12-30, with labels ending by 2019-12-31 (`m3_dev_runs.py:48-51`).
- **DSR.** N = 8 from the ledger (T01 to T03, T05 to T09; T04 dropped before any run). Daily Sharpes on both sides.
- **Switch day against cutoff.md 10.2, word for word.** "For each year, split its sessions into the first 20 and the
  rest": calendar sessions, `switch_day.py:188-192`. "Compute the news effect for each day": live IC minus
  price-only IC (10.2 "Limits"), line 186. "The mean over all years' first-20 days minus the mean over all years'
  other days, with Newey-West standard errors over the pooled days": the slope on a dummy with an intercept, HAC
  over pooled days in date order, line 203. (a) one-sided 5%: line 206. (b) "in at least half of the years, the
  first-20 mean is above the rest of that year's mean by more than two of its standard errors": per-year fit, `d >
  2 se` strict, `2 x count >= years`: lines 197 and 207. Years 2017 to 2019 only (`report.py:75, 209`). Reproduced
  from the stored ICs.
- **The earlier judge's fixes hold.** (1) N is `max(ledger, Sharpes shown)` with a warning under 2
  (`report.py:179-184`). (2) Switch years are a parameter, default 2017 to 2019 (`report.py:75, 209`). (3) The
  replay test now runs with `freeze=("rev",)` across a year end (`tests/test_report.py:167-172`). (4) Vol uses an
  expanding median (`metrics.py:212`). (5) The shock walk starts at SPY's first close (`metrics.py:216`). (6) Trend
  tests a missing prior close (`metrics.py:211`). (7) Sector tilt is shown for both books. (8) and (11) The normal
  p and the short lag are in the report header (`report.py:88-90`). (9) The no-switch test draws noise per day
  (`tests/test_report.py:327`). (10) The vol test checks the median line (`tests/test_report.py:250`).
