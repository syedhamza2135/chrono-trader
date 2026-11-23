# M3 kickoff (22 Nov 2026)

Read this first when M3 starts. It says where things stand, what M3 has to deliver, what exists to build on, the
decisions the owner must make before building starts, the build order with costs, and the risks to the time wall.
This session read and wrote only: no code, no data, no agents. Nothing in M3 is built yet.

**The owner approved all six decisions on 22 Nov 2026** ("Yes, approve all", relayed by the lead), as written
below: the 90-day view window, the switch-day check as frozen, the older-vintage rerun after the dev result and
before `PREREG.md`, SPY and sectors for `eval` only, a trial list of about 10 fixed before the first run, and 5 seeds
for each random part. Building starts with steps 1 and 2 after the 5-hour window resets.

## Where things stand

- **M0, M1 and M2 are done** and on master `6894217` ("Merge M2, the reader"; `git log -1`), which GitHub matches
  (project-status memory, 22 Nov).
- **The store** in `D:\chrono-data\store` holds the M1 tables and M2's `embeddings.parquet`: 502,712 rows, one per
  story, plus the two `.npy` arrays that `World.load` maps read-only (`research/audit/reader.md`, "The finish").
- **The known limit from M2.** The owner accepted all 11 vintages as published ("Accept, go on"). Only the 2016
  vintage has evidence; the other nine that read news are too weak to judge, and 2026 was never checked
  (`research/audit/cutoff.md`, section 9). Any M3 result that leans on the news carries this limit.
- **Tests.** 344 pass and 1 skips, in 6 to 11 minutes (AGENTS.md, Commands). The skip is the slow leak test
  (`tests/test_leaks.py:310`).
- This note is on the branch `claude/m3-kickoff-56264f`, cut from master `6894217`. Uncommitted.

## What M3 has to deliver

PLAN 9.2, M3, "Done when": "A dev report shows IC by quarter, frozen twins, placebo, price-only twin, matched
baselines, holding-period variants, costs and exposures." PLAN 8, step 5: "Track A on the dev years, with the twins,
the placebo and the baselines." The pieces, by section:
1. **The agent** (PLAN 5.3, 9.5, 9.6, 9.7, 9.8). Each year's 50 most-traded members (in 2016 from the first trading
   day of April). Features per stock per day: `news_count`, `news_new`, `news_memory` (half-life 5 trading days),
   r1, r5, r20, r60, vol20, `dvol_ratio`. Target: the log open-to-open return minus that day's mean across the 50.
   A ridge refit on the first trading day of each month from running sums (X'X and X'y) of every lived row whose
   label is visible, in float64; nothing fitted before 6 lived months. Penalty (10^-2 to 10^4) and pooling chosen
   on the most recent 20% of lived days (at least 3 months), with the k-2 gap at the boundary. Long the top 10 and
   short the bottom 10, equal-weighted and dollar-neutral, filled at the open; a long-only top 10 version.
2. **The dev variants** (PLAN 5.3, 9.7, 9.8): averaged monthly coefficients, recency weighting, River's online
   learners on identical data, holding periods of 1, 3 or 5 days, a turnover band (keep a holding until it leaves
   the top or bottom 15), a sector-neutral ranking. Each counts as a trial.
3. **The comparison runs** (PLAN 5.3, 9.9): frozen twins at each year end (the end-of-2019 twin is the
   pre-registered one), a price-only twin, a shuffled-news placebo (embeddings swapped between stocks within each
   day), long-short baselines (random ranking, 12-1 momentum, 5-day reversal) and long-only baselines (SPY
   buy-and-hold, all 50 equally). Every random part runs with several seeds (PLAN 5.5).
4. **The trial ledger** (PLAN 5.5, step 2): every dev run logged with a hash of its settings in `runs/trials.csv`.
5. **The dev report** (PLAN 9.10): daily rank IC by quarter with Newey-West t-stats; frozen-twin gaps by year;
   long-short and long-only return, volatility, Sharpe before and after costs, maximum drawdown, turnover, beta and
   sector tilt; costs at 0, 5, 10 and 20 bps; deflated Sharpe from the trial count; the seed spread; regimes,
   shocks and coefficient life (reported, not tested); the charts.
6. **The switch-day check** (`research/audit/cutoff.md`, section 10.2), fixed in M2 to run in M3's evaluation.

Not M3: `PREREG.md`, the seal and the sealed run (M4); the morning job (M5); H1 to H3 are tested on the sealed years
only (PLAN 9.10).

## What exists to build on

Read from the code on master `6894217` and from commands run on 22 Nov.

- **The loop.** `sim.simulator.run(world, agent, first, last)` calls `agent.decide(world.view(...))` at 9:00 New
  York each session and fills at the official open (`sim/simulator.py:117`). `sim.seal.settings_hash` already
  hashes a run's settings (`sim/seal.py:25`).
- **A toy agent.** `agent/reversal.py` (111 lines) already does the yearly pick of 50 by median dollar volume, the
  2016 April pick, a monthly ridge refit on visible labels, a fit record for the label-embargo test, and long 10,
  short 10. Its pick reproduces M0's `research/audit/universe_preview.csv` through the wall
  (`tests/test_leaks.py:290`). Track A can reuse the pick and the embargo record.
- **The leak check.** `eval.leaks.non_interference(tables, make_agent, first, last, how)` builds a World from
  in-memory tables, perturbs every record not visible at the decision on `last` (scramble, shift or delete,
  embeddings included), reruns and compares positions exactly and predictions within 1e-12 (`eval/leaks.py:170`).
- **Metrics.** Only `eval.metrics.daily_rank_ic` exists (18 lines, `eval/metrics.py`). Everything else in PLAN
  9.10 is still to write.
- **Sessions** (`world.clock.Clock().between`): 252 in 2016, 754 in the dev years 2017 to 2019 (also
  `reference/split.json`), 945 from 2016-04-01 to 2019-12-31. The sealed years have 1,715 (`split.json`).
- **Views with every past embedding** (`research/audit/reader.md`, "Memory"): `World.load` 17 s (50 s cold), 2.50 GB.
  A view on 2019-12-31 takes 0.6 s and holds 112,309 embeddings (345 MB). One on 2026-10-28 takes 10.2 s and holds
  499,809 (1,535 MB), with a process peak of 5.01 GB on a 7.8 GB laptop.
- **Missing from the store, needed by M3:**
  - SPY. `D:\chrono-data\bars\plan.csv` has no SPY row (`grep -ci spy` prints 0). It is needed for the long-only
    baseline and for the book's market beta.
  - Sectors. No sector column in `reference/entities.csv` or the store tables (PLAN 9.4). Needed for the sector
    tilt and the sector-neutral variant. Whether the Wikipedia list in `D:\chrono-data\membership` carries one was
    not checked.
- **Libraries.** The venv has no River, scikit-learn, SciPy, statsmodels or DuckDB (`importlib.util.find_spec`, 22
  Nov). The ridge, Newey-West and the deflated Sharpe are hand-written in numpy unless the owner adds a library.

## Decisions (the owner approved all six on 22 Nov: "Yes, approve all")

### 1. How many past embeddings a view serves: a recent window

