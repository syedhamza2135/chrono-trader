# M2 kickoff (8 Nov 2026)

Read this first when M2 starts. It says where things stand, what M2 has to deliver, what was measured, the decisions
the owner approved, and the build order. This session measured and proposed only. Nothing in M2 is built yet.

**The owner approved all six decisions on 8 Nov**, as written below: the laptop, the stories from 2016 on (2015 left
out), the download of the 10 vintages (about 6.0 GB to `D:\chrono-data\hf`), the job's shape, the cutoff check and
the build order. At the owner's request the download ran the same day, before the build, and all 11 vintages match
their pins ("The download", at the end). The rest of the build starts after a fresh 5-hour window.

## Where things stand

- **M1 is built, reviewed twice and fixed** on the branch `claude/m1-kickoff-832c2d` (commits `b2b9441`, `c9c09cf`,
  `87bacdc`), open as PR #1 and not merged. Master is still `7b4a200`.
- **M2 starts from M1's tip.** This note is on the branch `claude/awesome-panini-89f869`, in the worktree
  `.claude\worktrees\awesome-panini-89f869`, fast-forwarded to `87bacdc`. Nothing is committed.
- **New files, uncommitted:** this note, `research/m2_counts.py` (which stories, counts only) and
  `research/bench_reader.py` (speed, value ranges and a masked-word loss pilot on real headlines). Neither script
  prints a headline.
- **The event store** is in `D:\chrono-data\store`. Its embeddings table doesn't exist yet, so the vintage test in
  `tests/test_suites.py` skips.
- **M1's open questions stay open** and M2 doesn't need them: failed-bank exits, never trading without an official
  open, and the deferred history rewrite of the old commits' trailer.

## What M2 has to deliver

PLAN 9.2: every filtered story is embedded by the right vintage, and the cutoff check passes, or a failing vintage is
replaced. The pieces:
1. **The reader job** (PLAN 5.2). Each story's headline is read by the vintage from the year before its New York
   publication year, capped at 2024 (`reader/vintage.py`). Two embeddings per story, 768 float16 values each: the
   mean of the last layer, and the mean over all layers.
2. **The embeddings table** (PLAN 9.4): `story_id`, `vintage_year`, `emb_last`, `emb_avg`, in
   `D:\chrono-data\store\embeddings.parquet`. The vintage test runs on it as soon as it exists.
3. **The cutoff check** (PLAN 5.2): masked-word loss by vintage on headlines from V-1 to V+2, and named-event probes.

## Measured on 8 Nov

### Which stories (`research/m2_counts.py`)

