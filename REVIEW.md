# Plan review

Date: 29 Oct 2026. Reviews `PLAN.md` as of the same day.

Status (30 Oct 2026): Option 1 (Alpaca) was chosen. Every finding below is addressed in `PLAN.md` version 2. FNSPID-specific findings (C1 to C4, minor 11 and 12) are resolved by dropping FNSPID, and their lessons carry over as tests: timestamp anchors, the survivorship audit, and steady reader inputs.

## Verdict

The idea and the harness hold up: time-locked reader, learner trained on lived outcomes, time wall, frozen twins, the seal, and Track B as the new part. **The data foundation does not.** Built on FNSPID as planned, the backtest would have leaked same-day news into morning decisions, had a two-year news hole for the biggest stocks, and quietly dropped most acquired companies.

There are 5 critical findings, 10 major and 18 minor. The fix is a different data foundation (section 5) plus a set of smaller corrections. One decision is needed from you: which data foundation to use.

## How this review was done

1. **Re-read and re-checked.** Every line of `PLAN.md` was re-read, and the shakiest facts were re-checked against sources.
2. **Probed the real FNSPID files** with HTTP range requests, without downloading all 29 GB:
   - 43,264 rows read from 12 points in `All_external.csv`
   - 1,822 rows from 12 points in `nasdaq_exteral_data.csv`
   - the full file list of the price zip (15,387 tickers) and 19 complete price files
   - binary searches for specific tickers in the news files
3. **The scripts are in `research/fnspid_probes/`.** Re-run them with `python -I <script> ...`.

## Critical findings (would invalidate results)

### C1. FNSPID's "UTC" timestamps are 8 hours early

The timed Benzinga rows are labelled UTC, but the stored time is **true UTC minus 8 hours**. The evidence comes from headlines whose real time of day is known from what they say:

| Story type | Stored hour (summer) | Stored hour (winter) | Implied New York time (stored + 8h) |
|---|---|---|---|
| "... Stocks Moving In Friday's Mid-Day Session" | 08 (17 rows), 09 (3) | 08 (1), 09 (4), 10 (2) | about 12:00 to 13:00 |
| "Stocks That Hit 52-Week Highs/Lows On ..." | 06 (15), 07 (7) | 07 (4), 08 (8) | about 10:00 to 11:00 |
| "... Stocks Moving In ... Pre-Market Session" | 03 (11), 04 (9) | 04 (3) | about 07:00 to 08:00 |
| "Biggest Movers From Friday/Yesterday" | 00 to 02 | 01 to 02 | about 04:00 to 06:00 |

- **Why it's exactly 8 hours.** The stored hour is one hour later in winter than in summer, which only fits "true UTC − 8h". Example: "Stocks That Hit 52-Week Highs On Friday" is stored as `2020-06-05 06:30:54 UTC`. Add 8 hours and it's 10:30:54 New York time.
- **Likely cause.** FNSPID's Benzinga rows come from the Kaggle "Massive Stock News Analysis DB" (Aenlle, 2009 to 2020). Its timed file uses a fixed UTC−4 clock. FNSPID appears to have subtracted the 4 hours instead of adding them.
- **Why it's critical.** Taken at face value, the mid-day story above becomes visible at 4:45 am, before the 9:00 decision, and it describes that same day's trading. That's a direct leak into the label.
- **Fix.** Never trust FNSPID times of day. If any time is used, true UTC = stored + 8h, checked by the anchor test in M6.

### C2. Almost no FNSPID row has a real time, and dates may run a day early

- **Benzinga rows:** 97% have no time of day (00:00:00). That's 0 of 2,169 rows in 2009 to 2010, and 312 of 1,694 in 2020.
- **Nasdaq.com rows:** 99.6% are 00:00:00.
- **The uploader's warning.** A mirror of the original Kaggle page (now offline) quoted the uploader advising users to assume each article in the untimed file was published the *next* day.
- **Fix.** For date-only rows, `available_at` = 9:00 ET on the first trading day after (stored date + 1 day). The plan's rule ("next trading day") is one day too early if that warning is right.
- **Consequence.** The AI acts on most news one to two days late. Most of the price reaction happens before then (Ke, Kelly, Xiu), so the signal will be much weaker than in the ChronoBERT paper, which used exact timestamps.

### C3. FNSPID's news for the biggest stocks has a two-year hole

