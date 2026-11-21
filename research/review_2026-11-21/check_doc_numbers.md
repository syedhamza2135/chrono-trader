# Check of the numbers the docs state (2026-11-21)

Docs read: `README.md`, `AGENTS.md`, `research/m1_kickoff.md` (Sessions 1 to 4). The store was measured today on the build of 2026-11-08, at commit dd40a5f. The tests were not rerun: the figures come from `research/review_2026-11-21/tests_output.txt`.

Scripts and their raw output are in `research/review_2026-11-21/scripts/check_doc_numbers/` (each `.out` file sits beside its script). Script names in the table are shortened to `c1` and so on. Counts, dates, symbols and sizes only. Returns are shown only as pass or fail within 0.01 percentage points. No prices are printed.

Verdicts: MATCH, MISMATCH, NOT CHECKABLE. A number that a later line of the same doc replaces is marked NOT CHECKABLE (superseded), and the later number is checked on its own row.

## Mismatches first

| # | Where | Stated | Reproduced | Note |
|---|---|---|---|---|
| A | `m1_kickoff.md:187` | CCE's last member-day label (2016-05-27) is +0.58% with the row | +3.01% (store label for 2016-05-27) | The "-24.99% before" figure does reproduce: from +3.01% and the vendor return it implies -24.99%. So +0.58% is wrong, and +3.01% is right. |
| B | `README.md:49` and `AGENTS.md:47` | Tests take 4 to 6 minutes | 383.13 s, which is 6 minutes 23 seconds | Slightly over the range. Today's run was done with other agents working, so a quieter machine may sit inside it. |
| C | `m1_kickoff.md:74` | LLY's 2019-08-12 is a gap in the source, listed with the stock-days that have no official open | LLY 2019-08-12 has an official open (1 print). Only its closing print is missing (0 close prints). LLY 2018-01-24 has no open, as stated | The sentence sits under "521 member stock-days have no official open", so it reads as an open gap. The trades-tape part cannot be checked without fetching the tape. |

## All numbers

