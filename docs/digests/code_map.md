# Code map: world, sim, eval, agent, reader, data_pipeline

Source: world/, sim/, eval/, agent/, reader/, data_pipeline/. Commit 89f35f7 plus the M3 review fixes, 23 Nov 2026; sim/seal.py, sim/simulator.py, eval/report.py and world/world.py refreshed to 095a855 (M4), 24 Nov 2026.
Line numbers are in the source file. "Store" means the Parquet tables in DATA_DIR/store. Private helpers (leading underscore) are listed only where they set a contract. Line counts are from `wc -l` of the working tree.

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

## world/rules.py (65 lines)
The availability rules: one function per kind of record. Table of rules in the docstring at rules.py:3-10.
- `story(updated_at) -> Series` at rules.py:27. `updated_at` plus 15 minutes (NEWS_DELAY, line 18).
- `embedding(updated_at) -> Series` at rules.py:31. A story's embedding is available when its story is (same as `story`).
- `keep_story(created_at, updated_at) -> bool Series` at rules.py:36. False where edited more than 3 days after publishing (MAX_EDIT_LAG, line 19).
- `bar(dates) -> Series` at rules.py:41. 16:00 New York on the bar's date (early closes too).
- `official_open(dates) -> Series` at rules.py:45. 9:30 New York on the date.
- `label(ends, at_close, end_open_time=None) -> Series` at rules.py:49. 9:30 on the end date; the next session's 9:30 where the label ends at a close; the later printed open time where an open printed late.
- `membership(dates) -> Series` at rules.py:64. 0:00 New York on the date.
- Constants HISTORY_BEFORE (400 days) and HISTORY_AFTER (14 days) at rules.py:23-24: how far outside a membership a company's records are kept and shown.

## world/view.py (37 lines)
What an agent may see at time t. The only module an agent may import.
- `View(t, sessions, members, joined, bars, labels, stories, story_entities, embeddings)` at view.py:23. Holds copies, no World reference. `today` is t's New York date; `sessions` are cut to `<= today` (view.py:29-30). Tables and columns are listed in the docstring at view.py:6-18. Every table has `visible_at`. `embeddings` is an `Embeddings` (rows, last, avg).

## world/world.py (386 lines)
The store's records, each with the time it becomes visible; builds views. Now also holds the embeddings and the embedding window.
- Constants at world.py:46-50: NEVER, ROOT, KEYS, EMBEDDING_WINDOW_DAYS (90, line 49), DAY_NS.
- `sealed_start(root=ROOT) -> Timestamp` at world.py:57. Reads `reference/split.json`, period "sealed" start.
- `spells(membership) -> DataFrame` at world.py:62. Per company: entity_id, start, end (first day after, NaT while a member); overlapping memberships merged.
- `known_from(entity_ids, dates, sp) -> int64 ns array` at world.py:86. Earliest time a view may show a company's record dated that day. In a membership or up to 14 days after: the membership start. Up to 400 days before the next one: that membership's start. Else NEVER.
- `visible_at(table, df, sp, stories=None, story_entities=None) -> int64 ns array` at world.py:110. Per row of bars, labels, stories, story_entities or embeddings. Bars and labels: the later of the rule time and `known_from`. Stories: the story rule. Story_entities: the later of the story's availability and `known_from` on the story's New York created date. Embeddings: the later of the story's embedding time and the story's first link time; NEVER for a story with no link.
- `_plain(df)` at world.py:142. Makes key columns plain strings and list columns tuples.
- `_Sorted(df, visible_at)` at world.py:156. Table sorted by visible_at. `upto(ns)` at world.py:165 returns a deep copy of rows visible at or before ns.
- `Embeddings(rows, last, avg)` at world.py:170. What a view holds: rows plus two aligned vector arrays. `__len__` at 180. `empty(dim=0)` at world.py:184 (classmethod).
- `embedding_problems(embeddings, stories, vintage_offset=0) -> list` at world.py:199. Reasons to refuse a table: no kept story, repeated story, wrong vintage, stored available_at not the story's.
- `_SortedEmbeddings(emb, visible_at)` at world.py:227. Embeddings in visible_at order. `upto(ns, since=None)` at world.py:250 returns fresh copies of rows visible at ns and after `since` (the window).
- `_parquet_footer(path)` at world.py:260. File size and SHA-256 of the Parquet footer.
- `load_embeddings(store) -> Embeddings` at world.py:272. Rows from `embeddings.parquet`, vectors as read-only maps of the two `.npy` files; stops if `embeddings.json` does not match them.
- `World(bars, labels, opens, stories, story_entities, membership, clock=None, allow_sealed=False, embeddings=None, embedding_window_days=90, vintage_offset=0)` at world.py:298. Refuses `vintage_offset` with `allow_sealed` (line 304): an offset World opens the sealed years only through `sim.simulator.run`, as the sealed older_vintage part. Drops stories failing `keep_story` (line 321) and story_entities of dropped stories (line 324). Refuses an embeddings table with problems (lines 327-330). Builds join/leave events from membership. `opens` is not time-cut (line 333).
  - `embedding_window_days` at world.py:339 and `vintage_offset` at world.py:344. Read-only properties.
  - `members_at(ns) -> (members, joined)` at world.py:348. From join and leave events at or before ns.
  - `view(t) -> View` at world.py:354. Needs a tz-aware t. Raises PermissionError (line 361) if t's New York date is on or after the sealed start and `allow_sealed` is False; only `sim.simulator.run` sets it, after the seal holds. Returns prefixes of each table visible at t, and embeddings visible in the window.
  - `load(store=None, clock=None, allow_sealed=False, embeddings=True, embedding_window_days=90, embeddings_store=None, vintage_offset=0)` at world.py:370 (classmethod). Reads the six store Parquet files and, if present, the embeddings.

