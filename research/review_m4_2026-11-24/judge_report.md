# M4 review: the sealed report against PREREG (Opus judge, 24 Nov 2026)

Branch `claude/m4-review` at `095a855`. PREREG.md is unchanged since `8c683f5` (`git diff 8c683f5 HEAD -- PREREG.md`
is empty). PLAN.md's last commit is `323f2e9`, so `docs/digests/plan_rules.md` applies. Nothing was rerun, rescored
or changed. The only script is `j2_recompute.py` in
`C:\Users\syedh\AppData\Local\Temp\claude\a742097078b03236\6cc4007d-fcb6-47d2-8b04-650f79c5109d\scratchpad\m4\`. It
works from the report's printed numbers only (standard library; run it with any Python).

## Verdict

Every test, every headline number I could check by hand and the outcome label follow PREREG's words. **Failure** is the
right label: both parts are complete (report line 9), H2 and H3 do not hold after Holm, and PREREG 6 (line 141) defines
Failure as a complete run in which H2 or H3 does not hold. H1 holding does not enter the rule (PREREG 138, 141). No
number is wrong. The report leaves out three statements PREREG says it must make (R4-1, R4-2, R4-3). By PREREG 7
(line 156) those go in a dated note below the report, and no number changes.

Counts: high 0, medium 2, low 3, info 4.

## Findings

### R4-1 (medium): the known limits PREREG requires are not in the report

- PREREG 6, lines 148-150: "Known limits, stated in the report": only the 2016 vintage has evidence for its cutoff,
  and 2026 was never checked (`cutoff.md` section 9); the sectors are a present-day list; the store's data ends on
  2026-10-28.
- `research/m4_sealed_report.md` states none of them. The writer has no text for them (`research/m4_sealed_report.py`
  184-227, and `eval/report.py` with `sealed=True` adds only the line at report line 85). The writer's tests do not
  look for them (`tests/test_m4_sealed_report.py` 154-156 lists the parts it requires).
- Check: `grep -n -i -E "known limit|2016 vintage|never checked|present-day|ends on" research/m4_sealed_report.md`
  finds nothing.
- Why it matters: the vintage-evidence limit is the context for reading both leak checks' "no warning". It changes no
  result.
- Fix: a dated note below the report that states the limits (see R4-4 on the sectors' wording), and a writer test for
  the next sealed report.

### R4-2 (medium): the after-cost baseline rows are not marked as not turnover-matched, under a heading that says "Matched"

- PREREG 4, lines 95-97: the baselines are compared with live **before costs**; "The after-cost rows are shown, marked
  as not turnover-matched, since only live has the band". This is how PREREG settled M3 entry rule 2
  (`research/m3_kickoff.md` 655-657: "PREREG decides whether the sealed baselines get the band; until then, compare
  them with live before costs"). PREREG decided: no band for the baselines, compare before costs.
- Report lines 219-241: the heading is "Matched baselines". The table puts `sharpe_after_costs` first, with no mark
  and no sentence saying the comparison is before costs. The heading comes from `eval/report.py` (the line
  `md.append("\n## Matched baselines ...")`), which `sealed=True` does not change.
- Check: `grep -n -i "turnover-matched\|not turnover\|before costs" research/m4_sealed_report.md` finds only column
  names (lines 223, 237).
- Effect on the reading: none on the outcome. Before costs, live's Sharpe (-0.1994, line 225) is still below
  momentum's (0.1460, line 226) and below random seeds 3 and 4 (0.8286, 0.1027). Live's turnover is 0.4513 against
  0.66 to 0.67 for random and reversal, so the after-cost rows are not like for like.
- Fix: the dated note says the comparison is before costs and the after-cost rows are not turnover-matched; in
  `eval/report.py`, `sealed=True` should print PREREG 4's sentence and drop "Matched" from the heading.

### R4-3 (low): the report does not say that the sessions after 2026-10-28 are scored by neither the sealed run nor the forward test

- PREREG 1, lines 36-37: "The sessions between 2026-10-29 and the forward test's first day are scored by neither, and
  the report says so."
- Check: `grep -n -E "2026-10-29|scored by neither|forward" research/m4_sealed_report.md` finds nothing.
- Fix: one line in the dated note.

### R4-4 (low): PREREG's known limit on sectors does not match the data or the report

- PREREG 149 says "the sectors are a present-day list". `research/audit/benchmarks.md` line 12 records 142 monthly
  revisions of Wikipedia's list, 2014-12-29 to 2026-09-25, with 89 companies changing sector (line 13). The report
  (lines 273, 287) says "Wikipedia's list as of each date". The report is right about the data. PREREG's wording is
  the error.
- Check: `sed -n '10,18p' research/audit/benchmarks.md`.
- Fix: the dated note for R4-1 should state what `benchmarks.md` shows (monthly as-of revisions, with 5 companies
  having no sector), not copy "present-day list". The remaining limit is that Wikipedia's list is an editor's record,
  not a point-in-time vendor file.

### R4-5 (low): the descriptive frozen-twin and coefficient-life tables include the dev years, under a line that says the sealed years only

- Report line 85: "Sealed years 2020-01-02 to 2026-10-28, described only". But the twin gaps for the 2016 to 2018
  twins include 2017, 2018 and 2019 (lines 153-182), and their "all" rows mix dev and sealed days (end of 2016:
  2,468 days, line 163). Coefficient life counts quarters from each snapshot, so the 2016 to 2018 twins' early
  quarters are dev quarters (lines 350-457).
- Cause: `eval/report.py` builds `ic` over all labels up to the sealed end and calls
  `metrics.twin_gaps(ic["live"], twins, last)` and `metrics.coefficient_life(twins, last)` with no cut at `first`.
- Effect: none on a test. H2's twin (end of 2019) has sealed days only (line 190: 1,714 days, t 0.7993, the same as
  H2's lag-7 t on line 37).
- Fix: say so in the dated note; for later reports, cut both tables at `first` or label the dev rows.

### R4-6 (info): each placebo seed shows its own t

- PREREG 81: "Each seed is shown as spread only, never tested alone". Report lines 306-316 show each seed's mean IC,
  t and after-cost Sharpe, with no p and no verdict, and no test of live against any one seed. The old "Reading"
  table, which did test each seed, is gone (`eval/report.py`, `if not sealed`). PREREG 90 also shows t-statistics as
  robustness without calling them tests. I read this as within PREREG's words, as `research/audit/m4_writer_check.md`
  line 39 did.

### R4-7 (info): two outcome edge cases the writer handles in a way PREREG does not spell out (not triggered)

- `research/m4_sealed_report.py` 125-127: if older_vintage is void and H2 or H3 fails, the label is "Failure ... (the
  older-vintage check did not run)". PREREG 141 defines Failure only for a complete run, and 143-146 names no label
  for this case.
- Lines 128-131: if H2 and H3 hold, a leak check warns and older_vintage is void, the label is "H3 not claimed"
  without saying the older-vintage check did not run.
- Neither applies here: both parts are complete (report line 9; both run-log entries have `"again": false`, lines
  5-6).

### R4-8 (info): two t values for the same series appear in the report

- H1's t is 2.2735 at lag 6 (line 21) and 2.2826 in the quarter table's "all" row (line 147), which uses the default
  lag 7. H2's is 0.8005 (line 22) and 0.7993 in the twin-gap table (line 190). Each is labelled, and the lag-7 values
  equal the robustness column (lines 36-37). This is consistent, but a reader could mix them up.

### R4-9 (info): PREREG's known limits leave out two of PLAN's

- `docs/digests/plan_rules.md` L289-290 lists two known limits: ModernBERT's 2024 tokenizer vocabulary, and
  ChronoBERT's design being chosen in 2025. PREREG 148-150 does not carry them. This is a gap between PREREG and PLAN,
  not between the report and PREREG. The R4-1 note can add them.

## What I checked and found right

Recomputed by hand from the printed t values (`j2_recompute.py`):

- p = 1 - Phi(t), one-sided normal, as PREREG 71 says, and as `eval/stats.py` 61-72 computes it: H1 0.0115, H2 0.2117,
  H3 vs price-only 0.2001, H3 vs placebo mean 0.1219. All four match the report (lines 21-24).
- H3's p is the larger of its two (0.2001, the price-only test; PREREG 77-78; code 87-88).
- Holm (PREREG 82-86): H1 0.0115 is at most 0.05/3 = 0.01667, so it holds. Next comes H3, 0.2001, against 0.05/2 =
  0.025, which fails, so Holm stops and H2 (0.2117, bound 0.05) is not rejected. The result is H1 yes, H2 no, H3 no
  (lines 26-30). `holm()` (code 48-59) sorts on unrounded values, passes a p equal to its bound, treats NaN as 1 and
  stops at the first failure, as PREREG 85-86 says.
- Outcome: Failure, by PREREG 141 (code 120-127). The report claims nothing more: there is no "skill", "learned" or
  "passed" anywhere (`grep -n -i -E "pass|skill|learn|significan|claim"` finds only column names).

Tests (PREREG 3):

- Series: H1 is live's IC. H2 is live minus `live_frozen_2019`. H3 is live minus price-only, and live minus the
  placebo's daily mean over the 5 seeds on days all 5 have an IC (code 62-72, 84-85). Each pair is matched on the
  days both have an IC and sorted by date.
- Dates: IC days run from 2020-01-02 and use labels that end by 2026-10-28 (code 158-162). That gives 1,714 days,
  against 1,715 book days (lines 80, 225), as PREREG 38 implies.
- One-sided, lag 6 for all four (code 31, 86; test lines 46-48). Robustness is at lags 7 and 21 and on monthly means
  at lag 0, with t only (lines 32-39; PREREG 90).

Switch-day check (PREREG 115-120, `cutoff.md` 10.2 at lines 784-800):

- The series is the news effect, live minus price-only (`eval/switch_day.py` 50). It runs over 2020 to 2025, with
  2026 shown apart (code 34-35, 97-99; lines 58-62).
- (a): the pooled p is 1 - Phi(0.8168) = 0.2070, which matches line 54, so (a) does not warn.
- (b): only 2024 is above two standard errors (0.0925 > 2 x 0.0451). That is 1 of the 6 counted years, below the 3
  needed, so (b) does not warn.
- The days add up: 120 + 1,388 + 206 (2026) = 1,714. The result is "no warning", never "passed" (line 56). PREREG's
  restatement of 10.2 is faithful. Its additions (calendar sessions, years counted, 2026 apart) are readings, not
  changes.

Older-vintage check (PREREG 121-129, `cutoff.md` 10.1, M3 entry rule 1 at `m3_kickoff.md` 650-653):

- The gate is the point estimate: the rule's news effect has a mean of 0.0049 > 0 (code 110; line 72).
- (a): is the older effect (0.0059) below half the rule's? No. (b): p = 1 - Phi(-0.3227) = 0.6265, which matches
  line 70. Not below 0.05.
- Result: "no warning". The power note is printed (line 74), as the rule's t, 0.8530, is below 1.645.
- Lag: the default `nw_lag(1714)` = 7, as PREREG 111 says. The rule's t equals H3 vs price-only's lag-7 t (line 38).
  A p is shown for (b) only (lines 68-70; PREREG 91).

Placebo and baselines:

- M3 entry rule 3 is carried exactly: there is one test against the seeds' daily mean (PREREG 80-81), and the seeds
  appear only in the spread table.
- Entry rule 2 is settled in PREREG 95-97: no band for the baselines, compared before costs. The numbers are there
  (lines 223-241). Only the marking is missing (R4-2).

Deflated Sharpe (PREREG 99-106):

- N = 8 + 0 `--again` runs = 8 (lines 5-6, 80; code 255-258).
- With N = 8 and V = 0.0013, sr0 is 0.0526 by hand. The printed 0.0523 implies V of about 0.001285, which is
  consistent with the rounded 0.0013 the writer's guard checks (code 147-149).
- Three versions are shown, with one marked "the result" and no verdict. n = 1,715.
- The checker recomputes the inputs from the raw runs, so I did not.

Trials and section 7:

- 8 trials in 21 ledger rows (line 89). The two sealed ledger rows are in the header (lines 7-8), with status run and
  dirty False. They were appended to `runs/trials.csv` after the writer (`git diff --stat 8c683f5 HEAD` shows +2
  rows), in PREREG 2's order (writer, then ledger).
- The report also has seal.lock, PREREG's SHA-256, both run-log entries, every test and check, every baseline and
  seed, and aggregates only (PREREG 154-157).
- The gaps are R4-1 to R4-3.
