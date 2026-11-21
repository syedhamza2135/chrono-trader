# Fixes for the review of 21 Nov 2026

The fixes for the findings in `research/review_2026-11-21.md` that live in master's code and docs. Branch
`claude/review-fixes-1121-957117`, cut from `c0a9b7f`. Nothing is committed: the owner approves each commit.

Checks written for these fixes are in `research/review_2026-11-21_fixes/`. Python is
`D:\venvs\chrono-trader\Scripts\python.exe`.

## The store is rebuilt

After the owner approved it (through the lead, 21 Nov), `D:\chrono-data\store` was copied to
`D:\chrono-data\store_backup_2026-11-21` (all 8 files hash the same) and rebuilt with `python -m
data_pipeline.store`, with `CHRONO_ENV_FILE` set to the main checkout's `.env`. The rebuild took 3 min 20 s and wrote the same counts
(`counts.json` and `research/audit/store.md` unchanged).
- `research/review_2026-11-21_fixes/compare_rebuild.py`, output in `compare_rebuild_output.txt`: bars, opens,
  stories, story_entities, membership and identity are identical to the backup. Labels keep the same 1,419,403 rows
  and the same `end` and `at_close`. Exactly 55 label values changed, all 55 expected and no other, each within
  4.4e-14 points of the value predicted from the old store. `end_open_time` changed on 36 labels, all of them
  expected and each to the predicted time.
- The backup stays in `D:\chrono-data\store_backup_2026-11-21` until the owner decides to remove it.

## Medium

