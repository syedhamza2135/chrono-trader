# Research brief check (7 Nov 2026)

On 7 Nov 2026 the owner shared a research brief with proposed design updates and asked for it to be checked before
any of it was adopted. Four verifiers checked each factual claim against primary sources, and a skeptic reopened the
sources and tried to refute every verdict. The skeptic agreed with all of them, with small corrections that are
included below. The full reports are kept off git in `D:\chrono-data\review\brief_check.json`.

## The facts

| Claim in the brief | Verdict | What's true |
|---|---|---|
| ChronoBERT and ChronoGPT (He, Lv, Manela, Wu; arXiv 2502.21206) have yearly vintages from 1999 to 2024, the earliest cut off on 1999-12-31, with weights under `manelalab` | Mostly right | All correct, with 26 vintages per family. "Trained only on text available before its cutoff" is the authors' best effort: they warn that a misdated document, for example one digitized by OCR, can let later text in. That is one more reason for the reader's own cutoff check (PLAN 5.2) |
| An instruction-tuned version exists (arXiv 2510.11677) | Right | ChronoGPT-Instruct, with 26 yearly vintages from 1999 to 2024 |
| The v1 series is about 1.5B parameters. It suits signals and embeddings, not reasoning, and the instruct versions hallucinate and loop | Partly | ChronoGPT and its instruct version have about 1.55B parameters, but ChronoBERT has 149M. The instruct paper shows garbled and repeated answers and weak chat quality (a win rate of about 13% to 17% against a 1.8B chat model). It doesn't test hallucination, looping or reasoning, so those parts are the brief's inference |
| Kelly et al.'s point-in-time models have monthly checkpoints from 2013 to 2024 | Partly | 2013 to 2024 is right, so they don't cover 1999 to 2012. The abstract says monthly, but the paper's text and the released weights are yearly: one checkpoint each December, except November 2015. The paper names the Hugging Face account `Diamegs` as the home of its weights |
| No date-locked model exists before 1999 | Wrong | NoLBERT is one 109M-parameter encoder trained only on 1976 to 1995 text. StoriesLM has yearly BERT models from 1900 to 1963. Language models trained on older text stop in 1946 or earlier. None of them is a yearly ladder that can read 1980s or 1990s financial news, so 1999 is still the earliest start for reading news with vintages |
| Profit Mirage (2025): FinMem, FinAgent and TradingAgents mostly fail to beat random baselines after their model's knowledge cutoff | Partly | The paper (Li et al., arXiv 2510.07920) ran five agents (FinMem, FinAgent, QuantAgent, FinCON and TradingAgents), all on GPT-4o, on NASDAQ-100 stocks. From a 2021 period before GPT-4o's cutoff to a 2024 period after it, total return fell by 50% to 72% and the Sharpe ratio by 51% to 62%. The "random baseline" line appears in its introduction, but the paper shows no random-baseline run |
| In one multi-agent trading study, short-term reflective memory over past decisions made results worse | Partly | Heil, Pramov and Gong (a CLEF 2026 workshop paper): giving the portfolio manager a 5-day or 10-day memory of its recent decisions and hit rate made results worse on TSLA and on BTC from August 2024 to January 2026. It is one small study of one simple design, and the recency-bias explanation is the authors' guess |
| Agentic Time Machine (2026, Shanghai Jiao Tong) rebuilds the past web by filtering out content from after the cutoff | Mostly right | It wraps live web search in a model that blocks late or answer-revealing pages, so it filters today's web: pages deleted since then can't come back. It was tested only on 2026 questions, and no code release was found |
| Bench to the Future (2025) works the same way, and its coverage of 1999 to 2005 is thin | Wrong | It stores about 20,000 pages scraped for each question at the time the question was asked, for 299 questions from 2025. It has no pages from before 2025, and access goes through its makers, FutureSearch |
| Use first-release vintages from ALFRED, never revised series | Partly | Never use today's revised series. But the value known on day T is the latest vintage published by T (the FRED API's `vintage_dates`), which can already be a revision. The first release fits only a decision made at the moment of release |

## What the plan takes from the brief

