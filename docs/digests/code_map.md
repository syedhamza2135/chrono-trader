# Code map: world, sim, eval, agent, reader, data_pipeline

Source: world/, sim/, eval/, agent/, reader/, data_pipeline/. Commit dd40a5f. Date 2026-11-21.
Line numbers are in the source file. "Store" means the Parquet tables in DATA_DIR/store. Private helpers (leading underscore) are listed only where they set a contract.

## world/__init__.py (4 lines)
Docstring only: states the time wall. `world` imports nothing from `agent`; `agent` may import only `world.view`.

## world/clock.py (67 lines)
The NYSE session calendar and the New York times of day, as UTC timestamps.
- `nyse() -> calendar` at clock.py:21. Cached XNYS calendar.
- `at(day, clock_time) -> UTC Timestamp` at clock.py:29. A New York date and time of day in UTC (daylight saving handled).
- `at_each(days, clock_time) -> Series of UTC` at clock.py:34. Same, per date of a Series, same index.
- `Clock(first="2015-01-01", last="2026-12-31")` at clock.py:40. Holds NYSE sessions in the range.
  - `is_session(day)` at clock.py:46. True if the date is a session.
  - `decision_time(day)` at clock.py:49. 9:00 New York on the day (DECISION, line 14).
  - `open_time(day)` at clock.py:52. The calendar's session open.
  - `close_time(day)` at clock.py:55. 16:00, or 13:00 on an early close.
  - `between(first, last)` at clock.py:59. Sessions in the closed range.
  - `next_session(day)` at clock.py:63. First session strictly after the date.
  - `previous_session(day)` at clock.py:66. Last session before the date.

## world/rules.py (59 lines)
The availability rules: one function per kind of record. Table of rules in the docstring at rules.py:3-9.
- `story(updated_at) -> Series` at rules.py:26. `updated_at` plus 15 minutes (NEWS_DELAY, line 17).
- `keep_story(created_at, updated_at) -> bool Series` at rules.py:30. False where edited more than 3 days after publishing (MAX_EDIT_LAG, line 18).
- `bar(dates) -> Series` at rules.py:35. 16:00 New York on the bar's date (early closes too).
- `official_open(dates) -> Series` at rules.py:39. 9:30 New York on the date.
- `label(ends, at_close, end_open_time=None) -> Series` at rules.py:43. 9:30 on the end date; the next session's 9:30 where the label ends at a close; the later printed open time where an open printed late.
- `membership(dates) -> Series` at rules.py:58. 0:00 New York on the date.
- Constants HISTORY_BEFORE (400 days) and HISTORY_AFTER (14 days) at rules.py:22-23: how far outside a membership a company's records are kept and shown.

## world/view.py (31 lines)
What an agent may see at time t. The only module an agent may import.
- `View(t, sessions, members, joined, bars, labels, stories, story_entities)` at view.py:18. Holds copies, no World reference. `today` is t's New York date; `sessions` are cut to `<= today` (view.py:24-25). Tables and columns are listed in the docstring at view.py:6-13. Every table has `visible_at`.

## world/world.py (185 lines)
The store's records, each with the time it becomes visible; builds views.
- `sealed_start(root=ROOT) -> Timestamp` at world.py:36. Reads `reference/split.json`, period "sealed" start.
- `spells(membership) -> DataFrame` at world.py:41. Per company: entity_id, start, end (first day after, NaT while a member); overlapping memberships merged.
- `known_from(entity_ids, dates, sp) -> int64 ns array` at world.py:65. Earliest time a view may show a company's record dated that day. In a membership or up to 14 days after: the membership start. Up to 400 days before the next one: that membership's start. Else NEVER.
- `visible_at(table, df, sp, stories=None) -> int64 ns array` at world.py:89. Per row of bars, labels, stories or story_entities. Bars and labels: the later of the rule time and `known_from`. Stories: the story rule. Story_entities: the later of the story's availability and `known_from` on the story's New York created date.
- `_plain(df)` at world.py:107. Makes key columns plain strings and list columns tuples.
- `_Sorted(df, visible_at)` at world.py:121. Table sorted by visible_at. `upto(ns)` at world.py:130 returns a deep copy of rows with visible_at at or before ns.
- `World(bars, labels, opens, stories, story_entities, membership, clock=None, allow_sealed=False)` at world.py:135. Drops stories failing `keep_story` (line 151) and story_entities of dropped stories (line 154). Builds join/leave events from membership. `opens` is not time-cut (line 156).
  - `members_at(ns) -> (members, joined)` at world.py:159. From join and leave events at or before ns.
  - `view(t) -> View` at world.py:165. Needs a tz-aware t. Raises PermissionError if t's New York date is on or after the sealed start and `allow_sealed` is False. Returns prefixes of each table visible at t.
  - `load(store=None, clock=None, allow_sealed=False)` at world.py:178 (classmethod). Reads the six store Parquet files from DATA_DIR/store.

