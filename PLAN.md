# Chrono-trader: problem statement and plan

Status: research and planning only. Nothing is built yet.

This is version 2 (30 Oct 2026). It's rebuilt on Alpaca data after the review in `REVIEW.md`. The review's evidence and probe scripts stay in `REVIEW.md` and `research/fnspid_probes/`.

Decisions so far:
- **29 Oct 2026: Track A comes first** (a time-locked reader plus a learner). Track B (a time-locked LLM trader) follows on the same harness.
- **30 Oct 2026: the data comes from Alpaca.** That means Benzinga news from 2015 and daily prices from 2016, with delisted companies kept.
  - FNSPID is dropped. Its timestamps are 8 hours early, almost all rows have no time of day, the biggest stocks have a 2020 to 2022 news hole, and its prices leave out most acquired companies (`REVIEW.md`, C1 to C4).

Pending:
- Confirm that Alpaca accepts an account from Pakistan, open it, and create API keys. Keys never go into git.

## 1. Problem statement

Build an AI that lives through stock market history once, in order, and learns to trade from what it lives through.

Each trading day it sees only what was public before it decides. Track A uses prices and news. Later versions add SEC filings and economic data as first published.

It reads the news with a language model whose training ended before that day. So it arrives able to read, but knowing nothing about the market. It picks positions, sees what happens, and updates itself. It can study its own past as often as it likes. It can never see a day it hasn't lived.

The question it answers: **does it get better with experience, on days it could not have known about?**

### What "learned, not pattern-matched" means here

Every model learns patterns, and so do people. What matters is when the patterns were learned. A model trained on today's internet has read how 2008, 2020 and 2022 ended, so in a backtest it can recall the answers instead of working them out. This project's AI can only learn from days it has already lived. Four properties have to hold at the same time:

1. **Its weights can't know the future.** Every model it uses finished training before the day it's used.
2. **Its data is point-in-time.** Every record carries the moment it became public, and the AI can't see it before then.
3. **It learns in a single pass.** It learns only from outcomes that have already happened, in order, one day at a time.
4. **There is a checked guarantee.** Automated tests prove that changing anything in the future can't change a past decision.

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

### Time-locked models exist, are open, and hold up

| Model | Size | Vintages | Weights | Notes |
|---|---|---|---|---|
| ChronoBERT | 149M-parameter ModernBERT encoder, 1,024-token context, ModernBERT's tokenizer | Yearly, 1999 to 2024 (26 models) | `manelalab` on Hugging Face, MIT license | The reader for this project |
| ChronoGPT | 1.55B-parameter decoder, 1,792-token context | Yearly, 1999 to 2024 | `manelalab`, MIT license | Custom architecture with its own inference script |
| ChronoGPT-Instruct | About 1.5B | Yearly, 1999 to 2024 (the paper evaluates a subset) | `manelalab` | Chat model. Got 0 of 76 major events after its cutoff right |
| DatedGPT | Twelve 1.3B models, about 100B tokens each | Yearly, 2013 to 2024 | Demo at datedgpt.com. Public weights not confirmed | Instruction-tuned, including finance data |
| PIT models (Kelly, Malamud, Schwab, Xu) | Up to 4B, trained on 1T tokens | Monthly, 2013 to 2024 | Appear on Hugging Face under `Diamegs`. Not yet confirmed as the authors' account | Finest-grained ageing |

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
- **History** goes back to 2015. The docs say to expect about 130+ stories a day across the market.
- **Fields:** id, headline, summary, content (HTML, may be empty), author, created_at, updated_at, symbols, source, url.
- **Paging:** 50 stories per page, sorted by update time.
- **Live stream:** a WebSocket (`wss://stream.data.alpaca.markets/v1beta1/news`) sends the same fields.
- **Updates:** stories can change after publishing, and the API returns the latest version.

**Prices** come from `GET /v2/stocks/bars`:
- **History:** daily bars from 2016.
- **Raw by default.** `adjustment` can be split, dividend, spin-off or all.
- **Renames:** `asof` follows them (FB became META on 2022-06-09). `asof=-` turns the mapping off.
- **Delisted symbols stay in the database,** according to an Alpaca staff reply on the forum.
- **Bar timestamps:** a daily bar is stamped at midnight New York time (the start of the day), not when its close is known.

**The free (Basic) plan:**
- history from 2016
- 200 calls a minute
- the latest 15 minutes of data held back
- real-time quotes from IEX only
- 30 symbols on a WebSocket

Whether news is included for free was true in the beta launch post; confirm at sign-up. The paid plan is $99 a month and isn't needed.

