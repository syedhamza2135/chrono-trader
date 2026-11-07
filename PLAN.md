# Chrono-trader: problem statement and plan

Status: M0, the data audit, is done (section 9.3, with the answers in `research/audit/audit.md`), and the fixes from its review are in (`research/audit/m0_review.md`). The time wall, the reader and the learner aren't built yet.

This is version 2 (30 Oct 2026). It's rebuilt on Alpaca data after the review in `REVIEW.md`. The review's evidence and probe scripts stay in `REVIEW.md` and `research/fnspid_probes/`.

Decisions so far:
- **29 Oct 2026: Track A comes first** (a time-locked reader plus a learner). Track B (a time-locked LLM trader) follows on the same harness.
- **30 Oct 2026: the data comes from Alpaca.** That means Benzinga news from 2015 and daily prices from 2016, with delisted companies kept.
  - FNSPID is dropped. Its timestamps are 8 hours early, almost all rows have no time of day, the biggest stocks have a 2020 to 2022 news hole, and its prices leave out most acquired companies (`REVIEW.md`, C1 to C4).

- **30 Oct 2026: Alpaca access is confirmed.** A paper account opened from Pakistan works, and its keys reach news and prices on the free plan.
  - The first audit results are in section 9.3.
  - The keys live in `.env`, which git ignores.
