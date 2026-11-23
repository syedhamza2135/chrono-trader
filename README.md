# Chrono-trader

An AI that lives through US stock market history once, in order. Each day it sees only what was public by then. It reads the news with a language model whose training ended before that year, and it learns only from outcomes it has already lived through. The goal is a trading AI that has learned to trade from what it lived through.

The full plan is [PLAN.md](PLAN.md). [REVIEW.md](REVIEW.md) is the review that moved the data from FNSPID to Alpaca.

## Status

M0, the data audit, is done (PLAN.md, section 9.3). The answers are in [research/audit/audit.md](research/audit/audit.md):

- **Identity:** every S&P 500 member since 2015 under a permanent company ID (its SEC CIK), with its tickers and share classes by date: [reference/](reference/), checked by `pytest`. Audit: [research/audit/identity.md](research/audit/identity.md).
- **Prices:** daily bars for every member company since 2016, raw and adjusted, fetched per ticker and date from the identity table. Audit: [research/audit/prices.md](research/audit/prices.md). Corrections, each with its evidence: [reference/price_events.csv](reference/price_events.csv).
- **News:** every Alpaca (Benzinga) headline since January 2015. Audit: [research/audit/news.md](research/audit/news.md).
- **Split:** the dev and sealed years, confirmed with counts only: [reference/split.json](reference/split.json).

A review of the M0 work confirmed 33 findings. The findings, the fixes and what is left are in [research/audit/m0_review.md](research/audit/m0_review.md).

M1, the time wall, is built and merged, and the findings of two reviews are fixed, with a few items left (PLAN.md, section 9.2; state, findings and decisions in [research/m1_kickoff.md](research/m1_kickoff.md)):

- **Official opens:** the listing exchange's opening and closing auction prints for every stock-day with a bar, from Alpaca's auctions endpoint. Audit: [research/audit/auctions.md](research/audit/auctions.md).
- **The event store:** bars, official opens, open-to-open labels, stories, the single-firm filter's links, membership and identity, as Parquet in `D:\chrono-data\store`. Counts: [research/audit/store.md](research/audit/store.md).
- **The time wall:** `world/` (the clock, the availability rules, `World.view(t)`), `sim/` (fills at the official open, costs, exits, the seal), `eval/` (the daily rank IC and the non-interference check) and a toy agent in `agent/`.
- **The tests in PLAN 9.11,** including the planted leaks and both import boundaries.

M2, the reader, has its table (PLAN.md, section 5.2; state and decisions in [research/m2_kickoff.md](research/m2_kickoff.md)):

- **The vintages:** all 11 ChronoBERT vintages (2014 to 2024), pinned by commit and weights hash in [reader/vintages.json](reader/vintages.json), on D:.
- **The cutoff check:** only the 2016 vintage is supported by evidence; the other nine that read news are too weak to judge, and the owner accepted all 11 as published, a known limit. Audit: [research/audit/cutoff.md](research/audit/cutoff.md).
- **The embeddings:** 502,712 stories, each read by the vintage the rule names, in `D:\chrono-data\store\embeddings.parquet`, served to agents only through `World.view(t)`. Audit: [research/audit/reader.md](research/audit/reader.md). Reviews: [research/audit/embed_judge.md](research/audit/embed_judge.md).

M3, Track A on the dev years, is built and reviewed (PLAN.md, section 9.2; state, decisions and the frozen trial plan in [research/m3_kickoff.md](research/m3_kickoff.md)):

- **Benchmarks for the report only:** SPY's daily bars and each company's GICS sector by date (`data_pipeline/benchmarks.py`, read only by `eval/benchmarks.py`). Audit: [research/audit/benchmarks.md](research/audit/benchmarks.md).
- **The 90-day embedding window:** a view serves only the embeddings that became visible in the last 90 days.
- **The agent:** `agent/track_a.py`, the monthly ridge learner over news embeddings and price features that ranks the 50 most-traded members.
- **The comparison harness:** frozen twins, the price-only twin, the shuffled-news placebo (`agent/placebo.py`), the baselines (`agent/baselines.py`) and the ledger `runs/trials.csv` (`eval/trials.py`), all fed by one pass over the views (`sim.simulator.run_many`).
- **The report:** metrics (`eval/metrics.py`), statistics (`eval/stats.py`), the switch-day check (`eval/switch_day.py`), charts (`eval/charts.py`) and the writer (`eval/report.py`). Results: [research/m3_dev_report.md](research/m3_dev_report.md). The older-vintage check: [research/m3_older_vintage.md](research/m3_older_vintage.md). Review: [research/review_m3_2026-11-23.md](research/review_m3_2026-11-23.md).