**Other data:**
- **Dividends and splits:** the corporate-actions API only goes back to April 2020, so for 2016 to 2020 they're worked out by comparing raw and adjusted bars.
- **Known quirks** from Alpaca's forum: some tickers have blended histories (`Q`, ADEA/XPER), and some adjustments have been missing.
- **S&P 500 membership** comes from `fja05680/sp500` (MIT license). Since 2019 it's compiled from Wikipedia, so check that it covers up to 2026.
- **Later versions:**
  - SEC EDGAR acceptance timestamps (a filing accepted after 5:30 pm ET counts as filed the next business day)
  - ALFRED macro data with `realtime_start` and `realtime_end`

### Compute

- **Kaggle:** about 30 free GPU hours a week on a T4 or P100. This is from third-party reports; Kaggle's own docs weren't checked.
- **Modal:** $30 a month in free credit. A T4 is about $0.59 an hour.
- **Your laptop:** an i5-1035G1 with 4 cores, 7.8 GB RAM and no NVIDIA GPU. It's fine for everything except reading the news at scale and running an LLM trader.
  - Disk: C: has 12.4 GB free and D: has 69 GB, so data goes on D:.
- **ChronoBERT:**
  - It's ModernBERT-base: 22 layers, a 768-number hidden size, and float32 weights of about 600 MB per vintage.
  - On a CPU, load it with `attn_implementation="sdpa"` or `"eager"`. A forum report hit a bug with sdpa, so pin the transformers version and test both.
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

The availability rules are conservative on purpose:

| Record | `available_at` |
|---|---|
| News story | Its `updated_at` plus 15 minutes. The text we get is the latest version, and the free plan delivers news about 15 minutes late, so the backtest sees exactly what the live job will see |
| Daily close, high, low and volume for day d | 16:00 ET on day d. The vendor's bar timestamp (midnight) is never used for timing |
| Opening price for day d | 9:30 ET on day d. Only the simulator uses it |
| Return label for day d | The open on day d+1. Dividends and splits inside the window are part of the label |
| S&P 500 membership change | Its effective date |
| SEC filing (later versions) | Acceptance time, or 6:00 am the next business day if accepted after 5:30 pm ET. This rule is uncertain but conservative |
| Macro value (later versions) | 9:00 ET on the trading day after its `realtime_start` |

More rules:

- **Daily clock.** Decide at 9:00 ET, fill at the open, and use the open-to-open total return as the label.
- **Newest usable label.** At 9:00 on day k, the newest outcome the AI can learn from is day k−2's. Day k−1's open-to-open return isn't complete until day k's open, which comes after the decision.
- **Returns only.** Total returns come from day-over-day ratios of adjusted bars, which are safe. Dollar volume comes from raw bars. Adjusted price levels are never used, because back-adjusted prices already include future dividends and splits.
- **Fit on lived days only.** Everything that gets fitted (scalers, the ridge penalty, which embedding pooling to use) is fitted only on days already lived.
- **The stock list is picked inside the loop**, each January, from `world.view`. In 2016 it's picked on the first trading day of April from January to March data, because Alpaca's prices start in 2016.
- **Identity.**
  - A hand-checked table covers every company that ever enters the list (about 100). It maps its tickers over time to a permanent ID (SEC CIK).
  - Alpaca's `asof` is set inside each period the company was a member.
  - Renames and reused tickers (FB to META, the old and new DELL) are listed explicitly.
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

### 5.2 The reader (one cloud job)

- **Input:** headline plus summary, with HTML stripped. Article content (its first 256 tokens) is only a variant, and only if the audit shows content is present at a steady rate across the years. Inputs that change over time are what broke FNSPID.
- **Single-firm filter.** Use only stories tagged to at most 2 symbols, as the ChronoBERT paper did (following Ke et al.). Lists like "46 Stocks Moving In ..." are price recaps, not company news.
- **Vintage.** News first available in year Y is read by the year Y−1 model, so 2016 news goes to `chrono-bert-v1-20151231`. News from 2025 and 2026 is read by the 2024 model, the latest, so its vocabulary will age.
- **Output:** two 768-number embeddings per story (last layer, and the average of all layers), stored as float16 Parquet.
- **Cutoff check.**
  - For each vintage V, measure its masked-word loss on headlines from years V−1 to V+2. It should jump after V. Compare against vintage V+1 on the same headlines.
  - Probe named events, such as "Brexit" for vintages before 2016 and "COVID" for vintages before 2020.
  - Flag any vintage that knows too much.
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
- **Model.** A ridge regression refit every month on all lived days, as in the ChronoBERT paper. Variants to try in dev:
  - averaged monthly coefficients
  - more weight on recent data
  - online models from River

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

