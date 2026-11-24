# M4 writer check: does the writer score what PREREG names, and nothing else?

Done on 23 Nov 2026 by a checker, by reading code only. Nothing was run except the two test files. The writer
`research/m4_sealed_report.py` and `m4_sealed_run.py` were not run. Nothing under `D:\chrono-data` was read. No repo file
was changed except this one. No prices or headlines were seen.

Files read: `PREREG.md` (sections 1 to 7), `research/m4_sealed_report.py` (called W below, line numbers are its own),
`git diff eval/report.py`, `eval/switch_day.py`, `eval/stats.py`, `eval/metrics.py`, `reference/split.json`,
`tests/test_m4_sealed_report.py`.

## What was run

```
D:\venvs\chrono-trader\Scripts\python.exe -m pytest tests/test_m4_sealed_report.py tests/test_report.py -q -p no:cacheprovider
```

It printed: `34 passed, 6 warnings in 119.94s`. The warnings are pandas deprecation notices. Result: pass.

I also ran `git diff eval/report.py`, and `grep -n "[^_a-z]table(" eval/report.py`. The grep found only the definition
of `table` (line 46) and the one call inside `tb` (line 105). So in `build`, every table goes through `tb`, and `tb`
drops every column named `p` when `sealed=True`.

## Table 1: what PREREG names, and where the writer does it

| PREREG item | Where (W unless noted) | Result |
|---|---|---|
| H1: live daily IC, mean above zero | 83, 84, 86 (`stats.nw_mean`, one-sided p) | found |
| H2: live minus `live_frozen_2019`, paired | 37 (`H2_TWIN`), 84 | found |
| H3 test 1: live minus price-only, paired | 84 | found |
| H3 test 2: live minus placebo daily mean, paired | 84 | found |
| H3 p is the larger of the two (max-p rule) | 88 | found |
| Holm at 5%, smallest at most 0.05/3, then 0.05/2, then 0.05 | 33 (`ALPHA`), 48-59, 89 | found |
| "At most": a p equal to its bound passes | 55 (`<=`) | found |
| Stop at the first failure | 57-58 (`break`) | found |
| NaN p counts as 1 | 43-45 (`nan1`), used at 52, 55, 88 | found |
| Lag 6 for H1 to H3 | 31 (`LAG`), 86 | found |
| Paired tests use days both series have an IC | 62-64 (`paired`, `dropna`) | found |
| Placebo daily mean over the 5 seeds, on days all 5 have an IC | 36, 67-72 (`concat`, `dropna`, `mean`) | found |
| Each seed shown as spread only, never tested | `eval/report.py` seed spread: columns mean IC, t, Sharpe; no `p` | found |
| Robustness: t at lag 7, lag 21, monthly means | 32, 75-78, 90-91 | found |
| IC days from 2020-01-02, labels ending by the sealed end | 30, 158-162 | found |
| Sealed end is 2026-10-28 | 231 (`R.sealed_end()`), which reads `reference/split.json` (end of the sealed period) | found; I did not confirm the printed value, see note 8 |
| Switch-day years 2020 to 2025 | 34, 97 | found |
| 2026 shown apart, outside the rule | 35, 98-99 | found |
| Switch-day (a): pooled difference, p below 0.05 | `eval/switch_day.py` 38 (`ALPHA`), 71 | found |
| Switch-day (b): at least half the years counted, above by two standard errors | `eval/switch_day.py` 66-72 | found |
| Years counted: those with days in both parts | `eval/switch_day.py` 69 | found |
| Leak checks keep the code's default lag (`nw_lag`) | `eval/switch_day.py` 55 (`nw_ols` with no lag); W 107-109 (`nw_mean` with no lag) | found |
| Older-vintage: three paired daily series | 107 (rule), 108 (older), 109 (live minus older) | found |
| Gate is the point estimate, mean above zero | 110 | found |
| Gate closed gives "not informative" | 115 | found |
| (a): older effect mean less than half the rule's | 111 (`< 0.5 *`) | found |
| (b): live minus live_older_vintage, p below 0.05 | 112 (`nan1(...) < ALPHA`) | found |
| Warning needs gate, (a) and (b) | 113 | found |
| Power note when rule's t is below 1.645 | 114 | found |
| Older part void gives "not run" | 104-105, 168-169 | found |
| Outcome: Success | 134 | found |
| Outcome: "H2 held; H3 held but is not claimed, because the [check] warned" | 128-131 | found |
| Outcome: Failure | 125-127 | found |
| Outcome: Void (main void) | 122-123 | found, with a gap, see item A below |
| Deflated Sharpe, main version (after-cost book vs after-cost dev trial Sharpes) | 150-151 | found |
| Version 2: after-cost book vs before-cost dev trial Sharpes | 152-153 | found |
| Version 3: before-cost book (0 bps replay) vs before-cost dev trial Sharpes | 154-155, 265 | found |
| N = 8 plus the number of `--again` runs of main | 38, 248-251 | found |
| Variance guard: stop if dev variance differs at its printed precision | 39, 147-149 (compares to "0.0013") | found; the dev report prints 0.0013 (`research/m3_dev_report.md:199`) |
| Other two versions shown without a verdict | 150-155, 217-218 (a table, no verdict text) | found |
| Leak tests (full suite) | not the writer's job | not applicable |

Nothing in this table is MISSING.

## Table 2: what the writer and `build(sealed=True)` produce, and the PREREG line that names it

