Digest of PLAN.md at commit 323f2e9, written 2026-11-23. Line numbers refer to PLAN.md at that commit: refreshed from the diff dd40a5f to 323f2e9, then each cited line was checked against its text.

## Status and decisions list (L1-30)
- L3: Status says M0 and its review fixes are done and M1 (the time wall) is built and reviewed. M2 (the reader) has its table: all 502,712 stories it reads are embedded by the vintage the rule names, served through the time wall and checked on the real store (`research/audit/reader.md`, `research/m2_kickoff.md`).
- L3: The cutoff check did not pass in the milestone's sense: only the 2016 vintage is supported by evidence, the other nine that read news are too weak to judge, and the owner accepted all 11 as published on 21 Nov, as a known limit (`research/audit/cutoff.md`, section 9). The learner "isn't built yet".
- L5: This is version 2 (30 Oct 2026), rebuilt on Alpaca data after `REVIEW.md`.
- L8: 29 Oct 2026: Track A (time-locked reader plus learner) comes first; Track B (time-locked LLM trader) follows on the same harness.
- L9-10: 30 Oct 2026: data comes from Alpaca (Benzinga news from 2015, daily prices from 2016, delisted companies kept).
- L10: FNSPID is dropped: timestamps 8 hours early, almost no time of day, a 2020 to 2022 news hole for the biggest stocks, prices omit most acquired companies (`REVIEW.md` C1 to C4).
- L12-14: 30 Oct 2026: Alpaca access confirmed on a paper account from Pakistan; keys are in `.env`, which git ignores.
- L15: 30 Oct 2026: the reader reads headlines only.
- L16: 30 Oct 2026: one share class per company (GOOG/GOOGL); keep the more liquid class.
- L17: 30 Oct 2026: Benzinga stories only; fiscal.ai was added 18 Oct 2026 and is 59% of the feed since.
- L18: 30 Oct 2026: the reader runs on the laptop: 511,678 single-firm headlines, 2016 to 2026, 6 to 7 headlines a second, about 22 hours, run a year at a time.
- L18: A cloud GPU is still faster; M2 picks one.
- L19: 31 Oct 2026: companies, not tickers. Permanent ID is the SEC CIK, with tickers and share classes by date (`reference/identity.csv`).
- L19: Prices are fetched per ticker inside those dates; news tags map to companies by date; counted by company the reader needs 500,745 headlines.
- L20: 31 Oct 2026: price corrections are data, in `reference/price_events.csv`, each with evidence; the simulator and features must apply them.
- L20: Alpaca adjusted bars get most spin-offs wrong; its daily open is the first trade on any venue.
- L21: 4 Nov 2026: incomplete bars are missing data. On 2021-04-19, 2021-10-25 and 2022-03-08, bars for 326 to 356 NYSE-listed members a day hold few trades.
- L21: A bar is flagged (`prices.incomplete`) when its trade count is below 5% of the median of its file's previous 20 bars: 1,035 member bars, counting one more on 2018-03-26.
- L21: Features treat flagged bars as missing; the stock picker ranks without them.
- L22: 4 Nov 2026: Alpaca's daily open is the first trade, not the opening auction. Judged within a cent or 0.2%, it misses the listing exchange's auction on 23 of 300 random stock-days and 259 of 787 checked.
- L22: Beyond the 54 corrections in `price_events.csv`, misses are not corrected one at a time; M1 fetches the official opening auction print for every stock-day the simulator trades.
- L23: 7 Nov 2026: a research brief was checked before adoption (`research/brief_check.md`).
- L24: 7 Nov 2026: official opens come from Alpaca's `/v2/stocks/auctions` (free plan), fetched by `data_pipeline/auctions.py` for all 787 bar files: 1,873,240 stock-days on NYSE sessions, about 15 minutes.
- L24: A stock-day's official open is the listing exchange's largest opening print, as in the M0 print check.
- L24: The listing exchange is the venue with the largest print on most of the 21 sessions around the day, because one day's records can lack its cross (2026-08-20 has no Nasdaq closing print for Nasdaq stocks).
- L24: The two agree on all 785 opens and 783 closes the print check judged (`research/audit/auctions.md`).
- L25: 7 Nov 2026: the simulator trades a stock only at its official open.
- L25: 519 of 1,371,723 member stock-days have none: 267 on 2023-01-24, 108 on 2018-01-24, 66 on 2022-03-08.
- L25: On such a day the stock is not traded and a holding waits for its next official open (`research/audit/auctions_missing_opens.csv`).
- L25: On 8 Nov the owner kept this rule rather than fall back to Alpaca's first trade.
- L26: 7 Nov 2026: a label runs from one official open to the next, chaining corrected close-to-close total returns, so closes cancel.
- L26: A company that stops trading exits at its last traded close, and that last label shows at the next session's open; a failure halted before the next open (SVB on 2023-03-10) is not known early.
- L27: 8 Nov 2026: a failed company is a total loss. SVB Financial, Signature Bank and First Republic (2023): exit label is -1, holding worth nothing at exit.
- L27: A company that is acquired exits at its last traded close (`failures` in `data_pipeline/store.py`).
- L28: 7 Nov 2026: the store keeps a company's days outside membership only up to 400 days before a membership and 14 days after.
- L28: Further away a file's bars can be another security's (IHS Markit's INFO file holds a thin NYSE Arca security in 2025).
- L29: 7 Nov 2026: a view shows a company's records only near its memberships, so the agent cannot learn it joins or rejoins later.
- L29: A record dated inside a membership, or up to 14 days after, shows at its own time.
- L29: A record dated up to 400 days before a membership shows from that membership's start, also for a rejoin (EQT's pre-2022 bars show at the rejoin, not during the 2018 to 2022 gap).
- L29: Views hold copies with plain string keys; agents may import only `View` (`world/view.py`); `World` is in `world/world.py`.
- L30: 7 Nov 2026: a label shows when the open that ends it prints: 9:30 on its end date, or later for a delayed opening.