- ChronoGPT-Instruct (yearly vintages, confirmed) reads each stock's stories, writes a short thesis, and trades through the same harness. DatedGPT or a PIT-4B model can replace it if their weights turn out to be available.
- After each outcome it writes a reflection into its own journal, and it looks up past entries before deciding. TradingAgents keeps a similar memory, but here the model can't know the future.
- **Stretch goal:** fine-tune it now and then with LoRA on its own lived outcomes, so the learning reaches the weights.
- **Compute.** Days have to run in order; stocks within a day can run in parallel. ChronoGPT's custom architecture may need its own inference code, which is slower than standard model servers. Expect hours per run on one cloud GPU. It isn't practical on the laptop.
- The evidence in section 3 suggests this track will probably trail Track A. That comparison is a finding in itself.

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

Holm's correction is applied across H1 to H3. Sharpe after costs, drawdowns, turnover and exposures are reported but not tested.

The MVP succeeds if:
- every leak test passes, and every planted leak is caught
- H2 holds (it learned)
- H3 holds (reading helped)

A clean "it didn't learn" is also a valid result, reported as-is.

## 6. Cost

- **Laptop:** the harness, Track A and the reports. Free.
- **Alpaca Basic:** free, if news is included (confirm at sign-up).
- **Reader job:** probably fits Kaggle's free hours or Modal's $30 credit.
- **Forward test:** GitHub Actions, within the free minutes.
- **Track B:** a few dollars a run on Modal. Rough estimate.

## 7. Risks and open questions

- **Alpaca from Pakistan** isn't confirmed. If it's not available, the fallback is GDELT (free, 15-minute updates since 2015), but stories would have to be matched to companies by name.
- **Free-plan news access** comes from a beta-era announcement. Confirm it.
- **News volume in 2015 and 2016** is unknown. If it's thin, the warm-up and dev years shift later.
- **Alpaca data quirks** (blended tickers, missing adjustments) are covered by the audits in section 9.3.
- **Short history.** It's about 10 years (from 2016): 3 dev years and about 7 sealed.
- **The S&P 500 membership list** is compiled from Wikipedia and may have gaps.
- **Licensing.** Benzinga news and market data can't be redistributed. Raw data never goes into git or any public repo.
- **Weak reasoning in Track B.** Small time-locked LLMs reason poorly. In AlpacaEval, ChronoGPT-Instruct's responses won 13 to 17% of head-to-head comparisons against a 1.8B chat model.
- **Unconfirmed weights.** The `Diamegs` account (PIT models) and DatedGPT's weights are unconfirmed.
- **Hindsight.** We both know how 2020 to 2026 went, and the reader's designers did too. The seal limits this. Only the forward test removes it.
- **Late GitHub runs.** Scheduled runs can start late. A day the job can't finish before the open is logged as missed, never back-filled.
- **ChronoBERT on CPU** depends on the sdpa or eager attention path working in the pinned transformers version.

## 8. Build order

1. **You:** check that Alpaca accepts accounts from Pakistan, open one, and create API keys.
2. **M0, data audit** (section 9.3), plus a benchmark of ChronoBERT on the laptop CPU against a Kaggle GPU.
3. **M1:** the time wall and all the test suites.
4. **M2:** the reader job and the cutoff check.
5. **M3:** Track A on the dev years, with the twins, the placebo and the baselines.
6. **M4:** write `PREREG.md`, seal, run the sealed years once, and write the report.
7. **M5:** start the forward test.
8. **Track B.**

## 9. Track A build spec

### 9.1 Where things live

