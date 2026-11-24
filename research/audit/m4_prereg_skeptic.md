# M4: the skeptic on the draft PREREG.md (23 Nov 2026)

The draft is the untracked `PREREG.md` (118 lines) on branch `claude/m4-kickoff` at `6401ee7`. I read it against
PLAN.md 5.5 and 9.9 to 9.12, the M4 entry rules (`research/m3_kickoff.md:645-657`), `research/audit/cutoff.md` 10.1
and 10.2, and `research/m4_kickoff.md` ("What PREREG.md must fix in advance" and "Owner decisions"). I checked its
claims about the code against the code. I read nothing under `D:\chrono-data`, ran nothing that reads the store, and
used only made-up numbers.

Severity: high means a choice still open after the results, or a conflict that can change an outcome. Medium means
two fair readings. Low means wording.

Summary: 3 high (P-1, P-2, P-4), 8 medium (P-3, P-5 to P-11), 5 low (P-12 to P-16).

## Claims about the code that hold

These were checked and need no change:
- `run_many` names a twin `<name>_frozen_<year just ended>` and adds it at the first session of the new year, before
  that session's decisions (`sim/simulator.py:236-240`). So `live_frozen_2019` trades from 2020-01-02. Only "live" is
  frozen (`research/m4_sealed_run.py:75`).
- `nw_lag(n)` is floor(4 (n/100)^(2/9)) (`eval/stats.py:20-22`). It gives 6 for 753 and 754 days. `nw_mean` drops
  NaNs first and takes the lag from the remaining n (`eval/stats.py:64-69`). The p is 1 minus the normal CDF of t
  (line 72).
- `daily_rank_ic` keeps days with at least 10 stocks that have both a prediction and a label (`eval/metrics.py:20-32`).
- The data fingerprint: each store table's size and footer hash (`world/world.py:261-270`,
  `research/m4_sealed_run.py:66-70`), and the embeddings' `arrays` record: rows, story ids' hash, files, width, dtype
  and the Parquet footer (`reader/embed.py:345-346`). No hash of the vectors.
- The parts, the seeds 1 to 5, 5 bps, the baselines' hold of 5 with no band, equal weight every session
  (`research/m3_dev_runs.py:37-38`, `132-139`; `agent/baselines.py:123-130`; `sim/simulator.py:26`).
- 1,715 sealed sessions from 2020-01-02 to 2026-10-28 (`reference/split.json`). The 2024 vintage reads 2025 and 2026
  (`reader/vintage.py:26-30`), so 1 January 2026 is not a switch.
- A part refused by `seal.check` never reaches `seal.begin` (`sim/simulator.py:150-157`), so it has not run.
- A crashed run saves no outputs: `run_step` saves only after `run_many` returns (`research/m4_sealed_run.py:127-130`).

## Findings

### P-1 (high). The Newey-West lag conflicts with the owner's decision 5

- **PREREG lines 51-53:** "the lag is Newey and West's (1994) rule ... for that series' n days ... it gives about 7
  on the sealed years' length."
- **Conflict.** `research/m4_kickoff.md:119` (item 4): "Newey-West with lag 6, as on dev." Decision 5, approved on 23 Nov:
  "H2 as the primary, Holm over H1 to H3 at 5%, H3's p as the larger of its two, lag 6". The M3 review: "Keep lag 6"
  (`research/review_m3_2026-11-23.md:192`). Line 6 ("this file rules") would overturn an owner decision silently.
- **Evidence.** `nw_lag` gives 7 for every n from 1,241 to 2,262 (checked on made-up n). The sealed series have about
  1,714 days, so the rule gives exactly 7, not "about" 7. On 400 made-up AR(1) series of 1,714 days, lag 6 and lag 7
  put the p on different sides of 0.05/3, 0.025 or 0.05 in 4 of 1,200 comparisons. So the choice can change an
  outcome.