| Output | PREREG line | Result |
|---|---|---|
| H1, H2, H3 vs price-only, H3 vs placebo: p in the test table | 74-81 | named |
| Hold table: p and "holds after Holm" for H1, H2, H3 | 82-84 | named |
| Robustness t-statistics (lag 7, lag 21, monthly) | 89-91 | named, and labelled "not tested (t-statistics only)" |
| Switch-day pooled p | 118-119 (a) | named |
| Switch-day per-year table (no p) | 119-120 (b) | named |
| 2026 table apart (no p) | 120-122 | named |
| Older-vintage p for live minus live_older_vintage | 128 (b) | named |
| Older-vintage p for "news effect, the rule's vintage" | none (PREREG says only "mean and t") | NOT IN PREREG |
| Older-vintage p for "news effect, the older vintage" | none | NOT IN PREREG |
| Older-vintage t of the rule's effect (power note) | 129 | named |
| Gate, (a), (b), power note, outcome | 123-129 | named |
| Outcome "Success", "H3 not claimed", "Failure", "Void" | 138-144 | named |
| Outcome "Not a success: H2 and H3 held, but the older-vintage check did not run" (line 133) | none (PREREG says only "the outcome can't be Success", line 144) | NOT IN PREREG |
| Outcome text "Failure ... (the older-vintage check did not run)" (line 126) | 141 | named, with an added note |
| Deflated Sharpe, three versions | 99-106 | named |
| Header: PREREG hash, `seal.lock`, run log, ledger rows | 154-155 (section 7) | named |
| `build(sealed=True)` tables | 88-91 (descriptive list) | named; none has a `p` column |

### Count of "p" columns that survive in sealed mode

Zero. In `eval/report.py`, `build` has two tables with a `p` column when not sealed: IC by quarter
(`metrics.ic_by_quarter`) and frozen-twin gaps (`metrics.twin_gaps`). Both go through `tb`, which drops `p`. The reading
table (p for each placebo seed), the variants table, the deflated Sharpe and the switch-day section are not built at all
in sealed mode. The test `test_the_whole_report_on_made_up_runs_tests_only_what_prereg_names` (line 152) also checks
that no markdown table row in the sealed text has a ` p ` column. It passed.

The `p` columns that do appear in the full sealed report all come from the writer's own `markdown`: the test table, the
hold table, the switch-day pooled row and the older-vintage table. That is 4 tables. Two rows of the older-vintage
table carry a p that PREREG does not name (see Table 2).

### Are the t-statistics called tests?

No. In the sealed build, `md[1]` says "nothing in this part is a test". The remaining t columns (IC by quarter, twin
gaps, seed spread, beta, regimes, coefficient life) sit under headings that do not say "test", and two say "reported,
not tested". The writer's robustness table says "Robustness, not tested (t-statistics only)". The words "test" and
"p-value" in sealed output appear only for the H1 to H3 tests and the two leak checks. Pass.

## Deviations from PREREG that I found

A. **H1 to H3 are tested and printed even when main is void** (`score` 170, `markdown` 189-194). PREREG section 6 says
   that if main is void, "H1 to H3 are not tested and the outcome is Void". The outcome string is right (122-123), but the
   tests table, hold table and robustness table are still written. `ics` also needs `live` in `runs`, so a main part with
   no live decisions would raise a KeyError instead. Fix suggestion: skip `hypotheses` and print "not tested" when
   `main_complete` is false.
B. **"Not a success: ..." (line 133) is a label PREREG does not name.** The rule behind it is in PREREG (an older void
   means the outcome can't be Success), but the wording is the writer's.
C. **Two older-vintage p-values** (rule's effect, older effect) are shown and not named. They decide nothing. PREREG
   names only the mean and t for these.
D. **Power note.** The writer shows it whenever the rule's t is below 1.645 or NaN (114), also when the gate is closed.
   PREREG's sentence on it follows the gate-open rule and does not say. This is harmless, but it is a choice.
E. **Monthly-means robustness uses lag 0** (78). PREREG says "on monthly means" and gives no lag.
F. **`names` in `_load_all` (244) silently drops a missing dev trial directory.** The count of 8 comes from
   `runs/trials.csv` (248), not from `names`. The variance guard (147-149) would still stop a wrong set, so the risk is
   small.
G. **H1 and H2 p stored as raw NaN** in `h["p"]` (87). The decisions use `nan1` (52, 55), so Holm is right. A NaN p
   would only show as a blank cell in the hold table.
H. **Sealed end value.** The writer reads it from `reference/split.json` via `sim/seal.py`. I read the file's first 30
   lines: `data_through` is 2026-10-28, and the sealed block is cut off in my read. I did not read its `end` line. The
   made-up test ties the last IC day to the last label ending by that end (2026-10-27 on that data).

## Verdict

Every item PREREG names for the tests, the Holm rule, the two leak checks, the outcomes and the deflated Sharpe has a
line in the writer. MISSING: none. NOT IN PREREG: items B and C (one outcome label, two older-vintage p-values). One
real gap against PREREG: item A (tests still written when main is void). Zero `p` columns survive in
`build(sealed=True)`. Tests: 34 passed.

## Fixes (23 Nov, uncommitted)

- (A) `score` returns no tests when the main part is void, and the report says H1 to H3 and both leak checks are not
  tested (PREREG section 6 now says both leak checks too). A test covers it.
- (B) PREREG section 6 now gives that outcome's label in words: "Not a success: H2 and H3 held, but the
  older-vintage check did not run".
- (C) The older-vintage table shows a p-value only for (b); PREREG section 3 says so. A test covers it.
- Minor: PREREG names lag 0 for the monthly-means robustness. `_load_all` now stops if any of the 8 dev trial folders
  is missing. The power note stays whenever t is below 1.645, as PREREG says, gate open or not.