## sim/__init__.py (3 lines)
Docstring only. `sim` imports nothing from `agent`.

## sim/seal.py (62 lines)
The seal check on runs that reach the sealed years.
- `SealError` at seal.py:16. Raised on any seal failure.
- `sealed_start(root=ROOT)` at seal.py:20. Reads `reference/split.json` sealed start.
- `settings_hash(settings) -> sha256 hex` at seal.py:25. Hash of the sorted JSON of the settings.
- `Git(root)` at seal.py:29. `head()` at seal.py:33 runs `git rev-parse HEAD`. `dirty()` at seal.py:37 runs `git status --porcelain`.
- `check(first, last, settings, root=ROOT, git=None) -> None` at seal.py:43. Returns if `last` is before the sealed start. Otherwise needs `seal.lock`, settings, and a match of settings hash, `PREREG.md` hash and git commit, and a clean tree. Else raises SealError.

## sim/simulator.py (135 lines)
The daily loop and portfolio accounting. Fills at the official open. Costs 5 bps per side (COST_BPS, line 26).
- `Run` at simulator.py:30. Dataclass: decisions, equity, stats (forced_sales, unmarked).
- `Simulator(world, cost_bps)` at simulator.py:37. Reads `world.opens` (rows with an open) and `world.labels.df` into dicts (lines 40-45), `data_end` from the last label end (line 49).
  - `_label_from(key, day)` at simulator.py:52. The label starting on that date: (end, label, at_close) or None.
  - `step(day, targets)` at simulator.py:61. Marks holdings whose label ends today (or at a close before today), sells exits, forces sales where no label runs from today's open (not on the data's last day), trades only stocks with an official open that day, charges costs, appends an equity row.
- `run(world, agent, first, last, cost_bps, settings=None) -> Run` at simulator.py:117. Calls `seal.check`, sets `world.allow_sealed` once the seal holds (line 124), then for each session calls `agent.decide(world.view(decision_time(day)))` and `Simulator.step`.

## eval/__init__.py (3 lines)
Docstring only. `eval` imports nothing from `agent`.

## eval/leaks.py (142 lines)
The non-interference check: change everything not visible at t, rerun, compare decisions.
- `late_rows(tables, t) -> dict of masks` at leaks.py:30. Per table (bars, labels, opens, stories, story_entities, joins, leaves) the records not visible at t, using `world.world.visible_at` and `world.rules`.
- `perturb(tables, t, how, seed=0) -> tables` at leaks.py:47. `how` is scramble, shift (7 days later) or delete. Touches only late records. For scramble and shift it then drops any changed record that would become visible by t (lines 92-99).
- `decisions_until(tables, make_agent, first, last, clock=None, give_world=False) -> DataFrame` at leaks.py:103. Builds a World, runs the agent over each session's view, returns sorted decisions.
- `compare(a, b, tol=1e-12) -> list of strings` at leaks.py:118. Lists rows in one run only, positions that differ, predictions beyond tol (NaN against a number counts).
- `non_interference(tables, make_agent, first, last, how, seed=0, clock=None, give_world=False) -> list` at leaks.py:137. Runs to the decision on `last`, perturbs records not visible then, reruns, compares.