- **Fix** (replace lines 51-53 from "the lag is" to "sealed years' length."): "the lag is 6 for every test in this
  section, passed as `eval.stats.nw_mean(x, lag=6)`, as the owner decided on 23 Nov (`research/m4_kickoff.md`,
  decision 5). Six is what Newey and West's (1994) rule gave on the dev years' 753 days. The rule's own lag for the
  sealed length (7) is shown in the robustness column, with no test." Then add "lag 7" to the robustness column on
  line 71. The leak checks in section 5 keep the lag their code uses (the rule, `eval/switch_day.py:41`), and section
  5 should say so. If the owner prefers the rule, the owner must amend decision 5 first, and the draft must then say
  "lag 7" as a fixed number.

### P-2 (high). The code that scores the sealed run is not sealed

- **PREREG lines 116-118:** "The sealed report, as its writer produces it, is committed ... unedited."
- **Conflict.** No code in the repo computes H1 to H3, the placebo's daily mean, Holm's method, or the sealed
  older-vintage check. A search for "holm" in every `.py` file finds nothing. `eval/report.build` is the dev report: its
  switch years default to 2017 to 2019 (`eval/report.py:75`), and its deflated Sharpe takes the trial Sharpes from the
  same window's returns (lines 176-181). M4 step 6 runs "the writer" after the sealed run, so it would be written with
  the sealed outputs on disk. PLAN 5.5 entry rule C-1 (`PLAN.md:345-347`): rules frozen in future, "such as a probe list
  or a scoring rule, are committed ... before anything is scored, and the scoring command refuses to run unless the
  files match that record". The words in section 3 are close to complete, but every gap left in words (P-7, P-8, P-12)
  would be closed by code written after the results.
- **Fix** (add to section 2, after line 31): "The writer is `research/m4_sealed_report.py` at the code commit. It is
  tested on made-up records before the seal, it computes every number in sections 3 to 5, and it runs unchanged on
  the sealed outputs. Its output is the result of record. If it fails, or a bug in it is found, after any sealed output
  is read, its numbers (or its failure) stay in the report, and a corrected writer's numbers go beside them in a dated
  note, never instead." And on line 116: "The sealed report, as `research/m4_sealed_report.py` at the sealed commit
  produces it, ...".

### P-3 (medium). The stated order makes the cost replays impossible under the seal

- **PREREG line 38:** "Main first, then older_vintage, then `ledger`." Line 43: "Cost replays at 0, 5, 10 and 20 bps."
  Line 76: the baselines "are compared with live **before costs**".
- **Conflict.** `replay` in the sealed years calls `seal.check` and `seal.require_started` (`sim/simulator.py:268-270`).
  `seal.check` needs a clean tree and HEAD equal to the lock's commit (`sim/seal.py:104-108`, `133-134`). The `ledger`
  step appends to `runs/trials.csv` (`research/m4_sealed_run.py:150-156`), which dirties the tree. Committing it moves
  HEAD. After `ledger`, no sealed replay can run, so no before-cost number exists for decision 4's comparison. The
  writer would then have to pick a way round the seal (for example the unguarded `Simulator`) after the run. Replays are
  deterministic, so the numbers would not change, which is why this is medium.
