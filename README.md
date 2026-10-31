# Chrono-trader

An AI that lives through US stock market history once, in order. Each day it sees only what was public by then. It reads the news with a language model whose training ended before that year, and it learns only from outcomes it has already lived through. The goal is a trading AI that has learned to trade from what it lived through.

The full plan is [PLAN.md](PLAN.md). [REVIEW.md](REVIEW.md) is the review that moved the data from FNSPID to Alpaca.

## Status

M0, the data audit, is done (PLAN.md, section 9.3). The answers are in [research/audit/audit.md](research/audit/audit.md):

- **Identity:** every S&P 500 member since 2015 under a permanent company ID (its SEC CIK), with its tickers and share classes by date: [reference/](reference/), checked by `pytest`. Audit: [research/audit/identity.md](research/audit/identity.md).
- **Prices:** daily bars for every member company since 2016, raw and adjusted, fetched per ticker and date from the identity table. Audit: [research/audit/prices.md](research/audit/prices.md). Corrections, each with its evidence: [reference/price_events.csv](reference/price_events.csv).
- **News:** every Alpaca (Benzinga) headline since January 2015. Audit: [research/audit/news.md](research/audit/news.md).
- **Split:** the dev and sealed years, confirmed with counts only: [reference/split.json](reference/split.json).

Nothing is trained yet. Next is M1, the time wall.

## Setup

1. Python 3.13:

   ```
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
   ```

   On the original laptop, `.venv` is a link to `D:\venvs\chrono-trader`, to keep C: free.
2. Copy `.env.example` to `.env` and fill in Alpaca keys. A free paper account works. `.env` is gitignored, so never commit it or paste it anywhere.
3. Data lives outside the repo, in `CHRONO_DATA_DIR` (default `D:\chrono-data`). Put the S&P 500 components history from [fja05680/sp500](https://github.com/fja05680/sp500) (MIT license) at `membership\components_updated.csv` inside it.

## Commands

Run these from the repo root with the venv's Python.

| Command | What it does |
|---|---|
| `python research/alpaca_check.py` | Checks that the keys reach Alpaca's news and prices. It prints counts only |
| `python -m data_pipeline.membership` | Extends the fja05680 membership file to today with Wikipedia's change log, and writes `research/audit/membership.md` |
| `python -m data_pipeline.identity` | Builds the identity tables in `reference/` from Wikipedia's monthly lists and the hand-checked `reference/identity_fixes.csv`, and writes `research/audit/identity.md` |
| `python -m pytest tests` | Checks the identity tables |
| `python -m data_pipeline.bars` | Downloads daily bars for each company's tickers, as the identity table dates them. It writes the download plan and resumes |
| `python -m data_pipeline.news` | Downloads every news headline, one file per month. About 4.5 hours, and it resumes |
| `python -m data_pipeline.audit_prices` | Writes `research/audit/prices.md` and its CSVs (about 3 minutes) |
| `python -m data_pipeline.audit_news` | Writes `research/audit/news.md` and its CSVs (about 3 minutes) |
| `python -m data_pipeline.split` | Writes `reference/split.json` from counts only |
| `python research/verify_prints.py IN OUT` | Checks daily bars against the exchanges' official opening and closing auction prints |
| `python research/identity_evidence.py` | Looks up local evidence for identity questions (Wikipedia revisions, change log, news tags, bars) |
| `python research/bench_chronobert.py` | Times ChronoBERT on the CPU |

## Data and licensing

Raw news and prices never go into git. Benzinga news and market data can't be redistributed, so only code, decisions, small audit summaries and the hand-checked reference tables are committed. A few rows of `reference/price_events.csv` carry single prices (official opening and closing prints) as corrections.