## eval/metrics.py (18 lines)
Skill metrics from decisions and realised labels.
- `daily_rank_ic(decisions, labels, min_stocks=10) -> Series by date` at metrics.py:5. Spearman rank correlation each day of prediction against label. Days with fewer than `min_stocks` are left out. No time cut-off.

## agent/__init__.py (3 lines)
Docstring only. An agent imports nothing from the project except `world.view`.

## agent/reversal.py (111 lines)
A toy agent: yearly pick of 50 by dollar volume, features from bars, monthly ridge refit, long 10 and short 10.
- `ReversalAgent(n_picks=50, n_side=10, penalty=1.0, warmup=126, first_pick="2016-04-01")` at reversal.py:26. Keeps `params`, `memory` and `fits`.
  - `pick(v) -> list of (entity_id, share_class)` at reversal.py:39. Members at v; bars from 1 Jan 2016 (in 2016) or one year before `today`, up to the day before `today`, complete bars only; median of close times volume; best class per company.
  - `features(v, picks) -> DataFrame` at reversal.py:50. r1, r5, r20, vol20 from bars in the last 45 days; missing counts as 0.
  - `refit(v)` at reversal.py:65. Ridge on remembered feature rows joined to labels present in the view. Target is log label minus the day's mean. Appends to `fits` the time and the latest `visible_at` of its labels.
  - `score(f, v)` at reversal.py:82. Minus r5 before the first fit, else the ridge score.
  - `rank(f)` at reversal.py:87. Plus and minus 1/n_side weights on the top and bottom n_side.
  - `decide(v) -> DataFrame or None` at reversal.py:96. None before `first_pick`. Re-picks on a new year, refits on a new month once warmed up.

## reader/__init__.py (1 line)
Docstring only. The embedding job is not built yet; the vintage rule is.

## reader/vintage.py (28 lines)
Which ChronoBERT vintage reads a story.
- `vintage_for(created_at) -> Series` at vintage.py:11. New York year of `created_at` minus 1, capped at 2024 (LAST, line 8). Raises ValueError if the result is below 2014.
- `breaches(embeddings, stories) -> DataFrame` at vintage.py:21. Embedding rows whose `vintage_year` is not the rule's year for their story; a missing story counts.

## data_pipeline/__init__.py (1 line)
One-line docstring.

## data_pipeline/settings.py (34 lines)
Paths and keys, from `.env` (or `CHRONO_ENV_FILE`) and environment variables.
- `DATA_DIR`, `DATA_URL` at settings.py:26-27. DATA_DIR defaults to `D:\chrono-data`.
- `alpaca_headers() -> dict` at settings.py:30. Key headers, or exit if keys are missing.

## data_pipeline/alpaca.py (60 lines)
Alpaca market-data client with a shared rate limit.
- `RateLimiter(per_minute)` at alpaca.py:12. `wait()` spaces requests across threads. `LIMITER` is 180 a minute (line 29).
- `get(path, **params) -> dict` at alpaca.py:33. GET with up to 7 retries on 429 and 5xx.
- `pages(path, **params)` at alpaca.py:52. Yields each page following `next_page_token`.

## data_pipeline/prices.py (72 lines)
Loads daily bars per plan row from the bars download plan.
- `plan() -> DataFrame` at prices.py:34. Reads `DATA_DIR/bars/plan.csv`.
- `trailing_ratios(bars)` at prices.py:38. Volume and trade count over the median of the previous 20 bars (needs 10).
- `incomplete(bars) -> bool Series` at prices.py:44. True where volume is above 0 and trades are under 5% of the previous-bars median.
- `load(adjustment="raw", columns=COLUMNS) -> DataFrame` at prices.py:53. Reads `DATA_DIR/bars/<adjustment>/<symbol>__<asof>.parquet` for each plan row. Adds entity_id, share_class, use_from, use_to, `member`, `incomplete`, `row`.

