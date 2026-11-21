# Skeptic checks of the identity, doc-number and rules findings

Date: 2026-11-21. Ran on Opus at high effort. Worktree: full-review-1121-0eb11c. The coordinator asked me to stop
early, so D3, D4 and R2 are NOT CHECKED, and R1 is only partly checked.

Scripts and their saved output are in `research/review_2026-11-21/scripts/skeptic_checks/`. All run from the repo
root with `D:\venvs\chrono-trader\Scripts\python.exe -W ignore <script>`. Only counts, ids, symbols, dates and (for
D1) percents are shown. No code was changed.

| Id | Verdict | Severity |
|---|---|---|
| I1 | REFUTED as a table defect (the shortfall is in the source) | info |
| I2 | REFUTED as a problem (by design) | info |
| I3 | REFUTED (no caller passes NaN) | info |
| D1 | CONFIRMED | low |
| D2 | CONFIRMED (barely) | info |
| D3 | NOT CHECKED | - |
| D4 | NOT CHECKED | - |
| R1 | PARTLY (one site checked in full, others read but not counted) | low |
| R2 | NOT CHECKED | - |

## I1. 41 sessions at 498 or 499 members

Verdict: REFUTED as a table step dropping members. The count does drop, but the source file drops with it.
Severity: info (was "minor fail").

Commands: `i1_low_sessions.py`, `i1_tickers.py`, `i1_diffs.py`, `i1_runs.py` (outputs `.out` beside each).

What they printed:
- On every one of the 41 low sessions, every ticker in the index file's snapshot has an active row in
  `reference/memberships.csv`, except CPRI (all 41) and CCEP (8). Both are later tickers for companies that do have
  an active row: the index file holds CPRI from 2016-01-04 (beside KORS, which it holds until 2018-09-19), and CCEP
  from 2016-01-04 to 2016-05-31 (beside CCE). Neither is a missing company. KORS's row (entity 0001530721) runs
  2013-11-13 to 2020-05-12, and CCE's (0001491675) to 2016-05-31.
- The rows not in the snapshot are TYC (0000833444, a row the pipeline added as missing from the file), ACE
  (0000896159, which continues under CB from 2016-01-15) and KORS (after 2018-09-19). None of these lowers the count.
- So the snapshot's 503 to 505 tickers overstate companies: they include 4 or 5 second share classes and the CPRI and
  CCEP duplicates. Example: on 2018-11-29 the snapshot holds 503 tickers, 503 rows are active, 5 companies hold two
  rows, so 498 companies.
- Each low run starts when a company leaves and ends when the source adds its replacement. 2018-11-27 to 11-30: COL
  (0001137411) leaves 2018-11-27 and AET leaves 2018-11-29 in the snapshot; MXIM, FANG and LW join on 2018-12-03.
  2016-01-15: the old Chubb Corp (0000020171, CB) leaves; EXR (0001289490) joins 2016-01-19. All 20 runs follow this
  pattern (list in `i1_runs.out`).
- 2016 to 2018 distinct-entity counts per session: 498 on 2, 499 on 39, 500 on 712, 501 on 1.

Missing entities on 2018-11-29: none relative to the source. Rockwell Collins (COL) and Aetna (AET) had left, and the
index file shows their replacements only from 2018-12-03.

Lines checked: `data_pipeline/membership.py:22-62` (snapshots and spells), the index file
`D:\chrono-data\membership\components_extended.csv`.

Fix: change the rule to "498 to 505 members a day" or note in PLAN that the source records an exit before its
replacement on 41 sessions in 2016 to 2018. Whether S&P's real effective dates were the same was not checked.

## I2. 8 overlapping membership row pairs in 7 two-class companies

Verdict: REFUTED as a problem. It is by design. Severity: info.

Checked: the 8 pairs in `scripts/check_identity/output_detail.txt` are CMCSA/CMCSK, FOXA/FOX, TFCFA/TFCF, UAA/UA,
DISCA/DISCK, NWSA/NWS, GOOGL/GOOG and FOX/FOXA (Fox Corp), one row per share class.
- `data_pipeline/bars.py:9-13, 83-94`: one membership period per class; `spell_class` picks the class for each row's
  `source_ticker`, so the bars need one row per class to flag both classes' member bars.
- `world/world.py:41-62` merges a company's overlapping rows into one spell.
- `world/world.py:144-163`: `members_at` sums +1 and -1 per row, so a company with two rows counts 2 and is a member
  while the sum is above 0. A class leaving early (CMCSK on 2015-12-14) leaves the company a member. Correct.
- `eval/leaks.py:42-43` works per row, the same way.