- **Nasdaq.com part** (first ~17.9 GB of `nasdaq_exteral_data.csv`): sorted by ticker, newest first. Its oldest article is 2022-06-05 for Apple, 2022-04-26 for Microsoft, 2019-09-03 for Exxon and 2012-05-18 for GE. It looks like a per-ticker cap on scraped articles, which hits the most-covered companies hardest.
- **Benzinga part:** ends in June 2020.
- **Result:** for the biggest companies there is no news from mid-2020 to 2022. The input also switches from short Benzinga headlines to full Nasdaq.com articles. The planned sealed years (2015 to 2023) would contain both the hole and the switch.

### C4. FNSPID's prices can't be used

- **Mixed snapshots with early cut-offs.** Several companies that are still trading stop early: BAC and FB at 2020-07-02, GOOGL at 2020-04-01 (while GOOG runs to 2023-12-28).
- **Acquired companies mostly missing.** Of 31 acquired or delisted names checked, **22 are missing entirely**: Celgene, Monsanto, Time Warner, EMC, DirecTV, Express Scripts, Genzyme, Medco, Burlington Northern, Schering-Plough, Wyeth, Heinz, Lorillard, Broadcom (old), SanDisk, CA, Red Hat, Anadarko, Lehman, Yahoo, Fannie Mae, Kraft.
- **The 8 that are present stop too soon,** at 2020-04-01 or 2020-07-02. Xilinx traded until 2022 and Activision until 2023.
- **Ticker reuse.** `DELL` is the new Dell (from 2016). The Dell delisted in 2013 is absent.
- **Not raw prices.** They're Yahoo-style split-adjusted closes, with two different column orders across files.
- **A mismatch with the news.** The news side does include some acquired companies (Monsanto 2009 to 2018, Time Warner, Express Scripts, Broadcom), so news and prices disagree about which companies exist.

### C5. The novelty claim overreaches

The ChronoBERT paper's real-time test already meets properties 1 to 3:
- a time-locked reader, with year Y news read by the year Y−1 model
- timestamped news (Dow Jones)
- an expanding-window ridge refit monthly on past data only

Track A is close to that design on a smaller universe with free data.

**What's actually new:**
- an open harness with machine-checked leak tests
- measuring the learning itself, with frozen twins
- trading costs and a forward test
- Track B: an agent on time-locked weights that learns from its own experience

**Fix:** narrow section 2's gap statement to those points.

## Major findings (would mislead, or break the build)

**M1. Warm-up and validation collide.** With a 12-month watch-only warm-up, "pick the penalty by walk-forward validation on the last 12 lived months" leaves nothing to train on at the first refit.
- Fix: validate on the latest 20% of lived days (minimum 3 months) until 5 years have been lived, then the last 12 months.

**M2. "Rank IC rises with experience" doesn't prove learning.** IC can rise because news coverage grows or the market changes.
- Fix: make the paired frozen-twin gap the primary evidence of learning (same days, same data), tested with Newey-West standard errors.
- Keep the raw learning curve as a picture, not as proof.

**M3. The deflated Sharpe is aimed at the wrong result.** It corrects for picking the best of many versions, which happens in the dev years. The sealed run is a single pre-chosen test.
- Fix: apply the deflated Sharpe to the dev result.
- Write `PREREG.md` before sealing, naming the primary hypotheses and metrics, and include its hash in `seal.lock`.
- Judge the sealed result against the pre-registered test only.

**M4. The Sharpe threshold is wrong.** With daily data, the standard error of an annual Sharpe is about 1/√T (the SR²/2 term applies to annual observations). So 9 years needs about **0.65** (not 0.75), and 7 years about 0.74.
- Daily rank IC is far more powerful. With 50 stocks it averages to a standard error of roughly 0.004 over 7 years (estimate), so make IC the primary skill metric.

**M5. Costs will probably decide the result.** Fully replacing both legs every day trades 200% of capital. At 5 bps a side that's about 25% a year in costs.
- With news acted on a day or two late, the edge will be small.
- Fix: make the holding period and turnover first-class design variables in the dev years, and always report results both before and after costs.

