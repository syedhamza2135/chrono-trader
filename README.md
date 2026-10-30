# Chrono-trader

An AI that lives through US stock market history once, in order. Each day it sees only what was public by then. It reads the news with a language model whose training ended before that year, and it learns only from outcomes it has already lived through. The goal is a trading AI that has learned to trade from what it lived through.

The full plan is [PLAN.md](PLAN.md). [REVIEW.md](REVIEW.md) is the review that moved the data from FNSPID to Alpaca.

## Status

M0, the data audit, is nearly done (PLAN.md, section 9.3):

- **Prices:** daily bars for every S&P 500 member since 2016, raw and adjusted. Audit: [research/audit/prices.md](research/audit/prices.md).
- **News:** every Alpaca (Benzinga) headline since January 2015. Audit: [research/audit/news.md](research/audit/news.md).
- **Next:** the identity table, which maps tickers to permanent company IDs by date. Then a check of one suspect Nordstrom price.

Nothing is trained yet.

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
| `python -m data_pipeline.bars` | Downloads daily bars for every membership spell. About 10 minutes, and it resumes |
| `python -m data_pipeline.news` | Downloads every news headline, one file per month. About 4.5 hours, and it resumes |
| `python -m data_pipeline.audit_prices` | Writes `research/audit/prices.md` and its CSVs |
| `python -m data_pipeline.audit_news` | Writes `research/audit/news.md` |
| `python research/bench_chronobert.py` | Times ChronoBERT on the CPU |

## Data and licensing

Raw news and prices never go into git. Benzinga news and market data can't be redistributed, so only code, decisions and small audit summaries are committed.