- **The question** (`research/audit/reader.md`, end of "Memory"): a view now gathers a copy of every embedding
  visible at t. Late views take 10.2 s and 1.5 GB. Across 1,715 sealed sessions, at up to 10.2 s each, that is up to
  about 4.9 hours of views per run (an upper bound from those two numbers), and a peak near 5 GB.
- **Recommendation: a window, set in M3 and used unchanged in M4 and M5.** The World serves the embeddings whose
  `visible_at` falls in the last 90 calendar days before t, a World setting recorded in each run's settings hash.
  The agent keeps its own running `news_memory` and its own lived feature rows, as the toy agent keeps its rows,
  so it never needs an old embedding again.
- **Why.**
  - PLAN 9.6 uses old embeddings only in `news_memory`, with a half-life of 5 trading days. 90 calendar days were
    62 sessions at the end of 2018 (`Clock().between("2018-10-02", "2018-12-31")`), and the weight left after 60
    sessions is 0.5^12 = 0.00024. So a window changes the feature by a negligible amount, and an agent that keeps
    its own memory loses nothing.
  - It can't open the wall: a window only removes rows a view would otherwise show. It is measured on `visible_at`,
    so an old story whose embedding shows late (J-1's rejoin case) still shows on the day it becomes visible.
  - Setting it now means the dev runs and the sealed run use the same features. Deciding in M4 would change the
    features after the dev years were tuned on them.
  - Rough size: the largest vintage read 116,635 stories (2024, which reads 2025 and 2026), so 90 days hold a few
    tens of thousands of rows, under 0.1 GB (an estimate, to be measured in step 2).
- **The alternative:** keep full views. The dev years cost little (0.6 s, 345 MB), and M4 would live with up to
  about 5 hours of views per sealed run. Choose this if the owner wants no change to the World before M4.

### 2. The switch-day check: run it in M3 as frozen

- **The plan** (`cutoff.md` section 10.2, fixed before any result on 21 Nov): the news effect on a day is the live
  agent's daily rank IC minus the price-only twin's. Split each year's sessions into the first 20 and the rest. A
  warning if the pooled difference is above zero at one-sided 5% (Newey-West), or if in at least half the years the
  first-20 mean is above the rest by more than two standard errors.
- **Recommendation: run it unchanged in the dev report, on the final dev configuration, and repeat it on the sealed
  years in M4.** Name it in `PREREG.md` as a reported check, not a hypothesis.
- **Why.** The rules were frozen before any result, so changing them now would weaken them (M2 review finding C-1,
  PLAN 5.5). The dev years give only three switches with news on both sides (1 January 2017, 2018 and 2019; 2016's
  first 20 sessions are before the April pick), so the check has little power in M3, as `cutoff.md` says. That is
  a reason to repeat it later, not to skip it. It needs no new run: it is a cut of the live and price-only runs.
- **One gap for the owner:** the rules do not say which configuration it runs on. The recommendation fixes it: the
  final dev configuration, chosen before the check is scored.

### 3. When the older-vintage rerun runs: after M3's dev result, before the seal

- **The plan** (`cutoff.md` section 10.1): read every story again with the vintage one year older (2016's stories
  by 2014; 2025 and 2026 by 2023), into `D:\chrono-data\reader_older`, then rerun the M3 agent unchanged. A warning
  if the news effect falls below half the rule's and the paired IC difference is above zero at one-sided 5%.
- **Cost.** About 6 to 14 hours on the laptop: the main run took 6 hours 12 minutes at 22.6 headlines a second; 14
  hours was the plan's speed (`reader.md`, "Counts and timings" and "Two planned checks"). Mostly waiting, not
  usage. D: needs about 3 GB more, a second table and its two arrays (1.48 GB and 1.54 GB in `reader.md`, "Disk").
  It also needs one planned World change: a `vintage_offset` the World accepts only for this check, with its own
  test (`cutoff.md` section 10.1).
- **Recommendation: step 7 below, once the final dev configuration and its dev report exist, and before M4 writes
  `PREREG.md`.** Start the reading earlier if the laptop is free (for example overnight during step 4), since the
  reading itself does not need the result; only the comparison does.
- **Why.** `cutoff.md` says it starts "after M3 has a result to compare". Before the seal, a warning can still
  change the plan (the owner decides what a warning means); after the seal it could only be reported. And if the
  dev news effect is not above zero, the check says nothing, which is worth knowing before spending the hours.

### 4. SPY and sectors: add both before the report

- **Recommendation.** SPY: download its daily bars from Alpaca, the same source as the rest, into a benchmark table
  the World does not serve to agents; only `eval` reads it. Sectors: one fixed sector per company, from a public
  list, used only by `eval` (tilt) and by the sector-neutral variant, and flagged in the report as a present-day
  label, not a point-in-time one.
- **Why.** PLAN 9.2 names exposures in M3's "done when", and PLAN 5.3 and 9.8 name SPY. Neither is in the store
  (see "What exists"). A present-day sector list is hindsight, so the agent's main version never reads it; only the
  sector-neutral variant would, and the report says so. The owner may prefer to drop the sector-neutral variant
  instead.

### 5. The trial budget: a short list, fixed before the first dev run

- **Recommendation.** Write the list of dev variants into `runs/trials_plan.md` before the first run, and run only
  those: the main agent; averaged coefficients; recency weighting; holding 1, 3 and 5 days; the turnover band on and
  off; the sector-neutral ranking. About 10 trials. River's online learners last, only if the owner adds the
  library (not in the venv) and usage allows.
- **Why.** Every run counts as a trial, and the deflated Sharpe in the report is penalized by the trial count (PLAN
  9.8, 9.10). A list fixed in advance keeps the count honest and small, as the frozen rules did in M2.

### 6. Seeds for the random parts: 5 each

- **Recommendation.** 5 seeds for the shuffled-news placebo and 5 for the random ranking, the same seeds for every
  configuration, listed in the settings.
- **Why.** PLAN 5.5 asks for "several seeds" and the spread in the report. Five shows a spread at a fifth of the
  cost of 25. The number is a judgement, not a measured need; the owner may pick another.

## The build order

Each step ends with its tests passing, the full suite included. Costs are estimates. Laptop times come from the
measured numbers above; usage from past milestones: M1's two reviews took about 20% and 26% of a 5-hour window
(`research/m2_kickoff.md`, step 6), and one Opus judge used 27 points (PLAYBOOK.md, rule 3).

| Step | What | Done when | Laptop | Agent usage |
|---|---|---|---|---|
| 1 | Data for the report: SPY bars and the sector table (decision 4), with their audits | Both tables in the store, counted, and readable by `eval` only; a test that `View` has neither | Minutes to download (prices took about 10 minutes for 787 rows in M0, PLAN 9.13) | A Sonnet checker: a few points |
| 2 | The embedding window in the World (decision 1), and a real-store leak test with embeddings | Views serve only the window; window size in the settings hash; time and memory of a late view measured; `non_interference` passes on the real store with embeddings in all three modes | Under an hour of tests | One Opus judge on the window: about 27 points, so after a reset |
| 3 | The Track A agent (`agent/track_a.py`): pick, features (9.6), scaler, running-sum ridge, validation (9.5), policy (9.8), its own news memory | Unit tests on each feature against a hand computation; label embargo; import boundary; same output twice (float64, fixed order, `PYTHONHASHSEED=0`, one BLAS thread, PLAN 9.7); `non_interference` passes on synthetic tables and on the real store with embeddings | A full 2016 to 2019 run: views at most 0.6 s each over 1,006 sessions, so at most about 10 minutes, plus ridge fits (PLAN 9.13: minutes) | Building: a large share of one window. One Opus judge on the agent's leak paths: about 27 points |
| 4 | The comparison harness: frozen twins (deep copy at each year end, learning off), the price-only twin, the placebo, the baselines, and `runs/` with `trials.csv` | Each twin and baseline has a test; the placebo swaps only within a day; one pass over the views feeds every agent, so views are built once | One pass of about 10 minutes feeds all agents; separate runs would take about 10 minutes each | A share of one window; one Sonnet checker |
| 5 | Metrics and the dev report writer (`eval/`): IC by quarter with Newey-West, twin gaps, both books' statistics, costs at 0/5/10/20 bps, beta, sector tilt, deflated Sharpe, seed spread, regimes, coefficient life, the switch-day check, charts | Each metric tested against a small hand-worked case; the switch-day check follows `cutoff.md` 10.2 word for word | Seconds per report | A share of one window |
| 6 | The dev runs: the trial list (decision 5), each logged in `trials.csv` | `research/m3_dev_report.md` shows everything PLAN 9.2 names, for the chosen configuration, and lists every trial | About 10 trials, each about 10 minutes plus its fits: a few hours | Little: waiting |
| 7 | The older-vintage rerun (decision 3), the reading started earlier if the laptop is free | `reader_older` table built and served through the `vintage_offset`; the agent rerun unchanged; the warning rule applied as frozen | 6 to 14 hours of reading, then one run | Little: waiting, plus one checker |
| 8 | The M3 review | A review report under `research/`, with judges on the agent and the harness's accounting and skeptics on any finding; the fixes; then the owner decides on the commit | Tests only | About 20% to 26% of a window, as M1's reviews were |

**Step 1, done on 22 Nov** (after the reset; uncommitted):
- `python -m data_pipeline.benchmarks` (`data_pipeline/benchmarks.py`) wrote `store\spy.parquet` and
  `store\sectors.parquet`, and the counts to `research/audit/benchmarks.md`. Raw SPY files are in
  `D:\chrono-data\bars\benchmark`. `eval/benchmarks.py` reads them; nothing else does.
- SPY: 2,721 sessions, 2016-01-04 to 2026-10-28, one on every session of the clock (a test checks it), from Alpaca's
  SIP feed, raw and fully adjusted, the same source as the companies' bars.
- Sectors: better than decision 4 asked. Not one present-day list, but the GICS sector Wikipedia's list showed in
  each of the 142 monthly revisions the identity table already uses (cached, nothing fetched). 839 runs of one sector
  for 741 of the 746 companies; 89 changed sector at least once. The 5 without one are stubs of a few days (Bemis in
  2019, Four Corners in 2015, MasterBrand in 2022) and two companies that joined after the last revision used
  (Twilio and Vylor, October 2026). One revision showed Avery Dennison under two sectors (2015-03-31): that revision
  is left out for it. Two spellings are merged into one name each. Wikipedia's dates lag S&P's own changes, so the
  table is close to point in time, not exact, and the report must say so.
- Tests: `tests/test_benchmarks.py` (8).

**Step 2, done on 22 Nov** (uncommitted):
- `World(..., embedding_window_days=90)` is the default (`world/world.py`, `EMBEDDING_WINDOW_DAYS`); `World.load`,
  `eval.leaks.decisions_until` and `non_interference` take the same setting with the same default, and
  `sim.simulator.run` puts it in the settings the seal hashes. The window is fixed once the World is built. A view
  holds the rows with `visible_at` in (t - 90 days, t]: the newest part of M2's full view, in the same order.
- Measured (`python research/world_memory.py`, output in `D:\chrono-data\reader\world_memory_window90.log`; `all`
  as the argument reproduces M2's full views): `World.load` 35 s, 2.51 GB. The last warm-up view, 2016-12-30: 0.4
  s, 7,635 embeddings, 23 MB of vectors. The last dev view, 2019-12-31: 0.6 s, 7,975, 24 MB. The last sealed view,
  2026-10-28: 2.0 s, 15,353, 47 MB, with a process peak of 2.93 GB. M2's full view on that day took 10.2 s and 1,535
  MB, with a peak of 5.01 GB.
- Tests: `tests/test_embedding_window.py` (33). The windowed view is the full view cut by `visible_at` (made-up world
  and real store, 2016, 2019 and 2026). A row leaves at exactly 90 days. A row shown late by a rejoin (judge J-1)
  shows when it becomes visible. The runner records the window. Non-interference passes on the made-up world under
  windows of 90 days, 30 days and none, for a news reader and for an agent that counts the window's rows. A planted
  window anchored after t is caught. On the real store, with the embeddings of stories available before 2017-05-01
  (the World accepts a subset), the news agent reads them, and non-interference passes in all three modes. Those
  three runs take about 70 s each.
- M2's tests that assert the full visible set now build their World with `embedding_window_days=None`. That is four
  tests in `tests/test_embeddings_wall.py`, `tests/test_embed.py` and `tests/test_embeddings_store.py`. The J-1
  subset check still runs under the default window.
- The judge (Opus, high effort, at 9% of the window; `research/audit/m3_window_judge.md`) found no must-change. Its
  should-changes W-1 (no planted wrong window) and W-4 (one M2 check compared only windowed views) and its notes W-2
  (order and index unchecked) and W-3 (the window could be changed after the World was built) are all fixed. Its notes
  W-5 (`sector_on` looks ahead, fine for `eval` only) and W-6 (whoever writes `seal.lock` must include the window;
  `sim.run` already does) stay as notes for M4.
- **The full suite after steps 1 and 2:** 385 pass and 1 skips (the slow leak test), in 12 minutes 18 seconds on 22
  Nov. It was 344 and 1 before M3. AGENTS.md's count (344) needs the same update in the commit.

**Step 3, built on 22 Nov** (the owner: "Yes, start step 3"; uncommitted): `agent/track_a.py`, class `TrackA`. Its
docstring states every rule. Tests: `tests/test_track_a.py`.
- **What it does.** The toy agent's pick (it reproduces M0's list). The PLAN 9.6 features, the news ones in both
  poolings. The target. Running sums (n, sum of x, x'x, sum of y, x'y) per pooling in float64. A monthly refit from
  6 lived months on, choosing the penalty (10^-2 to 10^4, one per decade) and the pooling on the validation part,
  then the scaler and the ridge on all the sums. Long 10 and short 10, or long-only. Hold 1, 3 or 5 and a turnover
  band. 2016 watch-only. `news=False` gives the price-only twin for step 4.
- **Choices where PLAN is silent**, each the simplest one that can't leak:
  - Returns are over the stock's own last n bars (dated before today, within 200 calendar days), with missing
    returns skipped. vol20 is the standard deviation (ddof 0) of the last 20 log returns. dvol_ratio uses the last
    5 and 60 bars, without incomplete ones.
  - A story becomes available to a stock when both its embedding and its link to that stock are in the view. On
    the first decision, "since the last decision" means since the previous session's 9:00.
  - news_memory includes today's new stories (age 0). Ages are counted in sessions. It is zeros, with no flag,
    before a stock's first story. It is started on the first decision from the stories the view holds. A test
    shows that equals the memory kept day by day.
  - The target is demeaned over the stocks that have a label that day. A day's rows enter the learner at a monthly
    refit, once every label is in the view or 10 sessions have passed.
  - "6 months lived" counts from the first decision (2016-04-01), so the first fit is on 2016-10-03.
  - The validation score is the mean daily rank IC (PLAN's primary metric). Ties go to the last-layer pooling, then
    to the larger penalty. With fewer than 20 training days there is no fit.
  - The k-2 gap: the lived day before the validation part is held out. So is any earlier day whose label showed at
    or after the first validation decision (judge S1).
  - A missing feature is 0 before scaling, in the sums and in scoring (judge S2). Features are rounded to float32
    once, so stored and summed rows agree.
  - Before the first fit there is no decision. In 2016 every position is 0 and no book is kept.
  - With the 90-day window, a story whose link to a stock shows more than 90 days after its embedding never counts
    for that stock.
- **The owner's rulings (22 Nov, "Yes, keep and commit"):** validation stays on the mean daily rank IC, and the
  penalty grid stays at one value per decade, 10^-2 to 10^4. Both were open in PLAN.
- **The judge** (Opus, high effort, at 25% of the window; `research/audit/m3_agent_judge.md`): no must-change. The
  agent can't see a record after t, or a label before it was realized, when it decides. Fixed:
  - S1: the gap was one lived day, so a training label that showed late could still train the model the validation
    scored. Late labels are now held out, with a unit test.
  - S2: a missing value counted as raw 0 in the sums but as the mean at scoring. Now 0 in both.
  - S3: the embargo test now also checks the validation boundary.
  - S4: the split test now checks the exact rows held out.
  - S5: the same-output test now also runs with another hash seed.
  - Notes N2 (tie order in the docstring), N3 (no 2016 book carries into 2017), N5 (an age can't go below 0) and N6
    (one pair per story and company).
  - N1 (labels settle only at the monthly refit) is documented. N4, N7 and N8 needed nothing.
- **Tests** (`tests/test_track_a.py`, 22). Each feature and the target against a hand computation. The ridge from
  the sums against a direct solve. The rank IC. The split, with a late label held out. The embargo at every refit
  and at the validation boundary. No fit before six lived months, and 2016 watch-only. The policy, hold and band.
  The same output in three runs (hash seeds 0, 0 and 1, one BLAS thread). Non-interference in all three modes on
  the made-up world (the news agent, the price-only twin, and hold 3 with a band of 15) and on the real store with
  the embeddings of stories available before 2017-04-01. The import boundary is `tests/test_boundaries.py`, which
  passes on the new file.
- **The timed run** (`python research/track_a_timing.py`, alone on the laptop after the fixes; log
  `D:\chrono-data\runs\m3_step3_timing\timing.log`). `World.load` took 21 s. The run from 2016-01-04 to 2019-12-31
  took 12.3 minutes, with 817 decision days (2016-10-03 on), 40,850 rows and 39 refits. The process peak was 3.49 GB.
  It printed no IC or return, so it tuned nothing, and it is not a dev trial.
- **The full suite after step 3:** 407 pass and 1 skips, in 25 minutes 7 seconds on 22 Nov. The real-store leak
  tests take most of it. AGENTS.md (385, about 12 minutes) needs the same update in the commit.

**Step 4, built on 22 Nov** (the owner: "Yes, start step 4"; uncommitted). The comparison harness:
- **Where it lives.** `world`, `sim` and `eval` may import nothing from `agent` (PLAN 9.1), so every twin, the
  placebo and the baselines are agents in `agent/`, and the loop takes them as arguments.
  - `agent/track_a.py`: `freeze()` gives a frozen twin.
  - `agent/placebo.py`: `Placebo(agent, seed)`.
  - `agent/baselines.py`: `RandomRanking(seed)`, `Momentum`, `Reversal`, `EqualWeight`.
  - `sim/simulator.py`: `run_many`.
  - `eval/benchmarks.py`: `spy_buy_and_hold`.
  - `eval/trials.py`: the ledger.
- **One pass.** `run_many(world, agents, first, last, freeze=("live",))` builds each session's view once. Every
  agent decides on its own shallow copy, with its own simulator, and the seal covers every agent's settings. pandas
  copies on write, and the vectors are read-only, so an agent that changes its view changes only its own copy. A
  test plants such an agent. Another test shows each agent gets exactly the decisions and equity it gets from
  `sim.simulator.run` alone.
- **Choices where PLAN is silent**, each the simplest one that can't leak:
  - A frozen twin is taken before the first session of each new year, from the live agent's state after its last
    December decision. Learning is off: no refit, and no rows kept. It still picks each year, keeps its news memory
    and trades, on a book of its own that starts on that session. Only the live agent gets twins, named
    `live_frozen_<year>`. In the dev years they are the 2016, 2017 and 2018 twins; the pre-registered end-of-2019
    twin first trades in 2020.
  - The placebo groups the (story, company) pairs by the decision they first reach. It permutes the companies within
    each group with a generator seeded by (seed, that session's date). Stories, times and the day's amount of news
    stay the same, and a pair is shuffled the same way in every later view while its embedding is in the window (a
    test checks both). It permutes among every company with news that day, not only the 50 picks.
  - Random ranking draws one score per pick from a generator seeded by (seed, date). Momentum (12-1) is the log
    return over the stock's bars [-252:-21] within 400 days. Reversal is minus r5. Equal weight holds every live pick
    at 1 / n, rebalanced daily. All the baselines use Track A's picks and have 2016 watch-only. Seeds 1 to 5 for both
    random parts (decision 6).
  - SPY buy-and-hold is valued at Alpaca's adjusted opens (the first trade), since the store has no official
    auction prints for SPY.
  - The memory change in `agent/track_a.py`. Rows kept for validation are stored as float32, which is exact, since
    they were rounded to float32 when made. Only the rows the next validation needs are kept (n_val + 64 days, not
    n_val + 274). Seven agents of this kind run at once, so this cuts their memory.
  - The ledger. Each run is a row of `runs/trials.csv`: run id, New York time, commit, dirty, settings hash, dates,
    agents and the output folder. Its settings go to `runs/settings/<hash>.json`. Both hold names, dates and
    parameters only, and are for git. Outputs go to `D:\chrono-data\runs\<run id>`. `.gitignore` now ignores
    everything in `runs/` but those two.
- **The timed pass** (`python research/m3_compare_timing.py`, alone on the laptop; log
  `D:\chrono-data\runs\m3_step4_timing\timing.log`). It prints times and counts only, so it is not a trial.
  `World.load` took 19 s. One pass from 2016-01-04 to 2019-12-31 fed 18 agents (the 15 above plus 3 frozen twins)
  in 95.2 minutes, with a process peak of 4.41 GB. Step 3's run of the live agent alone took 12.3 minutes. So the
  plan's guess of about 10 minutes for one pass was wrong. The agents' own work sets the time, not the views: seven
  Track A agents each fit and keep their own news memory. The live agent's decisions equal step 3's
  run exactly (817 decision days, 40,850 rows). The baselines decide from their first pick on 2016-04-01 (945 days).
- **Tests.** `tests/test_comparison.py` has 15 tests, 39 cases with their parameters. Every twin, the placebo and
  each baseline pass `non_interference` in all three modes on synthetic tables, and the placebo also passes on the
  real store with embeddings (scramble). No judge ran, since step 4 does not change the time wall: it adds agents
  and a loop that hands each agent a copy of the same view.
- **The Sonnet checker** passed all 8 of its checks: no em-dashes, `.gitignore` keeps outputs out and the ledger in,
  the import boundary, the timing numbers, every name cited, the old keep value (n_val + 274), the test count, and
  sentence length. Its one finding, a 47-word sentence in the timed-pass bullet, is fixed. It also noted that the
  settings file holds whatever the caller passes. Step 6, the first caller, must pass names, dates and parameters
  only, as the ledger's docstring says.
- **The full suite after step 4:** 446 pass and 1 skip, in 31 minutes 45 seconds on 23 Nov. A rerun after the owner's rulings gave the same, in 35 minutes 33 seconds. AGENTS.md (407, about
  25 minutes) needs the same update in the commit.
- **For the owner (PLAN leaves these open):**
  - Should the placebo permute among every company with news that day (built), or only among the 50 picks?
  - Should equal weight be rebalanced daily (built), or bought once a year at the pick and held?
  - Should the price-only twin get frozen twins too? Only the live agent has them now.
- **The owner's rulings, 23 Nov:** "Yes. Make the recommended choices (as long as they are better)".
  - The placebo stays all-companies, as built. The picks-only version was checked first and failed the "better"
    check. The check sampled every 10th session from 2017 to 2019 (76 days) and used each day's new (story, company)
    pairs as Track A forms them. A permutation never changes a company's number of links, so the picks' news counts
    stay nearly equal either way: 2,637 pick pairs live, 2,633 shuffled among all companies, and 2,624 among the
    picks only. The all-companies shuffle moves 95.7% of pick pairs to another company, against 88.6% for picks
    only, so it leaves less true news in the placebo. That makes it the cleaner test for H3. The picks-only code and
    the check are kept outside git, in the lead's notes folder.
  - Equal weight stays rebalanced daily.
  - The price-only twin gets no frozen twins.

**Step 5, built on 23 Nov** (the owner: "Yes, start step 5"; uncommitted). The metrics and the dev report writer.
No real dev result was computed: every test runs on made-up or hand-built data.
- **Where it lives.**
  - `eval/stats.py`: Newey-West, the normal distribution, a book's statistics, the deflated Sharpe.
  - `eval/metrics.py`: IC by quarter, the twin gaps, the books, costs, beta, sector tilt, the seed spread, regimes
    and coefficient life.
  - `eval/switch_day.py`: the switch-day check.
  - `eval/charts.py`: the SVG charts.
  - `eval/report.py`: the writer for `research/m3_dev_report.md`.
  - `sim/simulator.py`: `replay` trades a finished run's own targets again at another cost.
  - The tests are in `tests/test_report.py`.
- **Choices where PLAN is silent**, each the standard or simplest one:
  - Newey-West uses the Bartlett kernel, with the lag floor(4 (T / 100) ^ (2 / 9)) from Newey and West (1994),
    the usual default. That gives 6 for the 754 dev sessions. A difference of means is the least-squares slope on a
    dummy, with the same standard errors. p-values use the normal distribution.
  - Sharpe is measured over zero, since the store has no cash rate. Long-short books are self-financing. There are
    252 sessions a year. The annual return is geometric. Turnover is the day's traded value (buys plus sells) over
    the pre-trade equity.
  - Costs: `sim.simulator.replay` trades a run's own targets again through a fresh simulator at 0, 5, 10 and
    20 bps. Costs change no decision, so this is that run at that cost exactly, and a test checks it against real
    runs at 0 and 20 bps. "Before costs" is the 0 bps replay. A first try rescaled the equity rows instead. It was
    off by up to 2.2e-5 a day at 20 bps on made-up data, so it was dropped.
  - Beta is the least-squares slope of the book's daily return on SPY's open-to-open return (Alpaca's adjusted
    opens), matching the simulator's marks at the open, with Newey-West errors.
  - Sector tilt is the net target weight per sector, averaged over the days the book holds anything. Sectors come
    from Wikipedia's list as it stood on each date (step 1). It uses the agent's targets, not the filled holdings.
  - The deflated Sharpe follows Bailey and Lopez de Prado (2014), on daily Sharpe ratios. N is the number of rows
    in `runs/trials.csv` (PLAN 9.10). The variance of the trials' Sharpe ratios comes from the trials shown in the
    report (the chosen version and its variants). One trial, or no spread, gives a bar of 0.
  - Regimes are read from SPY's adjusted closes before each session:
    - trend is up when the last close is above its 200-session mean (Faber 2007 uses the 10-month mean);
    - volatility is high when the last 20 sessions' standard deviation is above its median over the period;
    - a shock is the session a correction starts (a close 10% or more below the highest close so far, the usual
      definition), plus the 19 sessions after it. A new one can start only after a new high.
  - Coefficient life is each frozen twin's mean daily IC by quarter since its snapshot.
  - The seed spread gives each seed's mean IC, t and Sharpe, then their min, max, mean and standard deviation.
  - The charts are plain SVG, since the venv has no plotting library: IC over time (a 63-session mean), the
    cumulative twin gaps, equity against the baselines for both books, and equity by cost.
- **The switch-day check** follows `cutoff.md` 10.2. Its rules are quoted in the module's docstring. Four details
  the text leaves open are read this way:
  - A year's first 20 sessions come from the calendar, whether or not there was a prediction.
  - The pooled difference is the slope on a first-20 dummy, with Newey-West errors over the pooled days in date
    order.
  - "Its standard errors" in (b) are that year's own Newey-West error.
  - The years counted in (b) are those with days in both parts.
- **The Opus judge** (`research/audit/m3_report_judge.md`) found nothing that must change, 3 should-change items
  and 8 nits. It checked Newey-West against a separate double loop (to 2e-16), the deflated Sharpe against Bailey
  and Lopez de Prado, the replay's exactness, and the switch-day code against 10.2 line by line. Fixed:
  - The deflated Sharpe's N is the larger of the ledger's rows and the trials shown, since one run can hold several
    trials. The report warns when fewer than 2 trials' Sharpe ratios give the spread.
  - The switch-day check runs on 2017 to 2019 (`switch_years`), not on every year from the report's first date.
  - The twin replay test now freezes a real twin over a year end and compares its replays at 5 and 20 bps.
  - Regimes use no later close: the volatility line is an expanding median, and the shock walk starts at SPY's
    first close (a test changes later closes and checks earlier labels stay). A missing close gives no trend label.
  - Sector tilt is shown for both books. The report names two limits: normal p-values for short quarters, and a lag
    of 6 that is shorter than a 20-day block. The no-effect test now draws new noise for each day, and the vol test
    checks the median line by hand.
- **The Sonnet checker** passed 8 of 9 checks. It recomputed every hand-worked number in plain Python, checked
  line lengths, the names cited, the licensing and the import boundary, and ran `tests/test_report.py`. The one
  fail was a literal em-dash in a test assertion, now written as an escape. Two long docstring sentences were split.
  It could not check the 2.2e-5 figure above: that came from the failed test of the first try (2.17e-5), whose code
  is gone.
- **The full suite after step 5:** 472 pass and 1 skip, in 52 minutes 20 seconds on 23 Nov (pytest exit 0). That
  is 26 new tests in `tests/test_report.py`. It took longer than step 4's 32 to 36 minutes, with nothing else
  running in this session; the cause was not measured. AGENTS.md (446, 32 to 36 minutes) needs the same update in
  the commit.
- **For the owner (PLAN leaves these open):**
  - The report has no cash return for Sharpe. Should it subtract one (for example the 3-month T-bill), or stay over
    zero?
  - The deflated Sharpe's variance needs the Sharpe ratio of every trial. Should step 6 log one ledger row per
    variant, so that N and the variance count the same trials?
  - Should the charts go into git next to the report, or stay on D:? They show only derived equity and IC, no raw
    prices.
- **The owner's rulings, 23 Nov** (the lead's three picks, and the commit: "Yes, commit step 5"):
  - Sharpe is measured over zero, as built. The report labels it "over zero, no cash rate".
  - Step 6 logs one ledger row per variant, so the deflated Sharpe's N matches the trials.
  - The charts stay out of git for now. `eval.report.write` puts them on D:, in
    `D:\chrono-data\runs\m3_dev_report_charts` by default, with the other run outputs.

**Step 6, phase 1, on 23 Nov** (the owner: "Yes, start step 6"; uncommitted). The trial list, the selection rule and
what the report shows, fixed before any dev result. No real 2016 to 2019 metric was computed in phase 1.

<!-- M3 trial plan: start -->
### The M3 trial plan (fixed on 23 Nov, before any dev result)

**The base setup.** Track A as built in step 3, `TrackA()` with its defaults:
- the 50 most-traded picks, re-picked each January (April in 2016);
- every news and price feature (PLAN 9.6), with both poolings;
- the monthly ridge on running sums over every lived day, with penalties 10^-2 to 10^4 (one per decade), chosen by
  the mean daily rank IC on the validation part;
- long the top 10 and short the bottom 10, equal-weighted and dollar-neutral;
- traded every session (hold 1), with no band;
- 5 bps per side, the 90-day embedding window, 2016 watch-only.

Each trial runs the live agent alone with `sim.simulator.run` from 2016-01-04 to 2019-12-31.

**The trials.** Stage 1 tries the model. Stage 2 tries the trading rule on stage 1's winner.

| Trial | Stage | What differs from the base |
|---|---|---|
| T01 | 1 | Nothing: the base. |
| T02 | 1 | Averaged coefficients (PLAN 5.3, 9.7): each day's prediction is the mean of the predictions of every monthly fit made so far, each with its own scaler, penalty and pooling. |
| T03 | 1 | Recency weighting (PLAN 5.3, 9.7): the running sums decay so that a lived day's weight halves every 252 lived days. Validation is unchanged. |
| T04 | 1 | Dropped by the owner on 23 Nov, before any run. A sector-neutral ranking needs sectors in the agent's view, and sectors stay eval-only, so the time wall is unchanged. |
| T05 | 2 | Stage 1's winner, holding 3 sessions (hold 3). |
| T06 | 2 | Stage 1's winner, holding 5 sessions (hold 5). |
| T07 | 2 | Stage 1's winner, with the turnover band (band 15: keep a holding while it stays in the top or bottom 15), hold 1. |
| T08 | 2 | Stage 1's winner, band 15, hold 3. |
| T09 | 2 | Stage 1's winner, band 15, hold 5. |

River's online learners are not trials: the venv has no River (decision 5).

**The selection rule.**
- Every measure is over the dev years only. A day's IC counts only if its label ends by 2019-12-31, so the decision
  days run from 2017-01-03 to 2019-12-30. Book returns run from 2017-01-03 to 2019-12-31. Nothing from 2020 on is
  read.
- Stage 1: the trial among T01 to T03 with the highest mean daily rank IC wins. T02 and T03 change the
  predictions, and the holding period and the band do not, so IC compares models fairly. If two trials are within 0.001 of each
  other, the earlier one in the table wins, so the simpler model is kept.
- Stage 2: the trial among stage 1's winner and T05 to T09 with the highest Sharpe ratio of the long-short book
  after costs at 5 bps wins. Trading rules do not change IC, so they are chosen on what they change. If two trials
  are within 0.05 of each other, the one with the lower mean daily turnover wins.
- The winner of stage 2 is the chosen configuration. No trial is added, removed or rerun with other settings after
  any result is seen. A trial that fails to run is reported as failed, not replaced.

**What runs on the chosen configuration only.**
- The full comparison pass, with `sim.simulator.run_many` over the same dates. Its agents:
  - the live agent, with its frozen twins at each year end;
  - its long-only book (`book="long_only"`);
  - its price-only twin and its 5 placebos (seeds 1 to 5);
  - random ranking (seeds 1 to 5), 12-1 momentum and 5-day reversal, each holding as many sessions as the chosen
    trial, so their turnover is matched (the band is Track A's alone);
  - equal weight, rebalanced every session.
  The live agent's decisions must equal its own trial run's.
- `sim.simulator.replay` at 0, 5, 10 and 20 bps for every book.
- The switch-day check (`cutoff.md` 10.2) on 2017 to 2019.

**What the dev report shows** (`research/m3_dev_report.md`, written by `eval.report.write`):
- Every trial, winners and losers alike, in one table: mean daily rank IC with its Newey-West t, the long-short
  Sharpe before and after costs, the maximum drawdown and the daily turnover. It also says which stage each trial
  was in, and which trial won each stage under the rule above.
- For the chosen configuration, everything PLAN 9.2 and 9.10 name, as step 5's writer lays it out: IC by quarter,
  the frozen-twin gaps, the price-only twin and the placebo, the matched baselines for both books, costs at 0, 5,
  10 and 20 bps, beta and sector tilt, the deflated Sharpe with N equal to the ledger's trials (8), the seed
  spread, regimes and shocks, coefficient life, the switch-day check and the charts.
- The ledger: every row of `runs/trials.csv`.
<!-- M3 trial plan: end -->

- **The hash.** `python research/m3_trial_plan.py` prints the SHA-256 of the block above, from its start line to its
  end line, each line ending in LF. It is now:
  `4a9a45a1238aad3b704a18f27c9bac046e13bbadf981ff642fc3d78986861e2f`.
  The first freeze was:
  `9e1c10f4579621d6b70475186f27038f3301b17d577e317a1b7831581761341a`.
  It changed, still before any run, for the owner's rulings 1 and 4 below: T04 was dropped, and the baselines hold
  as long as the chosen trial.
- **Dates.** "23 Nov" in this section is the owner's own date, as in their messages. The ledger's stamps are New
  York time, so the same moments read 22 Nov there (17:21 for the planned rows, 17:39 for T04's dropped row).
- **The ledger.** `python research/m3_trial_plan.py --log` added one row per trial (T01 to T09) to
  `runs/trials.csv`, with status "planned" and out_dir "not yet run". Each planned row's settings file in
  `runs/settings/` holds the base parameters, the trial's change and the first freeze's hash. T03's planned file
  names its change `recency_half_life_days`; the code calls it `half_life_days`. Rows are only added, so these
  stay as written. `--drop` then added a "dropped" row for T04, carrying the new hash. The ledger has two more
  columns: `trial` (empty for a run that is not a trial, such as the comparison pass) and `status`.
  `eval.trials.count` counts the distinct trial names whose latest row is not "dropped": 8.
- **Built for phase 2** (after the rulings, before any run):
  - T02 and T03 in `agent/track_a.py`: `coefficients="averaged"` and `half_life_days`. Their docstring gives the
    rules. With the defaults, every base computation is unchanged.
  - The `hold` option in `agent/baselines.py`, the same rule as Track A's.
  - `tests/test_variants.py`: hand-worked cases for each, and `non_interference` in all three modes for T02, T03,
    momentum with hold 3, random with hold 5, and equal weight (15 cases, all pass).
  - `research/m3_dev_runs.py`, the runner: `stage1`, `stage2`, `compare` and `report`, one job at a time, each
    holding the PC awake in its own process.
  - The Sonnet checker passed 7 of 8 checks. It recomputed every hand-worked number in plain Python, confirmed the
    defaults change nothing, checked the hashes, the ledger and the dates. It flagged long sentences and stale text
    here, now fixed. One long sentence inside the hashed block is left as it is, since editing it would change the
    hash.
  - The full suite, before any real run: a first pass had 1 failure in 496 (a test's stand-in for `Sums.minus`
    took two arguments, and refit now passed three). Refit now passes the weights only when recency weighting
    is on. The rerun gave 496 pass and 1 skip, in 35 minutes 56 seconds (pytest exit 0).
- **PC time (estimates).** One trial alone took 12.3 minutes in step 3, so 9 trials are about 2 hours. The
  comparison pass took 95.2 minutes for 18 agents in step 4, and the long-only book adds one more Track A agent, so
  about 100 to 110 minutes. The replays and the report take minutes. In all, about 4 hours, one job at a time.
- **The owner's rulings, 23 Nov** (the lead's four picks: "Yes, take them"):
  1. T04 is dropped, so there are 8 trials. Sectors stay eval-only, and the time wall is unchanged. Its ledger row is
     kept, and a later row marks it "dropped".
  2. T03 keeps its half-life of 252 lived days.
  3. The ties stay at 0.001 of IC and 0.05 of Sharpe.
  4. The baselines hold as long as the chosen trial, so turnover is matched. Equal weight stays rebalanced every
     session, as the owner ruled in step 4. The band is not given to the baselines.
- **For the owner (asked on 23 Nov, answered above):**
  - T04 needs sectors in the agent's view, a change to the time wall. Build it (one more judge), or drop T04 and run
    8 trials?
  - T03's half-life of 252 lived days (one year) is a judgement. Keep it, or pick another?
  - The ties: 0.001 of IC in stage 1, 0.05 of Sharpe in stage 2. Keep them?
  - The baselines trade every session. If the chosen trial holds 3 or 5 sessions, should they hold as long?
- **Checkpoint 1** is commit `83a35cd` (the rulings, the re-freeze, T02, T03 and the matched-hold baselines).
- **Phase 2 runs** (22 Nov, New York time; logs in `D:\chrono-data\runs\m3_dev\`). Each trial took about 10
  minutes, with 817 decision days, 39 fits, no forced sales and no unmarked days.
  - Stage 1. T01 mean IC 0.00763 (Newey-West t 1.38), T02 -0.00262 (t -0.46), T03 0.00829 (t 1.42). T03 beats T01
    by 0.00067, inside the 0.001 tie, so the earlier trial wins: T01. T01's decisions equal step 3's run exactly.
  - Stage 2, on T01 (the IC is the same for every stage 2 trial). Sharpe after 5 bps and daily turnover: T05
    -1.250 and 0.713, T06 -0.460 and 0.495, T07 -0.862 and 1.151, T08 -1.060 and 0.535, T09 -0.243 and 0.389. T09
    is ahead by more than 0.05, so it wins: the chosen configuration is `{"band": 15, "hold": 5}`.
  - The comparison pass ran 19 agents and 3 frozen twins in 87.7 minutes. The live agent's decisions equal T09's
    own run. Each book's replay at 5 bps equals its run. Every trial was replayed at 0 bps for the report.
  - `research/m3_dev_report.md` holds the results. Every trial loses money after 5 bps; costs dominate. The
    long-short Sharpe is 0.18 before costs and -0.24 after. Retraining beats the end-of-2016 twin by 0.0179 of
    daily IC (t 2.61). The reading adds 0.0069 over the price-only twin (t 0.74), which is not significant. The
    switch-day check raises neither warning.
  - Things to note, none a leak sign: the ledger marks the runs after T01 "dirty", because the ledger itself is in
    git and each run adds a row; the code was at `83a35cd` throughout. Placebo seed 5 has a mean IC of 0.0130
    (t 2.47), above the live agent's, and the placebo seeds' t values spread with a standard deviation of 1.59, so
    the t values here may be too large. The 40 days after a shock show an IC of 0.0649 (t 4.01); that is reported,
    not tested, and a small sample.
- **Checkpoint 2** is commit `210bfaf` (the dev report, this note and the ledger rows).

### Step 7: the older-vintage rerun (started 23 Nov)

- **The World's `vintage_offset`** (`world/world.py`, `reader/vintage.py`):
  - Offset 1 gives a story from New York year Y the vintage Y-2, capped at 2023. So 2016's stories are read by
    2014, and the 2025 and 2026 stories by 2023. Only 0 and 1 are accepted, and the offset is fixed when the World
    is built.
  - A World with offset 1 takes only the older table: a row with the rule's own vintage is refused. The default
    World still refuses any row with a wrong vintage, the older table included.
  - An offset World never opens the sealed years. It refuses `allow_sealed`, and its views refuse sealed dates even
    if `allow_sealed` is set later. `sim.simulator.run` and `run_many` refuse it for any sealed date, before the seal
    is checked.
  - The runner puts `vintage_offset: 1` into the run's settings, so it goes into the settings hash. With offset 0
    the settings stay as they were, so older runs' hashes don't change.
  - `World.load(embeddings_store=..., vintage_offset=1)` reads the older table from `D:\chrono-data\reader_older`
    and every other table from the store.
- **The reader** (`reader/embed.py`): `run-older`, `finish-older` and `arrays-older` are the same jobs with offset 1.
  The parts and the table all go to `D:\chrono-data\reader_older`. Each manifest records the offset.
- **The leak check** (`eval/leaks.py`): `non_interference` takes the offset, so a shifted story's embedding takes
  the older vintage.
- **Tests** (`tests/test_vintage_offset.py`, 12): the rule with offset 1 by hand; only 0 and 1 accepted; the
  default World refusing one wrong-vintage row and the whole older table; the offset World refusing the rule's
  vintage; the sealed years shut, in the World and in the runner; the offset in the settings and their hash; the
  older reader's rows accepted by the offset World only; and `non_interference` in all three modes for the chosen
  configuration on the older table.
- **The rerun** (`research/m3_older_vintage.py`): `space`, `count` (the older table against the main one's 502,712
  rows, story ids, times and vintages), `run` (the chosen configuration from `stage2.json`, unchanged, on the older
  table, to 2019-12-31) and `result` (the warning rule exactly as `cutoff.md` 10.1 froze it). The run is a ledger
  row with no trial name, so the trial count stays 8.
- **Disk.** D: had 60.6 GB free on 23 Nov. The main table and its arrays take 3.02 GB.
- **The full suite after step 7's build:** 508 pass and 1 skip, in 36 minutes 55 seconds on 23 Nov (pytest exit 0).
- **The reading** started at 22:57 New York on 22 Nov (`python -m reader.embed run-older`, a detached process; log
  `D:\chrono-data\reader_older\run.log`; `run.pid` holds the venv launcher's pid, 17736, and the reader itself is
  7324). It counts 502,712 stories, the main table's count. Its first five parts (vintage 2014) each took about 3.7
  minutes, about 22 headlines a second, so the whole reading takes about 6.3 hours. The log is buffered, so the
  parts on disk show progress first.
- **Commits.** The auto-mode check first refused the commit of this build, since the owner's permission to commit was
  given for step 6's phase. On 23 Nov the owner approved it ("Yes, commit step 7", relayed by the lead), but the
  check refused the commit again, since the approval reached this session through another session. The owner then
  told the lead directly to make it, and the lead committed the build as `001d01c` (step 7's checkpoint 1).
- **The lead's reading of an ambiguous line** (23 Nov, decided after seeing the dev result; for the owner and the
  step 8 review). `cutoff.md` 10.1 says: "If the news effect isn't above zero in the first place, the check says
  nothing". The lead reads "above zero" as above zero at one-sided 5%, the same test the warning uses in (b). The
  dev news effect is +0.0069 (Newey-West t 0.74, one-sided p 0.23), so by the frozen rule the check says nothing on
  the dev years: it is "not informative", never "passed". The reading and the rerun still run, since they cost
  laptop hours, not usage, and the table can serve a sealed-year repeat if M4 adds one. Every rerun number is
  descriptive only, outside the frozen rule. Neither the rule nor the trial changes.
- **The result, 23 Nov** (in full in `research/m3_older_vintage.md`). The reading ended at 05:58 New York, 106
  parts. `finish-older` wrote 502,712 rows, and the count check passed: the same rows, story ids and `available_at`
  as the main table, and every vintage the rule's minus one. T09 reran unchanged on the older table to 2019-12-31 in
  12.9 minutes (ledger row `20261123T061536_0f452837`, no trial name). The outcome is **not informative**: the rule's
  news effect is +0.00687 (t 0.74, p 0.23). Descriptive only: the older news effect is +0.00692, and the rule's run
  minus the older run is -0.00005 a day (t -0.01), so (a) and (b) both fail and no reading of the gate gives a
  warning.

Steps 1 and 2 can be built in either order; 3 needs 2; 4 needs 3; 5 can start beside 4; 6 needs 4 and 5; 7 needs 6.
By the playbook, each step is its own task session, one at a time, and each starts at 55% or less of the window if
it runs a judge.

## The time wall: risks, and how each step keeps `non_interference` passing

`eval.leaks.non_interference` shows that an agent can't reach past the wall's rules. It does not check the rules
themselves (`eval/leaks.py`, its docstring). Each risk below names the test that covers it.

- **The real-store leak tests run without embeddings.** The `real_tables` fixture reads six tables, not the
  embeddings (`tests/test_leaks.py:284-286`), so no test has yet perturbed real embeddings under a real agent.
  Track A is the first agent that reads them. Step 2 adds a real-store test with embeddings in all three modes.
  Memory is the obstacle: `non_interference` builds two Worlds from in-memory tables, and the full vectors are
  1.5 GB. The World does not require an embedding for every story (`world/world.py:187-205` checks only unknown,
  repeated, wrong-vintage or wrongly timed rows), so the test can pass the embeddings of stories up to a date some
  weeks after `last`. That keeps late rows to perturb and keeps memory small.
- **The window could hide or show the wrong rows.** It must be measured on `visible_at`, from t back, inside the
  World (step 2). A test plants an old story whose link shows late (the J-1 rejoin case) and checks it shows on
  the day it becomes visible, and another checks a row just outside the window is absent. The window size goes in
  the settings hash, so the leak test and the run use the same one.
- **The agent's own memory.** Track A keeps state between days (news memory, lived rows, running sums). State built
  only from past views can't leak, and `non_interference` runs the whole sequence from `first`, so it covers state.
  The risk is a label used before it is visible: the label-embargo test (`tests/test_leaks.py:267`) must cover
  Track A's fit record, as it covers the toy agent's.
- **Validation inside the lived days.** The penalty and pooling choice (PLAN 9.5) must use only lived rows, with the
  k-2 gap at the boundary. A test fits on a world where every row after the boundary is scrambled and checks the
  chosen penalty is unchanged. This is the planted leak "a scaler fitted on all the data" in PLAN 9.11, applied to
  the validation split.
- **Twins and the placebo.** A frozen twin must be a deep copy, so the live agent's later learning never reaches it.
  The placebo swaps embeddings within one day's view only, so it can't move news across days. Each runs through
  the same views, so `non_interference` covers them by running it on each twin's factory as well as the live
  agent's.
- **Eval-only data.** SPY and sectors (step 1) are not in `View`; a test asserts that. SPY's bars are dated like the
  others, so the long-only baseline uses closes only up to the last close.
- **Stock picks.** The yearly pick must use only the year before the pick (PLAN 9.11, "a stock list made with future
  data"). Reusing the toy agent's pick keeps the test that it matches M0's preview.
- **The older-vintage rerun.** `vintage_offset` loosens the World's vintage check, so it must be accepted only for
  that check: refused by `sim.simulator.run` for any sealed date, recorded in the settings hash, and covered by its
  own test that the default World still refuses a wrong-vintage row (`cutoff.md` section 10.1).
- **The sealed years stay shut.** M3 runs only to 2019-12-31. `World.view` refuses sealed dates unless
  `allow_sealed` (`world/world.py:318-324`), and only `sim.simulator.run` with a matching `seal.lock` opens them.
  The report writer must not call `World(..., allow_sealed=True)` as the M0 preview test does
  (`tests/test_leaks.py:293`); a grep in the review checks it.

## Running it inside the usage limits

- This session started at 65% of the 5-hour window and wrote this note at about 70%, with no agents.
- Building M3 starts after a reset. The judges in steps 2 and 3 each need 55% or less at their start.
- The long jobs (step 6's runs, step 7's reading) run detached, as M2's reader did, so they don't depend on a
  session staying open.