## data_pipeline/bars.py (179 lines)
Downloads daily bars (raw and fully adjusted) and writes the plan.
- `last_complete_day() -> date` at bars.py:40. Yesterday in New York (UTC minus 5 hours, minus one day).
- `existing()` at bars.py:51. Files on disk with both adjustments.
- `spell_class(rows, ticker, start, end)` at bars.py:65. The share class a membership period is about.
- `plan(last_day) -> DataFrame` at bars.py:76. Reads `reference/identity.csv` and `reference/memberships.csv`; one row per (company, ticker, asof, use_from, use_to).
- `fetch(ticker, asof, adjustment, end)` at bars.py:113. Pages Alpaca `/v2/stocks/bars`, from 2016-01-01.
- `save(path, ticker, asof, rows)` at bars.py:121. Writes one Parquet file.
- `main()` at bars.py:139. Writes `plan.csv`, downloads missing files, appends `manifest.csv`.

## data_pipeline/news.py (86 lines)
Downloads Alpaca (Benzinga) news, one Parquet file per month under `DATA_DIR/news`.
- `months(first, last)` at news.py:24. Year-month pairs.
- `fetch_month(y, m)` at news.py:31. Pages `/v1beta1/news`. The current month ends 20 minutes ago.
- `save(path, rows)` at news.py:43. Columns: id, created_at, updated_at, headline, author, source, url, symbols.
- `run_month(y, m, is_current)` at news.py:59. Skips finished months.
- `main()` at news.py:69. Months from 2015-01 to today, three at a time.

## data_pipeline/auctions.py (268 lines)
Downloads auction prints and builds the official open and close per stock-day.
- `path_for(symbol, asof)` at auctions.py:53. Print file path.
- `bar_dates(symbol, asof)` at auctions.py:57. Dates of one raw bar file.
- `jobs()` at auctions.py:63. (symbol, asof) pairs from the plan.
- `fetch(symbol, asof, start, end)` at auctions.py:69. Pages `/v2/stocks/auctions`.
- `save(path, rows)` at auctions.py:84. Writes the prints file.
- `official(prints) -> DataFrame` at auctions.py:102. Per date: listing exchange (vote over a 21-session window), largest open and close prints on it, with times.
- `split_sessions(off)` at auctions.py:137. Splits rows on NYSE sessions from rows on other days.
- `build_official(files)` at auctions.py:148. Writes `official.parquet`.
- `late_opens(off)` at auctions.py:160. Official opens printed over an hour after the session open.
- `check(off)` at auctions.py:171. Compares with the print check files.
- `summary(...)` at auctions.py:205. Writes `research/audit/auctions.md` (counts).
- `main()` at auctions.py:229.

## data_pipeline/audit_prices.py (427 lines)
Audits the bars and writes `research/audit/prices.md` and CSVs. Also holds `returns` and `foreign`, which the store uses.
- `read_reference()` at audit_prices.py:38. Reads entities, memberships, price_events from `reference/`.
- `pick_dates(sessions) -> dict` at audit_prices.py:48. First session of each year; 2016 uses the first session of April.
- `members_on(day, members) -> set` at audit_prices.py:59. Entities with member_from at or before the day and member_to after it.
- `survivorship(raw, members, picks)` at audit_prices.py:64. Members with no bar within 10 days of each pick date.
- `shared_histories(raw)` at audit_prices.py:75. Company pairs with at least 20 identical member days.
- `foreign(raw) -> bool array` at audit_prices.py:90. Bars outside their row that equal another security's member bar.
- `returns(raw, adj) -> (raw, adj, counts...)` at audit_prices.py:101. Close-to-close returns per plan row, stitched across row changes, undefined where the previous bar is not the company's own; adds `next_ret`.
- `coverage(raw, sessions, events)` at audit_prices.py:151. Member sessions without a bar, with a reason.
- `company_member_days(raw, sessions)` at audit_prices.py:173. Member sessions per company, and those with no bar.
- `incomplete_bars(raw)` at audit_prices.py:183. Ratios for incomplete member bars.
- `correction(r)` at audit_prices.py:196. Short text for a price_events row.
- `large_moves(adj, prints, events)` at audit_prices.py:207. Member days with an adjusted move above 25%.
- `print_checks(moves)` at audit_prices.py:222. Count of large moves the print check judged.
- `adjustment_events(raw, adj, events)` at audit_prices.py:234. Member days where adjusted and raw moves differ by over 4%.
- `universe_preview(raw, members, picks, names)` at audit_prices.py:248. Top 50 by median dollar volume over the year before each pick date. Writes `universe_preview.csv`.
- `main()` at audit_prices.py:276. Writes the CSVs and `prices.md`.

