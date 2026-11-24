# Chrono-trader: pre-registration of the sealed run (Track A)

Written on 23 Nov 2026 (New York), before any sealed outcome was run, read or computed. It fixes, in words, every test,
check and decision rule for the sealed years. Its SHA-256, of its bytes as committed (LF line endings;
`.gitattributes` marks it `-text`, so every checkout keeps those bytes), goes into `seal.lock` (PLAN 5.5 item 4,
9.12), so any change after the seal breaks it. The plan behind it is `research/m4_kickoff.md` (section 3 and the
owner's decisions of 23 Nov) and `PLAN.md` 5.5. It was checked by a skeptic before the seal
(`research/audit/m4_prereg_skeptic.md`).

## 1. What is sealed

- **The agent.** Track A, configuration T09: `{"band": 15, "hold": 5}` on top of the M3 defaults
  (`research/m3_dev_report.md:4`). The frozen trial plan's SHA-256 is
  `4a9a45a1238aad3b704a18f27c9bac046e13bbadf981ff642fc3d78986861e2f` (`research/m3_dev_report.md:3`). Its features
  are the code of `agent/track_a.py` at the code commit below. Nothing about the agent changes for the sealed run.
- **The dev check.** Before the seal, T09 reruns on the dev years at the code commit (`research/m4_t09_check.py`, M4
  step 2). Its decisions must equal step 6's T09 run day by day. If they differ, nothing is sealed until the owner
  decides, in a dated note, what the difference means.
- **The code commit:** `7b9a138542e14667954822cc18024d575aed60aa`.
  The sealed commit, which `seal.lock` records, is that commit plus this file and nothing else. This file can't name
  the sealed commit, since the commit holds this file.
- **The settings hashes** (`sim.simulator.settings_many`, as `python research/m4_sealed_run.py settings` prints them):
  - main: `755dcf398dcb34975ae84fa65518190d9504d591057ff80591b79f5ac74ee3a5`
  - older_vintage: `380ebc4f7809de2f15b4f117d1a016514978a0ba0b2233a05dea656dbada0941`

  Each covers the chosen configuration, every agent's class and parameters, the costs, the embedding window, the
  dates, the part, and a fingerprint of the data (each store table's size and Parquet footer hash, and the
  embeddings' arrays record: row count, story ids' hash, width and Parquet footer, not a hash of the vectors).
- **The scoring code.** `research/m4_sealed_report.py` at the code commit. It is tested on made-up records before the
  seal, it computes every number in sections 3 to 6, and it runs unchanged on the sealed outputs (PLAN 5.5, C-1). Its
  output is the result of record. If it fails, or a bug in it is found, after any sealed output is read, its numbers
  (or its failure) stay in the report, and a corrected writer's numbers go beside them in a dated note, never instead.
- **The dates.** The sealed years are the sessions from 2020-01-02 to 2026-10-28, 1,715 sessions
  (`reference/split.json`). The end is the store's last day, not the last trading day before the seal, by the owner's
  decision 1 of 23 Nov (`research/m4_kickoff.md`). Each part runs from 2016-01-04 to 2026-10-28, so the agent lives
  through the warm-up and the dev years first, as on dev. The sessions between 2026-10-29 and the forward test's
  first day are scored by neither, and the report says so.
- **IC days:** the sessions from 2020-01-02 whose label ends by 2026-10-28. **Book returns:** 2020-01-02 to 2026-10-28.

## 2. The runs

All runs come from `research/m4_sealed_run.py` at the sealed commit, with the seal checked by `sim/seal.py`.
- **Part "main"** (`run main`): live (T09), live long-only, the price-only twin (`news: false`), the placebo with
  seeds 1 to 5, the random ranking with seeds 1 to 5, 12-1 momentum, 5-day reversal and equal weight, in one pass.
  The live agent gets a frozen twin at the first session of each new year (`live_frozen_<year just ended>`).
- **Part "older_vintage"** (`run older_vintage`): the live agent alone, reading every story by the vintage a year
  older than the rule's (`D:\chrono-data\reader_older`, `vintage_offset` 1). It reuses main's price-only twin, which
  reads no news.
- **Order.** Main first, then older_vintage, then the replays at 0, 5, 10 and 20 bps of every book in both parts
  (`run replay`: `sim.simulator.replay`, with that part's sealed settings, saved outside git), then the writer, then
  `ledger`.
  Nobody reads a sealed output until both parts and the replays have run.
- **Once.** Each part runs once. A part refused by the seal before it starts has not run. A part that starts and stops
  before its last session is void. A void part is rerun once with `--again`, at the same sealed commit and settings,
  before anyone reads any sealed output. That rerun counts as another trial (PLAN 9.12) and is the part's result of
  record. If the rerun is void too, the part is void. A complete run is one in which both parts reached their last
  session.
- **A bug after the seal.** If a bug is found after the seal and before any part has started, the seal may be redone
  once: `seal.lock` goes to the Recycle Bin in its own commit, the fix is committed, this file's three filled values
  are updated and nothing else in it changes, and a new lock is written. A dated note records the bug, the fix and both
  locks. Once any part has started, a fix means a second run with `--again` under a new seal. The first run stays the
  result of record, and the second is reported beside it, never instead of it.
- **Costs.** 5 bps per side for every after-cost number (`sim/simulator.py`, `COST_BPS`).

## 3. The hypotheses and their tests

The metric is the daily rank IC: each day's Spearman correlation between the agent's predictions and the realized
open-to-open labels across the stocks it predicted, on days with at least 10 such stocks (`eval.metrics.daily_rank_ic`).
Every test in this section is one-sided, on a daily series in date order, with Newey-West standard errors and lag 6,
passed as `eval.stats.nw_mean(x, lag=6)`, as the owner decided on 23 Nov (`research/m4_kickoff.md`, decision 5). Six is
what Newey and West's (1994) rule gave on the dev years' 753 days. The p-value is 1 minus the normal CDF of t. A paired
test uses the days on which both of its series have an IC.

- **H2, the main claim: it learned.** Live's daily IC minus the IC of the twin frozen at the end of 2019
  (`live_frozen_2019`, which trades from 2020-01-02), on the IC days. Mean above zero.
- **H1: skill.** Live's daily IC on the IC days. Mean above zero.
- **H3: reading helped.** One hypothesis with two paired tests. Its p-value is the larger of the two tests' p-values,
  so Holm rejects H3 only when both tests are at or below H3's bound:
  - live's daily IC minus the price-only twin's; mean above zero;
  - live's daily IC minus the placebo's daily mean IC, where the placebo's daily IC is the mean of the 5 seeds' ICs
    on days all 5 have one (M4 entry rule 3). Mean above zero. Each seed is shown as spread only, never tested alone.
- **The correction.** Holm's method over the three p-values (H1, H2, H3) at a family level of 5%: sort them from
  smallest to largest; the smallest must be at most 0.05/3, the next at most 0.05/2, the last at most 0.05; stop at the
  first that fails, and every hypothesis from there on is not rejected. "Holds" means rejected by Holm.
- **Numbers.** Every comparison uses the unrounded double-precision value. In Holm, a p equal to its bound passes. A
  NaN p (fewer than 2 days, or a zero standard error) counts as 1. Ties in Holm's sort don't change the result.
- **Nothing else is tested.** The report shows, without tests: Sharpe before and after costs, return, volatility,
  maximum drawdown, turnover, beta and sector tilt; the long-short and long-only baselines; the other frozen twins'
  gaps by year; IC by quarter; results by regime and after big shocks; coefficient life; each seed; and a robustness
  column of H1 to H3's t-statistics with lag 7 (the 1994 rule's lag for the sealed length), lag 21 and on monthly
  means (lag 0). The older-vintage check shows a p-value only for its test (b). None of these changes an outcome.

## 4. The baselines (M4 entry rule 2, decision 4)

As on dev: the random ranking, momentum and reversal hold 5 sessions with no band; equal weight rebalances every
session; SPY is bought and held. They are compared with live **before costs**. The after-cost rows are shown, marked
as not turnover-matched, since only live has the band. Sharpe is over zero, with no borrow fee or short rebate.

The deflated Sharpe of the live long-short book after 5 bps, over 2020-01-02 to 2026-10-28, uses
`eval.stats.deflated_sharpe`. Its number of trials is 8 plus the number of `--again` runs of the main part. Its trial
Sharpes are the 8 dev trials' daily after-cost Sharpes over the dev years (2017-01-03 to 2019-12-31), exactly as
`research/m3_dev_report.md` computed them (var_trials 0.0013 there, rounded). The writer recomputes that variance
from the dev runs and stops if it differs from the dev report's at its printed precision. Beside it, without a
verdict, the other two versions the M3 review named (S3-3, `research/review_m3_2026-11-23/judge_stats.md:106-107`):
the after-cost book against the dev trials' before-cost Sharpes, and the before-cost book (the sealed live book at 0
bps) against the dev trials' before-cost Sharpes. The dev trials' before-cost Sharpes come from their 0 bps replays.