| Doc:line | Stated | Command (script) | Reproduced | Verdict |
|---|---|---|---|---|
| README:11 | Members since 2015 | c7: min of non-null `member_to` in membership.parquet | 2015-01-27 | MATCH |
| README:12 | Daily bars since 2016 | c2, c7: min date in bars.parquet | 2016-01-04 | MATCH |
| README:13 | News since January 2015 | c7: min `created_at` in stories.parquet | 2015-01-01 | MATCH |
| README:16 | 33 findings confirmed | c6: count numbered findings per section of `m0_review.md` | 3 + 5 + 5 + 8 + 12 = 33, of which 2 marked Major | MATCH (counts the list in the review note, not the review itself) |
| README:29 | Python 3.13 | `D:\venvs\chrono-trader\Scripts\python.exe --version` | 3.13.7 | MATCH |
| README:49 | Tests take 4 to 6 minutes | last line of `tests_output.txt` | 383.13 s (0:06:23) | MISMATCH (B) |
| README:51 | News download about 4.5 hours | c5: first and last write time of the 142 news files | 2026-10-30 01:07 to 05:34, 4 h 27 min | MATCH |
| README:52 | Prices audit about 3 minutes | none recorded | no timing in any file | NOT CHECKABLE (past run time) |
| README:53 | News audit about 3 minutes | none recorded | no timing in any file | NOT CHECKABLE (past run time) |
| README:54 | Auction fetch about 15 minutes | c1: first and last write time of the 787 print files | 14.2 minutes (2026-11-07 18:58 to 19:12) | MATCH |
| README:55 | Store build a few minutes | store file times run 22:43:08 to 22:45:31 on 2026-11-08, but the start time is not recorded | no start time | NOT CHECKABLE |
| README:52 | Incomplete bar: trade count below 5% of the median of the previous 20 bars | grep `data_pipeline/prices.py` (c6) | `TRAILING = 20`, `INCOMPLETE_TRADES = 0.05` | MATCH |
| README:57 | `verify_prints.py` OUT has 19 columns | c6: count entries of `HEADER` with `ast` | 19 | MATCH |
| README:63 | `price_events.csv` has 125 rows | c3: `len` of the csv | 125 | MATCH |
| README:63 | 120 of the 125 rows carry prices | c3: 62 rows with a price column filled, plus 58 `total_return` rows | 62 + 58 = 120 | MATCH |
| README:63 | 62 hold them in price columns: 54 opens, 7 closes, 1 rebuilt bar (JWN 2018-03-26, with volume) | c3: rows with a value in open, high, low, close, volume or vwap, by action | 62: override_open 54, override_close 7, override_bar 1; the JWN row has volume | MATCH |
| README:63 | 58 quote the Alpaca closes in evidence | c3: `total_return` rows whose evidence contains the word "close" | 58 of 58 (a weak test: it finds the word, not the quoted figure) | MATCH |
| README:63 | Other 5: two Biogen halts and three bank failures | c3: rows with no price column filled, by action and symbol | 63 rows have none: the 58 above plus 5: no_trade BIIB x2, stopped_trading FRC, SBNY, SIVB | MATCH |
| AGENTS:10 | Ranks the 50 most-traded members | c3: rows per year in `universe_preview.csv` | 50 per year, 11 years, 550 rows | MATCH |
| AGENTS:16 | Five subagent types | c6: `ls .claude/agents` | 5 files: checker, digest, judge, scout, skeptic | MATCH |
| AGENTS:18 | M1 merged into master on 8 Nov | c6: `git log` date of dd40a5f, and its place under master | dd40a5f dated 2026-11-08, in master's history (master tip is now 3f45e94) | MATCH |
| AGENTS:47 | 258 pass and 1 skip | last line of `tests_output.txt` | 258 passed, 1 skipped, 6 warnings | MATCH |
| AGENTS:47 | The skip is the embeddings table | c6: grep `skip` in tests | `tests/test_suites.py:95` skips with "no embeddings yet (M2)" | MATCH (from the code; the run output names no skip reason) |
| AGENTS:47 | 4 to 6 minutes | same as README:49 | 383.13 s | MISMATCH (B) |
| m1_kickoff:19 | 5 stocks over 3 days took one request and 1.3 seconds | none | probe timing not recorded | NOT CHECKABLE (past run time) |
| m1_kickoff:19-21 | NYSE delayed opens on 2023-01-24 for LLY, MA and XOM: the sizes and times stated | c5: prints files, exchange N, open side, that date | for all three, one N open print with the stated size at the stated New York time | MATCH (prices not compared, by rule) |
| m1_kickoff:22 | 2023's 50 picks: 12,500 stock-day records and 90,153 prints, all 50 with all 250 sessions | c5: the 2023 picks in `universe_preview.csv`, their print files over 2023 | 12,500 records, 90,153 prints, 50 of 50 symbols with 250 sessions | MATCH |
| m1_kickoff:22 | 12 requests and 22 seconds | none | not recorded | NOT CHECKABLE (past run time) |
| m1_kickoff:24-25 | NYSE open prints appear twice, under conditions O and Q; Nasdaq's under codes Q and T | c5: N open prints for LLY, MA, XOM on 2023-01-23 to 25; AAPL open codes | Per stock, 5 prints in 3 days: Q 3, O 2. The delayed 2023-01-24 open has only the Q print. AAPL codes: Q, T, plus small P and V | MATCH (on normal days; not on a delayed open) |
| m1_kickoff:28 | The trades-method rerun of 912 stock-days took about an hour | looked in `D:\chrono-data\audit\recheck` | its inputs hold 68 and 19 rows; no 912-row file or timing | NOT CHECKABLE |
| m1_kickoff:33 | `plan.csv` has 787 rows | c1 | 787 rows, 787 distinct (symbol, asof) files | MATCH |
| m1_kickoff:34 | About 1,600 requests, under 10 minutes | none | a forecast; the real fetch took 14.2 minutes | NOT CHECKABLE (forecast) |
| m1_kickoff:40 | 787 stock-days in `official_prints.csv` | c1: rows in the csv | 787 | MATCH |
| m1_kickoff:66-67 | All 787 bar files fetched in about 15 minutes, no failures | c1: print files and write times | 787 print files for 787 plan rows, 14.2 minutes | MATCH |
| m1_kickoff:68 | 1,873,240 of 1,877,968 stock-days with a bar have an auction record | c1: unique dates over the 787 raw bar files; rows in `official.parquet` | 1,877,968 and 1,873,240 | MATCH |
| m1_kickoff:69 | 680 records on Saturday 2024-07-20, no session | c1: prints on dates outside the XNYS calendar; weekday of the date | 680 records, one date, 2024-07-20, a Saturday | MATCH |
| m1_kickoff:71 | Agrees with the print check on 785 opens and 783 closes | c1b: print check joined to `official.parquet` through the plan rows | 785 of 785 opens and 783 of 783 closes agree | MATCH |
| m1_kickoff:72 | Two print-check days (ARNC 2020-04-01 and 04-03) are not plan stock-days | c1b | the same two ARNC days have no serving plan row | MATCH |
| m1_kickoff:73 | 521 member stock-days have no official open | c1 | 519 now. Session 3 (line 165) replaces 521 with 519 | NOT CHECKABLE (superseded by line 165) |
| m1_kickoff:73 | Split: 267 on 2023-01-24, 108 on 2018-01-24, 66 on 2022-03-08 | c1: missing opens by date | 267, 108, 66 (next is 17 on 2021-04-09) | MATCH |
| m1_kickoff:74 | LLY 2018-01-24 and 2019-08-12 are gaps in the source | c5b: LLY rows in `official.parquet` and the missing list | 2018-01-24 has no open. 2019-08-12 has an open and no close | MISMATCH (C) |
| m1_kickoff:75 | 246 opens more than an hour late | c1 | now 218. Session 3 (line 166) replaces 246 with 218 | NOT CHECKABLE (superseded by line 166) |
| m1_kickoff:76 | Only 1 of those is on a member day | c1: late opens that fall on plan member stock-days | 1 | MATCH |
| m1_kickoff:78 | The 54 overridden opens equal the auctions' opens | c5: `override_open` rows against the store's opens | 54 found, 54 equal | MATCH |
| m1_kickoff:84 | 210 passed and 1 skipped before the review | none | an old run; no record | NOT CHECKABLE (past run) |
| m1_kickoff:87 | All 550 picks in 11 years match the preview | c3: rows in `universe_preview.csv`; the picks test is in the suite | 550 rows, 50 per year, 11 years. The test in `tests/test_leaks.py` passed in today's run | MATCH |
| m1_kickoff:102 | The first missing-open count (34,148) was a bug | none | the old summary code is not kept | NOT CHECKABLE (past state) |
| m1_kickoff:108 | The leak review confirmed 10 findings | c6: numbered items in lines 108 to 137 | 10 | MATCH (counts the list) |
| m1_kickoff:108, 151 | About 20% and about 26% of a window | none | usage is not in any file | NOT CHECKABLE (past usage) |
| m1_kickoff:110 | EQT, PCG, FSLR, KDP, ILMN, CHK leave and rejoin | c2: entities with a gap between membership rows | 6 companies: EQT, PCG, FSLR, ILMN, and KDP (also DPS), CHK (also EXE) | MATCH |
| m1_kickoff:129 | 125 labels start on a member day and end on a non-member day | c2: join labels to bars | 125, with no end bar missing | MATCH |
| m1_kickoff:130 | None of those ends at a close | c2 | 0 of the 125 have `at_close` | MATCH |
| m1_kickoff:138 | 225 pass and 1 skips, 3 to 4 minutes | none | an old run | NOT CHECKABLE (past run) |
| m1_kickoff:151 | 10 more problems in the second review | c6: numbered items in lines 151 to 173 | 10 | MATCH (counts the list) |
| m1_kickoff:156 | 12 bars after the data end, to 2026-10-30 | c5: member stock-days after 2026-10-28 in the plan files | 12, latest 2026-10-30; store ends 2026-10-28 | MATCH |
| m1_kickoff:162-163 | 9 member stock-days took an NYSE Arca print of 1 to 25 shares on 2026-08-20 | none | the old code is not kept; today 2026-08-20 has 1 Arca row among 661 | NOT CHECKABLE (fixed bug, past state) |
| m1_kickoff:164 | COF 2016-10-13 and CXO 2017-10-09 got real opens back | c1 | both have an official open | MATCH |
| m1_kickoff:165 | 519 member stock-days lack an official open | c1 | 519 | MATCH |
| m1_kickoff:166 | 218 opens more than an hour late | c1 | 218 | MATCH |
| m1_kickoff:171 | Exits: 103 stopped, 119 cut | c2: for the 222 `at_close` series, raw file's last traded day against the store's last bar and last member day | 103 stopped, 119 window cut | MATCH |
| m1_kickoff:172 | 125 labels start on a member day and end on one that is not | c2 | 125 | MATCH |
| m1_kickoff:174-175 | 255 pass and 1 skips, 4 to 5 minutes | none | an old run | NOT CHECKABLE (past run) |
| m1_kickoff:177 | 48,935 non-member bars | c2: bars with `member` false | 48,935 | MATCH |
| m1_kickoff:177-180 | The screen flagged 12 days, 8 are splits Alpaca got right | none | the screens' outputs were in a session scratchpad | NOT CHECKABLE |
| m1_kickoff:180-181 | Three rows added (EQT 2018-11-13, DPS 2018-07-10, CCE 2016-05-31), file now has 125 rows | c7, c3 | all three rows present as `total_return`; 125 rows | MATCH |
| m1_kickoff:182-183 | EQT: +1.82% instead of -57.15%; last member label -58.21% before, -0.70% after | c3, c9, c3c | store return +1.82; Alpaca adjusted return -57.15; label -0.70; the before-label implied is -58.21 (all within 0.01 pp) | MATCH |
| m1_kickoff:184 | DPS: +1.84% instead of +11.45% | c3, c9 | store return +1.84; Alpaca adjusted +11.45 (within 0.01 pp) | MATCH |
| m1_kickoff:186 | CCE: +3.41% instead of -24.70% | c3, c9 | store return +3.41; Alpaca adjusted -24.70 (within 0.01 pp) | MATCH |
| m1_kickoff:186-187 | CCE last member-day label (2016-05-27): -24.99% before, +0.58% after | c3, c3b, c3c | before -24.99 reproduces; after is +3.01 | MISMATCH (A) |
| m1_kickoff:189-193 | Left open: no rows for WYN/WH 2018-06-01, HLT 2017-01-04, FTI 2021-02-16 | c7 | no rows for any of them in `price_events.csv` | MATCH |
| m1_kickoff:193 | Alpaca's spin-off records start in 2019 | c8: earliest date in `spin_offs.json` | 2019-02-25, none before 2019 | MATCH |
| m1_kickoff:197-198 | 9 older commits carried the Co-Authored-By line (8 on master and the M1 branch's first) | c6b: grep the three backup branches | backup master 8 of 8 with it; union of the three has 9 | MATCH |
| m1_kickoff:197-198 | No attribution now | c6: grep master and both claude branches for the trailer and "Generated with" | 0 commits | MATCH |
| m1_kickoff:208-209 | Exactly three labels are -1: SVB from 2023-03-09, Signature from 2023-03-10, First Republic from 2023-04-28 | c2 | 3 labels: SIVB 2023-03-09, SBNY 2023-03-10, FRC 2023-04-28, all `at_close` | MATCH |
| m1_kickoff:209-210 | Every other count in `store.md` unchanged | c6: `git diff 658db1c dd40a5f` on `store.md` | one line changed, only the added "Failed companies: 3 ... -1" sentence | MATCH |
| m1_kickoff:210 | Three new tests | c6: `+def test_` lines in tests in dd40a5f | 3 | MATCH |
| m1_kickoff:210-211 | 258 tests, 1 skip | tests_output.txt | 258 passed, 1 skipped | MATCH |
| m1_kickoff:214-217 | 12 commits compared, across master and both claude/ branches | c6b: unique commits over the three backup branches | 12 | MATCH |
| m1_kickoff:222-235 | 12 old to new hashes, with commit titles | c6: `git log -1` for each new hash; `git cat-file` for each old one | all 12 new hashes exist with the stated title; all 12 old hashes still exist (backups and `refs/original`, 3 refs) | MATCH |

## Notes

- Not in the three docs, but seen on the way: `auctions.md` counts 1,371,723 member stock-days with a bar, while the store has 1,371,711 member bars. The 12 extra are the bars after the data end (m1_kickoff:156). PLAN.md line 26, as digested, also says 1,371,723.
- README says 120 of 125 rows carry prices. `m0_review.md` says 115 of 117 for an earlier state of the file. Both fit their own file.