## 1. Problem statement (L32-55)
- L34: Build an AI that lives through market history once, in order, and learns from what it lives through.
- L36: Each trading day it sees only what was public before it decides. Track A uses prices and news; later versions add SEC filings and economic data as they stood that day.
- L38: It reads news with a language model whose training ended before that day.
- L38: It can study its own past as often as it likes and can never see a day it has not lived.
- L40: The question: does it get better with experience, on days it could not have known about?
- L44-49: Four properties must hold together: (1) weights cannot know the future; (2) data is point-in-time, each record carrying when it became public; (3) it learns in one pass, only from outcomes already happened, in order; (4) automated tests show changing the future cannot change a past decision.
- L51: Frontier models never decide. They may write code, tests and reports. They make no decision on a replayed day and write no lessons, priors, rubrics or features that carry later knowledge.
- L53: Track A learns which stocks to rank above others, from news and recent prices. Holding time, bet size and long/short rules are set by us.
- L55: The headline result is the learning evidence in section 5.5, not a profit number.

## 2. What exists, and the gap (L57-77)
- L59-65: A table compares frontier-LLM agents, experience-learning agents, time-locked models, live benchmarks and leak checkers, with what each solves and leaves open.
- L67-71: ChronoBERT's real-time test already meets properties 1 to 3: each year's news read by the previous year's model, ridge refit monthly on past data only. Track A builds on it.
- L74-77: Not found elsewhere: an open harness with a machine-checked no-leak guarantee; learning measured against frozen copies; trading costs plus a live forward test on the same source; Track B.