Fix: reword the rule as "no overlapping rows for one entity and share class".

## I3. `identity.py:460` uses `member_to or date.max`

Verdict: REFUTED. No caller passes NaN. Severity: info.

Command: `i3_member_to_types.py`. It rebuilds the identity inputs offline, pinned to 2026-10-31 as in
`D:\chrono-data\review\scripts\run_identity_pinned.py`, with network calls and table writes blocked.

Printed: 799 resolved rows; `member_to` types reaching `compare`: None 503, date 296, float NaN 0. `compare` ran:
0 missing, 0 extra. `reference/memberships.csv` has 503 empty `member_to`, the same 503.

Lines checked: `identity.py:244-266` (`periods` builds the frame from dicts, so None stays None),
`identity.py:455-474`, the only caller `identity.py:525`. A NaN would also crash the comparisons at line 461, so the
original run could not have passed one silently.

Fix: optional hardening, `date.max if pd.isna(r.member_to) else r.member_to`.

## D1. CCE's last member-day label in `m1_kickoff.md:187`

Verdict: CONFIRMED. The doc says +0.58%; the store and a rebuild give +3.01%. Severity: low (doc only; the stored
label is right).

Commands: `d1_cce_label.py`, `d1_rebuild.py`.

Printed: CCE is entity 0001491675, member to 2016-05-31. The 2016-05-27 label ends at the 2016-05-31 open,
at_close False, label +3.01%. Rebuilt by the store.py rule (first day close/open, the 2016-05-31 return, last day
open/close) with the store's return +3.41%: +3.01%. With the vendor return -24.70% instead: -24.99%, which matches
the doc's "before" figure. No variant gave +0.58%. The +0.58% came in with commit 658db1c, the same commit that added
the CCE row; `reference/price_events.csv` has not changed since.

Lines checked: `research/m1_kickoff.md:182-188`.

Fix: change "+0.58%" to "+3.01%" at `m1_kickoff.md:187`.

## D2. Tests take "4 to 6 minutes"

Verdict: CONFIRMED, barely. Severity: info.

Evidence: the last line of `research/review_2026-11-21/tests_output.txt` is
`258 passed, 1 skipped, 6 warnings in 383.13s (0:06:23)`, 23 seconds over 6 minutes. `README.md:49` and
`AGENTS.md:47` say 4 to 6 minutes. I started a rerun (`d2_tests_rerun.out`), but it was not finished when I wrote this
note, so it was not used. The 383 s run was made with other agents working, so one run is weak evidence.

Fix: say "4 to 7 minutes", or "about 6 minutes".

## D3. LLY 2019-08-12 in `m1_kickoff.md:74`

NOT CHECKED. Stopped early at the coordinator's request.

## D4. 1,371,723 member stock-days in a doc

NOT CHECKED. Stopped early. Leads not verified by me: the checker's notes name `research/audit/auctions.md` and PLAN.md
line 26 (`check_doc_numbers.md:103`, `check_identity.md:112`).

## R1. Dates not converted to New York

Verdict: PARTLY. One site checked in full; the others were read but their effect was not counted. Severity: low.

- `bars.py:43` (fixed UTC-5): used by `last_complete_day` (bars.py:40-44), which sets the bar fetch end
  (`bars.py:140`) and `today` for the identity build (`identity.py:520`). UTC-5 is never ahead of the New York date
  (New York is UTC-5 or UTC-4), so in daylight time from 00:00 to 01:00 New York it gives the day before. That can
  only end a fetch one day early. It never reaches a day that has not closed. The original identity run is pinned to
  2026-10-30 (`run_identity_pinned.py`). It cannot change a stored bar value. Harmless.
- `identity.py:61`: the UTC date of a monthly Wikipedia revision stamp. The stamps feed first and last seen dates and
  the "approximate (first revision showing it)" dates in `reference/identity.csv` (identity.py:354, 360). A revision
  saved between 00:00 and 04:00 or 05:00 UTC would get a date one day later than its New York date. So it could move
  an approximate date by a day. I did not count how many stamps fall in that window.
- `membership.py:109`: the same conversion, used only for the month-by-month report table (lines 104-111). Report
  only.
- `wikipedia.py:165`: local (Pakistan) date, used as `today` in `membership.main` (line 95) for the cache file name and
  the change-log extension. Effect not checked.
- `split.py:59`: default `last_day` when none is passed. Callers not checked.
- `news.py:72`: not read.

Fix: one helper for "today in New York" (zoneinfo America/New_York) used at all six sites, and convert revision stamps
to New York before `.date()`.

## R2. Derived CSVs and split.json in git

NOT CHECKED. Stopped early at the coordinator's request.