**M-2. Ex-date labels used that day's closes. Fixed.**
- `reference/price_events.csv` has two new last columns, filled on 55 of the 58 `total_return` rows:
  - `open_value`: what one share held the evening before is worth at the ex-date's official opens, parent open x its
    ratio + ratio x other security's open + cash.
  - `open_value_time`: when the last of those opens printed, in UTC.
  Each row's evidence ends with the opens used and the open-based total return over the store's previous close.
  (The first version stored that return as `open_return`; the judge's J-3 and J-5 below led to this form.)
- `research/ex_date_opens.py` fills them from each row's own formula. The parent's open, its print time and its
  previous close come from the store. Each other security's open is the listing exchange's opening print from
  Alpaca's auctions endpoint, asof the ex-date, so a reused ticker (ARNC, DLPH, AA, IR) is the new security. Cash, and
  values the row fixes (OXY's warrants at a later close), stay as they are.
- The 3 rows left blank are plain price ratios with no distribution added: JCI 2016-09-06 (the 0.955 consolidation),
  IR 2020-03-02 and GE 2019-02-25 (raw returns). There the close-based end piece already cancels the closes (the
  judge measured gaps of 0.004 points or less, the csv's rounding).
- `data_pipeline/store.py`: `apply_events` puts both into the series (`open_val`, `open_val_time`). `labels` ends a
  label on that day with `open_val / close[j - 1]`, after the closes up to the day before, so the closes cancel even
  if the close before the ex-date is corrected later. The label's `end_open_time` is the later of the parent's open
  and `open_val_time`. The bars keep the close-based `ret`. The module docstring says so.
- Tests (`tests/test_store.py`):
  - `test_a_label_that_ends_on_an_ex_date_values_the_distribution_at_the_open`: a made-up spin-off; the label is
    (5.5 + 5.0) / 10.8 - 1 whatever the two closes are, and it shows at the spin-off's later open. It failed against
    the code before the fix.
  - `test_every_distribution_with_a_value_has_its_value_at_the_opens`: 55 rows with a sum in their formula, each
    with both columns; the other 3 blank. It failed against the csv before the fix.
  - `test_an_ex_date_label_divides_by_the_series_own_previous_close` (J-5): a corrected close before the ex-date
    leaves the label unchanged. A frozen return, as in the first version, would have moved it.
- Effect on the labels (`research/review_2026-11-21_fixes/m2_label_changes.py`, predicted from the old store): 55
  labels end on one of these ex-dates, 54 of them start on a member day. They move under 0.1 points on 6, 0.1 to 1 on
  22, 1 to 3 on 15 and 3 or more on 12. The review's measured rows move by the size of its error: AIV 2020-11-03
  +2.09 (review: -2.09), NLOK 2020-02-03 +1.11 (review: -1.11), EQT 2018-11-13 -3.07 (review: +3.07 whole label). The
  largest moves are AIV 2020-12-15 -17.47, HWM 2020-04-01 +10.67 and CTVA 2026-10-01 -9.39 points. On 36 of the 55,
  another security's open printed after the parent's, so the label now shows later (the latest: 10:07 New York, HWM
  2020-04-01).
- For the owner (also the judge's J-4): 15 spun-off securities opened with a print under 10,000 shares on their first
  day (the script prints them; ZIMV's was 495 shares, ARNC's 4,398). Those opens are the listing exchange's official
  ones, but a thin first-day open can be far from the day's trading: Arconic Corp opened at more than twice its close,
  and HWM's label moves +10.67 points. A rule for thin opens is the owner's call.
- L-S5 (labels visible at 9:30 on the ex-date that used that day's close) is fixed with it: the 55 labels no longer
  use the ex-date's close and show only once every open they use has printed, and the other 3 cancel the close.

**M-1. A file-reading agent passed the boundary test. Fixed as the review proposed, without a sandbox.**
- `tests/test_boundaries.py`: `agent_name_problems` now checks every name in an import as well: each part of the
  module's path, the imported name and its alias. So `from pandas import read_parquet as rp` is caught at the import.
  `fromregex`, `npyio`, `lib`, `ctypes`, `builtins`, `tempfile`, `glob`, `mmap`, `urllib` and `zipfile` joined
  FORBIDDEN. The one allowed import, `from world.view import View`, is exempt from the path check.
- New test `test_the_checks_catch_an_agent_that_reads_future_labels_from_a_file`: the review's leaky agent (it reads
  future labels from a parquet file, plus an aliased numpy `load` and `fromregex`). It fails against the old check
  and passes now; each of the three imports is caught on its own line.
- After the judge's J-1 and J-2: `__dict__` is no longer exempt, `query`, `get_type_hints`, `ForwardRef`,
  `_evaluate` and `singledispatch` joined FORBIDDEN (they run code held in a string), and `load_` joined the
  prefixes (`scipy.sparse.load_npz`). No file in `agent/` uses any of them. The leaky agent in the test now also uses
  `load_npz`, `pd.__dict__`, a query string and `typing.get_type_hints`, and the test asserts each is caught.
- Rerun of the skeptic's Part A (`research/review_2026-11-21/scripts/skeptic_timewall/m1_boundary.py`): all 7
  snippets are now caught, the 5 that got past before included. Rerun of the judge's `m1_bypass.py`: every snippet
  is caught except `from ..world.view import View`, which is the allowed import written relatively (no hole, the
  judge found).
- Not built: a process that cannot read `DATA_DIR` or `reference/` for `decide()`. It is the only real guarantee, and
  the module docstring names it as a later option. A name check can always miss a new way to read files.

## Low and info

| Id | Result | Where, and the check |
|---|---|---|
| L-T1 | Fixed | `eval/leaks.py`, `non_interference`'s docstring: the check uses the wall's own rules, so a wrong rule passes it; the rules have their own tests, such as `same_day_bars` in `tests/test_leaks.py` |
| L-T4 | Fixed, opt-in | `tests/test_leaks.py::test_non_interference_across_the_dev_years_on_the_real_store`: three runs in Oct 2017 to Nov 2017, Jul to Aug 2018 and Apr to Jun 2019, each under all three perturbations. It runs only with `CHRONO_SLOW_LEAKS=1`, so the default run shows one more skip |
| L-T5 | Fixed | `world/view.py` docstring lists `labels.end_open_time` and `stories.n_companies` |
| L-S1 | Fixed (the `traded` part) | `sim/simulator.py`: an exit sale at a last close now counts in `traded`. Test: `test_a_company_that_stops_trading_is_sold_at_its_last_close` asserts `traded` is 0.4 on the exit day (the old code left 0) |
| L-S4 | Fixed (the flag part) | `sim/simulator.py:run` puts `allow_sealed` back after the run, also on an error. Test: `test_a_sealed_run_opens_the_sealed_years_for_that_run_only`. Logging sealed runs stays an M4 item |
| L-S5 | Fixed by M-2 | see M-2 |
| L-C1 | Fixed | `research/m1_kickoff.md:187`: CCE's label is +3.01% with the row (the old store), not +0.58%; +3.52% in the rebuilt store, with M-2 |
| L-C2 | Fixed | `data_pipeline/identity.py:61`: the Wikipedia revision stamp is converted to New York before `.date()` |
| D3 | Fixed | `research/m1_kickoff.md:73-74`: LLY 2019-08-12 has an official open and only its closing print is missing (store check: the open is there, `official_close` is empty); 2018-01-24 has no open, as stated |
| R1 rest | Fixed | `data_pipeline/news.py:73`, `split.py:59`, `wikipedia.py:166`: New York's date instead of the machine's (Pakistan's date runs up to 10 hours ahead) |
| I-2 | Fixed | `README.md` and `AGENTS.md`: the test time and count (see the test run below) |
| L-P1 | Fixed | PLAN L218: the backtest sees no more than the live job, and can see less (an edited story shows only from its last edit). M5 measures the live lag |
| L-P2 | Fixed | PLAN L3: M1 is built and reviewed |
| L-P3 | Fixed | PLAN L221, L230 and L541 (L535 before the 9.4 rewrite): a label is usable once it is visible in the view; the k-2 rule alone would take 525 labels on 16 dates that are not |
| L-P4 | Fixed | PLAN 9.4 rewritten from `docs/digests/store_tables.md`: one `bars` table, `opens` and `labels`, no `available_at`, and the real membership and identity columns. `embeddings` is marked "M2, not built yet" with its columns unchanged |
| L-P9 | Fixed | `docs/digests/plan_rules.md`: 106 cites moved by one line, and all cites carried through this branch's PLAN edits (`research/review_2026-11-21_fixes/fix_digest_lines.py`). The skeptic's check `l8_digest_offsets.py` now finds 4 lines whose best match is a neighbour; 2 of the 4 are ranges and 2 (digest lines 179 and 365) were left as they are. The digest lines for the edited PLAN lines were rewritten to match |
| L-S2 | Not fixed: for the owner | The 119 window-cut exits are a documented choice: `store.py` counts them as `exits_window_cut` and `research/audit/store.md` reports them. Setting `at_close` only where a company stopped changes which labels exist; all 119 are on non-member days, 11 to 17 days after the last member day |
| L-S3 | Not fixed: the review proposes no fix now | Decide from facts known at the open if agents hold non-members |
| I-1 | Not fixed: changes a PLAN rule | PLAN L218 says `updated_at` plus 15 minutes; `max(created_at, updated_at)` would change it. 4 stories differ, none visible before creation. The owner decides |
| D4 | Not fixed: a dated count | PLAN L25 and `research/audit/auctions.md:9` (1,371,723) count M0's member stock-days; the store's 1,371,711 drops 12 bars after the data end. The stage 3 reviewer judged the passage fine |

## Left out, unchanged

- M-3 and M-4: for M2. They go into the M2 step 2 brief.
- L-P5, L-P7 and L-P8: for M2 (the M2 note is on `claude/awesome-panini-89f869`).
- L-P6 (rebase the M2 branch): for the owner.
- L-T2 (a failure label at its public evidence time, a change to PLAN L26): for the owner.
- R2 (whether derived CSVs such as `adjustment_events.csv` fall under the licensing rule): for the owner.

## The judge

The first session skipped the judge: usage was above the 55% gate. After the 5-hour window reset, `chrono-judge` ran
on Opus at high effort on the M-1 and M-2 changes (`research/review_2026-11-21_fixes/judge_m1_m2.md`, scripts in
`judge_scripts/`). It found the formula and the 55 values right (each recomputes exactly from the store and
Alpaca), and raised six points. J-1 and J-2 were checked by rerunning `m1_bypass.py` before the fix, J-3 by this branch's own count (36,
`compare_rebuild.py`), and J-5 by the new test. J-4 and J-6 were not rechecked; they need no code change here. The judge's M-2 scripts check the
first version (`open_return`); after J-5 the same checks are covered by `compare_rebuild.py` and the new tests.

| Id | Severity | Result |
|---|---|---|
| J-1 | medium | Fixed. `pd.__dict__[...]`, a query string and a string annotation read a file and passed the check (`m1_bypass.py` reproduced all three). See M-1 |
| J-2 | low | Fixed. `load_npz` passed; `load_` is now a forbidden prefix |
| J-3 | low | Fixed. 36 labels used an open that printed after their `end_open_time`; `open_value_time` now sets it. The compare script counts 36 too |
| J-4 | low | For the owner: a rule for thin first-day opens (see M-2) |
| J-5 | low | Fixed. The csv holds the value at the opens and `labels` divides by the series' own previous close. Test: `test_an_ex_date_label_divides_by_the_series_own_previous_close` |
| J-6 | info | Not fixed, older than M-2: the OXY 2020-07-02 row values its warrants at the 2020-08-04 close, a month later, as the row says. It now enters the label too. For the owner |

Other agents: the full test runs were run directly in the background rather than through `chrono-checker`, to save
usage. `docs/digests/code_map.md` was not refreshed: no public function was added, renamed or given new arguments
(`store.labels` and `apply_events` read two more columns, and `simulator.run` restores a flag).

## The test run

- Final full run, after the judge's fixes and on the rebuilt store, `python -m pytest tests -q -p no:cacheprovider`:
  263 passed, 2 skipped, 6 warnings in 230 s (3 min 50 s), in `research/review_2026-11-21_fixes/tests_output.txt`.
  Before the fixes: 258 passed, 1 skipped. The 5 new tests are 3 for M-2 (one of them J-5's), 1 for M-1 and 1 for
  L-S4. The 2 skips are the embeddings table (M2) and the opt-in slow leak test.
- The opt-in L-T4 test with `CHRONO_SLOW_LEAKS=1`, run once before the rebuild: 1 passed in 614 s (10 min 14 s), in
  `research/review_2026-11-21_fixes/slow_leaks_output.txt`. All 9 (run, perturbation) pairs on the real store pass.
  It was not rerun on the rebuilt store.