## data_pipeline/audit_news.py (276 lines)
Audits the news and writes `research/audit/news.md`, `news_by_day.csv` and others.
- `companies(df)` at audit_news.py:41. Maps each story's tags to companies on its New York date (via `SymbolIndex`); adds n_companies and entities.
- `member_stories(single)` at audit_news.py:62. Single-firm stories from 2016 for companies that are members on the story's date.
- `reading_load(single, uni, picks)` at audit_news.py:73. Per year counts about members and about picked companies from the pick date.
- `by_day(df, single)` at audit_news.py:84. Per New York date: stories and member stories.
- `load()` at audit_news.py:94. Reads all monthly news files; de-duplicates by id keeping the latest update.
- `recaps(df)` at audit_news.py:107. Marks session recaps inside, late or early against their session windows.
- `main()` at audit_news.py:121. BENZINGA is the label set `{"benzinga", ""}` (line 34).

## data_pipeline/split.py (74 lines)
Writes `reference/split.json`: warm-up 2016, dev 2017 to 2019, sealed from 2020-01-01. Counts only.
- `counts(start, end, sessions, members, daily)` at split.py:34. Sessions, member company-days, picked stock-days, story counts for one period.
- `main(last_day=None)` at split.py:54. Reads `research/audit/news_by_day.csv` and `reference/memberships.csv`; writes `reference/split.json`.

## data_pipeline/membership.py (152 lines)
S&P 500 membership snapshots and spells.
- `load_snapshots(path=None)` at membership.py:22. [(date, tickers)] from the extended file if it exists, else the source file.
- `members_on(day, snapshots)` at membership.py:34. Tickers in the last snapshot dated at or before the day.
- `spells(snapshots, since)` at membership.py:43. {ticker: [(start, end)]}; end is the first snapshot date without it.
- `extend(snapshots, changes, renames=())` at membership.py:65. Applies the change log and renames after the last snapshot; returns (snapshots, problems).
- `main()` at membership.py:91. Writes `components_extended.csv` and `research/audit/membership.md`.

## data_pipeline/wikipedia.py (165 lines)
Wikipedia's S&P 500 pages, cached under `DATA_DIR/membership/wikipedia`.
- `_get(params)` at wikipedia.py:26. API call with retries.
- `current(title, day)` at wikipedia.py:42. The page as it stands, cached by fetch day.
- `revision(title, day)` at wikipedia.py:51. (timestamp, wikitext) of the revision in force at 00:00 UTC on the day.
- `constituents(wikitext)` at wikipedia.py:129. [{symbol, security, cik, date_added}].
- `changes(wikitext)` at wikipedia.py:148. Change log rows: date, added, removed, reason.
- `today()` at wikipedia.py:164. Local date as ISO text.
- Parsers `_rows`, `_table`, `_header`, `_symbol`, `_name`, `_date` at wikipedia.py:64-126.

## data_pipeline/identity.py (590 lines)
Builds the identity table: entities, tickers by date, memberships. Writes `reference/entities.csv`, `identity.csv`, `memberships.csv` and `research/audit/identity.md`.
- `normalize(symbol)` at identity.py:51. BRK-B, BRK/B to BRK.B.
- `wiki_months(today)` at identity.py:56. One revision per month since 2015-01-01, plus today's.
- `name_changes(today)` at identity.py:71. Alpaca name changes since 2020; cached in `DATA_DIR/corporate_actions/name_changes.json`.
- `Wiki(w)` at identity.py:83. Lookups over the revisions. `resolve(symbol, stamp)` at identity.py:100 gives (cik, how).
- `resolve_spells(spell_map, wiki)` at identity.py:113. Splits each spell into CIK segments.
- `chains(wiki, fixes)` at identity.py:137. Union-find over CIKs.
- `read_fixes()` at identity.py:172. Reads `reference/identity_fixes.csv`.
- `absorb_lag`, `apply_wiki_fixes`, `merge_same_entity`, `apply_segment_fixes`, `periods` at identity.py:178, 194, 205, 217, 244. Segment clean-up and membership periods.
- `timelines(wiki, find, members, fixes, renames, today)` at identity.py:269. Ticker rows with valid_from and valid_to.
- `SymbolIndex(rows=None)` at identity.py:399. Reads `reference/identity.csv`. `lookup(tag, day)` at identity.py:421 gives the entities a tag names on that date. `entities(tags, day)` at identity.py:433 gives (known set, count).
- `overlaps(rows)` at identity.py:444. Symbols meaning two entities on one day.
- `compare(wiki, find, members)` at identity.py:455. Differences from Wikipedia beyond 12 days (LAG_DAYS, line 44).
- `build_all(today)` at identity.py:477. Runs the steps above.
- `write_tables(b)` at identity.py:495, `main()` at identity.py:519. Write the reference CSVs and the report.