## 5. The two leak checks

Both measure the news effect: on each IC day, live's daily IC minus the price-only twin's. Neither is in the Holm
family, and each keeps the lag its code uses (Newey and West's 1994 rule for its series' length, `eval.stats.nw_lag`).
Each is reported as "warning" or "no warning", never as "passed". "At one-sided 5%" means p below 0.05, as the code has
it.

- **The switch-day check** (`research/audit/cutoff.md` 10.2, `eval/switch_day.py`), on the switches of 1 January 2020
  to 2025: for each of those years, its first 20 sessions against the rest. Warning if (a) the pooled difference,
  first 20 minus the rest, is above zero at one-sided 5%, or (b) in at least half of the years counted (those with
  days in both parts, as `eval/switch_day.py` counts them; 3 of 6 when all six count), the first-20 mean is above the
  rest of that year's by more than two of its standard errors. 1 January 2026 is not a vintage switch (the 2024
  vintage reads both 2025 and 2026), so 2026 is shown apart and is not in the rule.
- **The older-vintage check** (`cutoff.md` 10.1 with M4 entry rule 1). Each of its three series is a paired daily
  difference on the days both of its series have an IC, as on dev (`research/m3_older_vintage.py:108-110`): the rule's
  news effect on live and price-only days, the older news effect (live_older_vintage's IC minus the price-only
  twin's) on those two's days, and the difference in (b) on live and live_older_vintage days. Every mean and t comes
  from `eval.stats.nw_mean` with its default lag. The gate: the rule's news effect has a mean above zero (the point
  estimate, not a test). If the gate is closed, the check is "not informative", and the report says so. If it is
  open, warning if both (a) the older news effect's mean is less than half the rule's, and (b) the paired daily
  difference, live's IC minus live_older_vintage's, is above zero at one-sided 5%. When the rule's news effect has a
  t below 1.645, the report adds a power note: the check could not have seen a small leak.
