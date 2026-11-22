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