- **Fix** (replace line 38): "**Order.** Main first, then older_vintage, then the replays at 0, 5, 10 and 20 bps of
  every book in both parts (`sim.simulator.replay`, with that part's sealed settings), saved outside git, then the
  writer, then `ledger`. Nobody reads a sealed output until both parts and the replays have run."

### P-4 (high). What happens when a part fails is open

- **PREREG lines 39-42, 105-109.** Line 40: a part that stops early "is void, and a second run needs `--again`".
  Line 106: "Failure: a complete run in which H2 or H3 does not hold."
- **Open choices.** (1) Whether a void part is rerun at all, and when. (2) Which run is of record after a void first
  run: lines 41-42 make the first run of record only "after a bug is found". (3) The outcome when main is void: H1 to H3
  can't be tested, and no label in section 6 covers it. (4) The outcome when older_vintage is void, or never run: line
  105 needs "neither leak check warns", which a check that never ran meets on its face. So Success could be claimed
  without the check decision 2 added, and that choice could be made after main's results are read. (5) "A complete run"
  is not defined when one part completes and the other does not.
- **Fix** (replace lines 39-42): "**Once.** Each part runs once. A part refused by the seal before it starts has not
  run. A part that starts and stops before its last session is void. A void part is rerun once with `--again`, at the
  same sealed commit and settings, before anyone reads any sealed output; that rerun counts as another trial (PLAN
  9.12) and is the part's result of record. If the rerun is void too, the part is void. If main is void, H1 to H3 are
  not tested and the outcome is Void. If older_vintage is void, its check is reported as 'not run', and the outcome
  can't be Success. A complete run is one in which both parts reached their last session." And on line 105:
  "**Success:** both parts complete, H2 and H3 both hold after Holm, and neither leak check warns."

### P-5 (medium). A bug found after the seal but before a run, or in the code, has no rule

- **PREREG lines 41-42:** "The same holds for a second run after a bug is found: the first run stays the result of
  record."
- **Open choice.** A code fix needs a new code commit, so the "TO FILL" values on lines 13, 17 and 18 change, the file's
  hash changes, and a new lock is needed. `seal.write` refuses a lock that exists (`sim/seal.py:143-144`), and the run
  log is shared (`sim/seal.py:22-25`), so after any start a new seal still needs `--again`. The draft doesn't say
  whether a re-seal is allowed before any part starts, how it is recorded, or what happens to the first lock.
- **Fix** (add after line 42): "If a bug is found after the seal and before any part has started, the seal may be
  redone once: `seal.lock` goes to the Recycle Bin in its own commit, the fix is committed, this file's three filled
  values are updated and nothing else in it changes, and a new lock is written. A dated note records the bug, the fix
  and both locks. Once any part has started, a fix means a second run with `--again` under a new seal; the first run
  stays the result of record, and the second is reported beside it."

### P-6 (medium). The test-suite rule doesn't match M4 step 4, and one leak test is skipped by default

- **PREREG lines 103-104:** "The full test suite passes at the sealed commit, including every leak test and planted
  leak, before the sealed run starts (M4 step 4). If it fails, nothing is sealed."
- **Conflict.** M4 step 4 writes and commits the lock first, then runs the suite (`research/m4_kickoff.md`, steps
  table, row 4). So when the suite fails, a lock already exists and "nothing is sealed" is false. Also the default
  suite skips one leak test (`tests/test_leaks.py:310`, run only with `CHRONO_SLOW_LEAKS=1`; AGENTS.md: "513 pass and
  1 skip"). PLAN 5.5 success needs "every leak test passes" (`PLAN.md:364`).
- **Fix** (replace lines 103-104): "**Leak tests.** The full suite, with `CHRONO_SLOW_LEAKS=1` so no leak test is
  skipped, passes on the clean tree at the code-plus-PREREG commit before `seal.lock` is written, and again at the
  lock's commit before the sealed run starts (M4 step 4). If either fails, no part runs, and P-5's re-seal rule
  applies."

### P-7 (medium). The older-vintage check's day sets are open

- **PREREG lines 92-97:** the rule's news effect, the older news effect, and "the paired daily difference, live's IC
  minus live_older_vintage's".
- **Open choice.** The three series can cover different days (a day can have an IC for live but not for
  live_older_vintage). The dev check used three pairwise day sets, each `(x - y).dropna()`
  (`research/m3_older_vintage.py:108-110`). A writer could also use the days all three share. Test (a) compares two
  means, so the choice can move it.
- **Fix** (add after line 93): "Each of the three series is a paired daily difference on the days both of its series
  have an IC, as on dev (`research/m3_older_vintage.py:108-110`): the rule's effect on live and price-only days, the
  older effect on live_older_vintage and price-only days, and (b) on live and live_older_vintage days. Every mean and
  t comes from `eval.stats.nw_mean` with its default lag."

### P-8 (medium). The deflated Sharpe's inputs are not fully fixed

- **PREREG lines 77-80:** "uses N equal to the ledger's trial count (8, plus any sealed rerun) and the variance of the
  dev trials' after-cost Sharpes, as the dev report did (M3 review S3-3); the before-cost version is shown beside it."
- **Open choices.** (1) The existing code takes the trial Sharpes from the report's own window for live and its
  variants (`eval/report.py:176-181`). The sealed run has no variants, so as coded the variance is 0 and the code prints
  its "fewer than 2 trials" warning. (2) Daily or annual Sharpes, and which window: the dev report used daily Sharpes
  over 754 dev days, giving var_trials 0.0013 (`research/m3_dev_report.md:197-199`, rounded). (3) `eval.trials.count`
  counts every named trial not dropped (`eval/trials.py:62-65`), so a rerun of older_vintage (`sealed_older_vintage_2`)
  would also raise N for the live long-short book. (4) The before-cost version's variance source is not stated. (5)
  S3-3 asked PREREG to "fix one and report the others" (`research/m4_kickoff.md`, open items); the third variant is not
  named.
- **Fix** (replace lines 77-80 from "The deflated Sharpe"): "The deflated Sharpe of the live long-short book after 5
  bps, over 2020-01-02 to 2026-10-28, uses `eval.stats.deflated_sharpe` with n_trials equal to 8 plus the number of
  `--again` runs of the main part, and the trial Sharpes equal to the 8 dev trials' daily after-cost Sharpes over the
  dev years (2017-01-03 to 2019-12-31), exactly as `research/m3_dev_report.md` computed them (var_trials 0.0013 there,
  rounded). The writer recomputes that variance from the dev runs and stops if it differs from the dev report's at
  its printed precision. Beside it, without a verdict: the before-cost version (sealed returns at 0 bps, the dev
  trials' before-cost Sharpes) and the version with the dev trials' annual Sharpes."

### P-9 (medium). This file's SHA-256 depends on line endings

- **PREREG line 4:** "Its SHA-256 goes into `seal.lock`". Line 117: "this file's SHA-256".
- **Evidence.** `core.autocrlf` is `true` in this repo, and `.gitattributes` keeps bytes only for `reader/*.csv`. The
  draft has LF endings now (0 carriage returns). `sim.seal.prereg_hash` hashes the working-tree bytes
  (`sim/seal.py:62-64`). A checkout made elsewhere on the laptop (the main checkout after a merge, say) writes CRLF,
  so its hash differs and the seal refuses the run there. The hash a reader computes from the GitHub blob can also
  differ from the lock's. This is J4-8 in `research/m4_kickoff.md`, still open.
- **Fix:** add `PREREG.md -text` and `seal.lock -text` to `.gitattributes` in the code commit, and on line 4 write: "Its
  SHA-256, of its bytes as committed (LF line endings; `.gitattributes` marks it `-text`, so every checkout keeps
  those bytes), goes into `seal.lock`".

### P-10 (medium). The dev check (M4 step 2) is missing

- **PREREG lines 10-12:** "Nothing about the agent changes for the sealed run."
- **Conflict.** `research/m4_kickoff.md` item 2 of "What PREREG.md must fix": the review changed `agent/track_a.py`
  after the dev runs (W3-3), "so step 2 checks that the sealed commit gives the same dev decisions". The draft neither
  states the check nor what happens if it fails.
- **Fix** (add after line 12): "Before the seal, `python research/m4_sealed_run.py dev-check` at the code commit gives
  live's decisions from 2016-01-04 to 2019-12-31 equal to the dev comparison pass's (M4 step 2). If they differ, nothing
  is sealed until the owner decides, in a dated note, what the difference means."

### P-11 (medium). One outcome has no label

- **PREREG lines 105-107.** Success needs H2, H3 and no warning. Failure is "H2 or H3 does not hold". A run where H2
  and H3 both hold and a check warns is neither. Line 107 names how H3 is reported, not the run's outcome.
- **Fix** (replace line 106-107's last sentence): "A complete run where H2 and H3 hold but a leak check warns is not a
  success. Its outcome is reported as 'H2 held; H3 held but is not claimed, because the [check] warned'."

### P-12 (low). Boundaries, rounding and missing p-values

- **PREREG lines 53, 65-67, 89, 96.** Holm uses "at most" (p equal to the bound passes). The leak checks' "at one-sided
  5%" is coded as p strictly below 0.05 (`eval/switch_day.py:70`; `research/m3_older_vintage.py:112`). Rounding is not
  stated. A p can be NaN when a series has under 2 days or a zero standard error (`eval/stats.py:66-70`), and Holm's
  sort is then undefined.
- **Fix** (add after line 67): "Every comparison uses the unrounded double-precision value. In Holm, a p equal to its
  bound passes. In the leak checks, 'at one-sided 5%' means p below 0.05, as the code has it. A NaN p counts as 1. Ties
  in Holm's sort don't change the result."

### P-13 (low). "Both hold" for H3's two tests is undefined

- **PREREG line 59:** "Two paired tests, and H3 holds only if both hold". "Holds" is defined only for H1 to H3 under
  Holm (line 67), not for each sub-test.
- **Fix** (replace line 59): "**H3: reading helped.** One hypothesis with two paired tests. Its p-value is the larger of
  the two tests' p-values, so Holm rejects H3 only when both tests are below H3's bound:".

### P-14 (low). The sealed end departs from PLAN 5.5 without saying why

- **PREREG lines 23-26.** PLAN 5.5 item 5: "Sealed years: 2020-01-01 to the last trading day before the seal"
  (`PLAN.md:335`). The seal comes in late November or later, so the last day before it is later than 2026-10-28.
- **Fix** (add to line 23): "The end is the store's last day, not the last trading day before the seal, by the owner's
  decision 1 of 23 Nov (`research/m4_kickoff.md`)."

### P-15 (low). The trial plan's hash is cut short

- **PREREG line 11:** "the trial plan's SHA-256 is `4a9a45a1...`".
- **Fix:** give it whole: `4a9a45a1238aad3b704a18f27c9bac046e13bbadf981ff642fc3d78986861e2f`
  (`research/m3_dev_report.md:3`).

### P-16 (low). "3 of 6" is hard-coded

- **PREREG line 90:** "in at least half of the years (3 of 6)".
- **Evidence.** The code counts only years with days in both parts, and "at least half" is twice the count above at
  least that number (`eval/switch_day.py:69-71`).
- **Fix:** "in at least half of the years counted (those with days in both parts, as `eval/switch_day.py` counts them;
  3 of 6 when all six count)".

## Fixes (23 Nov, in the uncommitted PREREG.md)

All 16 findings were taken, with the skeptic's wording or close to it. P-1: lag 6 for H1 to H3, with lag 7 in the
robustness column. P-2: the writer `research/m4_sealed_report.py` is named as the scoring code, to be built and tested
before the seal (it does not exist yet: a new M4 step). P-3: the replays run before the writer and `ledger`. P-4, P-5,
P-11: the void, rerun, re-seal and "H3 not claimed" rules. P-6: the suite with `CHRONO_SLOW_LEAKS=1`, before the lock
and again after it. P-7: the older check's day sets. P-8: the deflated Sharpe's inputs. P-9: `PREREG.md -text` and
`seal.lock -text` in `.gitattributes`. P-10: the dev check, named as `research/m4_t09_check.py` (T09 alone through the
dev path, as the lead asked for step 2). P-12 to P-16: the boundaries and NaNs, H3's wording, the sealed end, the full
plan hash and the counted years.