## sim/__init__.py (3 lines)
Docstring only. `sim` imports nothing from `agent`.

## sim/seal.py (199 lines)
The seal (PLAN 9.12, M4): the lock, the check on runs that reach the sealed years, and the run log that lets each sealed part start once.
- Constants at seal.py:37-38: PARTS ("main", "older_vintage"), LOCK ("seal.lock").
- `SealError` at seal.py:42. Raised on any seal failure.
- `sealed_start(root=None)` at seal.py:54. Reads `reference/split.json`, period "sealed" start (via `_split`, line 50).
- `settings_hash(settings) -> sha256 hex` at seal.py:58. Hash of the sorted JSON of the settings.
- `prereg_hash(root=None)` at seal.py:62. SHA-256 of PREREG.md's bytes, or None if there is none.
- `runs_log()` at seal.py:67. The run log, `DATA_DIR/sealed/runs.jsonl` (outside git).
- `Git(root)` at seal.py:74. `head()` at 82, `dirty()` at 85 (`git status --porcelain`), `parents(rev)` at 88, `tracked(path)` at 91, `changed(rev)` at 95.
- `_commit_matches(sealed, git)` at seal.py:104. HEAD is the lock's own commit: its one parent is the sealed commit, it changes seal.lock alone, and seal.lock is tracked.
- `check(first, last, settings, root=None, git=None) -> None` at seal.py:116. Returns if `last` is before the sealed start. Otherwise needs `seal.lock`, the settings, a match of the part's settings hash, the PREREG hash and the commit rule, and a clean tree. Else raises SealError.
- `write(parts, root=None, git=None, now=None) -> lock` at seal.py:137. Writes seal.lock once for HEAD from {part: settings}; refuses an existing lock, no PREREG.md, a dirty tree, an unknown part, or no "main". The lock is committed alone straight after.
- `started(log=None)` at seal.py:162. The run log's entries, oldest first.
- `require_started(settings, log=None)` at seal.py:170. For a sealed replay: the log must hold a start of that part with the same settings hash.
- `begin(settings, again=False, ...) -> entry` at seal.py:179. Records a sealed part's start before any sealed view opens; refuses a second start unless again=True (which counts as another trial), and again=True for a part never started.

## sim/simulator.py (280 lines)
The daily loop and portfolio accounting. Fills at the official open. Costs 5 bps per side (COST_BPS, line 26).
- `Run` at simulator.py:31. Dataclass: decisions, equity (date, equity, cost, gross, traded), stats (forced_sales, unmarked).
- `Simulator(world, cost_bps)` at simulator.py:37. Reads `world.opens` (rows with an open) and `world.labels.df` into dicts, and `data_end` from the last label end.
  - `_label_from(key, day)` at simulator.py:52. The label starting on that date: (end, label, at_close) or None.
  - `step(day, targets)` at simulator.py:61. Marks holdings whose label ends today (or at a close before today), sells exits, forces sales where no label runs from today's open (not on the data's last day), trades only stocks with an official open that day, charges costs, appends an equity row.