- **Code:** `C:\Users\syedh\dev\chrono-trader`, a git repo.
- **Data:** `D:\chrono-data`.
- **API keys:** environment variables, or a `.env` file listed in `.gitignore`.
- **Python:** 3.13 in a virtual environment, with these libraries:
  - `alpaca-py` (Alpaca's official SDK) or plain HTTP
  - pyarrow and Parquet for storage, and DuckDB for local queries
  - numpy, and scikit-learn for checks against the hand-rolled ridge
  - `exchange_calendars` for NYSE trading days, holidays and early closes
  - pytest and hypothesis for property-based leak tests
  - transformers and torch, only for the CPU benchmark (the real embedding job runs in the cloud)

```
chrono-trader/
  PLAN.md  REVIEW.md  PREREG.md (before the seal)
  config/          one YAML per run, hashed into the trial ledger
  data_pipeline/   Alpaca download, audit, identity table, event store (allowed to see everything)
  world/           the time wall: Clock, World.view(t), availability rules
  agent/           stock picking, features, learner, policy (allowed to see World.view only)
  sim/             fills, costs, portfolio accounting
  eval/            metrics, twins, placebo, pre-registered tests, reports
  cloud/           the embedding job notebook
  research/        probes and notes (FNSPID probes live here)
  tests/
  runs/            one folder per run, plus trials.csv
  seal.lock        created at the seal
```

The `agent` package may import only `world.view`, and a test enforces this.

### 9.2 Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Data audit | `audit.md` answers every question in 9.3, the identity table is checked, and the dev/sealed split is confirmed using counts only |
| M1 | Time wall | Every test in 9.11 passes, and every planted leak gets caught |
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

Outputs: `audit.md`, `identity.csv` and `split.json`.

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

**Target:** the log total return from day k's open to day k+1's open, minus that day's average across the 50 stocks.

### 9.7 The learner

- Scale features using means and variances from lived rows only.
- Use a ridge regression, refit monthly from running sums over an expanding window. As variants, try averaged monthly coefficients (as in the ChronoBERT paper) and recency weighting.
- Try penalties from 10⁻² to 10⁴, and validate as described in 9.5.
- Compute in float64. Sort everything into a fixed order and set `PYTHONHASHSEED=0`. Tests run with a single BLAS thread.

### 9.8 Portfolio and costs

- **Main version:** long the top 10 and short the bottom 10, equal-weighted and dollar-neutral, filled at the open.
- **Long-only version:** hold the top 10, compared against SPY and against holding all 50 equally.
- **Holding period:** 1, 3 or 5 days, plus an optional turnover band (keep a holding until it drops out of the top or bottom 15). These are dev variables, and each one counts as a trial.
- **Costs:** 5 bps per side on traded value (an assumption). The report shows results at 0, 5, 10 and 20 bps, before and after costs.
- **Exits:** a company that's delisted or acquired leaves at its last available price.

### 9.9 Comparison runs

Every run uses the same harness:
- the live agent
- frozen twins, one per year end, with the end-of-2019 twin pre-registered
- a price-only twin
- a shuffled-news placebo, where embeddings are swapped between stocks within each day using a fixed seed
- long-short baselines: random ranking, 12-1 momentum and 5-day reversal
- long-only baselines: SPY buy-and-hold and holding all 50 equally

### 9.10 Metrics and the report

- **Daily rank IC** (the Spearman correlation between prediction and outcome across the 50 stocks), by quarter, with Newey-West t-stats. This is the primary skill metric.
- **Frozen-twin gaps:** paired daily IC differences, by year after each snapshot.
- **The pre-registered tests H1 to H3,** with Holm's correction (sealed years only).
- **Long-short and long-only results:** return, volatility, Sharpe before and after costs, maximum drawdown, turnover, beta and sector tilt.
- **Deflated Sharpe** for the chosen dev version, using the number of trials in `runs/trials.csv`.
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
| Trading days | Decision days equal the trading days in the price data, with no decisions on holidays |
| Seal | The runner refuses sealed dates without a matching `seal.lock` (settings, `PREREG.md` and commit) and a clean git tree |

### 9.12 The seal

- `seal.lock` records the settings hash, the `PREREG.md` hash and the git commit.
- The runner refuses any date in the sealed years unless all three match and the working tree is clean.
- There is one sealed run. A second needs an explicit flag and is logged as another trial.
- The feature list is part of the seal.

### 9.13 Rough sizes (estimates)

- **Price bars:** about 700 symbols (every S&P 500 member since 2015) × about 2,700 trading days ≈ 1.9M bars. At 10,000 bars per request, that's about 190 requests.
- **News:** the volume is unknown until the audit. At 50 stories per request and 200 requests a minute, a million stories takes about 100 minutes.
- **The trading list:** 50 stocks × about 2,700 trading days ≈ 135,000 stock-days.
- **Embeddings:** 3 KB per story (two poolings in float16), so a million stories is about 3 GB. They're processed one year at a time to stay inside 7.8 GB of RAM.
- **Vintages:** 2014 to 2024, which is 11 models at about 600 MB each, roughly 6.6 GB. They're downloaded in the cloud job.
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
- PIT model weights (account unconfirmed). https://huggingface.co/Diamegs/PIT-1B-202312
- Drinkall et al. Time Machine GPT. https://arxiv.org/abs/2404.18543
- Benhenda. Look-Ahead-Bench. https://arxiv.org/abs/2601.13770

Leakage evidence
- Lopez-Lira, Tang, Zhu. The Memorization Problem. https://arxiv.org/html/2504.14765v2
- Sarkar, Vafa. Lookahead Bias in Pretrained Language Models. https://conference.nber.org/conf_papers/f205530/f205530.pdf
- Glasserman, Lin. Assessing Look-Ahead Bias in Stock Return Predictions Generated by GPT Sentiment Analysis. https://arxiv.org/abs/2309.17322
- Cheng et al. Dated Data. https://arxiv.org/abs/2403.12958

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