## 3. Research findings that shape the design (L79-185)
- L83: Prompting does not remove leakage; masking names and dates fails (Lopez-Lira, Tang, Zhu).
- L84: Sarkar and Vafa found lookahead bias in two forecasting tasks.
- L85: Glasserman and Lin: in-sample gain faded out of sample, strongest for large firms.
- L86: Dated Data: a model's real cutoff can differ from the stated one, so we check the reader's cutoff ourselves.
- L87: Profit Mirage: five GPT-4o agents on NASDAQ-100; total return fell 50% to 72% and Sharpe 51% to 62% from 2021 to 2024; no random baseline.
- L93-99: Time-locked model table: ChronoBERT 149M encoder, 1,024-token context, yearly 1999 to 2024 (26 models), `manelalab`, MIT; the reader for this project.
- L94: ChronoGPT 1.55B decoder, 1,792-token context, yearly 1999 to 2024.
- L95: ChronoGPT-Instruct about 1.55B; got 0 of 76 major events after its cutoff right.
- L96: DatedGPT: twelve 1.3B models, yearly 2013 to 2024; public weights not confirmed.
- L97: PIT models: up to 4B, 1T tokens, yearly checkpoints (December, November in 2015) 2013 to 2024, `Diamegs`; do not cover 1999 to 2012.
- L99: Cutoffs are the authors' best effort; a misdated document can let later text in, hence our own cutoff check (5.2).
- L101: No pre-1999 model reads news by year, so 1999 stays the earliest start for vintage reading.
- L105-108: Read, then learn: Sharpe 4.80 (ChronoBERT embeddings plus monthly ridge); Llama 3.1 8B scored 4.90; difference not significant (p = 0.315). Setup: Dow Jones Newswire 2008 to mid-2023, next-day returns, equal-weighted long-short daily, no costs.
- L108: Ask for an opinion: ChronoGPT-Instruct Sharpe 0.95; Llama 3.2 3B 1.76.
- L110: Design rule: read with the time-locked model, decide with a learner trained on lived outcomes.
- L114: Published Sharpe ratios will not carry over (equal-weighted, exact timestamps, before costs); across 50 large stocks after costs the signal will be much weaker.
- L115: Replacing both sides of the book daily trades 200% of capital; at 5 bps a side that is about 25% a year.
- L116-118: FINSABER (20 years, 100+ stocks): LLM advantages fade. StockBench: most LLM agents do not beat buy-and-hold. Alpha Arena season 1: 4 of 6 frontier models lost money.
- L123: News: Benzinga via Alpaca `GET /v1beta1/news`; 2,260,406 stories from 1 Jan 2015 to 29 Oct 2026.
- L124: Fields: id, headline, summary, content, author, created_at, updated_at, symbols, source, url.
- L125: Paging is 50 stories per page; date filter and sort both use update time.
- L126: Benzinga only until 18 Oct 2026, with a blank `source` until 4 Jan 2022; since then fiscal.ai adds press releases and analyst-rating notes.
- L127: Symbols are the tickers in use at publication (PCLN, FB); class shares are spelled several ways.
- L128: Live stream is a WebSocket `wss://stream.data.alpaca.markets/v1beta1/news` with the same fields.
- L129: Stories can change after publishing; the API returns the latest version.
- L131-134: Checked 30 Oct 2026: stories back to 1 Jan 2015; true UTC; `summary` empty before recent years; content on 34% to 76% of stories.
- L138-139: Prices: `GET /v2/stocks/bars`, daily bars from 2016, raw by default; `adjustment` can be split, dividend, spin-off or all.
- L139: `asof` follows renames (FB became META 2022-06-09); `asof=-` turns it off.
- L140: Histories follow a symbol, not a company: FOXA is 21st Century Fox until 2019-03-18; Under Armour's UA is class A until 2016-12-06 and class C after; DWDP is Dow Chemical before 2017-09-01.
- L140: A company's member days come only from inside the dates the identity table gives each ticker; readers outside those dates keep only the company's own bars.
- L141: The daily open is the day's first trade on any exchange; on 2023-01-24 NYSE opened LLY, MA, XOM and 12 others late, 8% to 24% from Alpaca's open.
- L141: It misses on ordinary days too (23 of 300 random stock-days), so M1 fetches official opens.
- L141: The daily close matches the official closing auction with a few exceptions.
- L142: Spin-off adjustments are unreliable: of 73 distributions with adjusted and raw moves differing by more than 4%, 31 are off by more than 1 percentage point (up to 88), and 17 more on member days are not adjusted at all (16 spin-offs and warrant dividends, plus Under Armour's class C dividend).
- L142: Corteva's 2026 Vylor spin-off is left as an 84% loss.
- L143: Delisted symbols stay in the database (Celgene, Monsanto, Time Warner return 2016 bars with `asof` set inside 2016).
- L144: Bar timestamp is midnight New York time, for example `2016-01-04T05:00:00Z`.
- L146-151: Free (Basic) plan: history from 2016, 200 calls a minute, latest 15 minutes held back, real-time quotes from IEX only, 30 symbols on a WebSocket.
- L153: News is included on the free plan (confirmed 30 Oct 2026). The paid plan is $99 a month and is not needed.
- L156: The corporate-actions API only goes back to April 2020; for 2016 to 2020 dividends and splits come from comparing raw and adjusted bars.
- L157: Known forum quirks: blended histories (`Q`, ADEA/XPER) and missing adjustments.
- L158: S&P 500 membership comes from `fja05680/sp500` (MIT); since 2019 compiled from Wikipedia, so check coverage up to 2026.
- L160: Later: SEC filing accepted after 5:30 pm ET counts as filed the next business day.
- L161: Later: ALFRED macro as of day T uses the latest vintage published by that day; never today's revised series, never the first release.
- L165: Kaggle about 30 free GPU hours a week (third-party report, docs not checked).
- L166: Modal: $30 a month free credit, T4 about $0.59 an hour.
- L167: Laptop: i5-1035G1, 4 cores, 7.8 GB RAM, no NVIDIA GPU; reading the news took it 6 hours 12 minutes for 502,712 headlines on 21 and 22 Nov 2026, at 22.6 a second (`research/audit/reader.md`); the earlier estimate of 21 hours came from a slower benchmark.
- L168-172: Disk: C: tight (about 8.7 GB free on 30 Oct 2026); data, model cache, pip cache, temp and the Python environment live on D:; `.venv` links to `D:\venvs\chrono-trader`.
- L174: ChronoBERT is ModernBERT-base: 22 layers, 768 hidden size, float32 about 600 MB per vintage.
- L175: On CPU load with `attn_implementation="sdpa"` or `"eager"`; pin transformers and test both.
- L176: Benchmark 30 Oct 2026 (transformers 5.22): both modes work; 6 to 7 headlines a second; median 21 tokens.
- L177: A T4 cannot run FlashAttention 2.
- L178: GitHub Actions runs the daily forward-test job, scheduled early, and skips any day it cannot finish before the open.
- L182: Annual Sharpe standard error is about 1/sqrt(T) with T in years; the sealed period is about 7 years, so Sharpe must exceed about 0.75 to be told from luck.
- L183: Daily rank IC is the more powerful test; one day's IC with 50 stocks has noise about 0.15; the 7-year average has standard error about 0.004 (estimate). IC is the primary skill metric.
- L184: The deflated Sharpe ratio corrects for picking the best of many dev versions; the sealed run is a single pre-registered test; Holm's correction covers the pre-registered hypotheses.
- L185: The probability of backtest overfitting estimates how likely the chosen dev version is a fluke.

## 4. How the plan changed (L187-199)
- L191: Stocks: the 50 most-traded S&P 500 members over the previous year, re-picked each January inside the agent loop from data available then (was 20 hand-picked stocks).
- L192: Data: Alpaca instead of FNSPID.
- L193: Test: dev 2017 to 2019, sealed 2020 to the seal date, then a forward test on the same source.
- L194: No leakage: `available_at` on every record, a non-interference test, planted leaks, timestamp anchors and a survivorship audit.
- L195: Labels: learn only from outcomes realized by decision time (day k-2 at 9:00 on day k).
- L196: Proof of learning: a pre-registered paired test against a frozen twin, plus a placebo and a price-only twin.
- L197: Statistics: rank IC primary, Sharpe after costs, deflated Sharpe on dev, pre-registered tests on sealed.
- L198: Execution: decide at 9:00 ET, trade at the open, charge costs, holding period is a dev variable.
- L199: Scope: Track A (the MVP), then Track B, both on one harness.

## 5.1 The time wall (L203-267)
- L205-208: Each record is `id, source, entity_id, symbol, about_time, available_at, payload`; `entity_id` is a permanent company ID, never a ticker.
- L210: The agent only calls `world.view(t)`, which returns records with `available_at <= t`; agent code imports nothing else.
- L212: `world`, `sim` and `eval` import nothing from `agent`; an agent plugs in by one call: given the view at time t, return target positions.
- L218: News `available_at` is `updated_at` plus 15 minutes, so the backtest sees no more than the live job will.
- L218: It can see less: live, a story's first version shows before any edit, while the backtest shows the story only from its last edit (review of 21 Nov, L-P1; M5 measures the live lag).
- L218: Stories edited more than 3 days after publishing are dropped (0.2% of 2015's stories, at most 0.5% in any year).
- L219: Daily close, high, low and volume for day d are available at 16:00 ET on day d; the vendor's midnight stamp is never used for timing.
- L220: Opening price for day d is available at 9:30 ET on day d; only the simulator uses it.
- L221: Return label for day d is available at the next official open, usually day d+1's; dividends and splits inside the window are part of the label.
- L222: S&P 500 membership change is available on its effective date.
- L223: SEC filing (later): acceptance time, or 6:00 am the next business day if accepted after 5:30 pm ET (uncertain but conservative).
- L224: Macro value (later): 9:00 ET on the trading day after its `realtime_start`.
- L228: Daily clock: decide at 9:00 ET, fill at the open, label is the open-to-open total return.
- L229: Dates are New York dates everywhere; the free plan refuses any request reaching into a session in progress.
- L230: At 9:00 on day k the newest outcome the AI can learn from is day k-2's at the latest; the test is that the label is visible in the view (525 labels on 16 dates are not visible by then).
- L231: Total returns come from day-over-day ratios of adjusted bars; dollar volume comes from raw bars; adjusted price levels are never used.
- L232: Everything fitted (scalers, ridge penalty, embedding pooling) is fitted only on days already lived.
- L233: The stock list is picked inside the loop each January from `world.view`; in 2016 it is picked on the first trading day of April from January to March data.
- L235-237: A hand-checked identity table (about 100 companies) maps tickers over time to an SEC CIK; `asof` is set inside each membership period; renames and reused tickers (FB to META, old and new DELL) are listed.
- L239-241: The price audit found 50 ticker pairs that are one company, one reused ticker (SNDK), and 11 spells the membership file labels with a later ticker (AABA was YHOO, APTV was DLPH, KDP was DPS).
- L243: News symbols map to entities by date: Booking is PCLN until early 2018; Facebook is FB until June 2022; from 30 Jun 2021 to June 2022 META meant Roundhill's Metaverse ETF.
- L244: Class shares (BRK.B, BRK-B, BRK/B, BRK; Brown-Forman likewise) all map to one entity.
- L245: When two classes of one company qualify, keep the more liquid one.
- L246: A company that is acquired or delisted leaves at its last available price; a failed company is a total loss.
- L280: Output is two 768-number embeddings per story (last layer, and average of all layers), float16 Parquet, with the same vectors as two `.npy` arrays that `World.load` maps read-only, since they do not fit in the laptop's memory twice.
- L281: Which stories (M2, decision 2): every story in `story_entities` from New York year 2016 on, kept by `rules.keep_story`: 502,712. 2015's news is not read, and the 2014 vintage serves only the cutoff check.
- L282: When an embedding shows: its `available_at` is its story's (`rules.embedding`, review finding M-3), and a view shows it only once its story's first company link shows (judge J-1), so an embedding never tells of a company the view hides.
- L251: Core test 1, non-interference: run to day t, scramble or delete every record with `available_at > t`, run again; every decision up to t must be identical.
- L252-257: Core test 2, planted leaks, each must fail the tests: a future return, a future headline, a scaler fitted on all data, a stock list made with future data, a vendor bar timestamp used as close time.
- L258: Core test 3, label embargo: no training row's label was realized after the decision it is used for.
- L262-267: Blind spots and cover: wrong source timestamps by the timestamp anchor test; source survivorship by the survivorship audit; wrong-vintage embeddings by the vintage test; our own hindsight by the seal and forward test.

## 5.2 The reader (L269-291)
- L272-277: Input is the headline only. `summary` is empty on every 2015 to 2020 story sampled; content on 34% to 76%; typical length about 2,000 characters in 2015 to 6,400 in 2026. Content is an exploratory dev variant at most.
- L277: Source is Benzinga only: a blank or `benzinga` label.
- L278: Single-firm filter: only stories about at most 2 companies, counted after the identity table maps tickers to entities (GOOG and GOOGL count once).
- L278: Counted by company 963 of Berkshire's 2,210 stories pass; by ticker 684. One sampled story carried 89 symbols.
- L278: Market-wide 80% to 88% of stories pass each year; 64% of Apple's January 2015 stories against 37% of Microsoft's September 2026 stories. Story counts are compared across stocks on the same day, never across years.
- L279: Vintage: news published in New York year Y is read by the year Y-1 model; 2016 news goes to `chrono-bert-v1-20151231`.
- L279: The publication year counts, not the year the story became available.
- L279: News from 2025 and 2026 is read by the 2024 model, the latest (`reader/vintage.py`).
- L280: Output is two 768-number embeddings per story (last layer, and average of all layers), float16 Parquet.
- L284-286: Cutoff check: for each vintage V, measure masked-word loss on headlines from years V-1 to V+2; it should jump after V; compare against vintage V+1. Probe named events ("Brexit" before 2016, "COVID" before 2020). Flag any vintage that knows too much.
- L287: Masking diagnostic: rerun with company names and dates masked. It is a diagnostic, not a leak test. The leak guarantees stay the vintage rule, the cutoff check and non-interference tests.
- L289-290: Known limits: ModernBERT's 2024 tokenizer vocabulary (tiny theoretical leak channel); ChronoBERT's design was chosen in 2025 knowing what worked on 2008 to 2023 news.

## 5.3 Track A: the learner (L293-317)
- L295-299: Features per stock per day: average embedding of new stories and count; fading memory of older stories; returns over 1, 5, 20 and 60 days; volatility; change in trading volume.
- L300: Market-wide and macro features are left out on purpose.
- L301: Model: ridge regression refit every month on all lived days; it is the batch learner and the live agent.
- L302-304: Dev variants: averaged monthly coefficients; more weight on recent data; River online models. `PREREG.md` decides whether the batch-versus-sequential comparison becomes a sealed hypothesis.
- L306: The ridge is kept as running sums (X'X and X'y), so the learner can only add lived days.
- L308-309: Main test: long top 10, short bottom 10 of the 50. Easier version: hold the top 10, long-only.
- L310: Holding period (1, 3 or 5 days) and a turnover band are dev variables.
- L311: Costs are 5 bps per side, sensitivity at 0, 5, 10 and 20 bps; results shown before and after costs.
- L312: Report the long-short book's market beta and sector tilt; sector-neutral ranking is a dev variant.
- L314: Matched baselines: long-short against cash and against long-short momentum, reversal and random rankings; long-only against SPY and holding all 50 equally.
- L315: Frozen twins: snapshot at each year end and keep running without learning; the twin frozen at the end of the dev years is the pre-registered one.
- L316: Shuffled-news placebo: news swapped between stocks within each day.
- L317: Price-only twin: no news.

## 5.4 Track B (L319-327)
- L321: ChronoGPT-Instruct reads each stock's stories, writes a thesis, trades through the same harness; DatedGPT or a PIT model can replace it if weights are available.
- L322: After each outcome it writes a reflection to its journal and looks up past entries before deciding.
- L323: The journal keeps beliefs as structured statistics (such as each signal's recent hit rate) alongside text.
- L324: Memory ablation: no memory, short memory, long memory. In one small study (Heil, Pramov, Gong, CLEF 2026), 5-day or 10-day memory made results worse.
- L325: Stretch goal: occasional LoRA fine-tuning on its own lived outcomes.
- L326: Days run in order, stocks within a day can run in parallel; expect hours per run on one cloud GPU; not practical on the laptop.
- L327: It is compared with Track A's batch learner on the same days; section 3 suggests it will probably trail Track A.

## 5.5 Evaluation protocol (L329-368)
- L331: Warm-up 2016, watch-only; stock list picked in April 2016.
- L332: Dev years 2017 to 2019, tune freely; every run is logged with a hash of its settings in `runs/trials.csv`.
- L333: Before sealing, write `PREREG.md` with hypotheses, metrics, tests and decision rules.
- L334: Seal: `seal.lock` records the settings hash, the `PREREG.md` hash and the git commit.
- L335: Sealed years: 2020-01-01 to the last trading day before the seal; run once and report as-is.
- L337-339: Forward test: from the next trading day a GitHub Actions job runs the same code on the same Alpaca source every morning and commits the day's decisions before the open; GitHub's server-side run times are the proof; OpenTimestamps optional; results scored daily.
- L340-344: E-1 (entry rule for M5, from the M2 review of 22 Nov 2026, `research/review_m2_2026-11-22.md`): the morning job's reader reuses `reader/embed.py`. Each part's manifest records the library and code versions as well as the vintage: the token cap, batch size, pooling, tokenizer file ids, torch and transformers versions, and a hash of `embed_ids`. A resume or a morning run whose versions differ from the manifest's stops, so vectors made two ways are never mixed.
- L345-347: C-1 (entry rule for M5, same review): any rules frozen in future, such as a probe list or a scoring rule, are committed (or their hashes sent to the owner) before anything is scored, and the scoring command refuses to run unless the files match that record.
- L349: The seal locks the feature list; anything added afterwards can only be judged by the forward test.
- L355: H1 (skill): live agent's mean daily rank IC is above 0; one-sided, Newey-West standard errors.
- L356: H2 (learning): live agent's daily IC beats the twin frozen at the end of 2019; paired, one-sided, Newey-West.
- L357: H3 (reading): live agent's IC beats both the price-only twin and the shuffled-news placebo; paired, one-sided, Newey-West.
- L359: Holm's correction across H1 to H3. Sharpe after costs, drawdowns, turnover, exposures, regime and shock results, and coefficient life are reported, not tested.
- L361: Every random part (placebo, random-ranking baseline) runs with several seeds and the report shows the spread.
- L363-366: MVP succeeds if every leak test passes and every planted leak is caught, H2 holds, and H3 holds.
- L368: A clean "it didn't learn" is a valid result, reported as-is.

## 6. Cost (L370-376)
- L372-373: Laptop (harness, Track A, reports) and Alpaca Basic with news are free.
- L374: Reader job: run on the laptop (M2, decision 1): 6 hours 12 minutes for 502,712 headlines, free (`research/audit/reader.md`).
- L375: Forward test runs on GitHub Actions within the free minutes.
- L376: Track B: a few dollars a run on Modal (rough estimate).

## 7. Risks and open questions (L378-390)
- L380: Free-plan terms can change; keep a local copy of everything downloaded; GDELT is the fallback but needs matching by company name.
- L381: Benzinga's source label went from blank to `benzinga` in January 2022; fiscal.ai joined in October 2026; the pipeline filters by source.
- L381: The forward test should compare each day's Benzinga story count with recent history to raise an alarm on feed changes.
- L382: Alpaca data quirks are covered by the section 9.3 audits.
- L383: Short history: about 10 years from 2016, 3 dev years and about 7 sealed.
- L384: The S&P 500 membership list comes from Wikipedia and may have gaps.
- L385: Benzinga news and market data cannot be redistributed; raw data never goes into git or any public repo.
- L386: Track B reasoning is weak: ChronoGPT-Instruct won 13 to 17% of AlpacaEval head-to-head comparisons against a 1.8B chat model.
- L387: DatedGPT's public weights are unconfirmed; PIT weights are under `Diamegs`.
- L388: Hindsight: we know how 2020 to 2026 went and so did the reader's designers; the seal limits this, only the forward test removes it.
- L389: A day the scheduled job cannot finish before the open is logged as missed, never back-filled.
- L390: ChronoBERT on CPU depends on the sdpa or eager path working in the pinned transformers version.

## 8. Build order (L392-402)
- L394: Done (30 Oct 2026): Alpaca paper account, keys in `.env`, access checked.
- L395: Done (31 Oct 2026): M0 data audit (prices and news downloaded and audited, identity table built, corrections recorded, split confirmed with counts, laptop benchmark done).
- L396: M1: the time wall, all test suites, and the official opening auction print for every stock-day the simulator trades.
- L397: Done (22 Nov 2026): M2, the reader job and the cutoff check. The table is built and served through the time wall. The cutoff check supports only the 2016 vintage, and the owner accepted all 11 as published, a known limit (`research/audit/reader.md`).
- L398: M3: Track A on the dev years with twins, placebo and baselines.
- L399: M4: write `PREREG.md`, seal, run the sealed years once, write the report.
- L400: M5: start the forward test.
- L401: Then Track B.
- L402: Later: a long replay from 1999 on one market (S&P 500 index or EUR/USD) with prices, FOMC statements and as-of economic data; deferred, not a replacement for Track A.
- L402: Agentic Time Machine and Bench to the Future cannot feed news for 1999 to 2015 (`research/brief_check.md`).

## 9.1 Where things live (L406-436)
- L408: Code in `C:\Users\syedh\dev\chrono-trader`, pushed to private repo `syedhamza2135/chrono-trader`.
- L409: Data in `D:\chrono-data`.
- L410: API keys in environment variables or a `.env` listed in `.gitignore`.
- L411-417: Python 3.13 venv with alpaca-py or plain HTTP; pyarrow, Parquet, DuckDB; numpy, scikit-learn (checks only); `exchange_calendars`; pytest and hypothesis; transformers and torch.
- L419-434: Layout: `config/`, `data_pipeline/` (allowed to see everything), `reference/`, `world/`, `agent/` (World.view only), `sim/`, `eval/`, `reader/`, `research/`, `tests/`, `runs/` (with trials.csv), `seal.lock`.
- L436: The `agent` package may import only `world.view` and a test enforces it; `world`, `sim` and `eval` import nothing from `agent`, and a test enforces that too.

## 9.2 Milestones and done-when (L438-447)
- L442: M0 Data audit: done when `audit.md` answers every question in 9.3, the identity table is checked, and the dev/sealed split is confirmed using counts only.
- L443: M1 Time wall and official opens: done when every test in 9.11 passes, every planted leak is caught, and the simulator has the listing exchange's official opening auction print for every stock-day it trades.
- L444: M2 Reader: done when every filtered story is embedded by the right vintage and the cutoff check passes (or any failing vintage is replaced).
- L445: M3 Track A on dev years: done when a dev report shows IC by quarter, frozen twins, placebo, price-only twin, matched baselines, holding-period variants, costs and exposures.
- L446: M4 Pre-register, seal, sealed run: done when `PREREG.md` is hashed into `seal.lock` and the sealed report is published as-is.
- L447: M5 Forward test: done when the GitHub Actions job has committed decisions before the open on every trading day for a month, and they have been scored.

## 9.3 The data audit, M0 (L449-527)
- L453: News questions: free-plan inclusion and rate limit; stories per member per year 2015 to 2026 (decides 2016 as warm-up); summary and content share by year; symbols per story (sets the single-firm filter).
- L456: Timestamp anchors: after conversion to New York time, "Pre-Market Session" lands 4:00 to 9:30, "Mid-Day" 11:00 to 14:00, "After-Hours" 16:00 to 20:00.
- L457: Gap between `created_at` and `updated_at` shows how often and how late stories change.
- L460-464: Price questions: survivorship at each January (Celgene, Monsanto, Time Warner); identity (renames, reused tickers); corporate actions (raw to adjusted ratios, review every one-day move above 25% in a big stock); blended histories (pairs with identical return series); membership complete to 2026.
- L466: Early results 30 Oct 2026 from `research/alpaca_check.py` and `research/alpaca_news_probe.py`, on samples: Apple (Jan 2015, Jan 2016, Jun 2018), JPMorgan (Jun 2016, Mar 2020), Microsoft (Sep 2026).
- L470-473: Early answers: news free at 200 requests a minute; stories from 1 Jan 2015 (Apple 255 that month); true UTC, all 8 anchor headlines inside their windows; summary present on 186 of 306 stories in Sep 2026.
- L475: Edits: 2.4% of Apple's Jan 2015 stories edited more than a day later (up to 14 days); none in later samples.
- L476: Stories with at most 2 symbols: 64% (Apple, Jan 2015) down to 37% (Microsoft, Sep 2026); one story had 89 symbols.
- L479: Alpaca filters by update time; timing always comes from each story's own fields.
- L481: Price audit 31 Oct 2026, rerun 5 Nov: `python -m data_pipeline.audit_prices` on bars from `python -m data_pipeline.bars`; report `research/audit/prices.md`.
- L485: Downloads: 787 plan rows for 719 companies, 1,574 files (raw and adjusted), 179 MB, 1,360,471 company member days to 2026-10-28.
- L486: Membership runs to today: fja05680 to 18 Aug 2026, then Wikipedia's change log; ends with 503 members.
- L487: Survivorship: every member company has bars on every picking date 2016 to 2026; 64 member sessions have no bar, all after a last trade: 58 acquisition closings before removal, 6 failed-bank halts (SVB Financial from 2023-03-10, First Republic from 2023-05-01).
- L488: Identity: no two companies share 20 or more identical member-day bars; splicing in FOXA, UA, ARNC, DLPH, so a ticker's member days are only those inside its row.
- L488: DowDuPont's 2018 pick used Dow Chemical's bars before the review; on its own bars it ranks 40th. XL is two securities, so two rows.
- L488: A company changes rows 56 times while a member; 11 of those days need a return stitched from the previous row.
- L488: On 195 first member days, or returns after a gap, the previous bar cannot be shown to be the company's own, so the return is undefined.
- L489: Large moves: 265 adjusted one-day moves above 25% on member days; 141 fail the print check (almost all on the open); 43 corrected in `price_events.csv`; 14 reversed by more than 20% the next day.
- L489: Of those 14, 3 match official prints (PG&E Nov 2018, Lincoln Financial and Noble Energy Mar 2020); 6 corrected (Nordstrom's bar, Hilton's and Oneok's closes, opens of Hess, Ventas, Aptiv); 5 match the close and miss the open by 0.4% to 1.6%.
- L489: The 10 large moves in picked stocks' own years all match the official close; 7 match the open; 3 miss by 0.2% to 0.5% (Twitter 2022, Oracle 2025, Supermicro 2026).
- L490: Official prints checked on 787 stock-days (436 dates); a match is within a cent or 0.2% of the listing exchange's auction print.
- L490: Alpaca's close matches on all 300 random days (largest gap 0.06%) and misses on 8 stock-days (7 closing auctions and Nordstrom's rebuilt bar), all corrected.
- L490: Alpaca's open misses the auction on 259 stock-days (128 dates), median gap 0.64%, including 23 of 300 random days and 15 stocks on 2023-01-24 by up to 24%.
- L490: 55 misses are corrected (54 opening prints and Nordstrom's bar); M1's official opens cover the rest; 2 closes had no print to judge.
- L490: The first check, 784 stock-days at 2% tolerance, called 198 of these open misses matches.
- L491: Adjustment events: 150 member days where adjusted and raw moves differ by more than 4%: 77 splits and 73 distributions; 31 are off by more than 1 point (1.1 to 88), 42 within 1 point; 17 unadjusted distributions found (16 spin-offs and warrant dividends, plus Under Armour's class C dividend), all corrected.
- L492: Incomplete bars: 1,035 (1 on 2018-03-26, 356 on 2021-04-19, 326 on 2021-10-25, 352 on 2022-03-08); 83 are in that year's picks; volume, high, low, VWAP and maybe open are not the day's, so features treat them as missing; list in `research/audit/incomplete_bars.csv`.
- L493: Trading days: Apple's bars match the NYSE calendar exactly to 2026-10-28.
- L494: Picking preview: 5 to 9 of the 50 names change each year, one class per company, own bars, no incomplete bars; picks that later left the index (Allergan, Celgene, Twitter, American Airlines) all have bars.
- L495: Laptop reading speed 6 to 7 headlines a second.
- L497: Identity audit 31 Oct 2026, rebuilt 4 Nov: `python -m data_pipeline.identity`; 131 tests; report `research/audit/identity.md`.
- L501: 746 companies since 2015 keyed by SEC CIK, 814 ticker rows; seven list two share classes at once (Alphabet, Comcast, Discovery, both Foxes, News Corp, Under Armour).
- L502: The membership file has about 25 early periods with later tickers, merges companies sharing a ticker, omits ACE, Tyco and Actavis, lists Michael Kors and Coca-Cola Enterprises twice, has three wrong dates (Trane, Cimarex, Four Corners), and misassigns Bemis's two days (2019-06-07, 2019-06-10), 21st Century Fox's last day (2019-03-19) and MasterBrand's two (2022-12-15, 2022-12-16).
- L502: All fixed in `reference/identity_fixes.csv`: 97 rows, each with evidence.
- L503: Wikipedia's CIK column lags events by months or years (Fox 18 months, Medtronic 4 years); the parser now reads Tractor Supply's three 2015 revisions.
- L504: News tags map by date: PCLN is Booking until 2018-02-26; META in 2021 is nobody; BRK/B and plain BRK are Berkshire; class tags on a plain root (LEN.B, CBS.A, STZ.B) map to that company, for US class tags in the news only.
- L505: Identity open items: None.
- L507: `reference/price_events.csv` holds 122 rows with evidence: 54 opening auctions, 7 closing auctions, Nordstrom 2018-03-26, 55 distributions, Biogen's two halts, and three failed banks (SVB Financial, First Republic, Signature Bank).
- L507: The 55 distributions: the 31 off by more than 1 point, GE's real ex-date for its 2019 Wabtec distribution (Alpaca applies it a day early), Under Armour's class C dividend, four at a change of ticker, 16 spin-offs and warrant dividends, Aimco's 2019 special dividend, and Occidental's dividend on 2020-03-09.
- L507: On 8 Nov M1 added three rows (making 125) from a screen of 48,935 non-member days: EQT's Equitrans spin-off 2018-11-13 (0.8 ratio applied as a split), DPS's $103.75 special dividend 2018-07-10, CCE's merger into Coca-Cola European Partners 2016-05-31 (one share and $14.50 cash per CCE share).
- L509: News audit 30 Oct 2026, rerun 5 Nov with New York years: `python -m data_pipeline.audit_news`; report `research/audit/news.md`.
- L513: Download: 142 months Jan 2015 to Oct 2026, 2,260,406 unique stories, 251 MB Parquet, about 4.5 hours.
- L514: Every story's `updated_at` falls inside the month whose query returned it; 0.09% were created in an earlier month; each story is stored once, under the month of its latest edit.
- L515: Sources: Benzinga only until 18 Oct 2026; blank label until 4 Jan 2022 (all link to benzinga.com); fiscal.ai made up 59% of stories from 19 to 29 Oct.
- L516: Benzinga stories a year: 138,536 (2015), low 107,848 (2017), high 261,738 (2024), 208,827 in 2026 to 29 Oct.
- L517: Each year 80% to 88% of stories carry 1 or 2 symbols and 2% to 10% carry none.
- L518: Edited more than 3 days after publishing: 0.2% of 2015's stories, at most 0.5% in any year (2021).
- L519: Timestamps: 12,231 session recaps checked; 5 stamped before their session; 4 are typos naming the next weekday; 1 unexplained (mid-day list stamped 08:03 on 13 Jul 2018, story 12016835).
- L519: Late stamps only delay a story: 247 pre-market lists, all but one from 2024 and 2025, stamped between 16:04 and 16:10.
- L520: Coverage: from each year's pick date the median picked stock has 121 to 319 single-firm stories a year on 71 to 151 days; 2016 from the 2016-04-01 pick is 125 stories on 71 days (fewest, 31, Berkshire), so 2016 works as warm-up; thinnest pick in any year has 28 (Schlumberger in 2017).
- L523: Reading load: single-firm stories about members on the story's date, 2016 to 2026: 500,745 headlines, about 21 hours, 1.5 GB of embeddings; for the 50 picked companies from each pick date: 168,803, about 7 hours.
- L525: Split (`reference/split.json`, counts only): warm-up 252 sessions, dev years 754, sealed years 1,715 so far; 79,000 single-firm member stories in dev years and 387,796 in sealed years; counted by New York date to each period's last session; sealed years stop at 2026-10-28.
- L527: Outputs: `research/audit/audit.md`, `reference/identity.csv` (with `entities.csv`, `memberships.csv`, `identity_fixes.csv`), `reference/price_events.csv`, `reference/split.json`.

## 9.4 The event store (L529-544)
- L531-533: The store is built in M1 by `data_pipeline/store.py` into `DATA_DIR/store`; counts and column rules are in `docs/digests/store_tables.md` (rewritten from it in the review of 21 Nov, L-P4). No table stores an availability time; `world/rules.py` sets it from raw times.
- L534-535: `bars`: entity_id, share_class, symbol, date, open, high, low, close, volume, trades, vwap, ret (the corrected close-to-close total return), incomplete, member, no_trade (one table, raw prices with the adjusted total return).
- L536: `opens`: entity_id, share_class, date, open, open_time, listing_exchange, official_close.
- L537: `labels`: entity_id, share_class, date, end, label, at_close, end_open_time.
- L538: `stories`: story_id, created_at, updated_at, headline, symbols, n_companies.
- L539: `story_entities`: story_id, entity_id (only stories passing the single-firm filter).
- L540-541: `membership`: entity_id, member_from, member_to (one row per spell and share class); `identity`: entity_id, symbol, share_class, valid_from, valid_to, cik.
- L542: `embeddings` (M2, built 22 Nov 2026): story_id, vintage_year, available_at, emb_last (768 float16), emb_avg (768 float16); 502,712 rows. The vectors are also in `embeddings_last.npy` and `embeddings_avg.npy`, and `embeddings.json` records the story set's hash, the pins and the arrays.
- L544: All times are stored in UTC and converted to New York time, with daylight saving handled, when rules are applied.

## 9.5 The daily loop, 9:00 ET on trading day k (L546-556)
- L548: `v = world.view(9:00 ET on day k)`.
- L549: On the first trading day of the year, pick the year's 50 stocks from `v` (2016: first trading day of April).
- L550: Build features for the 50 stocks from `v`.
- L551: On the first trading day of each month, refit the scaler and ridge on every lived row whose label is visible in the view (day k-2 and earlier at the latest). Nothing is fitted until 6 months have been lived.
- L552: Choose penalty and embedding pooling by validating on the most recent 20% of lived days (at least 3 months) until 5 years have been lived; after that use the last 12 months.
- L553: Training ends before validation starts, with the k-2 gap at the boundary.
- L554: Predict, rank and set target positions given the holding-period rule.
- L555: `sim` fills at day k's open and charges costs.
- L556: Log one row per stock: date, entity_id, prediction, position, config hash.

## 9.6 Features (L558-571)
- L562: news_count: filtered stories available since the last decision.
- L563: news_new: mean embedding of those stories (zeros and a flag if none).
- L564: news_memory: exponentially weighted mean of past story embeddings, half-life 5 trading days.
- L565: r1, r5, r20, r60: log total returns up to the last close, from adjusted-bar ratios.
- L566: vol20: standard deviation of daily returns over 20 days.
- L567: dvol_ratio: log of 5-day over 60-day average dollar volume, from raw bars.
- L569: Bars flagged incomplete count as missing for every feature built from volume, range or VWAP.
- L571: Target: log total return from day k's open to day k+1's open, minus that day's average across the 50 stocks.

## 9.7 The learner (L573-579)
- L575: Scale features using means and variances from lived rows only.
- L576: Ridge refit monthly from running sums over an expanding window; variants: averaged monthly coefficients and recency weighting.
- L577: Penalties from 10^-2 to 10^4, validated as in 9.5.
- L578: Compute in float64; fixed ordering; `PYTHONHASHSEED=0`; tests run with a single BLAS thread.
- L579: The monthly ridge is the batch learner and the live agent; River online models run on identical data in the dev years; `PREREG.md` decides whether that becomes a sealed hypothesis.

## 9.8 Portfolio and costs (L581-587)
- L583: Main version: long top 10, short bottom 10, equal-weighted, dollar-neutral, filled at the open.
- L584: Long-only version: hold top 10, compared with SPY and holding all 50 equally.
- L585: Holding period 1, 3 or 5 days, plus optional turnover band (keep a holding until it drops out of the top or bottom 15); dev variables, each a trial.
- L586: Costs: 5 bps per side on traded value (an assumption); report at 0, 5, 10 and 20 bps, before and after costs.
- L587: Delisted or acquired companies leave at the last available price; a failed company is a total loss with exit label -1.

## 9.9 Comparison runs (L589-598)
- L591-598: Same harness for: the live agent; sequential learners (dev years); frozen twins, one per year end, end-of-2019 twin pre-registered; price-only twin; shuffled-news placebo; long-short baselines (random ranking, 12-1 momentum, 5-day reversal); long-only baselines (SPY buy-and-hold, all 50 equally).

## 9.10 Metrics and the report (L600-610)
- L602: Daily rank IC (Spearman across the 50 stocks) by quarter with Newey-West t-stats; primary skill metric.
- L603: Frozen-twin gaps: paired daily IC differences by year after each snapshot.
- L604: H1 to H3 with Holm's correction, sealed years only.
- L605: Long-short and long-only: return, volatility, Sharpe before and after costs, maximum drawdown, turnover, beta, sector tilt.
- L606: Deflated Sharpe for the chosen dev version using the number of trials in `runs/trials.csv`.
- L607: Seed spread for the placebo and random ranking.
- L608-609: Regimes and shocks, and coefficient life: reported, not tested.
- L610: Charts: IC over time, frozen-twin gaps, equity curves against matched baselines, cost sensitivity.

## 9.11 Tests (L612-628)
- L616: Non-interference (property-based): for random days t inside the dev years, scrambling, shifting or deleting every record available after t leaves every position up to t identical and every prediction within 1e-12.
- L617: Planted leaks: a future return, a future headline, a scaler fitted on all data, a stock list made with future data, a vendor bar timestamp as close time; each must make a test fail.
- L618: Label embargo: every training row's label was realized before the decision that used it.
- L619: Availability rules: each source's rule holds, including `updated_at` plus 15-minute news delay, early closes and daylight-saving changes.
- L620: Timestamp anchors: Benzinga's "Pre-Market", "Mid-Day" and "After-Hours" headlines land in their windows.
- L621: Vintage rule: every story was read by a model from an earlier year.
- L622: Survivorship audit: every S&P 500 member on each January has bars or is a listed known gap.
- L623: Identity: no two entities share a return series; every symbol maps to exactly one entity on each date.
- L624: Large moves: every one-day move above 25% in a listed stock has been reviewed.
- L625: Import boundary: `agent` imports nothing except `world.view`.
- L626: Reverse import boundary: `world`, `sim` and `eval` import nothing from `agent`.
- L627: Trading days: decision days equal the trading days in the price data; no decisions on holidays.
- L628: Seal: the runner refuses sealed dates without a matching `seal.lock` (settings, `PREREG.md`, commit) and a clean git tree.

## 9.12 The seal (L630-635)
- L632: `seal.lock` records the settings hash, the `PREREG.md` hash and the git commit.
- L633: The runner refuses any sealed-year date unless all three match and the working tree is clean.
- L634: One sealed run; a second needs an explicit flag and is logged as another trial.
- L635: The feature list is part of the seal.

## 9.13 Rough sizes (L637-645)
- L639: Price bars (measured): 787 plan rows, 719 companies, 1,574 files, 179 MB on 7 Nov; first download about 10 minutes.
- L640: News (measured): 2,260,406 stories Jan 2015 to Oct 2026 (2,243,739 Benzinga's), 251 MB, about 4.5 hours.
- L641: Trading list: 50 stocks x about 2,700 trading days is about 135,000 stock-days.
- L642: Embeddings 3 KB per story, about 1.5 GB for 500,745 headlines; processed a year at a time inside 7.8 GB RAM. Measured (M2): 502,712 rows, 1.48 GB of Parquet and 1.54 GB of arrays.
- L643: Vintages 2014 to 2024: 11 models at about 600 MB, roughly 6.6 GB, downloaded wherever the reader runs.
- L644: Headlines median 21 tokens; at 6 to 7 a second, 500,745 take about 21 hours. Measured (M2): 22.6 a second, 6 hours 12 minutes for 502,712.
- L645: Ridge fits are small; a full Track A replay should take minutes.

## Sources (L647-718)
- L649-718: Reference list only (time-locked models, leakage evidence, agents and benchmarks, return predictability, Alpaca docs and forum posts, other data, methods and compute). Not digested line by line.

## OPEN items stated by PLAN
- OPEN: L18: reader compute (laptop or cloud GPU) is picked in M2. L374 now records the choice: the laptop (M2, decision 1).
- OPEN: L304, L579: `PREREG.md` decides whether the batch-versus-sequential comparison becomes a sealed hypothesis.
- OPEN: L351: hypotheses H1 to H3 are drafts, finalized in `PREREG.md`.
- OPEN: L96, L387: DatedGPT public weights not confirmed.
- OPEN: L158, L384: S&P 500 list coverage and gaps to be checked.
- OPEN: L165: Kaggle quota is from third-party reports, own docs not checked.
- OPEN: L223: SEC filing availability rule is uncertain.
- OPEN: L519: story 12016835 stamp is unexplained.