**M6. The non-interference test has blind spots.** It can't see anything computed outside the run: a stock list built with future data, embeddings from the wrong vintage, wrong timestamps in the source, survivorship in the source, or our own hindsight. Fixes:
- Pick the stocks inside the agent loop from `world.view`, not from an offline CSV.
- Keep the vintage test.
- Add a **timestamp anchor test**: after conversion, "Pre-Market Session" stories must land 4:00 to 9:30 ET, "Mid-Day" 11:00 to 14:00, "After-Hours" 16:00 to 20:00. If not, the conversion is wrong.
- Add a survivorship audit: compare the companies that have prices against the index members on each date.
- Add a planted leak where a vendor's daily-bar timestamp (midnight, the start of the day) is wrongly used as the time the close is known.

**M7. Multi-ticker lists and price recaps.** Benzinga tags stories like "46 Stocks Moving In Friday's Mid-Day Session" to dozens of tickers. They're price recaps, not company news.
- Fix: copy the single-firm filter the ChronoBERT paper used (Ke et al.), keeping only stories tagged to one or two tickers.

**M8. Company identity.** FB/META, DELL reuse, KRFT/KHC, GOOG/GOOGL, and formats like `HEI.A` vs `HEI-A` all break joins.
- Fix: keep a mapping table to a permanent ID (SEC CIK), valid by date.
- Alpaca's `asof` option follows renames, but its forum reports blended histories (ticker `Q`, ADEA/XPER). Add a check for pairs of tickers with identical returns.

**M9. The forward test as planned can't work.**
- FNSPID has no live feed, so the forward test would switch news source (and writing style) on day one.
- Git commit dates are set by the computer making the commit, so they prove nothing.
- Fix: use one news source that runs from history into today (section 5).
- Fix: run the daily job on GitHub Actions, whose server-side run times are independent. Optionally stamp each file with OpenTimestamps.

**M10. Track A learns a ranking, not "how to trade".** The holding period, position sizes and long/short rules are set by us.
- Fix: say so in the problem statement.
- A later version can let the agent choose its holding period or exposure from lived results, but that needs much more data.

## Minor findings

1. **ChronoGPT-Instruct row is out of date.** Hugging Face has all 26 yearly vintages (1999 to 2024) for ChronoBERT, ChronoGPT *and* ChronoGPT-Instruct. There's no "Realtime" model on Hugging Face; the paper's "realtime" means using last year's vintage.
2. **"Same setup" overstates it.** The two Sharpe results (4.80 vs 0.95) also differ in how the portfolio was built (decile sort vs three-way labels). The conclusion stands, but say "similar setup".
3. **"Used as fixed predictors" is wrong.** The ChronoBERT regression is refit monthly. Say "used for research regressions, not wrapped in a trading agent".
4. **Drop or hedge "news covers ~20% of stock-days".** The paper's sentence is garbled.
5. **The Calendar test checks a library against itself.** Replace it with: decision days equal the trading days in the price data.
6. **"Bit-identical" needs more.** Sort everything into a fixed order and set `PYTHONHASHSEED=0`. Alternatively, require positions to match exactly and predictions to within 1e-12.
7. **Leak tests should only pick days from the dev years,** so they never show sealed-period outcomes.
8. **Tokenizer.** ChronoBERT uses ModernBERT's 2024 tokenizer. Its vocabulary is a tiny theoretical leak channel. Note it.
9. **Hindsight in the reader's design.** The ChronoBERT authors chose its architecture in 2025, knowing what worked on 2008 to 2023 news. The effect is negligible, but it's one more reason the forward test is the gold standard.
10. **Spin-offs and special dividends** create fake ±30% days in adjusted data. Add a check that flags large one-day moves in big stocks.
11. **DuckDB can read the Hugging Face files directly** (`hf://`, since v0.10.3). Read every column as text: the file mixes Russian text into numeric-looking columns and has articles that span several lines.
12. **File layout, now known:**
    - `All_external.csv` (bytes are approximate): Benzinga analyst headlines A to Z (0 to ~0.34 GB), then Lenta in Russian (to ~2.5 GB), then partner headlines A to Z (~2.55 to 2.85 GB), then Reuters and Bloomberg with no tickers.
    - `nasdaq_exteral_data.csv`: Nasdaq.com articles A to Z (0 to ~17.9 GB), then the same external blocks appended. Use one file, not both.