- `settings_run(world, agent, cost_bps, settings=None)` at simulator.py:117 and `settings_many(world, agents, cost_bps, settings=None, freeze=())` at simulator.py:127. The whole settings `run` and `run_many` check against the seal (the caller's, costs, agents and parameters, embedding window, offset).
- `_with_offset(world, full)` at simulator.py:138. Records a non-zero vintage_offset in the settings.
- `_open(world, first, last, full, settings, again)` at simulator.py:145. Calls `_offset` and `seal.check`; for a run reaching the sealed years, checks the settings name these dates, calls `seal.begin` (once per part) and sets `world.allow_sealed`. Callers restore it in a `finally`.
- `run(world, agent, first, last, cost_bps, settings=None, again=False) -> Run` at simulator.py:161. For each session calls `agent.decide(world.view(decision_time(day)))` and `Simulator.step`.
- `_offset(world, last, full)` at simulator.py:184. An offset World reaches the sealed years only as the sealed "older_vintage" part (line 192), and that part only with offset 1 (line 195).
- `_fresh(base)` at simulator.py:198. A simulator sharing base's lookups with a new empty book.
- `_own_view(v)` at simulator.py:208. Shallow table copies and read-only vectors, one view per agent.
- `run_many(world, agents, first, last, cost_bps, settings=None, freeze=(), again=False) -> {name: Run}` at simulator.py:221. One view per session shared by several agents, each with its own simulator; frozen twins `<name>_frozen_<year>` at each new year for names in `freeze`. Same `_open`.
- `replay(world, run, costs=(0, 5, 10, 20), base=None, settings=None) -> {bps: equity rows}` at simulator.py:259. Trades the run's own targets again at each cost. Seal-checks the run's dates and, in the sealed years, needs a started sealed run with those settings (`seal.require_started`).

## eval/__init__.py (3 lines)
Docstring only. `eval` imports nothing from `agent`.

## eval/leaks.py (185 lines)
The non-interference check: change everything not visible at t, rerun, compare decisions. Now covers embeddings.
- Constants HOW, SHIFT (7 days), SIGNED at leaks.py:30-32.
- `late_rows(tables, t) -> dict of masks` at leaks.py:35. Per table (bars, labels, opens, stories, story_entities, joins, leaves, and embeddings if present) the records not visible at t.
- `perturb(tables, t, how, seed=0, vintage_offset=0) -> tables` at leaks.py:56. `how` is scramble, shift (7 days later) or delete. Touches only late records. Embeddings: scramble swaps and scales vectors, shift moves `available_at` and takes the shifted story's vintage, delete drops them. For scramble and shift it then drops any changed record that would become visible by t (lines 126-133).
- `decisions_until(tables, make_agent, first, last, clock=None, give_world=False, embedding_window_days=90, vintage_offset=0) -> DataFrame` at leaks.py:137. Builds a World, runs the agent over each session's view, returns sorted decisions.
- `compare(a, b, tol=1e-12) -> list of strings` at leaks.py:155. Lists rows in one run only, positions that differ, predictions beyond tol (NaN against a number counts).
- `non_interference(tables, make_agent, first, last, how, seed=0, clock=None, give_world=False, embedding_window_days=90, vintage_offset=0) -> list` at leaks.py:174. Runs to the decision on `last`, perturbs records not visible then, reruns, compares.

## eval/metrics.py (253 lines)
Dev-report metrics from decisions, equity rows and realised labels. Nothing here is seen by an agent.
- `daily_rank_ic(decisions, labels, min_stocks=10) -> Series by date` at metrics.py:20. Spearman rank correlation each day of prediction against label. Days with fewer than `min_stocks` are left out.
- `within(s, first=None, last=None)` at metrics.py:35. Cuts a Series by date.
- `ic_by_quarter(ic, first, last)` at metrics.py:49. Per quarter and "all": days, mean IC, Newey-West se, t, p.
- `paired_gaps(a, b, first, last, by="year")` at metrics.py:58. Daily differences a minus b by year and "all".
- `twin_gaps(live_ic, twin_ics, last=None)` at metrics.py:69. Live minus each frozen twin, per year after the twin's year.
- `book_returns(equity, first, last)` at metrics.py:83. Daily returns from equity rows; starts from 1.0.
- `turnover(equity, first, last)` at metrics.py:92. Mean daily traded value over pre-trade equity.
- `book_table(books, first, last, before=None)` at metrics.py:100. Per book: annual return and vol, Sharpe after and before costs, max drawdown, turnover, days.
- `cost_table(by_cost, first, last)` at metrics.py:116. Book statistics at each cost.
- `spy_open_returns(spy)` at metrics.py:125. SPY open-to-open returns from adjusted opens.
- `beta(book, market)` at metrics.py:132. Slope on the market with an intercept and Newey-West se.
- `sectors_for(pairs, sectors)` at metrics.py:143. Each (entity, date) row's sector; first run's sector before the first run; "Unknown" if never listed.
- `sector_tilt(decisions, sectors, first, last)` at metrics.py:158. Mean net and mean absolute net target weight per sector.
- `seed_spread(ics, books, first, last)` at metrics.py:177. Per seed mean IC, t, Sharpe; then min, max, mean, std.
- `regimes(spy, sessions, trend_days=200, vol_days=20, fall=0.10, after=20)` at metrics.py:193. Each session's trend, vol and shock labels from SPY closes before that session.
- `regime_table(ic, book, labels, first, last)` at metrics.py:229. Per regime column and value: days, mean IC, t, book Sharpe.
- `coefficient_life(twin_ics, last=None)` at metrics.py:243. Each twin's mean IC by quarter since its snapshot, with t.

## eval/stats.py (136 lines)
Statistics in plain numpy (no SciPy). YEAR is 252 (line 16).
- `nw_lag(n)` at stats.py:20. Newey-West (1994) lag floor(4 (n/100)^(2/9)).
- `nw_ols(y, X, lag=None) -> (coefficients, se, lag)` at stats.py:25. Least squares with Bartlett-kernel Newey-West standard errors.
- `norm_cdf(z)` at stats.py:43. From `math.erfc`.
- `norm_ppf(p)` at stats.py:47. Inverse by bisection.
- `nw_mean(x, lag=None) -> dict` at stats.py:61. n, mean, se, t, one-sided p, lag.
- `max_drawdown(r)` at stats.py:75. Largest fall from a peak, as a negative fraction.
- `book_stats(r) -> dict` at stats.py:82. days, total, annual return, annual vol, Sharpe over zero, max drawdown.
- `moments(r)` at stats.py:98. Daily Sharpe, skewness, kurtosis (not excess).
- `psr(sr, n, skew, kurt, benchmark=0.0)` at stats.py:109. Probabilistic Sharpe ratio.
- `expected_max_sharpe(n_trials, var_trials)` at stats.py:116. Expected largest of n noise Sharpe ratios; 0 for one trial.
- `deflated_sharpe(r, n_trials, trial_srs) -> dict` at stats.py:126. sr, annual sr, skew, kurt, n, n_trials, var_trials, sr0, dsr.

## eval/switch_day.py (73 lines)
The switch-day check (cutoff.md section 10.2): news effect right after each 1 January switch of vintage.
- `FIRST = 20`, `ALPHA = 0.05` at switch_day.py:31-32.
- `_diff(effect, first20)` at switch_day.py:35. Difference of means by a first-20 dummy with Newey-West se, t, one-sided p, day counts.
- `switch_day(live_ic, price_only_ic, sessions, years) -> dict` at switch_day.py:46. Effect is live IC minus price-only IC. Returns a per-year table, the pooled fit, `years_counted`, `warning_a` (pooled p below 0.05), `warning_b` (at least half the years above two se), `warning`.

## eval/benchmarks.py (45 lines)
The evaluation's own tables, read only by `eval` (the World never loads them).
- `load_spy(store=STORE)` at benchmarks.py:13. Reads `spy.parquet`.
- `load_sectors(store=STORE)` at benchmarks.py:18. Reads `sectors.parquet`.
- `sector_on(sectors, entity_ids, day) -> {entity_id: sector}` at benchmarks.py:23. Latest run on or before the day; first run's sector if the day is earlier; None if never listed.
- `spy_buy_and_hold(spy, first, last) -> DataFrame` at benchmarks.py:38. date and equity from adjusted opens, starting at 1.0.

## eval/charts.py (79 lines)
Plain SVG line charts (no plotting library).
- `lines(series, title, path, ylabel="", zero=True) -> path` at charts.py:14. Writes an SVG of {name: Series by date}; NaN breaks a line.
- `wealth(r)` at charts.py:77. Wealth path of daily returns, starting at 1.

## eval/trials.py (65 lines)
The trial ledger `runs/trials.csv` (COLUMNS at trials.py:26).
- `record(settings, first, last, agents, out_dir, runs=..., git=None, now=None, trial="", status="run") -> row` at trials.py:30. Appends a row, writes `runs/settings/<hash>.json`. Status is planned, run or dropped.
- `rows(runs=...)` at trials.py:54. All ledger rows.
- `count(runs=...)` at trials.py:62. Distinct trial names whose latest row is not dropped.

## eval/report.py (288 lines)
Writes the dev report markdown and its charts from finished runs, and the descriptive part of the sealed report (`sealed=True`). Runs nothing and reads no view.
- `_fmt(v)` at report.py:34. Cell text; numbers to 4 decimals.
- `table(df, index=True)` at report.py:46. Markdown table.
- `read_trials(path)` at report.py:58. Ledger rows from a CSV.
- `build(runs, labels, spy, sectors, sessions, first, last, run_bps, trials_csv, replays=None, variants=None, charts_dir=None, switch_years=(2017, 2018, 2019), title="M3 dev report", notes=(), trial_table=None, sealed=False) -> markdown` at report.py:74. Sections: trials, IC by quarter, frozen-twin gaps, price-only twin and placebo, baselines, variants, costs, beta and sector tilt, deflated Sharpe, seed spread, regimes, coefficient life, switch-day check, charts. With sealed=True it drops p-values and the tested sections, which `research/m4_sealed_report.py` writes from PREREG (lines 98, 127, 164, 193, 226).
- `_charts(d, replays, ic, ret, twins, spy_r, first, last)` at report.py:241. Writes the SVG charts and returns their links.
- `write(path, charts_dir=CHARTS, **kw)` at report.py:282. Builds and writes the report; CHARTS is `DATA_DIR/runs/m3_dev_report_charts` (line 279).

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

## agent/track_a.py (482 lines)
Track A's agent: price and news features, monthly ridge on running sums, validation picks penalty and pooling, long-short or long-only policy. Rules are in the docstring at track_a.py:1-51.
- Constants at track_a.py:62-69: PRICE (6 features), POOLINGS (last, avg), PENALTIES (10^-2 to 10^4), HALF_LIFE 5, LOOKBACK 200 days, SETTLE 10 sessions, MIN_TRAIN_DAYS 20, KEY.
- `_ic(pred, y, day_index)` at track_a.py:72. Mean over days of Spearman correlation (days with at least 3 rows and some spread).
- `Sums(k)` at track_a.py:86. Running sums n, sum x, x'x, sum y, x'y in float64.
  - `add(X, y, sign=1.0, w=None)` at track_a.py:93. Adds rows or takes them out, optionally weighted.
  - `decay(f)` at track_a.py:109. Multiplies every weight by f.
  - `minus(X, y, w=None)` at track_a.py:114. A copy with rows removed.
  - `scaled()` at track_a.py:120. Mean, std, Z'Z and Z'(y minus mean y) from the sums alone.
- `_solve(zz, zy, penalties)` at track_a.py:132. Ridge coefficients for each penalty from one eigendecomposition.
- `TrackA(n_picks=50, n_side=10, book="long_short", hold=1, band=None, news=True, first_pick="2016-04-01", trade_from="2017-01-01", fit_after_months=6, min_val_months=3, val_share=0.2, full_val_years=5, recent_val_months=12, penalties, poolings, coefficients="last", half_life_days=None)` at track_a.py:139. Keeps `params`, `fits`, memory, pending and recent day blocks.
  - `pick(v)` at track_a.py:180. Uses `ReversalAgent.pick`.
  - `price_features(v, picks)` at track_a.py:184. r1, r5, r20, r60, vol20, dvol_ratio from bars before today within 200 days.
  - `_pairs(v)` at track_a.py:206. (story, company) pairs in the view with their availability; one per pair.
  - `update_news(v)` at track_a.py:223. Moves the decayed news memory to today, adds new pairs, returns them.
  - `news_features(v, picks, new)` at track_a.py:262. news_count, news_none, news_new, news_memory per pooling.
  - `features(v, picks, new)` at track_a.py:283. Feature matrix per pooling, rounded to float32; missing is 0.
  - `settle(v)` at track_a.py:293. Moves day blocks whose labels are in the view (or 10 sessions old) into the sums and kept rows; applies recency decay.
  - `_val_days(today)` at track_a.py:327. Size of the validation part.
  - `refit(v)` at track_a.py:335. Picks penalty and pooling on validation, refits on all rows in the sums, appends to `fits`, trims kept rows.
  - `freeze()` at track_a.py:375. A frozen twin with learning off.
  - `split(n_val)` at track_a.py:392. Gap, validation, first validation time and latest training label; raises RuntimeError on a label embargo breach.
  - `_weights(days)` at track_a.py:411. Current weights of kept rows, or None.
  - `score(X)` at track_a.py:418. Prediction from the last fit, or the mean of every past fit if `coefficients="averaged"`.
  - `targets(keys, pred)` at track_a.py:423. Position weights, with holding band logic.
  - `decide(v) -> DataFrame or None` at track_a.py:446. None before `first_pick` and before the first fit. Output columns entity_id, share_class, prediction, position. Positions are 0 before `trade_from`.

## agent/baselines.py (130 lines)
Matched baselines that learn nothing; same picks and loop as Track A. Rules in the docstring at baselines.py:1-26.
- `Baseline(n_picks=50, n_side=10, first_pick, trade_from, hold=1)` at baselines.py:33. `LOOKBACK` is 400 days (line 30).
  - `pick(v)` at baselines.py:47. Uses `ReversalAgent.pick`.
  - `returns(v, picks)` at baselines.py:50. Log returns of each pick's bars before today.
  - `scores(v, picks)` at baselines.py:62. Abstract.
  - `positions(picks, score)` at baselines.py:65. Long top n_side, short bottom n_side, ties by id.
  - `decide(v)` at baselines.py:73. Trades every `hold` sessions; zero before `trade_from`.
- `RandomRanking(seed, **kw)` at baselines.py:95. Random score seeded by (seed, date).
- `Momentum` at baselines.py:107. Sum of log returns over bars [-252:-21].
- `Reversal` at baselines.py:115. Minus the sum of the last 5 log returns.
- `EqualWeight` at baselines.py:123. Long-only, each live pick at 1/n (`positions` at 129).

## agent/placebo.py (66 lines)
The shuffled-news placebo.
- `shuffled_links(v, seed) -> story_entities` at placebo.py:28. Permutes companies of embedded links within each decision's group, seeded by (seed, session date).
- `Placebo(inner, seed)` at placebo.py:52. Wraps an agent. `fits` property at placebo.py:60. `decide(v)` at placebo.py:63 gives the inner agent a new View with shuffled links.

## reader/__init__.py (1 line)
Docstring only.

## reader/vintage.py (43 lines)
Which ChronoBERT vintage reads a story.
- `FIRST, LAST = 2015, 2024` at vintage.py:12. `OFFSETS = (0, 1)` at vintage.py:14.
- `check_offset(offset)` at vintage.py:17. Returns the offset if allowed, else ValueError.
- `vintage_for(created_at, offset=0) -> Series` at vintage.py:24. New York year of `created_at` minus 1 minus offset, capped at 2024 minus offset. Raises ValueError if below 2015 minus offset.
- `breaches(embeddings, stories, offset=0) -> DataFrame` at vintage.py:36. Embedding rows whose `vintage_year` is not the rule's year for their story; a missing story counts.

## reader/download.py (74 lines)
Downloads the pinned vintages (`reader/vintages.json`) into DATA_DIR/hf and checks every file.
- `sha256(path)` at download.py:27. File hash.
- `git_oid(path)` at download.py:35. Git blob id of a file.
- `problems(folder, pin) -> list` at download.py:40. What does not match the pins (weights size and hash, four small files by object id).
- `main()` at download.py:59. Fetches each year's pinned commit, checks it, prints a count of matches.

## reader/embed.py (384 lines)
The reader job: every story in story_entities from 2016 on, read by its vintage into two float16 vectors of 768 values. Usage: run, smoke N, finish, arrays, and run-older, finish-older, arrays-older.
- Constants at embed.py:51-58: FIRST_YEAR 2016, PART 5000, BATCH 64, CAP 256, DIM 768, OUT, STORE, OLDER.
- `select(stories, story_entities, offset=0)` at embed.py:63. Stories to read, with vintage_year and available_at.
- `read_stories(offset=0)` at embed.py:76. `select` on the store's tables.
- `parts(story_ids)` at embed.py:83. Cuts ids into parts of 5000.
- `ids_hash(ids)` at embed.py:88. SHA-256 of ids.
- `set_hash(story_ids, updated_at)` at embed.py:92. Hash of each id with its updated_at.
- `manifest(vintage, stories, offset=0)` at embed.py:99. Parts and pinned weights of a vintage.
- `embed_ids(model, encoded, batch=64, pad_id=0) -> (last, avg)` at embed.py:116. Token-mean of the last layer, and mean over layers of the token mean.
- `encode(tok, texts, cap=256)` at embed.py:142. Token ids.
- `part_table(rows, n_tokens, last, avg)` at embed.py:149. One part as an Arrow table; refuses non-finite values.
- `write_atomic(table, path)` at embed.py:167. Write to a temporary name, then rename.
- `check_manifest(folder, want)` at embed.py:174. Writes or checks `manifest.json`.
- `run_vintage(vintage, stories, model, tok, folder, log, offset=0)` at embed.py:186. Reads one vintage part by part, skipping finished parts.
- `load_model(vintage)` at embed.py:203. The vintage's encoder.
- `cmd_run(stories=None, out=OUT, vintages=None, log=print, offset=0)` at embed.py:209.
- `cmd_smoke(n)` at embed.py:227.
- `read_part(path)` at embed.py:236. (rows, last, avg).
- `cmd_finish(out=OUT, store=STORE, offset=0)` at embed.py:248. Checks parts, writes `embeddings.parquet` and `embeddings.json`, then the arrays.
- `ARRAYS` at embed.py:295. `parquet_footer(path)` at embed.py:298. `drop_arrays(store)` at embed.py:310.
- `cmd_arrays(store=STORE)` at embed.py:319. Writes `embeddings_last.npy` and `embeddings_avg.npy` and records them in `embeddings.json`.
- `stay_awake()` at embed.py:351. Asks Windows not to idle-sleep.
- `main(argv)` at embed.py:359.

## reader/cutoff.py (703 lines)
The cutoff check of the vintages (M2 step 2): masked-word loss gains, bootstrap intervals, and the probe-based rules that decide. Usage: sample, pilot, run N, report N, probes2, report-probes2. Rules in the docstring at cutoff.py:1-38.
- Constants at cutoff.py:58-76: YEARS, VINTAGES, CHECK_A, CHECK_B, MASK_RATE, seeds, N_MAX 2000, N_CHOICES, BOOT 10000, OUT, STORE, PROBES, PROBES2, MARGIN 3.0, MIN_INFORMATIVE 3, FAIL_FLAGS 2, PINS.
- Design: `cells()` at 81, `n_masked(n_tokens)` at 86, `mask_positions(story_id, n_tokens)` at 95, `draw_sample(frame, n_max, seed)` at 101, `sample_hash(sample)` at 120.
- Model: `headline_losses(mlm, encoded, story_ids, ...)` at 131, `snapshot(vintage)` at 161, `load_vintage(vintage)` at 166, `tokenizer()` at 180, `headlines()` at 188, `encode(tok, texts, chunk)` at 201.
- Statistics: `gains(losses)` at 210, `boot_means(d, ...)` at 215, `interval(x)` at 236, `statistics(losses, ...)` at 241, `outcomes(G, checks)` at 257, `pick_n(d_own, d_next)` at 277.
- Probes: `load_probes(path)` at 291, `file_sha256(path)` at 306, `span_tokens(offsets, start, end)` at 310, `candidate_inputs(tok, sentence, candidate)` at 315, `candidate_logprob(mlm, ids, pos, mask_id)` at 326, `probe_score(logps)` at 338, `probe_flags(scores, event_year)` at 344.
- Stronger-probe rules: `probe2_lo(scores, V)` at 370 (BASE 3 at line 367), `probe2_threshold(table, probes)` at 377, `probe2_cell(scores, event_year, V, t)` at 387, `probe2_last(scores, t)` at 401, `probe2_outcomes(table, probes)` at 411.
- Commands: `cell_path` at 453, `load_sample` at 457, `cmd_sample` at 465, `measure(todo, n, folder)` at 485, `read_cells` at 526, `cmd_pilot` at 539, `run_probes(folder, path, name)` at 553, `cmd_probes2` at 572, `cmd_report_probes2` at 583, `cmd_run(n)` at 617, `fmt_ci(c)` at 623, `cmd_report(n)` at 627, `main(argv)` at 683.

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

## data_pipeline/benchmarks.py (191 lines)
Builds the two evaluation-only tables: `spy.parquet` and `sectors.parquet` in the store. Writes `research/audit/benchmarks.md` (counts).
- `data_through(root=ROOT)` at benchmarks.py:40. The `data_through` date of `reference/split.json`.
- `fetch_spy(adjustment, end)` at benchmarks.py:45. Pages Alpaca bars for SPY.
- `spy_table(raw, adjusted)` at benchmarks.py:57. One row per session: date, open, close, volume, adj_open, adj_close, ret. Raises if dates repeat or differ.
- `sectors_in(wikitext) -> [(cik, sector)]` at benchmarks.py:80. From one revision of Wikipedia's list.
- `monthly_sectors(last)` at benchmarks.py:99. One row per revision and company, monthly from 2015-01.
- `entity_of_cik(entities)` at benchmarks.py:111. {cik: entity_id} from `reference/entities.csv`.
- `sector_spells(monthly, cik_map)` at benchmarks.py:126. Runs of months with one sector per company; revisions showing two sectors for a company are left out. Returns (spells, count left out). SPELLING at line 122.
- `main()` at benchmarks.py:141. Writes both tables and the report.

## data_pipeline/news.py (87 lines)
Downloads Alpaca (Benzinga) news, one Parquet file per month under `DATA_DIR/news`.
- `months(first, last)` at news.py:25. Year-month pairs.
- `fetch_month(y, m)` at news.py:32. Pages `/v1beta1/news`. The current month ends 20 minutes ago.
- `save(path, rows)` at news.py:44. Columns: id, created_at, updated_at, headline, author, source, url, symbols.
- `run_month(y, m, is_current)` at news.py:60. Skips finished months.
- `main()` at news.py:70. Months from 2015-01 to today (New York date), three at a time.

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

## data_pipeline/split.py (75 lines)
Writes `reference/split.json`: warm-up 2016, dev 2017 to 2019, sealed from 2020-01-01. Counts only.
- `counts(start, end, sessions, members, daily)` at split.py:35. Sessions, member company-days, picked stock-days, story counts for one period.
- `main(last_day=None)` at split.py:55. Reads `research/audit/news_by_day.csv` and `reference/memberships.csv`; writes `reference/split.json`. The default last day is the New York date (line 60).

## data_pipeline/membership.py (152 lines)
S&P 500 membership snapshots and spells.
- `load_snapshots(path=None)` at membership.py:22. [(date, tickers)] from the extended file if it exists, else the source file.
- `members_on(day, snapshots)` at membership.py:34. Tickers in the last snapshot dated at or before the day.
- `spells(snapshots, since)` at membership.py:43. {ticker: [(start, end)]}; end is the first snapshot date without it.
- `extend(snapshots, changes, renames=())` at membership.py:65. Applies the change log and renames after the last snapshot; returns (snapshots, problems).
- `main()` at membership.py:91. Writes `components_extended.csv` and `research/audit/membership.md`.

## data_pipeline/wikipedia.py (166 lines)
Wikipedia's S&P 500 pages, cached under `DATA_DIR/membership/wikipedia`.
- `_get(params)` at wikipedia.py:27. API call with retries.
- `current(title, day)` at wikipedia.py:43. The page as it stands, cached by fetch day.
- `revision(title, day)` at wikipedia.py:52. (timestamp, wikitext) of the revision in force at 00:00 UTC on the day.
- `constituents(wikitext)` at wikipedia.py:130. [{symbol, security, cik, date_added}].
- `changes(wikitext)` at wikipedia.py:149. Change log rows: date, added, removed, reason.
- `today()` at wikipedia.py:165. New York date as ISO text.
- Parsers `_rows`, `_table`, `_header`, `_symbol`, `_name`, `_date` at wikipedia.py:65-127 (starts 65, 84, 90, 101, 109, 116).

## data_pipeline/identity.py (592 lines)
Builds the identity table: entities, tickers by date, memberships. Writes `reference/entities.csv`, `identity.csv`, `memberships.csv` and `research/audit/identity.md`.
- `normalize(symbol)` at identity.py:52. BRK-B, BRK/B to BRK.B.
- `wiki_months(today)` at identity.py:57. One revision per month since 2015-01-01, plus today's. A revision's date is its New York date (line 63).
- `name_changes(today)` at identity.py:73. Alpaca name changes since 2020; cached in `DATA_DIR/corporate_actions/name_changes.json`.
- `Wiki(w)` at identity.py:85. Lookups over the revisions. `resolve(symbol, stamp)` at identity.py:102 gives (cik, how).
- `resolve_spells(spell_map, wiki)` at identity.py:115. Splits each spell into CIK segments.
- `chains(wiki, fixes)` at identity.py:139. Union-find over CIKs.
- `read_fixes()` at identity.py:174. Reads `reference/identity_fixes.csv`.
- `absorb_lag`, `apply_wiki_fixes`, `merge_same_entity`, `apply_segment_fixes`, `periods` at identity.py:180, 196, 207, 219, 246. Segment clean-up and membership periods.
- `timelines(wiki, find, members, fixes, renames, today)` at identity.py:271. Ticker rows with valid_from and valid_to.
- `SymbolIndex(rows=None)` at identity.py:401. Reads `reference/identity.csv`. `lookup(tag, day)` at identity.py:423 gives the entities a tag names on that date. `entities(tags, day)` at identity.py:435 gives (known set, count).
- `overlaps(rows)` at identity.py:446. Symbols meaning two entities on one day.
- `compare(wiki, find, members)` at identity.py:457. Differences from Wikipedia beyond 12 days (LAG_DAYS, line 45).
- `build_all(today)` at identity.py:479. Runs the steps above.
- `write_tables(b)` at identity.py:497, `main()` at identity.py:521. Write the reference CSVs and the report.

## data_pipeline/store.py (333 lines)
Builds the event store (Parquet tables) from bars, auctions, news and reference files. Tables: bars, opens, labels, stories, story_entities, membership, identity.
- `file_rows()` at store.py:65. Every plan row's raw bars with the adjusted return and `foreign`.
- `company_series(df)` at store.py:75. One bar per company, class and date; non-member days only within 400 days before or 14 days after a row.
- `apply_events(s, events)` at store.py:98. Applies `reference/price_events.csv`: override_bar, override_close, total_return, no_trade. New: a total_return row with `open_value` also sets `open_val` and `open_val_time` (lines 137-139).
- `official_opens(s)` at store.py:146. Joins official prints to the series.
- `failures(s, events, within=7 days)` at store.py:156. Series whose last traded bar is followed within 7 days by a failure event.
- `labels(s, opens, data_end, failed)` at store.py:172. Open-to-open total return per official open; ends at the last traded close where the company stopped before `data_end`; -1 for failures; `end_open_time` is when the end open printed. Where the end day has `open_val`, the last piece uses it and the label shows no earlier than `open_val_time` (lines 204-209).
- `stories()` at store.py:219. Benzinga stories passing `keep_story`, and (story, company) pairs for stories naming 1 or 2 companies.
- `reference_tables()` at store.py:234. Membership and identity tables.
- `main()` at store.py:244. Writes the seven tables, `counts.json` and `research/audit/store.md`.
- `report(c)` at store.py:307. Writes the counts report.

## Time cut-offs and store reads

### Time cut-off sites (36)
1. world/rules.py:18, 27-28. News available at `updated_at` plus 15 minutes.
2. world/rules.py:31-33. An embedding is available when its story is.
3. world/rules.py:19, 36-38. Stories edited over 3 days after publishing are dropped.
4. world/rules.py:41-42. Bar available 16:00 New York on its date.
5. world/rules.py:45-46. Official open available 9:30 on its date.
6. world/rules.py:49-61. Label available at the end open (or the next session's open after a close exit, or the later printed open time).
7. world/rules.py:64-65. Membership change available 0:00 on its date.
8. world/rules.py:23-24. HISTORY_BEFORE 400 days and HISTORY_AFTER 14 days.
9. world/world.py:86-107. `known_from`: when a company's record may show, by membership spell.
10. world/world.py:110-139. `visible_at`: rule time or `known_from`, whichever is later; embeddings with their story's first link.
11. world/world.py:165-167. `_Sorted.upto`: only rows visible at or before the time.
12. world/world.py:250-257. `_SortedEmbeddings.upto`: rows visible at the time and after `since`.
13. world/world.py:49, 365. The embedding window: 90 days up to t, measured on visible_at.
14. world/world.py:346-350. `members_at`: join and leave events at or before the time.
15. world/world.py:352-367 (check at 357-361). `view(t)` returns prefixes at t; sealed dates refused unless `allow_sealed`, and always with a vintage_offset.
16. world/view.py:29-30. `sessions` cut to the New York date of t.
17. world/world.py:321-325. Late-edited stories and their entity rows dropped at load.
18. world/clock.py:14, 49-50. Decision time 9:00 New York.
19. sim/seal.py:116-134, 179-199. Dates in the sealed years need a matching seal.lock (part settings, PREREG.md hash, the lock-commit rule) and a clean tree, and each part starts once (run log).
20. sim/simulator.py:73. A label is marked on the day it ends (or the day after a close exit).
21. sim/simulator.py:85-89. Forced sales except on the data's last day.
22. sim/simulator.py:145-182, 221-257, 259-280. `run`, `run_many` and `replay` seal dates and give the agent the view at 9:00 each session.
23. sim/simulator.py:184-195. A World with a vintage_offset reaches the sealed years only as the sealed older_vintage part.
24. eval/leaks.py:35-53. `late_rows`: records not visible at t, embeddings included.
25. eval/leaks.py:126-133. Changed records forced to stay hidden at t.
26. eval/leaks.py:174-185. Decision time of `last` is the cut for the perturbation.
27. agent/reversal.py:40-42, 52, 66-69, 80, 97. Pick window (to the day before today), 45-day feature window, labels only from the view, `latest_label` record, `first_pick` date.
28. agent/track_a.py:186, 223-260, 293-325, 392-409. Features from bars before today within 200 days; news pairs new since the last decision; labels enter only when in the view or 10 sessions old; the label embargo split.
29. agent/baselines.py:47-60, 73-92. Bars before today within 400 days; zero positions before `trade_from`.
30. agent/placebo.py:28-49. Groups links by the first session whose 9:00 is at or after their availability.
31. reader/vintage.py:24-33. Vintage is the New York year of `created_at` minus 1 minus offset, capped at 2024 minus offset.
32. data_pipeline/store.py:55-59, 75-96. Non-member bars kept 400 days before and 14 days after a row. Also 156-170 (failure within 7 days), 192 and 248-250 (data end), 223 (3-day edit rule), 204-209 (ex-date label end).
33. data_pipeline/prices.py:25-31, 44-50. Incomplete-bar rule uses only the previous 20 bars.
34. data_pipeline/bars.py:40-44 and news.py:32-36. Never ask for the latest day (bars) or latest 20 minutes (news).
35. data_pipeline/identity.py:423-433 and audit_news.py:41-59, 62-70. Tags mapped to companies, and members taken, on the story's New York date. Also identity.py:63 and news.py:73, split.py:60, wikipedia.py:165 (New York dates).
36. data_pipeline/audit_prices.py:48-61, 190-215 and membership.py:34-40. Pick dates, members on a day, year of trading before the pick date. Also auctions.py:46-47, 102-135, 160-168 and wikipedia.py:52-62 (21-session window vote, the one-hour late-open rule, the Wikipedia revision in force at 00:00 UTC on a day).

### Store reads (direct path or table name) (30)
1. world/world.py:57-59. `reference/split.json`.
2. world/world.py:379-386. DATA_DIR/store files: bars, labels, opens, stories, story_entities, membership (Parquet).
3. world/world.py:277-293. `embeddings.json`, `embeddings.parquet`, and the two `.npy` arrays in the store (or the older-vintage folder).
4. sim/seal.py:50-55. `reference/split.json`.
5. sim/seal.py:62-71, 116-160. `seal.lock`, `PREREG.md` and the run log `DATA_DIR/sealed/runs.jsonl`.
6. eval/benchmarks.py:15, 20. `spy.parquet` and `sectors.parquet` in the store.
7. eval/trials.py:54-59, 30-52. Reads and appends `runs/trials.csv`; writes `runs/settings/<hash>.json`.
8. eval/report.py:58-63, 279. Reads the trials CSV; charts go to `DATA_DIR/runs/m3_dev_report_charts`.
9. reader/embed.py:56-58, 76-80. `DATA_DIR/reader`, `reader_older`, and store `stories.parquet` and `story_entities.parquet`.
10. reader/embed.py:248-292, 319-348. Writes `embeddings.parquet`, `embeddings.json`, and the two `.npy` files.
11. reader/cutoff.py:69-76, 188-200. Cutoff outputs in `DATA_DIR/reader/cutoff`, `reader/probes.csv`, `probes2.csv`, `vintages.json`, and store stories.
12. reader/download.py:23. `reader/vintages.json`; models go to `DATA_DIR/hf`.
13. data_pipeline/prices.py:21-22, 35, 58. `DATA_DIR/bars/plan.csv` and `bars/<adjustment>/*.parquet`.
14. data_pipeline/bars.py:78-79. `reference/identity.csv`, `reference/memberships.csv`. Also lines 36 and 55 (plan and bar files).
15. data_pipeline/news.py:21, 61. `DATA_DIR/news/<year-month>.parquet`.
16. data_pipeline/auctions.py:36-41, 59, 65, 154, 173-176, 247. Bar files, `plan.csv`, prints files, `official.parquet`, `audit/official_prints.csv`, `official_prints_input_v2.csv`.
17. data_pipeline/audit_prices.py:39-44. `reference/entities.csv`, `memberships.csv`, `price_events.csv`.
18. data_pipeline/audit_prices.py:286. `DATA_DIR/audit/official_prints.csv`.
19. data_pipeline/audit_news.py:95. `DATA_DIR/news/*.parquet`.
20. data_pipeline/audit_news.py:65. `reference/memberships.csv`.
21. data_pipeline/audit_news.py:160-162. `research/audit/universe_preview.csv`.
22. data_pipeline/split.py:56-57. `research/audit/news_by_day.csv`, `reference/memberships.csv`.
23. data_pipeline/membership.py:16-17, 22-29. `DATA_DIR/membership/components_updated.csv` and `components_extended.csv`.
24. data_pipeline/wikipedia.py:18, 43-49, 52-61. Cache `DATA_DIR/membership/wikipedia/`.
25. data_pipeline/identity.py:174-177. `reference/identity_fixes.csv`.
26. data_pipeline/identity.py:44, 73-82. `DATA_DIR/corporate_actions/name_changes.json`.
27. data_pipeline/identity.py:412. `reference/identity.csv` (in `SymbolIndex`).
28. data_pipeline/store.py:65-67, 148, 223, 235-239, 251. Bars via `prices.load`, `DATA_DIR/auctions/official.parquet`, news via `audit_news.load`, and `reference/memberships.csv`, `identity.csv`, `entities.csv`, `price_events.csv`.
29. data_pipeline/benchmarks.py:35, 41, 146-150, 154. `DATA_DIR/bars/benchmark/SPY__<adjustment>.parquet`, `reference/split.json`, `reference/entities.csv`; Wikipedia revisions via `wikipedia.revision`.
30. data_pipeline/benchmarks.py:152, 158, 186. Writes `spy.parquet`, `sectors.parquet` and `research/audit/benchmarks.md`.

The store's own writes are at store.py:266 and 299 (bars, opens, labels, stories, story_entities, membership, identity Parquet) and store.py:302 (`counts.json`).