## data_pipeline/store.py (311 lines)
Builds the event store (Parquet tables) from bars, auctions, news and reference files. Tables: bars, opens, labels, stories, story_entities, membership, identity.
- `file_rows()` at store.py:60. Every plan row's raw bars with the adjusted return and `foreign`.
- `company_series(df)` at store.py:70. One bar per company, class and date; non-member days only within 400 days before or 14 days after a row.
- `apply_events(s, events)` at store.py:93. Applies `reference/price_events.csv`: override_bar, override_close, total_return, no_trade.
- `official_opens(s)` at store.py:136. Joins official prints to the series.
- `failures(s, events, within=7 days)` at store.py:146. Series whose last traded bar is followed within 7 days by a failure event.
- `labels(s, opens, data_end, failed)` at store.py:162. Open-to-open total return per official open; ends at the last traded close where the company stopped before `data_end`; -1 for failures; `end_open_time` is when the end open printed.
- `stories()` at store.py:197. Benzinga stories passing `keep_story`, and (story, company) pairs for stories naming 1 or 2 companies.
- `reference_tables()` at store.py:212. Membership and identity tables.
- `main()` at store.py:222. Writes the seven tables, `counts.json` and `research/audit/store.md`.
- `report(c)` at store.py:285. Writes the counts report.

## Time cut-offs and store reads