13. **Exposure.** Report the long-short book's market beta and sector tilt. Consider a sector-neutral ranking.
14. **Benchmarks should match the strategy.** Compare long-short against cash and the other long-short baselines, and long-only against SPY and equal weight.
15. **Alpaca and Pakistan.** I couldn't confirm that Alpaca accepts users in Pakistan. You'd check and sign up yourself; I can't create accounts.
16. **Updated stories.** Alpaca returns each story's latest version (`updated_at`). Count it as available only from `updated_at`, not `created_at`.
17. **ChronoBERT's last vintage is 2024,** so it will read 2025 and 2026 news with an older vocabulary. That's acceptable, but note it.
18. **The EDGAR 6:00 am rule is uncertain.** It's irrelevant to Track A (no filings) and to a 9:00 clock.

## What survived

- The four-property framing, with the narrower gap statement.
- Read with a time-locked model, then decide with a learner trained on lived outcomes. The evidence supports this well.
- The time wall and `available_at` design. The newest-label rule (day k−2 at 9:00 on day k) checks out.
- Returns only, fitting on lived days only, the seal, frozen twins, the placebo and the price-only twin.
- Track B as the genuinely new contribution.

## 5. The data foundation: a decision for you

**Option 1 (recommended): Alpaca for both news and prices.**
- **News:** Benzinga, from 2015 to live, with real `created_at`/`updated_at` timestamps, ticker tags and optional full text. The docs say about 130 stories a day across the market.
- **Prices:** daily bars from 2016, raw by default, with delisted symbols kept and `asof` for renames.
- **Free tier:** 200 requests a minute, per the docs and the launch post. Confirm the current terms.
- **Years:** 2016 warm-up, dev 2017 to 2019, sealed 2020 to the seal date (about 7 years, including the COVID crash and 2022), forward test after.
- **Pros:** correct timestamps, no news hole, includes acquired companies, and the same source continues live, so the forward test is like-for-like.
- **Cons:**
  - It needs an Alpaca account (not confirmed for Pakistan).
  - The history is shorter.
  - There are free-tier terms to confirm, and some known data quirks.
  - News volume for 2015 and 2016 needs counting.

**Option 2: FNSPID, with the fixes.**
- Use only Benzinga 2009 to June 2020 with the date+1 rule, and take prices from Tiingo or a paid source.
- **Pros:** no account needed, and an earlier start.
- **Cons:**
  - The AI acts a day or two after the news.
  - The data ends in mid-2020.
  - There's no live source, so the forward test switches data.
  - Survivorship has to be patched by hand.

**Option 3: hybrid.**
- Use FNSPID Benzinga for dev years 2010 to 2014, and Alpaca from 2015 for the sealed and forward periods.
- **Con:** timestamp quality differs between dev and sealed, so the dev results would understate what the sealed years can do.

If Alpaca isn't available to you, GDELT is a free fallback (15-minute updates since 2015), but stories would have to be matched to companies by name.

## Sources added in this review

- FNSPID files, probed directly: https://huggingface.co/datasets/Zihan1004/FNSPID
- Kaggle source of FNSPID's Benzinga rows (Aenlle). Mirror summary via search; the mirror is now offline. https://www.kaggle.com/datasets/miguelaenlle/massive-stock-news-analysis-db-for-nlpbacktests
- ManelaLab model list (78 models, 26 per family). https://huggingface.co/api/models?author=manelalab&limit=200
- FlashAttention 2 GPU support. https://pypi.org/project/flash-attn/2.1.0
- DuckDB `hf://` support. https://duckdb.org/docs/extensions/httpfs/hugging_face and https://duckdb.org/2026/09/25/hugging-face
- Alpaca news API reference. https://docs.alpaca.markets/us/reference/news-3
- Alpaca historical news docs. https://docs.alpaca.markets/us/docs/historical-news-data
- Alpaca news launch post (free-tier terms). https://alpaca.markets/blog/introducing-news-api-for-real-time-fiancial-news/
- Alpaca forum: a reported 2015 to 2016 news gap that was a client bug. https://forum.alpaca.markets/t/historical-news-data-missing-for-2016/13576
- Alpaca forum: bar history and delisted symbols. https://forum.alpaca.markets/t/are-alpaca-historical-tick-data-point-in-time/8493
- Alpaca forum: blended ticker histories. https://forum.alpaca.markets/t/fixing-data-historical-bars-of-symbol-q-are-comprised-of-two-different-stocks/18184 and https://forum.alpaca.markets/t/shared-market-data-between-different-tickers/18302
- Alpaca rate limits (third-party summary). https://apis.io/rate-limits/alpaca-markets/alpaca-markets-rate-limits/