- **30 Oct 2026: the reader reads headlines only.** Summaries and article text appear unevenly across the years (section 5.2).
- **30 Oct 2026: one share class per company.** GOOG and GOOGL both rank in the top 50 every year, which would let the ranking bet a company against itself. Keep the more liquid class.
- **30 Oct 2026: Benzinga stories only.** Alpaca added a second source, fiscal.ai, on 18 Oct 2026, and it has made up 59% of the feed since. Every earlier story is Benzinga's, so keeping fiscal.ai would hand the forward test a news mix the model never learned on.
- **30 Oct 2026: the reader can run on the laptop.** It only needs single-firm stories about S&P 500 members: 511,678 headlines from 2016 to 2026. At 6 to 7 headlines a second that's about 22 hours, run a year at a time. This replaces the earlier plan to read on a free cloud GPU, which assumed millions of headlines. A cloud GPU is still the faster option, and M2 picks one.
- **31 Oct 2026: companies, not tickers.** Every S&P 500 member since 2015 has a permanent ID, its SEC CIK, with its tickers and share classes by date (`reference/identity.csv`). Prices are fetched per ticker inside those dates, and news tags map to companies by date. Counted by company, the reader needs 500,745 headlines (section 9.3).
- **31 Oct 2026: price corrections are data.** Alpaca's adjusted bars get most spin-offs wrong, and its daily open is the first trade on any venue, which can be far from the opening auction on a chaotic day. Corrections live in `reference/price_events.csv`, each with its evidence, and the simulator and features must apply them.
- **4 Nov 2026: incomplete bars are missing data.** On 2021-04-19, 2021-10-25 and 2022-03-08, Alpaca's bars for 326 to 356 NYSE-listed members a day hold only a handful of trades. A bar whose trade count is below 5% of the median of its file's previous 20 bars is flagged (`prices.incomplete`): 1,035 member bars, counting one more on 2018-03-26. The features must treat those bars as missing, and the stock picker ranks without them.
- **4 Nov 2026: Alpaca's daily open is the first trade, not the opening auction.** Judged to within a cent, or 0.2% when that is more, it misses the listing exchange's opening auction on 23 of 300 random stock-days, and on 259 of the 787 stock-days checked. Beyond the 54 already in `reference/price_events.csv`, misses aren't corrected one at a time. Instead, M1 fetches the listing exchange's official opening auction print for every stock-day the simulator trades (sections 8 and 9.3).
- **7 Nov 2026: a research brief was checked before any of it was adopted.** `research/brief_check.md` records its claims, the verified facts, what the plan takes from it, what waits and what it rejects.
- **7 Nov 2026: the official opens come from Alpaca's auctions endpoint.** `/v2/stocks/auctions` returns each stock-day's auction prints from every exchange on the free plan. `data_pipeline/auctions.py` fetched them for all 787 bar files, which is 1,873,240 stock-days on NYSE sessions, in about 15 minutes (the files' write times). A stock-day's official open is the listing exchange's largest opening print, as in the M0 print check, and the two agree on all 785 opens and 783 closes the print check judged on plan stock-days (`research/audit/auctions.md`).
- **7 Nov 2026: the simulator trades a stock only at its official open.** 521 of 1,371,723 member stock-days have none: 267 on 2023-01-24 (the NYSE's failed openings), 108 on 2018-01-24 and 66 on 2022-03-08. On such a day the stock isn't traded, and a holding waits for its next official open (`research/audit/auctions_missing_opens.csv`).
- **7 Nov 2026: a label runs from one official open to the next.** It chains the corrected close-to-close total returns between them, so the closes cancel and a wrong close can't move a label. A company that stops trading exits at its last traded close, and that last label shows at the next session's open, like every other label. So a failure halted before the next open (SVB on 2023-03-10) isn't known early.
- **7 Nov 2026: the store keeps a company's days outside membership only near it.** That means up to 400 days before a membership (the stock picker's year, and the 60 days of features) and 14 days after (to sell a removed stock). Further away, a file's bars can be another security's: IHS Markit's INFO file holds a thin NYSE Arca security in 2025.
- **7 Nov 2026: a view shows a company's records only near its memberships.** The store holds every company that was a member at any time since 2015, so showing one outside its memberships would tell the agent it joins, or rejoins, later. A record dated inside a membership, or up to 14 days after one, shows at its own time. One dated up to 400 days before a membership shows from that membership's start, also for a rejoin (EQT's bars from before its 2022 rejoin show at the rejoin, not during its 2018 to 2022 gap). Views hold copies with plain string keys, so nothing reachable from a view holds a later record, and agents may import only `View` (`world/view.py`); `World` is in `world/world.py`.
- **7 Nov 2026: a label shows when the open that ends it prints.** That is 9:30 on its end date, or later for a delayed opening.

## 1. Problem statement

Build an AI that lives through stock market history once, in order, and learns to trade from what it lives through.

Each trading day it sees only what was public before it decides. Track A uses prices and news. Later versions add SEC filings and economic data, each as it stood on that day.

It reads the news with a language model whose training ended before that day. So it arrives able to read, but knowing nothing about the market. It picks positions, sees what happens, and updates itself. It can study its own past as often as it likes. It can never see a day it hasn't lived.

The question it answers: **does it get better with experience, on days it could not have known about?**

### What "learned, not pattern-matched" means here

Every model learns patterns, and so do people. What matters is when the patterns were learned. A model trained on today's internet has read how 2008, 2020 and 2022 ended, so in a backtest it can recall the answers instead of working them out. This project's AI can only learn from days it has already lived. Four properties have to hold at the same time:

1. **Its weights can't know the future.** Every model it uses finished training before the day it's used.
2. **Its data is point-in-time.** Every record carries the moment it became public, and the AI can't see it before then.
3. **It learns in a single pass.** It learns only from outcomes that have already happened, in order, one day at a time.
4. **There is a checked guarantee.** Automated tests prove that changing anything in the future can't change a past decision.

**Frontier models never decide.** They can write code, tests and reports. They make no decision on a replayed day, and they write no lessons, priors, rubrics or features that carry what happened later.

**What Track A learns, honestly:** which stocks to rank above others, from news and recent prices. We set how long to hold, how much to bet, and the long/short rules. Learning those from experience is a later step and needs far more data than one replay of history.

The headline result is the **learning evidence** in section 5.5, not a profit number.

## 2. What exists, and the gap

| Approach | Examples | What it solves | What it leaves open |
|---|---|---|---|
| Frontier-LLM agents on point-in-time data | TradingAgents (v0.5, Sept 2026), TraderHarness, OpenPM, LumiBot | The data is timed correctly | The model's weights already know what happened. Masking names and dates doesn't fix that, and neither does telling the model to ignore what it knows |
| Agents that learn from experience | TradingAgents' decision log and reflections. EvolveTrade rewrites its own instructions after seeing its results | Learning between decisions | Built on models that know the past, and the learning lives in prompts, not weights |
| Time-locked models | ChronoBERT, ChronoGPT, ChronoGPT-Instruct, DatedGPT, PIT models, Time Machine GPT | Weights trained only on text up to a cutoff date | Used in research regressions and benchmarks, not inside a trading agent with costs, leak tests and a forward test |
| Live benchmarks | LiveTradeBench, StockBench, Alpha Arena | No leakage, because they trade forward in real time | Can't replay history, each result takes months, most models don't learn between days, and most fail to beat buy-and-hold |
| Leak checking | OpenPM's contamination certificate, Fonseca's formal non-interference checker, Look-Ahead-Bench | Ways to measure or prove leakage | Tools, not agents |

**What's already been done.** The ChronoBERT paper's real-time test already meets properties 1 to 3 as a research regression:
- each year's news is read by the previous year's model
- a ridge regression is refit every month on past data only

Track A builds on that design.

**What I didn't find anywhere:**
- An open harness where the no-leak guarantee is checked by machine (property 4).
- The learning itself measured directly, against frozen copies of the same agent.
- Trading costs, plus a live forward test on the same data source as the backtest.
- Track B: an agent on time-locked weights that learns from its own experience.

## 3. Research findings that shape the design

### Leakage through the model is real, and prompting doesn't remove it

- **Lopez-Lira, Tang and Zhu.** Once a model has seen an outcome, a correct forecast can't be told apart from recall. Masking company names and dates fails, because models rebuild them from context. Telling the model to respect the date also fails. Their suggested workaround is to rewrite text as anonymized economic logic, which reduces recall.
- **Sarkar and Vafa.** They found lookahead bias in two forecasting tasks and explain why fixes based on prompting are limited.
- **Glasserman and Lin.** GPT-3.5 sentiment on headlines with company names removed did better in-sample, and the gap faded out of sample. The effect was strongest for large firms, which the model knows most about.
- **Dated Data (Cheng et al.).** A model's real knowledge cutoff can differ from the stated one, so we check our reader's cutoff ourselves.
- **Profit Mirage (Li et al.).** Five LLM trading agents (FinMem, FinAgent, QuantAgent, FinCON and TradingAgents), all on GPT-4o, traded NASDAQ-100 stocks. From a 2021 period before GPT-4o's cutoff to a 2024 period after it, their total return fell by 50% to 72% and their Sharpe ratio by 51% to 62%. The paper runs no random baseline.

### Time-locked models exist, are open, and hold up

| Model | Size | Vintages | Weights | Notes |
|---|---|---|---|---|
| ChronoBERT | 149M-parameter ModernBERT encoder, 1,024-token context, ModernBERT's tokenizer | Yearly, 1999 to 2024 (26 models) | `manelalab` on Hugging Face, MIT license | The reader for this project |
| ChronoGPT | 1.55B-parameter decoder, 1,792-token context | Yearly, 1999 to 2024 | `manelalab`, MIT license | Custom architecture with its own inference script |
| ChronoGPT-Instruct | About 1.55B | Yearly, 1999 to 2024 (the paper evaluates a subset) | `manelalab` | Chat model. Got 0 of 76 major events after its cutoff right |
| DatedGPT | Twelve 1.3B models, about 100B tokens each | Yearly, 2013 to 2024 | Demo at datedgpt.com. Public weights not confirmed | Instruction-tuned, including finance data |
| PIT models (Kelly, Malamud, Schwab, Xu) | Up to 4B, trained on 1T tokens | Yearly, one checkpoint each December from 2013 to 2024, with November instead of December in 2015. The abstract says monthly, but the paper's text and the released weights are yearly | `Diamegs` on Hugging Face, the account the paper names | Don't cover 1999 to 2012 |

**The cutoffs are the authors' best effort.** ChronoBERT and ChronoGPT are trained only on text dated before each cutoff, but their authors warn that a misdated document, for example one digitized by OCR, can let later text in. That's one more reason for our own cutoff check (section 5.2).

**Models from before 1999 exist, but none can read news by year.** NoLBERT is one 109M-parameter encoder trained only on 1976 to 1995 text. StoriesLM has yearly BERT models from 1900 to 1963. Models trained on older text stop in 1946 or earlier. None is a yearly ladder that can read 1980s or 1990s financial news, so 1999 stays the earliest start for reading news with vintages.

### How you use them matters more than which one you pick

Both results below use a similar setup: Dow Jones Newswire from 2008 to mid-2023, next-day returns, equal-weighted long-short portfolios rebalanced daily, and no trading costs. The portfolios differ in detail: decile sorts for the first, three-way labels for the second.

- **Read, then learn: Sharpe 4.80.** ChronoBERT turned each story into an embedding, and a ridge regression refit every month on past data turned embeddings into predictions. Each year's news was read by the previous year's model. Llama 3.1 8B, which has seen the future, scored 4.90. The difference isn't statistically significant (p = 0.315).
- **Ask for an opinion: Sharpe 0.95.** ChronoGPT-Instruct was asked directly whether each headline was good or bad. Llama 3.2 3B scored 1.76 the same way.

So the AI **reads with the time-locked model and decides with a learner trained on lived outcomes.**

### Keep expectations realistic

- **The published Sharpe ratios won't carry over.** They're equal-weighted across every stock with news, use exact timestamps, and come before costs. News takes longer to reach prices in smaller, more volatile firms (Ke, Kelly, Xiu). Across 50 large stocks after costs, the signal will be much weaker.
- **Costs.** Replacing both sides of the book every day trades 200% of capital. At 5 bps a side, that's about 25% a year. The holding period and turnover will decide the result after costs.
- **FINSABER.** Tested over 20 years and 100+ stocks, the advantages reported for LLM strategies fade badly. The LLMs were too cautious in bull markets and too aggressive in bear markets.
- **StockBench.** Most LLM agents don't beat buy-and-hold.
- **Alpha Arena season 1.** Real money, crypto: 4 of 6 frontier models lost money.

### Data: Alpaca

**News** comes from Benzinga through Alpaca's news API (`GET /v1beta1/news`):
- **History** goes back to 2015: 2,260,406 stories from 1 Jan 2015 to 29 Oct 2026. The docs say to expect about 130+ stories a day across the market. Benzinga alone ran about 300 to 700 a day.
- **Fields:** id, headline, summary, content (HTML, may be empty), author, created_at, updated_at, symbols, source, url.
- **Paging:** 50 stories per page. The date filter and the sort both use the update time (confirmed on the full download).
- **Sources:** Benzinga only until 18 Oct 2026, with a blank `source` label until 4 Jan 2022. Since then fiscal.ai adds press releases and analyst-rating notes.
- **Symbols** are the tickers in use when a story was published (PCLN, FB), and class shares are spelled several ways (section 9.3).
- **Live stream:** a WebSocket (`wss://stream.data.alpaca.markets/v1beta1/news`) sends the same fields.
- **Updates:** stories can change after publishing, and the API returns the latest version.
- **Checked on 30 Oct 2026** (section 9.3):
  - Stories go back to 1 Jan 2015.
  - Timestamps are true UTC.
  - `summary` is empty before recent years.
  - Content appears on 34% to 76% of stories, depending on the sample.

**Prices** come from `GET /v2/stocks/bars`:
- **History:** daily bars from 2016.
- **Raw by default.** `adjustment` can be split, dividend, spin-off or all.
- **Renames:** `asof` follows them (FB became META on 2022-06-09). `asof=-` turns the mapping off.
- **Histories follow a symbol, not a company or a share class.** A history fetched with `asof` can splice in another security that used the same symbol before or after: the FOXA file is 21st Century Fox until 2019-03-18 and Fox Corporation after, and Under Armour's UA file is class A until 2016-12-06 and class C after, because the classes swapped tickers. The DWDP file is Dow Chemical before 2017-09-01. So a company's member days come only from inside the dates the identity table gives each ticker, and anything that reads a file outside those dates, like the stock picker's year of trading before a company joins, keeps only the company's own bars (section 9.3).
- **The daily open is the day's first trade**, on any exchange. On a chaotic day that can be far from the listing exchange's opening auction, where a market-on-open order fills: on 2023-01-24 the NYSE opened LLY, MA, XOM and 12 others late, 8% to 24% away from Alpaca's open. It misses on ordinary days too, by less (23 of 300 random stock-days), so M1 fetches the official opens. The daily close matches the official closing auction, with a few exceptions (section 9.3).
- **Spin-off adjustments are unreliable.** Of the 73 distributions where Alpaca's adjusted and raw moves differ by more than 4%, its adjusted return on the ex-date is off by more than 1 percentage point at 31 (by up to 88 points), and 17 more distributions on member days aren't adjusted at all (16 spin-offs and warrant dividends, and Under Armour's class C dividend), such as Corteva's 2026 Vylor spin-off, left as an 84% loss (section 9.3).
- **Delisted symbols stay in the database.** Confirmed: Celgene, Monsanto and Time Warner all return 2016 bars with `asof` set inside 2016.
- **Bar timestamps:** a daily bar is stamped at midnight New York time (the start of the day), not when its close is known. Confirmed: `2016-01-04T05:00:00Z`.

**The free (Basic) plan:**
- history from 2016
- 200 calls a minute
- the latest 15 minutes of data held back
- real-time quotes from IEX only
- 30 symbols on a WebSocket

News is included on the free plan (confirmed 30 Oct 2026). The paid plan is $99 a month and isn't needed.

**Other data:**
- **Dividends and splits:** the corporate-actions API only goes back to April 2020, so for 2016 to 2020 they're worked out by comparing raw and adjusted bars.
- **Known quirks** from Alpaca's forum: some tickers have blended histories (`Q`, ADEA/XPER), and some adjustments have been missing.
- **S&P 500 membership** comes from `fja05680/sp500` (MIT license). Since 2019 it's compiled from Wikipedia, so check that it covers up to 2026.
- **Later versions:**
  - SEC EDGAR acceptance timestamps (a filing accepted after 5:30 pm ET counts as filed the next business day)
  - ALFRED macro data as of day T: each decision sees the latest vintage published by that day (the FRED API's `vintage_dates`), which can already be a revision. Never today's revised series, and not the first release either

### Compute

- **Kaggle:** about 30 free GPU hours a week on a T4 or P100. This is from third-party reports; Kaggle's own docs weren't checked.
- **Modal:** $30 a month in free credit. A T4 is about $0.59 an hour.
- **Your laptop:** an i5-1035G1 with 4 cores, 7.8 GB RAM and no NVIDIA GPU. It's fine for everything except running an LLM trader. Reading the news takes it about 21 hours (section 9.3).
  - **Disk:** C: is tight (about 8.7 GB free on 30 Oct 2026). Everything big lives on D::
    - the data
    - the model cache
    - pip's cache and temp files
    - the Python environment (the repo's `.venv` is a link to `D:\venvs\chrono-trader`)
- **ChronoBERT:**
  - It's ModernBERT-base: 22 layers, a 768-number hidden size, and float32 weights of about 600 MB per vintage.
  - On a CPU, load it with `attn_implementation="sdpa"` or `"eager"`. A forum report hit a bug with sdpa, so pin the transformers version and test both.
  - **Benchmark (30 Oct 2026, transformers 5.22):** both modes work. This CPU reads 6 to 7 headlines a second, and headlines are a median of 21 tokens.
  - A T4 can't run FlashAttention 2.
- **GitHub Actions** runs the daily forward-test job. Scheduled runs can start late when GitHub is busy, so the job is scheduled early and skips any day it can't finish before the open.

### Statistics

- **Sharpe.** With daily data, the standard error of an annual Sharpe ratio is about 1/√T, where T is in years. Lo's formula with daily observations makes the SR²/2 term negligible. The sealed period is about 7 years, so a strategy needs a Sharpe above about **0.75** before it can be told apart from luck.
- **Daily rank IC** is a far more powerful test. With 50 stocks, one day's IC has noise of about 0.15. Over 7 years the average has a standard error of about 0.004 (estimate). IC is the primary skill metric.
- **The deflated Sharpe ratio** (Bailey and López de Prado) corrects for picking the best of many versions, which happens in the dev years. The sealed run is a single pre-registered test, and Holm's correction covers the several pre-registered hypotheses.
- **The probability of backtest overfitting** (Bailey, Borwein, López de Prado, Zhu) estimates how likely it is that the chosen dev version is a fluke.

## 4. How the plan changed

| | Version 0 (first idea) | Now | Why |
|---|---|---|---|
| Stocks | About 20 big US stocks, picked by hand | The 50 most-traded S&P 500 members over the previous year, re-picked each January inside the agent loop using only data available then | Picking by hand means picking winners we already know about, and a list made outside the loop escapes the leak tests |
| Data | FNSPID | Alpaca | FNSPID leaks and has holes (`REVIEW.md`, C1 to C4) |
| Test | One replay of 2012 to 2023 | Dev 2017 to 2019, sealed 2020 to the seal date, then a forward test on the same source | Our own hindsight is a leak too |
| No leakage | Careful code | `available_at` on every record, a non-interference test, planted leaks, timestamp anchors and a survivorship audit | Proof beats care, and each test's blind spots are named |
| Labels | Learn from returns | Learn only from outcomes realized by decision time (day k−2 at 9:00 on day k) | Training on an outcome before it's known is the most common hidden leak |
| Proof of learning | Equity curve against buy-and-hold | A pre-registered paired test against a frozen twin, plus a placebo and a price-only twin | A rising IC can come from more news coverage or a calmer market |
| Statistics | Hit rate by year | Rank IC as the primary metric, Sharpe after costs, deflated Sharpe on dev, pre-registered tests on sealed | Honest significance |
| Execution | Not specified | Decide at 9:00 ET, trade at the open, charge costs, and treat the holding period as a dev variable | Costs will likely decide the result |
| Scope | One agent | Track A (a learner, the MVP), then Track B (a time-locked LLM trader with a journal), both on the same harness | Track B is the new part, and Track A proves the harness first |

## 5. Design

### 5.1 The time wall

Each record is stored as `id, source, entity_id, symbol, about_time, available_at, payload`:
- `entity_id` is a permanent company ID, never a ticker.
- `about_time` is the date the record refers to.
- `available_at` is when it became public.

The agent only ever calls `world.view(t)`, which returns records with `available_at <= t`. Agent code can't import anything else.

**The environment stands alone.** `world`, `sim` and `eval` import nothing from `agent`. An agent plugs in through one call: given the view at time t, return target positions. Track A, Track B and later experiments share it, and the harness and its leak tests could be released one day without the licensed data.

The availability rules are conservative on purpose:

| Record | `available_at` |
|---|---|
| News story | Its `updated_at` plus 15 minutes. The text we get is the latest version, and the free plan delivers news about 15 minutes late, so the backtest sees exactly what the live job will see. Stories edited more than 3 days after publishing are dropped, because their timing no longer means anything (0.2% of 2015's stories, and at most 0.5% in any year) |
| Daily close, high, low and volume for day d | 16:00 ET on day d. The vendor's bar timestamp (midnight) is never used for timing |
| Opening price for day d | 9:30 ET on day d. Only the simulator uses it |
| Return label for day d | The open on day d+1. Dividends and splits inside the window are part of the label |
| S&P 500 membership change | Its effective date |
| SEC filing (later versions) | Acceptance time, or 6:00 am the next business day if accepted after 5:30 pm ET. This rule is uncertain but conservative |
| Macro value (later versions) | 9:00 ET on the trading day after its `realtime_start` |

More rules:

- **Daily clock.** Decide at 9:00 ET, fill at the open, and use the open-to-open total return as the label.
- **New York dates everywhere.** Downloads and the daily job work out dates in New York time. Pakistan runs 9 to 10 hours ahead, and the free plan refuses any request reaching into a session still in progress. The first price download failed for exactly this reason.
- **Newest usable label.** At 9:00 on day k, the newest outcome the AI can learn from is day k−2's. Day k−1's open-to-open return isn't complete until day k's open, which comes after the decision.
- **Returns only.** Total returns come from day-over-day ratios of adjusted bars, which are safe. Dollar volume comes from raw bars. Adjusted price levels are never used, because back-adjusted prices already include future dividends and splits.
- **Fit on lived days only.** Everything that gets fitted (scalers, the ridge penalty, which embedding pooling to use) is fitted only on days already lived.
- **The stock list is picked inside the loop**, each January, from `world.view`. In 2016 it's picked on the first trading day of April from January to March data, because Alpaca's prices start in 2016.
- **Identity.**
  - A hand-checked table covers every company that ever enters the list (about 100). It maps its tickers over time to a permanent ID (SEC CIK).
  - Alpaca's `asof` is set inside each period the company was a member.
  - Renames and reused tickers (FB to META, the old and new DELL) are listed explicitly.
  - The price audit found what the table must fix (section 9.3):
    - 50 ticker pairs that are one company
    - one reused ticker (SNDK)
    - 11 spells the membership file labels with a later ticker (AABA was YHOO, APTV was DLPH, KDP was DPS, and others)
  - The news audit adds what the news needs (section 9.3):
    - Stories carry the ticker in use when they were published, so news symbols map to entities by date. Booking is PCLN until early 2018, Facebook is FB until June 2022, and from 30 Jun 2021 to June 2022 META meant Roundhill's Metaverse ETF.
    - Class shares are spelled several ways (BRK.B, BRK-B, BRK/B and plain BRK, and Brown-Forman the same), and all of them map to one entity.
- **One share class per company.** When two classes of one company qualify (GOOG and GOOGL), keep the more liquid one.
- **Exits.** A company that's acquired or delisted leaves at its last available price.
- **Raw data stays out of git,** because of both size and license. Only code, configs, decisions and metrics are committed.

Every change runs the test suites in section 9.11. The three core ones:

1. **Non-interference test.** Run up to day t. Scramble or delete every record with `available_at > t`, then run again. Every decision up to t must be identical. This is the hands-on version of what Fonseca formalizes as temporal non-interference.
2. **Planted leaks.** Deliberately plant each of these. The tests must fail every time.
   - a future return
   - a future headline
   - a scaler fitted on all the data
   - a stock list made with future data
   - a vendor's bar timestamp used as the time a close is known
3. **Label embargo.** No training row's label was realized after the decision it's used for.

What the non-interference test can't see, and what covers each gap:

| Blind spot | Covered by |
|---|---|
| Wrong timestamps in the source | The timestamp anchor test |
| Survivorship in the source | The survivorship audit |
| Embeddings made by the wrong vintage | The vintage test |
| Our own hindsight | The seal and the forward test |

### 5.2 The reader (one batch job)

- **Input: the headline only.** Inputs that change over time are what broke FNSPID, and the audit found that only the headline is steady:
  - `summary` is empty on every 2015 to 2020 story sampled, but filled on most recent ones.
  - Article content appears on 34% to 76% of stories depending on the sample.
  - Its typical length grows from about 2,000 characters in 2015 to 6,400 in 2026.

  Content is an exploratory dev variant at most.
- **Source.** Benzinga stories only, meaning a blank or `benzinga` label (section 9.3).
- **Single-firm filter.** Use only stories about at most 2 companies, as the ChronoBERT paper did (following Ke et al.). Companies are counted after the identity table maps tickers to entities, so GOOG and GOOGL count once, and so do Berkshire's four spellings. Counted by company, 963 of Berkshire's 2,210 stories pass; counted by ticker, only 684. Benzinga's lists of a session's movers are price recaps, not company news, and one sampled story carried 89 symbols. Market-wide, 80% to 88% of stories pass each year, but the share for a single stock shifts: 64% of Apple's January 2015 stories against 37% of Microsoft's September 2026 stories. That's why story counts are compared across stocks on the same day, never across years.
- **Vintage.** News first available in year Y is read by the year Y−1 model, so 2016 news goes to `chrono-bert-v1-20151231`. News from 2025 and 2026 is read by the 2024 model, the latest, so its vocabulary will age.
- **Output:** two 768-number embeddings per story (last layer, and the average of all layers), stored as float16 Parquet.
- **Cutoff check.**
  - For each vintage V, measure its masked-word loss on headlines from years V−1 to V+2. It should jump after V. Compare against vintage V+1 on the same headlines.
  - Probe named events, such as "Brexit" for vintages before 2016 and "COVID" for vintages before 2020.
  - Flag any vintage that knows too much.
- **Masking diagnostic.** Rerun the reader with company names and dates masked. With time-locked vintages, a change shows that the signal leans on what the model knew about a company before its cutoff, which is allowed. So this is a diagnostic, not a leak test. The leak guarantees stay the vintage rule, the cutoff check and the non-interference tests.
- **Known limits.**
  - The tokenizer is ModernBERT's 2024 vocabulary, a tiny theoretical leak channel.
  - ChronoBERT's design was chosen in 2025, knowing what worked on 2008 to 2023 news.
  - Both are reasons the forward test matters.

### 5.3 Track A: the learner (the MVP)

- **Features per stock per day:**
  - the average embedding of new stories, and how many there were
  - a slowly fading memory of older stories
  - returns over 1, 5, 20 and 60 days
  - volatility, and change in trading volume
- **Left out on purpose:** market-wide and macro features. The model ranks stocks against each other, and a number that's the same for every stock can't change a ranking.
- **Model.** A ridge regression refit every month on all lived days, as in the ChronoBERT paper. This is the batch learner, and it's the live agent. Variants to try in dev:
  - averaged monthly coefficients
  - more weight on recent data
  - online models from River. These are sequential learners, compared with the batch learner on identical data in the dev years. `PREREG.md` decides whether that comparison becomes a sealed hypothesis.

  The ridge is kept as running sums (X'X and X'y), so memory stays small and the learner can only ever add lived days.
- **Trading:** rank stocks by predicted return.
  - The main test goes long the top 10 and short the bottom 10 of the 50.
  - An easier-to-follow version holds the top 10, long-only.
  - The holding period (1, 3 or 5 days) and a turnover band are dev variables.
  - Costs are 5 bps per side, with a sensitivity check at 0, 5, 10 and 20 bps. Results are always shown before and after costs.
- **Exposure.** Report the long-short book's market beta and sector tilt. A sector-neutral ranking is a dev variant.
- **Comparison runs:**
  - **Matched baselines.** Compare long-short against cash and against long-short momentum, reversal and random rankings. Compare long-only against SPY and against holding all 50 equally.
  - **Frozen twins.** At the end of each year, snapshot the agent and keep running the snapshot without letting it learn. The twin frozen at the end of the dev years is the pre-registered one.
  - **Shuffled-news placebo.** The same agent with news swapped between stocks within each day.
  - **Price-only twin.** The same agent with no news.

### 5.4 Track B: the time-locked LLM trader (after Track A)

- ChronoGPT-Instruct (yearly vintages, confirmed) reads each stock's stories, writes a short thesis, and trades through the same harness. DatedGPT can replace it if its weights turn out to be available, and so can a PIT model (weights under `Diamegs`).
- After each outcome it writes a reflection into its own journal, and it looks up past entries before deciding. TradingAgents keeps a similar memory, but here the model can't know the future.
- **Memory as numbers.** The journal keeps its beliefs as structured statistics, such as each signal's recent hit rate, alongside any text.
- **Memory ablation.** It runs with no memory, a short memory and a long memory. In one small study (Heil, Pramov and Gong, a CLEF 2026 workshop paper), giving a portfolio manager a 5-day or 10-day memory of its recent decisions and hit rate made results worse.
- **Stretch goal:** fine-tune it now and then with LoRA on its own lived outcomes, so the learning reaches the weights.
- **Compute.** Days have to run in order; stocks within a day can run in parallel. ChronoGPT's custom architecture may need its own inference code, which is slower than standard model servers. Expect hours per run on one cloud GPU. It isn't practical on the laptop.
- It's compared with Track A's batch learner on the same days. The evidence in section 3 suggests this track will probably trail Track A. That comparison is a finding in itself.

### 5.5 Evaluation protocol

1. **Warm-up: 2016.** Watch-only. The stock list is picked in April 2016.
2. **Dev years: 2017 to 2019.** Tune freely. Every run is logged with a hash of its settings in `runs/trials.csv`.
3. **Pre-registration.** Before sealing, write `PREREG.md` with the hypotheses, metrics, tests and decision rules below.
4. **Seal.** `seal.lock` records the settings hash, the `PREREG.md` hash and the git commit.
5. **Sealed years: 2020-01-01 to the last trading day before the seal.** Run once, and report as-is, good or bad.
6. **Forward test.**
   - From the next trading day, a GitHub Actions job runs the same code on the same Alpaca source every morning.
   - It commits the day's decisions before the open. GitHub's server-side run times are the proof; OpenTimestamps is optional.
   - Results are scored daily. This is the only test that's free of our own hindsight.

The seal locks the feature list. Anything added afterwards can only be judged by the forward test.

Draft pre-registered hypotheses (finalized in `PREREG.md`), all measured over the sealed years:

| | Hypothesis | Test |
|---|---|---|
| H1 (skill) | The live agent's mean daily rank IC is above 0 | One-sided, Newey-West standard errors |
| H2 (learning) | The live agent's daily IC beats the twin frozen at the end of 2019 | Paired, one-sided, Newey-West |
| H3 (reading) | The live agent's IC beats both the price-only twin and the shuffled-news placebo | Paired, one-sided, Newey-West |

Holm's correction is applied across H1 to H3. Sharpe after costs, drawdowns, turnover and exposures are reported but not tested. So are results by market regime and after big shocks, and how long learned coefficients keep working.

Every random part (the shuffled-news placebo and the random-ranking baseline) runs with several seeds, and the report shows the spread.

The MVP succeeds if:
- every leak test passes, and every planted leak is caught
- H2 holds (it learned)
- H3 holds (reading helped)

A clean "it didn't learn" is also a valid result, reported as-is.

## 6. Cost

- **Laptop:** the harness, Track A and the reports. Free.
- **Alpaca Basic:** free, with news included (confirmed).
- **Reader job:** about 21 hours on the laptop for 500,745 headlines (free), or a much shorter run on Kaggle's free hours or Modal's $30 credit. M2 picks one.
- **Forward test:** GitHub Actions, within the free minutes.
- **Track B:** a few dollars a run on Modal. Rough estimate.

## 7. Risks and open questions

- **Free-plan terms can change.** Access was confirmed on 30 Oct 2026. Keep a local copy of everything downloaded. GDELT (free, 15-minute updates since 2015) stays the fallback, but stories would have to be matched to companies by name.
- **The feed changes.** Benzinga's source label went from blank to `benzinga` in January 2022, and fiscal.ai joined in October 2026. The pipeline filters by source. The forward test should also compare each day's Benzinga story count with recent history, so the next change raises an alarm instead of quietly shifting the features. (News volume in 2016, once a worry, is fine: section 9.3.)
- **Alpaca data quirks** (blended tickers, missing adjustments) are covered by the audits in section 9.3.
- **Short history.** It's about 10 years (from 2016): 3 dev years and about 7 sealed.
- **The S&P 500 membership list** is compiled from Wikipedia and may have gaps.
- **Licensing.** Benzinga news and market data can't be redistributed. Raw data never goes into git or any public repo.
- **Weak reasoning in Track B.** Small time-locked LLMs reason poorly. In AlpacaEval, ChronoGPT-Instruct's responses won 13 to 17% of head-to-head comparisons against a 1.8B chat model.
- **Unconfirmed weights.** DatedGPT's public weights are unconfirmed. The PIT models' weights are under `Diamegs`, the account their paper names.
- **Hindsight.** We both know how 2020 to 2026 went, and the reader's designers did too. The seal limits this. Only the forward test removes it.
- **Late GitHub runs.** Scheduled runs can start late. A day the job can't finish before the open is logged as missed, never back-filled.
- **ChronoBERT on CPU** depends on the sdpa or eager attention path working in the pinned transformers version.

## 8. Build order

1. **Done (30 Oct 2026):** Alpaca paper account, keys in `.env`, and access checked.
2. **Done (31 Oct 2026): M0, data audit** (section 9.3). Prices and news are downloaded and audited, the identity table is built and checked, price corrections are recorded, the split is confirmed with counts, and the laptop benchmark is done.
3. **M1:** the time wall and all the test suites, and the listing exchange's official opening auction print for every stock-day the simulator trades (section 9.3).
4. **M2:** the reader job and the cutoff check.
5. **M3:** Track A on the dev years, with the twins, the placebo and the baselines.
6. **M4:** write `PREREG.md`, seal, run the sealed years once, and write the report.
7. **M5:** start the forward test.
8. **Track B.**
9. **Later: a long replay from 1999.** One market, for example the S&P 500 index or EUR/USD, with prices, FOMC statements and as-of economic data, on the same environment. It's deferred, not a replacement for Track A: Track A's 2015 to 2026 data is audited and ready, ranking 50 stocks every day gives far more statistical power than trading one market, and Track A reads real company news through time-locked models. A rebuilt past web (Agentic Time Machine, Bench to the Future) can't feed it news, because neither covers 1999 to 2015 (`research/brief_check.md`).

## 9. Track A build spec

### 9.1 Where things live

- **Code:** `C:\Users\syedh\dev\chrono-trader`, a git repo, pushed to the private GitHub repo `syedhamza2135/chrono-trader`.
- **Data:** `D:\chrono-data`.
- **API keys:** environment variables, or a `.env` file listed in `.gitignore`.
- **Python:** 3.13 in a virtual environment, with these libraries:
  - `alpaca-py` (Alpaca's official SDK) or plain HTTP
  - pyarrow and Parquet for storage, and DuckDB for local queries
  - numpy, and scikit-learn for checks against the hand-rolled ridge
  - `exchange_calendars` for NYSE trading days, holidays and early closes
  - pytest and hypothesis for property-based leak tests
  - transformers and torch for the reader (on the laptop, or a cloud GPU if M2 picks one)

```
chrono-trader/
  PLAN.md  REVIEW.md  PREREG.md (before the seal)
  config/          one YAML per run, hashed into the trial ledger
  data_pipeline/   Alpaca download, audit, identity table, event store (allowed to see everything)
  reference/       hand-checked tables: identity, memberships, price corrections, split.json
  world/           the time wall: Clock, World.view(t), availability rules
  agent/           stock picking, features, learner, policy (allowed to see World.view only)
  sim/             fills, costs, portfolio accounting
  eval/            metrics, twins, placebo, pre-registered tests, reports
  reader/          the embedding job (on the laptop, or as a cloud notebook)
  research/        probes and notes (FNSPID probes live here)
  tests/
  runs/            one folder per run, plus trials.csv
  seal.lock        created at the seal
```

The `agent` package may import only `world.view`, and a test enforces this. The other way round, `world`, `sim` and `eval` import nothing from `agent`, and every agent plugs in through the one call in section 5.1. A test enforces that too.

### 9.2 Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Data audit | `audit.md` answers every question in 9.3, the identity table is checked, and the dev/sealed split is confirmed using counts only |
| M1 | Time wall and official opens | Every test in 9.11 passes, every planted leak gets caught, and the simulator has the listing exchange's official opening auction print for every stock-day it trades |
| M2 | Reader | Every filtered story is embedded by the right vintage, and the cutoff check passes (or any failing vintage is replaced) |
| M3 | Track A on dev years | A dev report shows IC by quarter, frozen twins, placebo, price-only twin, matched baselines, holding-period variants, costs and exposures |
| M4 | Pre-register, seal, sealed run | `PREREG.md` is hashed into `seal.lock`, and the sealed report is published as-is |
| M5 | Forward test | The GitHub Actions job has committed decisions before the open on every trading day for a month, and they've been scored |

### 9.3 The data audit (M0)

**News:**
- Is news included on the free plan, and at what rate limit?
- How many stories are there per S&P 500 member per year, from 2015 to 2026? This decides whether 2016 works as the warm-up.
- What share of stories has a summary, and what share has content, by year? This decides the reader's input.
- How are symbols per story distributed? This sets the single-firm filter.
- **Timestamp anchors:** after conversion to New York time, do "Pre-Market Session" headlines land between 4:00 and 9:30, "Mid-Day" between 11:00 and 14:00, and "After-Hours" between 16:00 and 20:00?
- What's the gap between `created_at` and `updated_at`? This shows how often stories change, and how late.

**Prices:**
- **Survivorship:** for each January, does every S&P 500 member have Alpaca bars around that date? Check especially the companies that left later (Celgene, Monsanto, Time Warner and others).
- **Identity:** list every rename and reused ticker among companies that ever rank in the top 50.
- **Corporate actions:** compute daily ratios of raw to adjusted bars, and review every one-day move above 25% in a big stock.
- **Blended histories:** flag any pair of tickers with identical return series.
- **Membership:** check that the S&P 500 list is complete up to 2026.

**Early results (30 Oct 2026).** These come from `research/alpaca_check.py` and `research/alpaca_news_probe.py`, run on samples: Apple (Jan 2015, Jan 2016, Jun 2018), JPMorgan (Jun 2016, Mar 2020) and Microsoft (Sep 2026).

| Question | Answer so far |
|---|---|
| News on the free plan | Yes, at 200 requests a minute |
| History | Stories from 1 Jan 2015 (Apple had 255 that month) |
| Timestamps | True UTC. All 8 "Pre-Market", "Mid-Day" and "After-Hours" headlines landed inside their New York windows |
| Summary | Empty on every 2015 to 2020 story sampled. Present on 186 of 306 stories in Sep 2026 |
| Content | 34% to 76% of stories, depending on the sample. Median length about 2,000 characters in 2015 and 6,400 in 2026 |
| Edits | Most happen within minutes. 2.4% of Apple's Jan 2015 stories were edited more than a day later (up to 14 days); none were in the later samples |
| Symbols per story | Stories with at most 2 symbols: 64% (Apple, Jan 2015) down to 37% (Microsoft, Sep 2026). One story carried 89 symbols |
| Delisted prices | Celgene, Monsanto and Time Warner all have 2016 bars with `asof` |
| Bar timestamps | Midnight New York time (`2016-01-04T05:00:00Z`) |
| Date filter | One query returned stories created weeks before its window. The full download showed why: Alpaca filters by update time. Timing always comes from each story's own fields |

**Price audit (31 Oct 2026; rerun on 5 Nov after the M0 review, `research/audit/m0_review.md`).** Run with `python -m data_pipeline.audit_prices`, on the bars `python -m data_pipeline.bars` fetches from the identity table. The full report is in `research/audit/prices.md`.

| Question | Answer |
|---|---|
| Downloads | 787 plan rows for 719 companies, each ticker fetched as of a date inside its own row: 1,574 files (raw and adjusted), 179 MB, covering 1,360,471 company member days to 2026-10-28 (a company listed with two classes counts once a day) |
| Membership coverage | The membership history runs to today: fja05680 to 18 Aug 2026, then Wikipedia's change log. It ends with the 503 members on Wikipedia's list |
| Survivorship | Every member company has bars on every picking date, 2016 to 2026. 64 member sessions have no bar, all after a company's last trade: 58 where an acquisition closes a few days before the index removal takes effect, and 6 where a failed bank's shares stop trading (SVB Financial from 2023-03-10, First Republic from 2023-05-01). The first run's gaps (10 names in 2016) were labelling problems, and the 2 sessions once put before Amcor's first trade were Bemis's |
| Identity | No two companies share 20 or more identical member-day bars. Alpaca's own histories splice securities that used one symbol (FOXA, UA, ARNC, DLPH), so a ticker's member days are only those inside its row, and the pick ranking keeps only a company's own bars. Before the review, the ranking used Dow Chemical's bars in the DWDP file for DowDuPont's 2018 pick and left it out of the top 50; on its own bars it ranks 40th. XL is two securities to Alpaca, so it has two rows. A company changes rows 56 times while a member, and 11 of those days need a return stitched from the previous row. On 195 first member days, or returns after a gap, the file's previous bar can't be shown to be the company's own, so the return is left undefined |
| Large moves | 265 adjusted one-day moves above 25% on member days; 141 fail the print check (almost all on the open) and 43 are corrected in `reference/price_events.csv`. 14 reversed by more than 20% the next day. Of those, 3 match the official auction prints on both sides (PG&E in Nov 2018, Lincoln Financial and Noble Energy in Mar 2020), and `price_events.csv` corrects 6: Nordstrom's bar, Hilton's and Oneok's closes, and the opens of Hess, Ventas and Aptiv. The other 5 match the official close and miss the open by 0.4% to 1.6% (First Republic on three days in Mar 2023, Globe Life in Apr 2024, Moderna in Aug 2026). The first run's 134 and 8 missed current members, whose file names depended on the run date; 267 and 14 on the draft identity table became 265 and 14. The 10 large moves in picked stocks' own years all match the official close; 7 match the open too, and the other 3 miss it by 0.2% to 0.5% (Twitter in 2022, Oracle in 2025, Supermicro in 2026) |
| Official prints | Checked on 787 stock-days (436 dates): the large moves, screens for suspicious opens and closes, and 300 random stock-days. A bar's open or close matches when it is within a cent of the listing exchange's official auction print, or 0.2% of it when that is more. Alpaca's close matches on all 300 random days (the largest gap is 0.06%) and misses on 8 stock-days: 7 closing auctions and Nordstrom's rebuilt bar, all corrected. Its open is the day's first trade on any exchange, and it misses the opening auction on 259 stock-days (128 dates), with a median gap of 0.64%. That includes 23 of the 300 random days, and 15 stocks on 2023-01-24, the NYSE opening glitch, by up to 24%. 55 of the misses are corrected (54 opening prints and Nordstrom's bar), and M1's official opens cover the rest. 2 closes had no print to judge. The first check, on 784 stock-days at a 2% tolerance, called 198 of these open misses matches |
| Adjustment events | 150 member days where the adjusted and raw moves differ by more than 4%: 77 splits and 73 distributions (spin-offs, special dividends, a warrant dividend). All 73 are checked against the true total return on the ex-date: 31 are off by more than 1 percentage point (1.1 to 88 points) and 42 are within 1 point. Distributions that Alpaca doesn't adjust at all never show here: 17 were found on member days, 16 spin-offs and warrant dividends (Yum China, nVent and Vylor among them) and Under Armour's class C dividend, all more than 1 point off and corrected |
| Incomplete bars | 1,035 member bars hold only part of the day's trades (a trade count below 5% of the median of the file's previous 20 bars): 1 on 2018-03-26, 356 on 2021-04-19, 326 on 2021-10-25 and 352 on 2022-03-08. 83 of them are in that year's picks. Their volume, high, low and VWAP aren't the day's, and their open may not be either, so the features must treat them as missing. The list is `research/audit/incomplete_bars.csv` |
| Trading days | Apple's bars match the NYSE calendar exactly, to 2026-10-28 |
| Picking preview | 5 to 9 of the 50 names change each year, with one share class per company. Each company is ranked on its own bars, without incomplete bars. Picks that later left the index (Allergan, Celgene, Twitter, American Airlines) all have bars |
| Laptop reading speed | 6 to 7 headlines a second with ChronoBERT on the CPU |

**Identity audit (31 Oct 2026; rebuilt on 4 Nov after the M0 review).** Run with `python -m data_pipeline.identity`, checked by `python -m pytest tests` (131 tests). The full report is in `research/audit/identity.md`.

| Question | Answer |
|---|---|
| Companies | 746 companies since 2015, keyed by SEC CIK, with 814 ticker rows dated exactly or by a membership day. Seven list two share classes at once (Alphabet, Comcast, Discovery, both Foxes, News Corp, Under Armour) |
| The membership file | Labels about 25 early periods with later tickers (Yahoo as AABA), joins companies that shared a ticker (CB, IR, JCI, AGN, FOX and FOXA, FTI), leaves out ACE, Tyco and Actavis, lists Michael Kors and Coca-Cola Enterprises twice, has three dates wrong (Trane, Cimarex, Four Corners), gives Bemis's two member days (2019-06-07 and 2019-06-10) to Amcor, and leaves out 21st Century Fox's last member day (2019-03-19, as TFCFA and TFCF) and MasterBrand's two (2022-12-15 and 2022-12-16). All fixed in `reference/identity_fixes.csv`: 97 rows, each with its evidence |
| Wikipedia | Its CIK column lags events by months or years (Fox by 18 months, Medtronic by 4 years). Our parser had dropped Tractor Supply from three 2015 revisions, and now reads it |
| News tags | Map to companies by date: PCLN is Booking until 2018-02-26, META in 2021 is nobody (Roundhill's ETF), and BRK/B and plain BRK are Berkshire. A class tag on a plain ticker's root (LEN.B, CBS.A, STZ.B) maps to that company, for the US class tags in the news only |
| Open items | None |

**Price corrections (31 Oct 2026; updated on 5 Nov after the M0 review).** `reference/price_events.csv` holds 122 rows, each with its evidence: 54 opening auctions that Alpaca's bars miss (from the first print check; M1's official opens cover the rest); 7 closing auctions; Nordstrom on 2018-03-26, rebuilt from clean trades; 55 distributions with their true total return; Biogen's two halts; and three failed banks whose shares stopped trading while they were still members (SVB Financial, First Republic and Signature Bank). The distributions are the 31 in `research/audit/adjustment_events.csv` where Alpaca's adjusted return is more than 1 percentage point off (named in `research/audit/audit.md`), GE's real ex-date for its 2019 Wabtec distribution (Alpaca applies it a day early), Under Armour's unadjusted class C dividend, four at a change of ticker, 16 spin-offs and warrant dividends that Alpaca never applies, Aimco's 2019 special dividend (only its reverse split is applied), and Occidental's dividend on 2020-03-09. The other 42 distributions in that table are within 1 point.

**News audit (30 Oct 2026; coverage and reading load recounted by company on 31 Oct; rerun on 5 Nov with New York years, and picked stories counted from each year's pick date).** Run with `python -m data_pipeline.audit_news`. The full report is in `research/audit/news.md`.

| Question | Answer |
|---|---|
| Download | All 142 months from Jan 2015 to Oct 2026: 2,260,406 unique stories, 251 MB of Parquet, about 4.5 hours |
| Date filter | Alpaca filters by update time. Every story's `updated_at` falls inside the month whose query returned it, and 0.09% were created in an earlier month. Each story is stored once, under the month of its latest edit |
| Sources | Benzinga only until 18 Oct 2026. Its `source` label is blank until 4 Jan 2022, and every blank-label story links to benzinga.com. Then fiscal.ai arrived with press releases and analyst-rating notes, and made up 59% of stories from 19 to 29 Oct |
| Volume | Benzinga stories a year: 138,536 in 2015, a low of 107,848 in 2017, a high of 261,738 in 2024, and 208,827 in 2026 up to 29 Oct |
| Symbols | Each year, 80% to 88% of stories carry 1 or 2 symbols, and 2% to 10% carry none |
| Edits | Edited more than 3 days after publishing: 0.2% of 2015's stories, and at most 0.5% in any year (2021) |
| Timestamps | 12,231 session recaps (Benzinga's lists of a session's movers, with the day and the session named in the headline) were checked against their stamps, and 5 are stamped before their session. Four of those fall inside the right session on the day they were stamped but name the next weekday, so they're typos. One, a mid-day list stamped 08:03 on 13 Jul 2018 (story 12016835), is unexplained. Late stamps only delay a story: 247 pre-market lists, all but one from 2024 and 2025, were stamped between 16:04 and 16:10 |
| Coverage | Counted from each year's pick date, the median picked stock has 121 to 319 single-firm stories a year, with news on 71 to 151 days. In 2016, from the 2016-04-01 pick, it's 125 stories on 71 days (the fewest, 31, for Berkshire), so 2016 works as the warm-up. The thinnest pick in any year has 28 (Schlumberger in 2017); counted by company, BKNG is no longer thin |
| Tickers in the news | Stories carry the tickers in use when they were published. Booking is PCLN until early 2018. Facebook is FB until June 2022. From 30 Jun 2021 to June 2022, META meant Roundhill's Metaverse ETF |
| Class shares | Berkshire is tagged BRK.B, BRK-B, BRK/B or plain BRK, and Brown-Forman the same way. Counted by company, 963 of Berkshire's 2,210 stories pass the single-firm filter; counted by ticker, 684 |
| Reading load | Single-firm stories about companies that are S&P 500 members on the story's date, 2016 to 2026: 500,745 headlines, about 21 hours on the laptop and 1.5 GB of embeddings. For the year's 50 picked companies only, from each pick date: 168,803, about 7 hours |

**The split (31 Oct 2026; rerun on 5 Nov).** `reference/split.json`, from counts only: the warm-up has 252 sessions, the dev years 754 and the sealed years 1,715 so far, with 79,000 single-firm stories about members in the dev years and 387,796 in the sealed years. Stories are counted by New York date up to each period's last session, so the sealed years stop at 2026-10-28.

Outputs: `research/audit/audit.md` (the answers above, question by question), `reference/identity.csv` (with `entities.csv`, `memberships.csv` and `identity_fixes.csv`), `reference/price_events.csv` and `reference/split.json`.

### 9.4 The event store (Parquet)

- `bars_raw` and `bars_adj`: entity_id, symbol, date, open, high, low, close, volume, trade count, vwap.
- `stories`: story_id, symbols, created_at, updated_at, available_at, headline, summary, has_content, source, n_symbols.
- `story_entities`: story_id, entity_id (only stories passing the single-firm filter).
- `embeddings`: story_id, vintage_year, emb_last (768 float16), emb_avg (768 float16).
- `membership`: date, entity_id.
- `identity`: entity_id, symbol, valid_from, valid_to, cik.

All times are stored in UTC and converted to New York time, with daylight saving handled, when the rules are applied.

### 9.5 The daily loop (9:00 ET, trading day k)

1. `v = world.view(9:00 ET on day k)`.
2. On the first trading day of the year, pick the year's 50 stocks from `v`. (In 2016, do this on the first trading day of April.)
3. Build features for the 50 stocks from `v`.
4. On the first trading day of each month, refit the scaler and the ridge on every lived row whose label is known (day k−2 and earlier). Nothing is fitted until 6 months have been lived.
   - Choose the penalty and the embedding pooling by validating on the most recent 20% of lived days (at least 3 months), until 5 years have been lived. After that, use the last 12 months.
   - The training part always ends before the validation part starts, with the k−2 gap at the boundary.
5. Predict, rank, and set target positions, given the holding-period rule.
6. `sim` fills at day k's open and charges costs.
7. Log one row per stock: date, entity_id, prediction, position, config hash.

### 9.6 Features (per stock, per day)

| Feature | Definition |
|---|---|
| news_count | Filtered stories that became available since the last decision |
| news_new | Mean embedding of those stories (zeros and a flag if there were none) |
| news_memory | Exponentially weighted mean of past story embeddings, with a half-life of 5 trading days |
| r1, r5, r20, r60 | Log total returns up to the last close, from adjusted-bar ratios |
| vol20 | Standard deviation of daily returns over 20 days |
| dvol_ratio | Log of 5-day over 60-day average dollar volume, from raw bars |

Bars flagged incomplete (`prices.incomplete`) count as missing for every feature built from volume, range or VWAP.

**Target:** the log total return from day k's open to day k+1's open, minus that day's average across the 50 stocks.

### 9.7 The learner

- Scale features using means and variances from lived rows only.
- Use a ridge regression, refit monthly from running sums over an expanding window. As variants, try averaged monthly coefficients (as in the ChronoBERT paper) and recency weighting.
- Try penalties from 10⁻² to 10⁴, and validate as described in 9.5.
- Compute in float64. Sort everything into a fixed order and set `PYTHONHASHSEED=0`. Tests run with a single BLAS thread.
- **Batch against sequential.** The monthly ridge is the batch learner, and it's the live agent. Online models from River are sequential learners, run on identical data in the dev years. `PREREG.md` decides whether that comparison becomes a sealed hypothesis.

### 9.8 Portfolio and costs

- **Main version:** long the top 10 and short the bottom 10, equal-weighted and dollar-neutral, filled at the open.
- **Long-only version:** hold the top 10, compared against SPY and against holding all 50 equally.
- **Holding period:** 1, 3 or 5 days, plus an optional turnover band (keep a holding until it drops out of the top or bottom 15). These are dev variables, and each one counts as a trial.
- **Costs:** 5 bps per side on traded value (an assumption). The report shows results at 0, 5, 10 and 20 bps, before and after costs.
- **Exits:** a company that's delisted or acquired leaves at its last available price.

### 9.9 Comparison runs

Every run uses the same harness:
- the live agent (the batch learner)
- sequential learners (the online variants), on identical data in the dev years
- frozen twins, one per year end, with the end-of-2019 twin pre-registered
- a price-only twin
- a shuffled-news placebo, where embeddings are swapped between stocks within each day
- long-short baselines: random ranking, 12-1 momentum and 5-day reversal
- long-only baselines: SPY buy-and-hold and holding all 50 equally

### 9.10 Metrics and the report

- **Daily rank IC** (the Spearman correlation between prediction and outcome across the 50 stocks), by quarter, with Newey-West t-stats. This is the primary skill metric.
- **Frozen-twin gaps:** paired daily IC differences, by year after each snapshot.
- **The pre-registered tests H1 to H3,** with Holm's correction (sealed years only).
- **Long-short and long-only results:** return, volatility, Sharpe before and after costs, maximum drawdown, turnover, beta and sector tilt.
- **Deflated Sharpe** for the chosen dev version, using the number of trials in `runs/trials.csv`.
- **Seed spread:** the result for each seed of the placebo and the random ranking, and their spread.
- **Regimes and shocks:** results by market regime and after big shocks. Reported, not tested.
- **Coefficient life:** how long learned coefficients keep working. Reported, not tested.
- **Charts:** IC over time, frozen-twin gaps, equity curves against matched baselines, and cost sensitivity.

### 9.11 Tests

| Test | What it proves |
|---|---|
| Non-interference (property-based) | For random days t inside the dev years, scrambling, shifting or deleting every record available after t leaves every position up to t identical, and every prediction within 1e-12 |
| Planted leaks | Each of these makes a test fail: a future return, a future headline, a scaler fitted on all the data, a stock list made with future data, and a vendor's bar timestamp used as the close time |
| Label embargo | Every training row's label was realized before the decision that used it |
| Availability rules | Each source's rule holds, including `updated_at` plus the 15-minute news delay, early closes and daylight-saving changes |
| Timestamp anchors | Benzinga's "Pre-Market", "Mid-Day" and "After-Hours" headlines land in their known time windows after conversion |
| Vintage rule | Every story was read by a model from an earlier year |
| Survivorship audit | Every S&P 500 member on each January has bars, or is listed as a known gap |
| Identity | No two entities share a return series, and every symbol maps to exactly one entity on each date |
| Large moves | Every one-day move above 25% in a stock on the list has been reviewed |
| Import boundary | `agent` imports nothing except `world.view` |
| Reverse import boundary | `world`, `sim` and `eval` import nothing from `agent` |
| Trading days | Decision days equal the trading days in the price data, with no decisions on holidays |
| Seal | The runner refuses sealed dates without a matching `seal.lock` (settings, `PREREG.md` and commit) and a clean git tree |

### 9.12 The seal

- `seal.lock` records the settings hash, the `PREREG.md` hash and the git commit.
- The runner refuses any date in the sealed years unless all three match and the working tree is clean.
- There is one sealed run. A second needs an explicit flag and is logged as another trial.
- The feature list is part of the seal.

### 9.13 Rough sizes (estimates)

- **Price bars (measured):** 787 plan rows for 719 companies, 1,574 files (raw and adjusted), 179 MB on disk on 7 Nov. The first download took about 10 minutes.
- **News (measured):** 2,260,406 stories from Jan 2015 to Oct 2026 (2,243,739 of them Benzinga's), 251 MB of Parquet, about 4.5 hours to download.
- **The trading list:** 50 stocks × about 2,700 trading days ≈ 135,000 stock-days.
- **Embeddings:** 3 KB per story (two poolings in float16), so the reader's 500,745 headlines come to about 1.5 GB. They're processed one year at a time to stay inside 7.8 GB of RAM.
- **Vintages:** 2014 to 2024, which is 11 models at about 600 MB each, roughly 6.6 GB. They're downloaded wherever the reader runs.
- **Headlines** are short (a median of 21 tokens). At the measured 6 to 7 a second, the reader's 500,745 take about 21 hours on the laptop.
- **Ridge fits** are small, so a full Track A replay should take minutes on the laptop.

## Sources

Time-locked models
- He, Lv, Manela, Wu. Chronologically Consistent Large Language Models. https://arxiv.org/html/2502.21206v3
- ChronoBERT model card. https://huggingface.co/manelalab/chrono-bert-v1-20111231
- ChronoBERT config. https://huggingface.co/manelalab/chrono-bert-v1-20111231/raw/main/config.json
- ChronoGPT model card. https://huggingface.co/manelalab/chrono-gpt-v1-20111231
- ManelaLab model list (78 models). https://huggingface.co/api/models?author=manelalab&limit=200
- He, Lv, Manela, Wu. Instruction Tuning Chronologically Consistent Language Models. https://arxiv.org/html/2510.11677v1
- DatedGPT. https://arxiv.org/abs/2603.11838
- Kelly, Malamud, Schwab, Xu. Scaling Point-in-Time Language Models. https://arxiv.org/abs/2607.11889 and https://www.sfi.ch/en/publications/n-26-37-scaling-point-in-time-language-models
- PIT model weights (the `Diamegs` account, named in the paper; one checkpoint a year). https://huggingface.co/Diamegs
- Kakhbod, Li. NoLBERT. https://arxiv.org/abs/2509.01110 and https://huggingface.co/alikLab/NoLBERT
- Sarkar. StoriesLM. https://huggingface.co/StoriesLM
- Drinkall et al. Time Machine GPT. https://arxiv.org/abs/2404.18543
- Benhenda. Look-Ahead-Bench. https://arxiv.org/abs/2601.13770

Leakage evidence
- Lopez-Lira, Tang, Zhu. The Memorization Problem. https://arxiv.org/html/2504.14765v2
- Sarkar, Vafa. Lookahead Bias in Pretrained Language Models. https://conference.nber.org/conf_papers/f205530/f205530.pdf
- Glasserman, Lin. Assessing Look-Ahead Bias in Stock Return Predictions Generated by GPT Sentiment Analysis. https://arxiv.org/abs/2309.17322
- Cheng et al. Dated Data. https://arxiv.org/abs/2403.12958
- Li, Zeng, Xing, Xu, Xu. Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents. https://arxiv.org/abs/2510.07920

Agents and benchmarks
- TradingAgents. https://github.com/tauricresearch/tradingagents
- EvolveTrade. https://arxiv.org/abs/2609.17632
- TraderHarness. https://hephaestlab.github.io/TraderHarness/
- OpenPM. https://arxiv.org/abs/2608.09988
- LumiBot agents. https://lumibot.lumiwealth.com/agents.html
- Fonseca. Look-Ahead-Freedom as Temporal Non-Interference. https://arxiv.org/abs/2607.04958
- FINSABER. https://arxiv.org/abs/2505.07078v5
- StockBench. https://arxiv.org/abs/2510.02209
- LiveTradeBench. https://arxiv.org/abs/2511.03628
- Alpha Arena season 1 results. https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/
- Heil, Pramov, Gong. On the Role of Tools in Agentic LLM-Based Trading Systems (CLEF 2026). https://ceur-ws.org/Vol-4283/paper196.pdf
- Chai et al. Agentic Time Machine as an Infrastructure for Future-Event Forecasting. https://arxiv.org/abs/2606.21013
- FutureSearch. Bench to the Future: A Pastcasting Benchmark for Forecasting Agents. https://arxiv.org/abs/2506.21558

Return predictability
- Ke, Kelly, Xiu. Predicting Returns with Text Data. https://www.nber.org/papers/w26186

Alpaca
- Market data plans. https://docs.alpaca.markets/docs/about-market-data-api
- Stock bars API (adjustment, asof). https://docs.alpaca.markets/us/reference/stockbars
- News API reference. https://docs.alpaca.markets/us/reference/news-3
- Historical news. https://docs.alpaca.markets/us/docs/historical-news-data
- Real-time news stream. https://docs.alpaca.markets/docs/streaming-real-time-news
- News launch post (free-tier terms). https://alpaca.markets/blog/introducing-news-api-for-real-time-fiancial-news/
- Corporate actions API (data since April 2020). https://alpaca.markets/blog/introducing-corporate-actions-api-announcements/
- Forum: daily bars start at midnight New York time. https://forum.alpaca.markets/t/why-is-timezone-eastern-time-0500z/15637
- Forum: delisted symbols kept, raw bars by default. https://forum.alpaca.markets/t/are-alpaca-historical-tick-data-point-in-time/8493
- Forum: blended ticker histories. https://forum.alpaca.markets/t/fixing-data-historical-bars-of-symbol-q-are-comprised-of-two-different-stocks/18184 and https://forum.alpaca.markets/t/shared-market-data-between-different-tickers/18302
- Forum: a reported 2015 to 2016 news gap that was a client bug. https://forum.alpaca.markets/t/historical-news-data-missing-for-2016/13576

Other data
- S&P 500 history. https://github.com/fja05680/sp500
- EDGAR filing times. https://www.hudson-labs.com/post/filing-after-hours-when-it-matters and https://dm.certent.com/help/Content/F_File/timing_filing.htm
- ALFRED. https://fredblog.stlouisfed.org/2021/04/alfred-at-15-archiving-fred-data-since-2006/ and https://github.com/mortada/fredapi
- FRED API: real-time periods and vintages. https://fred.stlouisfed.org/docs/api/fred/realtime_period.html and https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- FNSPID (rejected; see `REVIEW.md`). https://huggingface.co/datasets/Zihan1004/FNSPID

Methods and compute
- Bailey, López de Prado. The Deflated Sharpe Ratio. https://papers.ssrn.com/abstract=2460551
- Bailey, Borwein, López de Prado, Zhu. The Probability of Backtest Overfitting. https://papers.ssrn.com/abstract=2326253
- Lo (2002). The Statistics of Sharpe Ratios. Financial Analysts Journal 58(4).
- River (online learning in Python). https://researchportal.ip-paris.fr/en/publications/river-machine-learning-for-streaming-data-in-python/
- ModernBERT without flash-attn (forum report). https://huggingface.co/answerdotai/ModernBERT-base/discussions/56
- ModernBERT in transformers. https://huggingface.co/docs/transformers/v5.14.0/model_doc/modernbert
- FlashAttention 2 GPU support. https://pypi.org/project/flash-attn/2.1.0
- Modal pricing. https://modal.com/pricing
- Kaggle GPU quota (third-party). https://www.gmicloud.ai/en/blog/best-free-gpu-cloud-options-for-ai-startups-and-researchers
