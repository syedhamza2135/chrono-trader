# Check of reference/price_events.csv

Date: 2026-11-21. Worktree: full-review-1121-0eb11c. Row numbers below count data rows from 1 (CSV file line = row + 1). No prices are shown.

Command for every check (one script, output saved next to it):

`D:\venvs\chrono-trader\Scripts\python.exe -W ignore research\review_2026-11-21\scripts\check_prices\check_prices.py`

Script: `research/review_2026-11-21/scripts/check_prices/check_prices.py`. Full output: `research/review_2026-11-21/scripts/check_prices/output.txt`. It reads the store at `D:\chrono-data\store` (bars.parquet, counts.json); the store was built 2026-11-08.

Plan figures come from `docs/digests/plan_rules.md` (L497: 122 rows, then 3 added on 8 Nov, making 125; L23 and L480: 54 opening corrections). The 58 total_return figure is 55 distributions plus 3 added rows.

## 1. Row count and counts by kind and action: PASS

Printed: `rows: 125`.
By action: total_return 58, override_open 54, override_close 7, stopped_trading 3, no_trade 2, override_bar 1.
By kind: open_print 54, spin_off 46, close_print 7, special_dividend 6, failure 3, halt 2, warrant_dividend 2, bad_print 1, stock_dividend 1, share_consolidation 1, dividend 1, merger 1.
Compared with PLAN: 125 rows matches. 54 opening corrections matches (open_print 54). 58 total_return matches (55 + 3). The other counts also match: 7 closing auctions, 1 Nordstrom bar (bad_print), 2 Biogen halts, 3 failed banks. The file has no kind or action that PLAN does not list.

## 2. Required fields present: PASS

Printed: blank rows for symbol, date, kind, action and evidence: none (`[]` each). Every override_bar row has open, high, low, close, volume and vwap. Every override_close row has close. Every override_open row has open. Every total_return row has total_return. No number is unparseable. Failing rows: none.

## 3. Dates are New York trading dates in range: PASS, with two by-design notes

Printed: all dates parse as YYYY-MM-DD. Range 2016-02-08 to 2026-10-14. Store data_end is 2026-10-28 and the store's first bar is 2016-01-04. No row is outside 2016-01-01 to data_end. No weekend dates. Every date is a session date that the store holds for some symbol.
Per symbol and date, 120 of 125 rows have a bar with volume above zero in the store. The other five are expected:
- Row 118 SIVB 2023-03-10 (failure) and row 119 FRC 2023-05-01 (failure): no bar in the store. The note on row 118 and PLAN L477 say the failed banks have no bars after their last trade.
- Row 120 SBNY 2023-03-13 (failure): the store has no traded bar (zero-volume fill, which the store drops).
- Rows 2 and 3 BIIB 2020-11-06 and 2023-06-09 (halt): bar exists with zero volume, as the rule for halts says.
Failing rows: none. The store's own check says the 54 opening overrides equal the official auction opens ("54 of 54", counts.json).

## 4. No duplicates: PASS

Printed: duplicates on (symbol, date, kind): none. Duplicates on (symbol, date, action): none.

## 5. Every row is used by store.py: PASS

Read in `data_pipeline/store.py`: `apply_events` (lines 93 to 133) handles override_bar, override_close, total_return, no_trade, and counts override_open and stopped_trading. `failures` (line 146) reads kind failure. `main` (line 238) checks override_open rows against the auctions.
Printed: actions in the file that store.py does not read: none. Rows with an unread action: none.
The store's counts.json confirms how each row was handled: total_return 58 applied, override_open 54 checked against the opens, override_close 7 applied, no_trade 2 applied, override_bar 1 applied, stopped_trading 3 "no bar to fix" (these rows still drive `failures`, which gives the three failed banks an exit label of -1; counts.json has exits_failed 3).
Note: override_open rows do not change a bar. They are only compared with the official opens. That is by design (store.py line 107).
Note: all other kinds (bad_print, halt, dividend and so on) are descriptive labels. Code reads only the action, and the kind "failure". No row is dead.

## 6. Headline quotes of about 15 words or fewer: PASS

Method: find text in single quotes that opens after a colon, comma or bracket, and closes before a space or punctuation. Double-quoted text was also searched.
Printed: 9 quotes in 9 rows (rows 2, 3, 79, 97, 114, 118, 119, 120, 124). Longest quote: 11 words. Rows with a quote over 15 words: 0. A separate grep found 9 quoted spans, and a manual pass over all rows with an opening quote mark found one more quoted fragment (row 84, 9 words, from a press release), so ten quotes in total, all 11 words or fewer.
Whole notes over 100 words (not quotes, listed for information): rows 79, 84, 100, 115, 123. Longest note: 133 words.
Failing rows: none.

## Result

All six checks PASS. Nothing in the file failed. Two things to know: five rows have no usable store bar by design (three failures and two halts), and 54 override_open rows are checked, not applied.