### Time cut-off sites (30)
1. world/rules.py:17, 26-27. News available at `updated_at` plus 15 minutes.
2. world/rules.py:18, 30-32. Stories edited over 3 days after publishing are dropped.
3. world/rules.py:35-36. Bar available 16:00 New York on its date.
4. world/rules.py:39-40. Official open available 9:30 on its date.
5. world/rules.py:43-55. Label available at the end open (or the next session's open after a close exit, or the later printed open time).
6. world/rules.py:58-59. Membership change available 0:00 on its date.
7. world/rules.py:22-23. HISTORY_BEFORE 400 days and HISTORY_AFTER 14 days.
8. world/world.py:65-86. `known_from`: when a company's record may show, by membership spell.
9. world/world.py:89-104. `visible_at`: rule time or `known_from`, whichever is later.
10. world/world.py:130-132. `_Sorted.upto`: only rows visible at or before the time.
11. world/world.py:159-163. `members_at`: join and leave events at or before the time.
12. world/world.py:165-175 (check at 170). `view(t)` returns prefixes at t; sealed dates refused unless `allow_sealed`.
13. world/view.py:24-25. `sessions` cut to the New York date of t.
14. world/world.py:151-154. Late-edited stories and their entity rows dropped at load.
15. world/clock.py:14, 49-50. Decision time 9:00 New York.
16. sim/seal.py:43-61. Dates in the sealed years need a matching seal.lock, PREREG.md hash, commit and clean tree.
17. sim/simulator.py:73. A label is marked on the day it ends (or the day after a close exit).
18. sim/simulator.py:84-88. Forced sales except on the data's last day.
19. sim/simulator.py:117-129. `run` seals dates and gives the agent the view at 9:00 each session.
20. eval/leaks.py:30-44. `late_rows`: records not visible at t.
21. eval/leaks.py:92-99. Changed records forced to stay hidden at t.
22. eval/leaks.py:137-142. Decision time of `last` is the cut for the perturbation.
23. agent/reversal.py:40-42, 52, 66-69, 80, 97. Pick window (to the day before today), 45-day feature window, labels only from the view, `latest_label` record, `first_pick` date.
24. reader/vintage.py:11-18. Vintage is the New York year of `created_at` minus 1, capped at 2024.
25. data_pipeline/store.py:55-56, 74-83. Non-member bars kept 400 days before and 14 days after a row. Also 177 (data end), 146-159 (failure within 7 days), 228 (bars cut at the data's last session), 197-201 (3-day edit rule).
26. data_pipeline/prices.py:25-31, 44-50. Incomplete-bar rule uses only the previous 20 bars.
27. data_pipeline/bars.py:40-44 and news.py:34-36. Never ask for the latest day (bars) or latest 20 minutes (news).
28. data_pipeline/identity.py:421-431 and audit_news.py:41-59, 62-70. Tags mapped to companies, and members taken, on the story's New York date.
29. data_pipeline/audit_prices.py:48-61, 190-215 and membership.py:34-40. Pick dates, members on a day, year of trading before the pick date.
30. data_pipeline/auctions.py:46-47, 102-135, 160-168 and wikipedia.py:51-61. 21-session window vote, the one-hour late-open rule, and the Wikipedia revision in force at 00:00 UTC on a day.

### Store reads (direct path or table name) (23)
1. world/world.py:36-38. `reference/split.json`.
2. world/world.py:181-185. DATA_DIR/store files: bars, labels, opens, stories, story_entities, membership (Parquet).
3. sim/seal.py:20-22. `reference/split.json`.
4. sim/seal.py:44-51. `seal.lock` and `PREREG.md`.
5. data_pipeline/prices.py:21-22, 35, 58. `DATA_DIR/bars/plan.csv` and `bars/<adjustment>/*.parquet`.
6. data_pipeline/bars.py:78-79. `reference/identity.csv`, `reference/memberships.csv`. Also lines 36 and 55 (plan and bar files).
7. data_pipeline/news.py:20, 60. `DATA_DIR/news/<year-month>.parquet`.
8. data_pipeline/auctions.py:36-41, 59, 65, 154, 173-176, 247. Bar files, `plan.csv`, prints files, `official.parquet`, `audit/official_prints.csv`, `official_prints_input_v2.csv`.
9. data_pipeline/audit_prices.py:39-44. `reference/entities.csv`, `memberships.csv`, `price_events.csv`.
10. data_pipeline/audit_prices.py:286. `DATA_DIR/audit/official_prints.csv`.
11. data_pipeline/audit_news.py:95. `DATA_DIR/news/*.parquet`.
12. data_pipeline/audit_news.py:65. `reference/memberships.csv`.
13. data_pipeline/audit_news.py:160-162. `research/audit/universe_preview.csv`.
14. data_pipeline/split.py:55-56. `research/audit/news_by_day.csv`, `reference/memberships.csv`.
15. data_pipeline/membership.py:16-17, 22-29. `DATA_DIR/membership/components_updated.csv` and `components_extended.csv`.
16. data_pipeline/wikipedia.py:44-48, 53-60. Cache `DATA_DIR/membership/wikipedia/`.
17. data_pipeline/identity.py:172-175. `reference/identity_fixes.csv`.
18. data_pipeline/identity.py:243. `DATA_DIR/corporate_actions/name_changes.json`.
19. data_pipeline/identity.py:410. `reference/identity.csv` (in `SymbolIndex`).
20. data_pipeline/store.py:62-63. Bars via `prices.load` (raw and all).
21. data_pipeline/store.py:138. `DATA_DIR/auctions/official.parquet`.
22. data_pipeline/store.py:199. News via `audit_news.load`.
23. data_pipeline/store.py:213-217, 229. `reference/memberships.csv`, `identity.csv`, `entities.csv`, `price_events.csv`.

The store's own writes are at store.py:244 and 276 (bars, opens, labels, stories, story_entities, membership, identity Parquet) and store.py:280 (`counts.json`).