On the dev years (2017 to 2019) the chosen configuration's mean daily rank IC is 0.0076 (t 1.38), and its long-short book loses money after 5 bps. The sealed years stay shut.

## Setup

1. Python 3.13:

   ```
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
   ```

   On the original laptop, `.venv` is a link to `D:\venvs\chrono-trader`, to keep C: free.
2. Copy `.env.example` to `.env` and fill in Alpaca keys. A free paper account works. `.env` is gitignored, so never commit it or paste it anywhere. A git worktree has no `.env` of its own: set `CHRONO_ENV_FILE` to the main checkout's `.env` there, rather than copying it.
3. Data lives outside the repo, in `CHRONO_DATA_DIR` (default `D:\chrono-data`). Put the S&P 500 components history from [fja05680/sp500](https://github.com/fja05680/sp500) (MIT license) at `membership\components_updated.csv` inside it.

## Commands

Run these from the repo root with the venv's Python.

| Command | What it does |
|---|---|
| `python research/alpaca_check.py` | Checks that the keys reach Alpaca's news and prices. It prints counts only |
| `python -m data_pipeline.membership` | Extends the fja05680 membership file to today with Wikipedia's change log, and writes `research/audit/membership.md` |
| `python -m data_pipeline.identity` | Builds the identity tables in `reference/` from Wikipedia's monthly lists and the hand-checked `reference/identity_fixes.csv`, and writes `research/audit/identity.md` |
| `python -m pytest tests` | Checks the identity tables, the price and news audits' rules, the split, the print check, M1 (the auctions, the store's rules, the time wall, the simulator, the seal, the import boundaries and the leak tests) and M2 (the cutoff check's rules, the reader job, the embeddings' time wall and the real embeddings table) and M3 (the window, the agent, the harness, the metrics and the vintage offset). About 35 to 52 minutes. Tests that need the store or the embeddings skip without them, and the slow leak test runs only with `CHRONO_SLOW_LEAKS=1` |
| `python -m data_pipeline.bars` | Downloads daily bars for each company's tickers, as the identity table dates them. It writes the download plan and resumes |
| `python -m data_pipeline.news` | Downloads every news headline, one file per month. About 4.5 hours, and it resumes |
| `python -m data_pipeline.audit_prices` | Writes `research/audit/prices.md` and its CSVs (about 3 minutes), including `incomplete_bars.csv`: member bars with a trade count below 5% of the median of the file's previous 20 bars |
| `python -m data_pipeline.audit_news` | Writes `research/audit/news.md` and its CSVs (about 3 minutes), including `news_by_day.csv`: stories and single-firm stories about members per New York date |
| `python -m data_pipeline.auctions` | Fetches the official auction prints for every bar file of the bar plan (about 15 minutes, and it resumes), then writes `research/audit/auctions.md` and compares them with the M0 print check |
| `python -m data_pipeline.store` | Builds the event store in `D:\chrono-data\store` from the bars, the official opens, the news and `reference/` (a few minutes), and writes `research/audit/store.md` |
| `python -m data_pipeline.split 2026-10-28` | Writes `reference/split.json` from counts only: the NYSE calendar, `reference/memberships.csv` and `research/audit/news_by_day.csv` (run the news audit first). The argument is the last day of data; without it the split runs to today |
| `python research/verify_prints.py IN OUT` | Checks daily bars against the listing exchange's official opening and closing auction prints, to within a cent or 0.2%. OUT has 19 columns, including `listing_exchange`, `open_checked` and `close_checked`. It resumes an OUT with the same columns and refuses one with other columns, so write to a new file |
| `python research/identity_evidence.py` | Looks up local evidence for identity questions (Wikipedia revisions, change log, news tags, bars) |
| `python research/bench_chronobert.py` | Times ChronoBERT on the CPU |
| `python -I reader/download.py [year ...]` | Downloads the pinned ChronoBERT vintages into `D:\chrono-data\hf` and checks every file against `reader/vintages.json` (all 11 by default; it resumes) |
| `python -m reader.cutoff sample \| pilot \| run N \| report N` | The cutoff check: draws the fixed sample, runs the pilot, reads every (vintage, year) cell and the named-event probes, and prints every number of `research/audit/cutoff.md`. Outputs in `D:\chrono-data\reader\cutoff` |
| `python -m reader.cutoff probes2 \| report-probes2` | The stronger probes (`reader/probes2.csv`, frozen by its SHA-256) and their report (`research/audit/cutoff.md`, section 8) |
| `python -m reader.embed smoke N` | Reads the first N stories of the 2015 and 2024 vintages into `D:\chrono-data\reader\smoke`; check them with `python research/check_smoke.py` |
| `python -m reader.embed run` | Reads every story from 2016 on with the vintage the rule names, part by part, into `D:\chrono-data\reader\v{vintage}`. About 6 hours on the laptop; it resumes at the first missing part and keeps the laptop from idle sleep |
| `python -m reader.embed finish` | Checks every part against its manifest and the store, then writes `embeddings.parquet`, `embeddings.json` and the two `.npy` arrays to the store |
| `python -m reader.embed arrays` | Writes the `.npy` arrays again from `embeddings.parquet` (`World.load` maps them read-only) |
| `python -m reader.embed run-older`, `finish-older`, `arrays-older` | The same jobs for the older-vintage rerun (M3 step 7): every story read by the vintage a year older, all into `D:\chrono-data\reader_older` |
| `python -m data_pipeline.benchmarks` | Downloads SPY's bars and builds the sector table from the saved Wikipedia lists, into `store\spy.parquet` and `store\sectors.parquet`, and writes `research/audit/benchmarks.md` |
| `python research/track_a_timing.py` | Times one Track A run over 2016 to 2019. Prints times, counts and memory only |
| `python research/m3_compare_timing.py` | Times one comparison pass with every agent over 2016 to 2019. Prints times, counts and memory only |
| `python research/m3_trial_plan.py [--log]` | Prints the frozen trial plan's SHA-256; with `--log`, adds the planned rows to `runs/trials.csv` |
| `python research/m3_dev_runs.py stage1 \| stage2 \| compare \| report` | The dev runs under the frozen plan: stage 1, stage 2, the comparison pass with its cost replays, and `research/m3_dev_report.md` (charts to D:). Each run is a row of `runs/trials.csv`; outputs in `D:\chrono-data\runs\m3_dev` |
| `python research/m3_older_vintage.py space`, `count`, `run`, `result` | The older-vintage rerun's steps: disk space, the table's counts, the rerun of the chosen configuration, and the warning rule |
| `python research/m4_sealed_run.py settings`, `dev-check`, `seal`, `run main`, `run older_vintage` | M4's sealed run (`research/m4_kickoff.md`): each part's settings hash, the dev check at the sealed commit, the `seal.lock` writer, and each part's one sealed run (`--again` for a second, logged as another trial). Only on the owner's go |
| `python research/reader_stats.py` | The run's counts, speeds and disk use, for `research/audit/reader.md` |
| `python research/world_memory.py` | `World.load`'s time and memory with the embeddings, and the cost of a view in each period |

## Data and licensing

Raw news and prices never go into git. Benzinga news and market data can't be redistributed, so only code, decisions, small audit summaries and the hand-checked reference tables are committed. The exception is `reference/price_events.csv`: 120 of its 125 rows carry prices. 62 hold them in the price columns (54 official opens, 7 official closes, and Nordstrom's 2018-03-26 bar rebuilt from clean trades, with its volume). 58 quote the Alpaca closes behind a distribution's or a merger's true return in their evidence. The other 5 (two Biogen halts and three bank failures) carry none. Its evidence notes also quote a few short Benzinga headlines.