The store's `story_entities` holds 534,619 stories (559,526 story-company pairs). A view shows a pair only when
`world.world.known_from` allows it: inside a membership or up to 14 days after one, or up to 400 days before one
(then from the membership's start). By New York year:

| Year | Vintage by the rule | In `story_entities` | A view can show it | Never shown |
|---|---|---|---|---|
| 2015 | 2014 | 31,907 | 31,907 | 0 |
| 2016 | 2015 | 33,251 | 33,251 | 0 |
| 2017 | 2016 | 23,910 | 23,845 | 65 |
| 2018 | 2017 | 27,013 | 26,906 | 107 |
| 2019 | 2018 | 28,807 | 28,320 | 487 |
| 2020 | 2019 | 36,455 | 36,102 | 353 |
| 2021 | 2020 | 47,607 | 47,396 | 211 |
| 2022 | 2021 | 58,380 | 58,280 | 100 |
| 2023 | 2022 | 65,544 | 65,414 | 130 |
| 2024 | 2023 | 65,110 | 64,950 | 160 |
| 2025 | 2024 | 63,553 | 63,382 | 171 |
| 2026 | 2024 | 53,082 | 53,030 | 52 |
| Total | | 534,619 | 532,783 | 1,836 |

- **PLAN's 500,745.** PLAN counts stories about a company that is a member on the story's New York date, 2016 to
  2026. The store has 500,313 of those, 432 fewer. The store drops stories edited more than 3 days after publishing,
  and the audit's count (`data_pipeline/audit_news.py`) applies no edit rule, which likely explains the gap. It was
  not checked story by story. By period, the store's counts are within 0.1% of `reference/split.json`: 33,246 in the
  warm-up (33,291 there), 78,990 in the dev years (79,000) and 387,419 in the sealed years (387,796).
- **From 2016 on, a view can show 500,876 stories:** those 500,313, plus 563 shown only from a join or after an
  exit. Over all years, 576 visible pairs fall outside a membership: 489 dated up to 400 days before one, and 87 up
  to 14 days after one.
- **2015.** All 31,907 stories from 2015 are about members on their day, and every view from 2016 shows them. Track
  A never uses them: prices start on 2016-01-04, the first pick is on 2016-04-01, and the news memory's half-life is
  5 trading days.
- 646 of the stories a view can show are dated 29 Oct 2026, after the store's last session (28 Oct).
- **Headline length** (all 534,619, one tokenizer for every vintage): a median of 22 tokens with [CLS] and [SEP]
  (21 to 23 by year), 44 at the 95th percentile, 62 at the 99th, 176 at most. 4,349 headlines are longer than 64
  tokens and 25 longer than 128.

### The vintages (Hugging Face's API, read on 8 Nov)

`manelalab` publishes 26 ChronoBERT vintages, 1999 to 2024. There is no 2025 vintage. The 11 that PLAN 9.13 lists
are public, MIT-licensed and not gated, and each was last changed on 2025-06-10:

| Vintage | Repository | Commit (main) | SHA-256 of `model.safetensors` (start) |
|---|---|---|---|
| 2014 | `manelalab/chrono-bert-v1-20141231` | `9e61adb8d667` | `11d99c1098caa09c` |
| 2015 | `manelalab/chrono-bert-v1-20151231` | `01122aa3fd7a` | `c48ea00d9018171c` |
| 2016 | `manelalab/chrono-bert-v1-20161231` | `89dff1bb2043` | `4a34990efc2c4680` |
| 2017 | `manelalab/chrono-bert-v1-20171231` | `02bde7f9d3d8` | `0ccb6691d8f94b07` |
| 2018 | `manelalab/chrono-bert-v1-20181231` | `e716596f5c90` | `a25d806efe68fcba` |
| 2019 | `manelalab/chrono-bert-v1-20191231` | `33a5fc6e8791` | `88eb7915c5ebb810` |
| 2020 | `manelalab/chrono-bert-v1-20201231` | `8402477b6b77` | `c99991a6ca24d571` |
| 2021 | `manelalab/chrono-bert-v1-20211231` | `2d187f3f29b1` | `258d0752c82f10a3` |
| 2022 | `manelalab/chrono-bert-v1-20221231` | `58bdf9ce273a` | `8905ece0120a4a06` |
| 2023 | `manelalab/chrono-bert-v1-20231231` | `d1cbfa139a61` | `8da109a3cbc8f152` |
| 2024 | `manelalab/chrono-bert-v1-20241231` | `2478c3bd4a67` | `f884da52bdb99020` |

- **Files.** Each vintage's `model.safetensors` is 598,635,032 bytes, about 602 MB with its small files. The other
  six files (config, tokenizer, special tokens, tokenizer config, model card and `.gitattributes`) are byte-identical
  across the 11, so one tokenizer serves every vintage.
- **What the model card says.** The first model is trained on text from before 2000. It is then updated each year
  from 2000 to 2024, with 65 billion more tokens in all, so each vintage is the one before it trained on one more
  year. The checkpoint is a `ModernBertForMaskedLM`, so the masked-word loss needs nothing more.
- **On D: now:** only the 2015 vintage, at commit `01122aa` (the current main), in `D:\chrono-data\hf` (575 MiB).
  Its weights' SHA-256 matches Hugging Face's in full.
- **To download:** the other 10, about 6.0 GB. D: has 67 GB free and C: 9.5 GB. In October the 2015 vintage's 599
  MB took about 5 minutes (the cache's file times), so the 10 should take under an hour at that rate.

### The laptop (`research/bench_reader.py`)

1,000 headlines drawn at random from 2016 on (a mean of 24.3 tokens, against 23.8 for all of them), the 2015
vintage, both poolings, transformers 5.22 and torch 2.15 on the CPU, `sdpa` attention, a 128-token cap. Other apps
were open: 2.4 GB of the 7.8 GB was free before the run.

| Order | Batch | Threads | Headlines a second |
|---|---|---|---|
| As drawn | 64 | 4 | 4.9 |
| Sorted by length | 64 | 4 | 10.0 |
| Sorted by length | 256 | 4 | 7.5 |
| Sorted by length | 64 | 8 | 7.7 |

- **Sorting by length doubles the speed**, since a batch is no longer padded to its longest headline. PLAN's 6 to 7
  a second (30 Oct) came from early-January 2016 headlines in the order they arrived, cut at 64 tokens.
- **At 10 a second**, the 502,712 headlines of decision 2 take about 14 hours. In random order they would take
  about 28 hours. A run of many hours may be slower if the laptop throttles (not measured).
- **Memory.** The peak working set was 2.8 GB with all 534,619 headlines loaded and tokenized at once, plus one
  model, and 3.5 GB after the batch-256 run.
- **Batch order changes an embedding only by float32 rounding:** at most 9.5e-6 in `emb_last` and 1.7e-3 in
  `emb_avg`, whose values reach about 640. So tests must compare with a tolerance, not exactly.
- **Float16 holds both poolings** (`bench_reader.py ranges`, 256 headlines from 2016 on). `emb_last` reaches 26.9 in
  absolute value. `emb_avg` reaches 638.5 (313.8 at the 99.9th percentile), because some values in layers 9 to 21 are
  large: their token means reach 413 to 1,999. All of it is far below float16's largest value, 65,504, and every
  value stays finite in float16.
- **Parquet holds float16 vectors.** pyarrow 26 writes and reads `fixed_size_list<halffloat, 768>` exactly (a check
  on 5,000 synthetic rows, 1,458 bytes a vector on disk against 1,536 raw). So the table is about 1.5 GB (502,712
  stories at 3,072 bytes raw, an estimate for real values).
- **The masked-word loss pilot** (the 2015 vintage, 300 headlines a year, 15% of each headline's tokens masked):
  4.175 on 2015 headlines (standard error 0.160), 4.281 on 2016 (0.134) and 4.341 on 2017 (0.142), at 6.0 to 10.4
  headlines a second. The rise is within the noise for one vintage alone, and each year's own difficulty is mixed
  in. That is why the check compares vintages on the same headlines (decision 5). How noisy those paired
  differences are needs a second vintage, so it isn't measured yet.

### Cloud GPUs (read on 8 Nov)

- **Modal** (modal.com/pricing): a T4 costs $0.000164 a second ($0.59 an hour), an L4 $0.000222 ($0.80) and an A10
  $0.000306 ($1.10). The Starter plan is $0 a month plus compute, with $30 of free credit a month.
- **Kaggle** (kaggle.com/docs/efficient-gpu-usage): free P100 GPUs, with a weekly GPU quota of 30 hours, sometimes
  more depending on demand.
- **Neither was measured for this job.** Both need an account, which is the owner's step, and both mean sending
  Benzinga's headlines to a third party.

## Decisions (the owner approved all six on 8 Nov)

### 1. Where the reader runs: the laptop

- About 14 hours for the headlines at the measured 10 a second, plus 1 to 2 hours for the cutoff check. The job runs
  vintage by vintage and resumes after any stop, so it can run over a few nights.
- It needs no new account and no token, and no licensed headline leaves the laptop. The forward test (M5) will read
  each day's news on a CPU with the same code.
- A cloud GPU would be much faster (not measured), but it sends the headlines to Modal or Kaggle. AGENTS.md's
  licensing rule covers git and public repos, not this, so it is the owner's call.
- **Fallback:** Modal, if the first vintage runs much slower than measured, or if the owner wants it sooner.

### 2. Which stories: every story in `story_entities` from 2016 on, 502,712

- That is the 500,876 a view can show, and 1,836 it never shows. Those few are kept so the set doesn't depend on the
  views' rules.
- **2015's 31,907 stories are left out.** Track A doesn't use them (above), and the 2014 vintage that would read them
  can't get the loss check, because the store has no 2014 headlines. `reader/vintage.py` moves `FIRST` to 2015, so a
  2015 story can't be embedded. For M3: news features start on 2016-01-01, and a feature that meets a story with no
  embedding stops with an error.
- By vintage: 2015 reads 33,251, 2016 reads 23,910, 2017 reads 27,013, 2018 reads 28,807, 2019 reads 36,455, 2020
  reads 47,607, 2021 reads 58,380, 2022 reads 65,544, 2023 reads 65,110, and 2024 reads 116,635 (2025 and 2026).

### 3. The vintages: all 11, pinned, on D:

- 2015 to 2024 read the news. 2014 serves only the cutoff check, as the 2015 vintage's predecessor.
- A new `reader/vintages.json` holds each vintage's repository, commit and SHA-256 (the table above, in full). The
  job loads a vintage only at its pinned commit, from `D:\chrono-data\hf` and offline, and stops if the weights'
  SHA-256 differs.
- **The download:** for each of the 10 vintages other than 2015, `model.safetensors` (598,635,032 bytes) and four
  small files (`config.json`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`), from the
  repositories above on huggingface.co, at the pinned commits, with `HF_HOME` set to `D:\chrono-data\hf`. About 6.0
  GB in all. The owner approved this download on 8 Nov.
- The weights are safetensors, so loading them runs no code, and nothing needs `trust_remote_code`.

### 4. The job's shape

- `python -m reader.embed`, a pipeline job that may see the whole store, like `data_pipeline`. It takes each story's
  vintage only from `reader.vintage.vintage_for`.
- **One vintage at a time, oldest first.** For each, its stories in `story_id` order, cut into parts of 5,000. Each
  part is sorted by token count, read in batches of 64 on 4 threads (the fastest measured), and written as
  `D:\chrono-data\reader\v{vintage}\part-{n}.parquet` under a temporary name, then renamed. A restart skips finished
  parts, so a stop loses at most one part (about 8 minutes).
- **The poolings, as measured:** `emb_last` is the mean over the headline's tokens ([CLS] and [SEP] included, padding
  left out) of the last layer's output, after ModernBERT's final norm. `emb_avg` is the mean over the 22 layers'
  outputs of the same token mean (`hidden_states[1:]` in transformers 5.22, whose last entry is the final output).
  Both are cast to float16, which holds them.
- **No truncation in practice:** a cap of 256 tokens, above the longest headline (176). Sorting puts the long ones
  together, so they cost little.
- **Finish** (`python -m reader.embed --finish`): write `D:\chrono-data\store\embeddings.parquet` one part at a time,
  so it never holds the 1.5 GB table in memory. Columns: `story_id`, `vintage_year`, and `emb_last` and `emb_avg` as
  `fixed_size_list<halffloat, 768>`. Beside it, `embeddings.json` records each vintage's repository, commit and
  SHA-256, the library versions, the poolings, the cap, and the count and a hash of the story set it covers.
- **Memory:** one model, and at most one vintage's headlines (116,635 for 2024). The benchmark peaked at 2.8 GB with
  every headline loaded at once.
- **Tests**, on synthetic data unless named: the vintage comes only from the rule; a story's embedding doesn't depend
  on its batch (within a tolerance); padding stays out of the means; a stop and a restart give the same table as one
  run; the float16 round trip. On the real table: the existing vintage test (`breaches`), and a new completeness
  test: every `story_entities` story from 2016 on has exactly one row, and no other story has one. A store rebuild
  leaves `embeddings.parquet` in place, so this test also catches a table gone stale.

### 5. The cutoff check

- **The sample.** N headlines per New York year from 2015 to 2026, drawn once with a fixed seed from
  `story_entities`. Each headline gets fixed masks: 15% of its tokens other than [CLS] and [SEP], at least one,
  chosen from its `story_id`. Every vintage sees the same headlines with the same masks. Write L(v, y) for vintage
  v's mean masked-word loss on year y's sample.
- **The gain.** G(v, y) = L(v-1, y) - L(v, y): how much vintage v beats the vintage before it on year y.
- **Check A, against the next vintage.** For the vintage V that reads year V+1: G(V+1, V+1) - G(V+1, V) > 0. The next
  vintage was trained on year V+1, so it should gain more there than on year V. If V already knew year V+1, the two
  gains would be equal. It runs for V from 2015 to 2023.
- **Check B, against the vintage before.** G(V, V) - G(V, V+1) > 0. V should gain over its predecessor more on its
  own year than on the year it reads. It runs for V from 2015 to 2024. The 2024 vintage has no successor, so B is its
  only loss check.
- Both checks use differences on the same headlines, so a year's difficulty and a vintage's general quality cancel.
- **A pass.** A vintage passes when each of its checks has a 95% interval above zero, from a bootstrap over the
  headlines (10,000 resamples). When check A passes for V, the same numbers show that a rule off by one year (year
  V+1 read by vintage V+1) would have been caught.
- **Power.** A leak shrinks these differences, but so would a yearly update too small to measure. So the report
  gives each vintage's gain on its own year. If those gains can't be told from zero, the check is reported as too
  weak to pass anything, not as a pass.
- **The cost.** 41 (vintage, year) cells, PLAN's V-1 to V+2 for each vintage, inside 2015 to 2026. At N = 1,000 that
  is 41,000 passes through a model, 1.1 to 1.9 hours at the measured 6 to 10 a second. A pilot with the 2015 and
  2016 vintages on 2015 to 2017 measures the paired spread and sets N first.
- **Named-event probes.** About two sentences per year from 2015 to 2025, written into `reader/probes.csv` and frozen
  before any probe runs. Each masks a word that no vintage before the event could know, best a new name: Alphabet as
  Google's parent (August 2015), COVID (2020), ChatGPT (November 2022), Leo XIV as the pope's name (May 2025). PLAN's
  example Brexit is a 2012 word, so its probe must ask for the June 2016 result instead. The score is the answer's
  log-probability against a few fixed wrong answers. For an event in year E, the vintages before E should score like
  the oldest ones, and one that scores like the vintages after E is flagged.
- **What fails a vintage:** a failed loss check. A probe flag alone doesn't, because one sentence is a crude test,
  but it gets a closer look and the owner decides.
- **Replacement.** A failing vintage V is replaced by the newest earlier vintage that passes, so year V+1's news is
  read by an older model. `reader/vintage.py` gets the replacement, and its test checks it.
- **The sealed years.** The check reads headlines from 2020 to 2026 as text only. It reads no price, return or label,
  so it says nothing about trading results.
- Results go to `research/audit/cutoff.md`, as numbers only.

### 6. The build order, and agents

The cutoff check runs before the long reader run, so that a replaced vintage never costs a second run. Each step comes
with its tests:
1. `reader/vintages.json` and the download of the 10 vintages, each checked against its SHA-256. **Done on 8 Nov**
   ("The download", at the end), except a test for `reader/download.py`'s checks.
2. The cutoff check (`reader/cutoff.py`): the two-vintage pilot, then the full check (1 to 2 hours on the laptop).
   The owner reviews any failure or flag before step 4.
3. The reader job (`reader/embed.py`), tested on synthetic data.
4. The run, vintage by vintage: about 14 hours, over a few nights. The first vintage (33,251 headlines, about an
   hour) checks the speed estimate.
5. The finish: the table, `embeddings.json`, the tests on the real table, `research/audit/reader.md` (counts and
   timings only), and the PLAN (5.2, 9.3, 9.13) and README updates.
6. **One review agent**, after step 5, hunting for leaks in the reader and the cutoff check, with usage checked
   before and after. M1's two reviews took about 20% and 26% of a window. Then the fixes, and the owner decides on
   the commit.

The main session builds steps 1 to 5 in order, since each needs the one before.

## Running it inside the usage limits

- The 5-hour window was at 54% when this session started and at 72% when it stopped (other sessions may share
  the window). Start the build after a reset.
- Steps 1 to 3 and 5 are code. The downloads, the cutoff check and the reader run are mostly waiting, not usage.
- Run the long jobs in a terminal tab, so they don't depend on a session staying open, and keep the laptop awake.

## The owner's answers (8 Nov)

1. Decisions 1 to 6: approved as written, including the download of about 6.0 GB from Hugging Face to
   `D:\chrono-data\hf`.
2. Where the reader runs: the laptop.
3. 2015's 31,907 stories stay out of the embeddings, and the 2014 vintage serves only the cutoff check.
4. Then the owner asked to run the download now, before the build.

## The download (8 Nov)

- **New files, uncommitted:** `reader/vintages.json` (each vintage's repository, full commit, weights size and
  SHA-256, and the git object ids of the four small files, from Hugging Face's API) and `reader/download.py`.
- **What the script does:** it fetches each vintage at its pinned commit, only `model.safetensors` and the four small
  files, into `D:\chrono-data\hf`. Then it checks the weights by size and SHA-256, and the small files by their git
  object ids. A vintage already in the cache is checked, not fetched again. Run it with
  `python -I reader/download.py`.
- **Result:** 11 of 11 vintages match their pins, the 2015 one included. The 10 new ones took 47 minutes, about
  2.1 MB a second on average. The cache is 6,319 MiB, and D: has 61 GB free. C:'s free space didn't drop (11 GB
  after).
