# M3 review, checker (Sonnet), 23 Nov 2026

Worktree `m3-review-76bcd4`, branch at `89f35f7`. M3 is `git log master..HEAD`: 8 commits over master `6894217`. I changed
and committed nothing. I did not read `.env` and did not run the test suite. Scratch scripts and output are in
`C:\Users\syedh\AppData\Local\Temp\claude\a742097078b03236\6cc4007d-fcb6-47d2-8b04-650f79c5109d\scratchpad\`
(`repro.py`, `rebuild.py`, `rebuilt_report.md`).

## Summary

| id | rating | what |
|---|---|---|
| K3-1 | info | All 12 headline numbers reproduce from `D:\chrono-data\runs\m3_dev` and match the report |
| K3-2 | info | Git holds no raw data and no charts |
| K3-3 | info | No em-dashes and no en-dashes in any changed file |
| K3-4 | info | No Claude attribution in the 8 commits |
| K3-5 | medium | `docs/digests/code_map.md` is stale: it knows none of the M3 code |
| K3-6 | medium | `README.md` lists none of the new M3 modules and none of the M3 run commands |
| K3-7 | low | `README.md` still says "Nothing is trained yet" and "About 10 minutes" for the tests |
| K3-8 | medium | `research/m3_kickoff.md` "Where things stand" is stale and never says steps 1 to 7 are done and step 8 is under way |
| K3-9 | low | `AGENTS.md` says "steps 1 to 6"; step 7 is done |
| K3-10 | low | The dev report's trials section cites the old worktree path and 19 rows; the ledger has 20 |
| K3-11 | info | The ledger marks all run rows after T01 dirty; known and explained |

## K3-1 Reproduction of the headline numbers (info, pass)

Method. `repro.py` loads the runs saved by `research/m3_dev_runs.py` (`D:\chrono-data\runs\m3_dev\compare\*` and
`T01` to `T09`), uses `m3_dev_runs.load`, `dev_labels`, `metrics.daily_rank_ic`, `metrics.within`,
`metrics.book_returns`, `stats.nw_mean`, `stats.book_stats` and `eval.switch_day.switch_day`, and reads `stage1.json`
and `stage2.json`. Command: `D:\venvs\chrono-trader\Scripts\python.exe repro.py`. I also ran `rebuild.py`, which
repeats `report_step` with the output sent to the scratchpad and no charts, then diffed the result against
`research/m3_dev_report.md`. The diff shows only the two differences in K3-10 and the chart list (charts were not drawn).
So every number in the report, not just the 12 below, reproduces.

| number as stated | report line | reproduced | match |
|---|---|---|---|
| T09 mean daily rank IC 2017 to 2019, 0.0076, NW t 1.38 | 50 | 0.0076265, t 1.38026, n 753 | yes |
| Long-short Sharpe after 5 bps, -0.24 | 83 (also 133) | -0.243228 | yes |
| Long-short Sharpe before costs, 0.18 | 83 (also 132) | 0.182519 (the 0 bps replay) | yes |
| Price-only gap, +0.0069, t 0.74 | 70 | +0.006869, t 0.7356, n 753 | yes |
| Frozen twin, end of 2016, +0.0179, t 2.61 | 59 | +0.017853, t 2.6051, n 753 | yes |
| Frozen twin, end of 2017, +0.0061 (t 0.87) | 62 | +0.006072, t 0.8688, n 502 | yes |
| Frozen twin, end of 2018, -0.0150, t -1.76 | 64 | -0.014972, t -1.7581, n 251 | yes |
| Placebo seed 5, IC 0.0130, t 2.47 | 207 | 0.013044, t 2.47288 | yes |
| Stage 1 pick: T01 IC 0.00763 | `m3_kickoff.md` 551 (report 105 shows 0.0076) | 0.0076265 (`stage1.json`) | yes |
| Stage 1 pick: T03 IC 0.00829 | `m3_kickoff.md` 551 (report 107 shows 0.0083) | 0.0082937 (`stage1.json`) | yes |
| T09 Sharpe -0.243 against T06 -0.460 | report 112 and 109; `m3_kickoff.md` 554 | -0.243228 and -0.459724 (equity files and `stage2.json`) | yes |
| Switch-day pooled difference -0.0107, p 0.62 | 280 | -0.010655, se 0.034498, t -0.30885, p 0.62128; 60 and 693 days; warnings (a) and (b) both False | yes |

Other checks that agree: stage 1's winner T01 (T03 is ahead by 0.00067, inside the 0.001 tie); stage 2's winner T09
`{"band": 15, "hold": 5}`; T02 -0.00262 (t -0.457) as in `m3_kickoff.md` 551.

## K3-2 Git holds no raw data and no charts (info, pass)

Commands and output:
- `git diff --name-only master..HEAD | grep '^runs/'` minus `runs/trials.csv` and `runs/settings/*.json`: nothing. The
  M3 diff holds `runs/trials.csv` and 20 settings files.
- Same diff for `.parquet .npy .svg .png .csv .pkl .feather .h5 .jpg .zip` other than `runs/trials.csv` and
  `reference/price_events.csv`: nothing.
- `git ls-files` for `.parquet .npy .svg .png` and for `runs/`: only `runs/trials.csv` and the settings json. The other
  tracked `.csv` files (`reader/probes*.csv`, `reference/*.csv`, `research/audit/*.csv`) all predate M3 and are not in
  the M3 diff.
- `.gitignore` now has `runs/*`, `!runs/trials.csv`, `!runs/settings/`.
- The settings json (20 files, 21,303 bytes in all): I walked every key. They hold only parameters (agent and its
  parameters, band, hold, penalties, pooling, seeds, trial and stage names, `cost_bps`, dates, `plan_sha256`,
  `embedding_window_days`, `vintage_offset`, `embeddings_store: reader_older`, `check: older_vintage`, `dropped`).
  The longest string is under 80 characters. No price, headline or story text.
- `runs/trials.csv` has 20 rows and 11 columns (`run_id, logged_at, commit, dirty, settings_hash, first, last, agents,
  out_dir, trial, status`); `out_dir` is a `D:\chrono-data\runs\...` path or a note. No data.

## K3-3 Dashes (info, pass)

Scanned every file in `git diff --name-only master..HEAD` that exists at HEAD for U+2014 and U+2013 with a Python
script. Em-dashes: 0 lines. En-dashes: 0 lines. No file:line to report.

## K3-4 Claude attribution (info, pass)

`git log master..HEAD --format=%H%n%an%n%ae%n%B`, then grep (case-insensitive) for `co-authored`,
`noreply@anthropic`, `generated with`, `claude`, `anthropic`: no match (exit 1). A second count of "claude" in the
message bodies gave 0. All 8 commits have the owner as author and committer, with the owner's own address; no
other name or address.

## K3-5 The code map is stale (medium)

`docs/digests/code_map.md:3` says "Commit dd40a5f. Date 2026-11-21". Last commit on the file is `c0a9b7f` (21 Nov).
Since `dd40a5f`, `git diff dd40a5f..HEAD --stat -- world sim eval agent reader data_pipeline` shows 28 files and
3,555 added lines. Against that:
- None of the M3 modules is in the map: `agent/track_a.py`, `agent/baselines.py`, `agent/placebo.py`,
  `eval/stats.py`, `eval/switch_day.py`, `eval/report.py`, `eval/charts.py`, `eval/trials.py`, `eval/benchmarks.py`,
  `data_pipeline/benchmarks.py` (0 mentions each). `eval/metrics.py` is there as "(18 lines)" at `code_map.md:80`;
  the M3 diff adds about 245 lines to it.
- It lists no M2 module either (`reader/embed.py`, `reader/cutoff.py`, `reader/download.py`). `code_map.md:98` says
  "The embedding job is not built yet".
- Its line counts and line numbers for `world/world.py` (185 lines, `code_map.md:37`), `sim/simulator.py` (135,
  `:61`), `eval/leaks.py` (142, `:72`), `world/view.py` (`:33`) and `reader/vintage.py` (28, `:100`) are older than the
  edits in `9d04ced`, `001d01c` and M2. Last commits touching them: world.py, simulator.py, leaks.py and vintage.py
  at `001d01c`; view.py at `9d04ced`.
- A step 8 judge or a later session that reads the map for M3 will not find the agent, the harness or the report writer.

## K3-6 README does not list the new M3 modules or commands (medium)

`grep` of `README.md` for `track_a`, `baselines`, `placebo`, `switch_day`, `report`, `charts`, `trials`,
`benchmarks`, `m3_dev_runs`, `m3_compare_timing`, `track_a_timing`, `m3_trial_plan`: no hit. The M3 diff to
`README.md` is two lines only (`README.md:73-74`, the step 7 `run-older` commands and `m3_older_vintage.py`).
Missing from the Commands table (`README.md:46-76`):
- `python research/m3_dev_runs.py stage1 | stage2 | compare | report` (`research/m3_dev_runs.py:2-7`).
- `python data_pipeline/benchmarks.py` (it has a `__main__` at `data_pipeline/benchmarks.py:190`; SPY and the sector table).
- `python research/m3_trial_plan.py` (the plan hash and planned rows, `m3_trial_plan.py:73`).
- `python research/track_a_timing.py` and `python research/m3_compare_timing.py` (timing runs).

Missing from the Status section (`README.md:7-32`): any M3 paragraph. The time-wall line (`README.md:22`) still says
"a toy agent in `agent/`" and lists `eval/` as "the daily rank IC and the non-interference check".
`AGENTS.md:4` says the commands are in the README, and `AGENTS.md:55` says the pipeline modules are listed there.
The modules the brief names (agent/track_a.py, agent/baselines.py, agent/placebo.py, eval/metrics.py, eval/stats.py,
eval/switch_day.py, eval/report.py, eval/charts.py, eval/trials.py, eval/benchmarks.py, data_pipeline/benchmarks.py)
appear nowhere in `README.md`.

## K3-7 README status and test time are out of date (low)

- `README.md:32`: "Nothing is trained yet." Track A fits a ridge in the dev runs (`research/m3_dev_report.md`).
- `README.md:51` (the pytest row): "About 10 minutes". `AGENTS.md:51-52` says 35 to 52 minutes for 508 tests, and
  `research/m3_kickoff.md:598` records 36 minutes 55 seconds.

## K3-8 The M3 kickoff note does not say where M3 stands (medium)

`research/m3_kickoff.md`, "Where things stand" (lines 12-23):
- Line 21: "344 pass and 1 skips, in 6 to 11 minutes (AGENTS.md, Commands)". Now 508 pass and 1 skip
  (`m3_kickoff.md:598`, `AGENTS.md:51`).
- Line 23: "This note is on the branch `claude/m3-kickoff-56264f`, cut from master `6894217`. Uncommitted." It is
  committed in the 8 M3 commits.
- Nothing in the file says steps 1 to 7 are done and step 8 (the review) is under way. Step 7 has its own section
  (`:569`, "started 23 Nov") and a result entry (`:616-620`); step 8 appears only as a future review
  (`:134`, `:609`). The build-order table is the plan, not the status.

`AGENTS.md:22-24` points to this note as the place to read the state.

## K3-9 AGENTS.md says steps 1 to 6 (low)

`AGENTS.md:22-24`: "M3 ... is under way on the branch `claude/m3-kickoff-56264f`: read `research/m3_kickoff.md` ...
and steps 1 to 6." Step 7 is done (`research/m3_older_vintage.md`: not informative). It does not mention
`research/m3_older_vintage.md` or the review. The test count at `AGENTS.md:51` (508 pass and 1 skip) matches
`research/m3_kickoff.md:598`; I did not re-run it (the session runs the suite). The M3 status line is right apart from
"1 to 6".

## K3-10 The dev report's ledger line is older than the ledger (low)

`research/m3_dev_report.md:10`: "8 trials in `C:/Users/syedh/dev/chrono-trader/.claude/worktrees/m3-kickoff-56264f/runs/trials.csv`
(19 rows)." The ledger in this worktree has 20 rows: step 7's row `20261123T061536_0f452837` (`live_older_vintage`, no
trial name) was added after the report. The rebuilt report shows 20 rows and that extra row at its line 33. The trial
count (8) and every number are unchanged. The path names another worktree, so a reader cannot check it from here.
Also the report's chart section (`:284-290`) points to `D:\chrono-data\runs\m3_dev_report_charts\*.svg`; I did not
check that those files exist.

## K3-11 Dirty flags in the ledger (info)

In `research/m3_dev_report.md:24-32`, T02 to T09 and the comparison row say `dirty True` and T01 says `False`. Cause
(`research/m3_kickoff.md:563-565`): the ledger itself is in git, so each run's row dirties the tree; the code was at
`83a35cd` throughout. The ledger's `commit` column is `83a35cd` for all of them. No other cause found.

## Test suite

Filled in by the session, which ran the suite in the background at `89f35f7`:
`D:\venvs\chrono-trader\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` printed "508 passed, 1 skipped,
9 warnings in 2584.95s (0:43:04)". Pytest exit code 0.