- **What a warning means** (decision 3). A warning in either check means H3 is not claimed as skill from reading,
  whatever its p-value. Every number is still reported. A warning leaves H1 and H2 as they are.

## 6. Outcomes

- **Leak tests.** The full suite, with `CHRONO_SLOW_LEAKS=1` so no leak test is skipped, passes on the clean tree at
  the code-plus-PREREG commit before `seal.lock` is written, and again at the lock's commit before the sealed run
  starts (M4 step 4). If either fails, no part runs, and the re-seal rule in section 2 applies.
- **Success:** both parts complete, H2 and H3 both hold after Holm, and neither leak check warns.
- **H3 not claimed:** a complete run where H2 and H3 hold but a leak check warns is not a success. Its outcome is
  reported as "H2 held; H3 held but is not claimed, because the [check] warned".
- **Failure:** a complete run in which H2 or H3 does not hold. "A clean 'it didn't learn' is also a valid result,
  reported as-is" (PLAN 5.5).
- **Void:** if main is void, H1 to H3 and both leak checks are not tested, and the outcome is Void. If older_vintage
  is void, its check is reported as "not run", and the outcome can't be Success: a run in which H2 and H3 hold and the
  switch-day check doesn't warn is then reported as "Not a success: H2 and H3 held, but the older-vintage check did
  not run". A void part is reported with the run log's entries.
- **"Not informative"** applies only to the older-vintage check when its gate is closed. It never applies to H1 to H3.
- **Known limits, stated in the report:** only the 2016 vintage has evidence for its cutoff, and 2026 was never
  checked (`research/audit/cutoff.md`, section 9); the sectors are a present-day list; the store's data ends on
  2026-10-28.

## 7. What is published as-is

The sealed report, as `research/m4_sealed_report.py` at the sealed commit produces it, is committed to the private repo
unedited: every test and check, every baseline and seed, the ledger rows, `seal.lock`, this file's SHA-256, and the
run log's entries (`D:\chrono-data\sealed\runs.jsonl`). Later notes go below it, dated, and never change a number. It
holds aggregates only, never raw prices or headlines.
