# Fixes after the M3 review (23 Nov 2026)

The owner took all six of the review's recommendations on 23 Nov ("Yes, take all six", relayed by the lead). The
review is `research/review_m3_2026-11-23.md`. These fixes are on the branch `claude/m3-review-76bcd4`, on top of
`89f35f7`. No judge ran: the only fixes near the time wall are the three the owner named (W3-1, W3-3, W3-4).

| Item | What changed | Where |
|---|---|---|
| S3-1 | The "turnover-matched" claim is corrected: the hold is matched, the turnover is not, so the after-cost baseline rows favour live. Compare the baselines before costs. The hashed plan block is unchanged (its hash still prints `4a9a45a1...`); a dated correction sits after the owner's ruling 4 | `agent/baselines.py` docstring, `research/m3_dev_report.md` (header note and "Matched baselines"), `research/m3_dev_runs.py` (the report's note), `research/m3_kickoff.md` (ruling 4) |
| D3-8, S3-1, S3-2 | Three M4 entry rules for PREREG: the plain, point-estimate reading of the 10.1 gate, reported as "warning" or "no warning" with a power note when t is below 1.645; whether the sealed baselines get the band; one test of live against the daily mean of the 5 placebo seeds | `research/m3_kickoff.md`, "M4 entry rules" |
| D3-8 | Step 7's outcome is "no warning" under the plain reading | `research/m3_kickoff.md` (step 7), `research/m3_older_vintage.md` (top and "For the owner") |
| W3-1 | The window test views dev dates only (2016-12-30, 2018-06-29, 2019-12-31) on a World without `allow_sealed`. A new test pins the files that may open the sealed years by hand, with the two data audits that read no labels named in the rule | `tests/test_embedding_window.py`, `tests/test_leaks.py` (`test_only_the_named_files_open_the_sealed_years_by_hand`), `research/m3_kickoff.md` (the time-wall rule) |
| W3-3 | Track A keeps the latest label among days trimmed from `recent` (they stay in the sums). The split counts it in `train_latest` and raises if any training label showed at or after the first validation decision. Frozen twins copy it. Three new tests | `agent/track_a.py`, `tests/test_track_a.py` |
| W3-4 | `replay` runs `seal.check` on the run's first and last sessions, so a run reaching the sealed years needs the seal. One new test | `sim/simulator.py`, `tests/test_report.py` |
| W3-2, W3-7, S3-4 | The placebo's docstring now says each company keeps its link count, a pair can repeat and be dropped, and a later view may shuffle a group cut by the window differently | `agent/placebo.py` |
| D3-2 | The first freeze's text was never committed, said where its hash is given | `research/m3_kickoff.md` |
| D3-4 | The kickoff's result summary also names the end-of-2018 twin, momentum's lead and the long-only shortfall | `research/m3_kickoff.md` |
| D3-6 | One line under the trial table gives T03's 0.00067 margin and T04's drop | `research/m3_dev_report.md` |
| D3-9 | "Just as well" replaced by the difference and its interval | `research/m3_older_vintage.md` |
| D3-10 | The two runs' commits are named, with the rerun a sealed repeat needs | `research/m3_older_vintage.md` |
| D3-12 | The sealed-year line carries its caveat | `research/m3_kickoff.md` |
| K3-5, D3-13 | Both digests refreshed: `code_map.md` (89f35f7 plus these fixes, every M2 and M3 module) and `plan_rules.md` (PLAN at `323f2e9`, line numbers checked against the text) | `docs/digests/` |
| K3-6, K3-7 | README has an M3 status section, the M3 commands and the suite's real time | `README.md` |
| K3-8 | The kickoff's top says where M3 stands, with the commit of each step | `research/m3_kickoff.md` |
| K3-9 | AGENTS names steps 1 to 7, the review and the older-vintage doc | `AGENTS.md` |
| K3-10 | The report names the ledger by its repo path, and the writer now does so | `research/m3_dev_report.md`, `eval/report.py` |

`research/m3_dev_report.md` stays a dated snapshot, edited by hand. A rerun of the writer would keep the S3-1 header
note and the repo path, but not the paragraph under "Matched baselines" or the line under the trial table (D3-6):
those two are hand notes.

Tests: `D:\venvs\chrono-trader\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` on the fixes, 23 Nov:
"513 passed, 1 skipped, 9 warnings in 2315.71s (0:38:35)", pytest exit code 0. That is 508 plus the five new tests
(three for W3-3, one for W3-4, one for W3-1); the skip is the slow leak test, as before.