**Adopted** (written into PLAN.md):
- **Batch against sequential learning.** Track A's live learner refits each month on every lived day, which makes it
  the brief's batch learner. The online variants become sequential learners, compared with it on identical data in
  the dev years. `PREREG.md` decides whether that comparison becomes a sealed hypothesis.
- **Memory as numbers, tested by ablation (Track B).** The journal agent keeps its beliefs as structured statistics,
  such as each signal's recent hit rate, alongside any text. It runs with no memory, a short memory and a long
  memory, because the one study found that a simple short memory made results worse. Track B is also compared with
  Track A's batch learner on the same days.
- **The environment stands alone.** `world`, `sim` and `eval` import nothing from `agent`, and an agent plugs in
  through one call: given the view at time t, return target positions. Track A, Track B and later experiments share
  it, and the harness and its leak tests could be released one day without the licensed data.
- **Frontier models never decide.** They can write code, tests and reports. They make no decision on a replayed day,
  and they write no lessons, priors, rubrics or features that carry what happened later.
- **More seeds.** Every random part (the shuffled-news placebo and the random-ranking baseline) runs with several
  seeds, and the report shows the spread.
- **More reporting.** Results by market regime and after big shocks, and how long learned coefficients keep
  working. These are reported, not tested.
- **A masking diagnostic.** The reader is rerun with company names and dates masked. With time-locked vintages, a
  change shows the signal leans on what the model knew about a company before its cutoff, which is allowed, so this
  is a diagnostic, not a leak test. The leak guarantees stay the vintage rule, the cutoff check and the
  non-interference tests.
- **Economic data as of day T.** When macro data is added, each decision sees the latest vintage published by that
  day.
- **Corrected facts.** The point-in-time models are yearly and their weights are named by the paper, the models
  from before 1999 are noted, and the cutoff caveat is added.

**Deferred:**
- **The brief's MVP: one market from 1999, learning from 1999 to 2010 and testing on 2011 to 2015, with little or no
  news.** It stays as a later long replay on the same environment, for example the S&P 500 index or EUR/USD with
  prices, FOMC statements and as-of economic data. It doesn't replace Track A now, for three reasons:
  - Track A's data for 2015 to 2026 is audited and ready.
  - Ranking 50 stocks every day gives far more statistical power than trading one market, and the brief itself
    calls its power low.
  - Track A reads real company news through time-locked models, which is what sets this project apart.
- **A rebuilt past web as a news source.** Neither tool covers 1999 to 2015.

**Not adopted:**
- "Results must not change when names and dates are masked" as a leak test. See the masking diagnostic above.
- "First-release vintages". See economic data above.
- "Frontier models may write lesson plans and grading rubrics up front". A lesson plan written today carries
  hindsight.

## Sources

- He, Lv, Manela, Wu. Chronologically Consistent Large Language Models. https://arxiv.org/abs/2502.21206
- ManelaLab models on Hugging Face. https://huggingface.co/api/models?author=manelalab&limit=200
- He, Lv, Manela, Wu. Instruction Tuning Chronologically Consistent Language Models. https://arxiv.org/abs/2510.11677
- Kelly, Malamud, Schwab, Xu. Scaling Point-in-Time Language Models. https://arxiv.org/abs/2607.11889 and the weights at https://huggingface.co/Diamegs
- Kakhbod, Li. NoLBERT. https://arxiv.org/abs/2509.01110 and https://huggingface.co/alikLab/NoLBERT
- Sarkar. StoriesLM. https://huggingface.co/StoriesLM
- Li, Zeng, Xing, Xu, Xu. Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents. https://arxiv.org/abs/2510.07920
- Heil, Pramov, Gong. On the Role of Tools in Agentic LLM-Based Trading Systems. https://ceur-ws.org/Vol-4283/paper196.pdf
- Chai et al. Agentic Time Machine as an Infrastructure for Future-Event Forecasting. https://arxiv.org/abs/2606.21013
- FutureSearch. Bench to the Future: A Pastcasting Benchmark for Forecasting Agents. https://arxiv.org/abs/2506.21558
- FRED API: real-time periods and vintages. https://fred.stlouisfed.org/docs/api/fred/realtime_period.html and https://fred.stlouisfed.org/docs/api/fred/series_observations.html
