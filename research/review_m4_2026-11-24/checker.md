# M4 review: Sonnet checker (24 Nov 2026)

Scope: `git log a9a216e..095a855` (5 commits), branch `claude/m4-review`. Nothing changed in the repo or in
`D:\chrono-data\runs\m4_sealed` (the report was rebuilt into the scratchpad). The test suite was not run.

## 1. Headline numbers, recomputed

Command: a scratch script (`...\scratchpad\m4\check\rebuild.py`) that imports `research/m4_sealed_report.py` at HEAD, points
its `OUT_MD` at `...\scratchpad\m4\check\rebuilt.md`, and calls `main()`. Python: `D:\venvs\chrono-trader\Scripts\python.exe -I`.
It printed `wrote ...\rebuilt.md: Failure: H2 or H3 does not hold` (2 min 36 s). Then `diff rebuilt.md research/m4_sealed_report.md`.

Diff result: 3 differing places, all the trials ledger, which has 2 more rows in the repo now than when the report was
written (the writer ran before `ledger`, as designed). Report line 89 says 21 rows; the rebuild says 23. Rebuilt lines 114-115
are the 2 sealed rows. Every test, p-value, table and the outcome match byte for byte. I also checked each p by hand with a
normal tail from its printed t (one-sided): all agree to 4 places.

| Item | Report (line) | Reproduced | Match |
|---|---|---|---|
| H1 mean IC, t, p | 0.0104, 2.2735, 0.0115 (21) | same | yes |
| H2 p | 0.2117 (22, 29) | same | yes |
| H3 vs price-only p | 0.2001 (23) | same | yes |
| H3 vs placebo mean p | 0.1219 (24); H3 = larger = 0.2001 (30) | same | yes |
| Holm | H1 yes, H2 no, H3 no (28-30) | same (0.0115 <= 0.05/3; 0.2001 > 0.05/2, stops) | yes |
| Overall label | Failure: H2 or H3 does not hold (13) | same; PREREG.md:141 defines Failure so | yes |
| Switch-day pooled p | 0.2070, t 0.8168, 120 and 1388 days (54); no warning (56) | same | yes |
| Older-vintage (b) p | 0.6265, live minus older mean -0.0010, t -0.3227 (70) | same | yes |
| Older-vintage gate | open, (a) no, (b) no, no warning (72) | same (gate open: rule mean 0.0049 > 0) | yes |
| Deflated Sharpe, N | dsr 0.0003, n_trials 8.0000, var 0.0013, sr_annual -0.4803 (80) | same | yes |

N 8 is right: 8 dev trials plus 0 `--again` runs (the run log shows `again: false` for both parts).

## 2. Git: no raw data, no charts

`git diff --name-only a9a216e..HEAD` lists 25 files. Under `runs/`: only `runs/trials.csv` and 3 files in `runs/settings/`.
No `.parquet`, `.npy`, `.svg` or `.png`. The only `.csv` is `runs/trials.csv` (`reference/price_events.csv` is not in the diff).
The report has no chart links (grep for svg, png, charts: none).

The 3 settings files (`380ebc4f...`, `755dcf39...`, `c7780628...`) hold only agent parameters (band, hold, penalties and so on),
dates, cost, the plan hash, table sizes and Parquet footer hashes, the embeddings' row count and ids hash. No prices, no
text. `seal.lock` holds the commit, the PREREG hash, the two settings hashes, the sealed dates and `written_at`. Nothing else.

## 3. Attribution

`git log a9a216e..HEAD --format=%H%n%an%n%ae%n%B`: all 5 commits have author and committer `syedhamza2135`
(`syedhamza2135@gmail.com`). Grep for Co-Authored-By, noreply@anthropic.com, "Generated with" and "Claude" in the
messages: no match. Clean.

## 4. Style

Em-dashes (U+2014) in every file the diff changed: none, in files or in added lines. En-dashes (U+2013): none.

## 5. Docs

README: the 3 M4 commands are listed (`README.md:88-90`: `m4_sealed_run.py`, `m4_t09_check.py`, `m4_sealed_report.py`).
But the Status section has no M4 paragraph (last is M3, `README.md:31`).

## Findings

- **K4-1 (high), `AGENTS.md:27-29`.** It says M4 "has started", on the branch `claude/m4-kickoff`, with steps 1 to 3, and that
  "Nothing is sealed, and the sealed years are still shut." That is false now: the seal is written (`423a9c2`), the sealed run
  happened once and the report is published (`095a855`, outcome Failure). A new session would think the run can still be
  planned. It needs the status, the sealed result (H1 holds, H2 and H3 do not, Failure), the run-once rule, and the branch
  `claude/m4-review`. It does not give the sealed result anywhere.
- **K4-2 (medium), `README.md:31-35` (Status).** No M4 paragraph: it does not say the seal was written, the sealed years ran once, or
  the report is `research/m4_sealed_report.md`. The command table (88-90) is complete.
- **K4-3 (medium), `research/m4_kickoff.md:15, 188, 244`.** Line 15 says the note is "Uncommitted" and sits on `claude/m4-kickoff`; the headings
  at 188 ("Step 1 ... (uncommitted)") and 244 ("Steps 2 and 3 (23 Nov, uncommitted)") are out of date, since all of that is
  committed. The file ends at line 279 with step 3. It has no record of steps 4 to 6 (the seal, the run, the report) and no result.
- **K4-4 (medium), `docs/digests/code_map.md:3, 61, 69, 152`.** Header says commit `89f35f7` plus M3 fixes uncommitted. The sources have moved:
  `sim/seal.py` was last changed at `6401ee7` and is 199 lines (digest says 62, heading at line 61); `sim/simulator.py`
  280 lines (digest 241); `eval/report.py` 288 (digest 270, last change `7b9a138`); `world/world.py` same 386 lines but 12 changed
  lines (`6401ee7`). New seal functions (`check` with git, `write`, `begin`, `started`, `require_started`, `prereg_hash`, `Git`) are
  not described. The digest itself was last committed at `a2a5f3e`.
- **K4-5 (low), `docs/digests/plan_rules.md:1, 439, 462, 463`.** PLAN.md has not changed since `323f2e9`, so the plan text in the digest is
  current. But the code cites `sim/seal.py:43-61`, `20-22`, `44-51` (439, 462, 463) point at the old 62-line file and are stale.
- **K4-6 (low), `AGENTS.md:56-57`.** The test count is 534 pass and 1 skip "after M4 step 3". Steps 4 to 6 added no test files in the diff
  (the 4 changed test files are from steps 1 to 3). So 534 is probably still right, but I did not run it. The session's run decides.
- **K4-7 (info), `research/m4_sealed_report.md:89`.** Says 21 rows in `runs/trials.csv`; the file has 23 now (the `ledger` step added the 2 sealed
  rows after the writer ran). Expected by the run order. The rebuilt report differs only there.
- **K4-8 (info), `runs/trials.csv`.** The 3 new rows are the step 2 dev check (`c7780628`, commit `6401ee7`, dirty True, dev years) and the
  two sealed parts (`755dcf39`, `380ebc4f`, commit `423a9c2`, dirty False). The dev-check row is not in `seal.lock`, and does not count in N.
  Fine; noted so the judge does not look for it.

## Test suite

Filled in by the session, which ran the suite in the background at `095a855`:
`D:\venvs\chrono-trader\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` printed "534 passed, 1 skipped,
9 warnings in 2896.11s (0:48:16)". Pytest exit code 0. Without `CHRONO_SLOW_LEAKS=1`, so the skip is the slow leak
test.
