# M2 kickoff (8 Nov 2026)

Read this first when M2 starts. It says where things stand, what M2 has to deliver, what was measured, the decisions
the owner approved, and the build order. This session measured and proposed only. Nothing in M2 is built yet.

**The owner approved all six decisions on 8 Nov**, as written below: the laptop, the stories from 2016 on (2015 left
out), the download of the 10 vintages (about 6.0 GB to `D:\chrono-data\hf`), the job's shape, the cutoff check and
the build order. At the owner's request the download ran the same day, before the build, and all 11 vintages match
their pins ("The download", at the end). The rest of the build starts after a fresh 5-hour window.

## Where things stand

- **M1 is built, reviewed twice and fixed**, and on master: commits `93d8f70`, `90ecb8a`, `658db1c` and `dd40a5f`
  (8 Nov), all ancestors of master (checked with `git merge-base --is-ancestor` on 22 Nov). GitHub shows PR #1
  closed, not merged, though all its commits are on master. These are the ids after the 8 Nov history rewrite; the
  old-to-new table is in `research/m1_kickoff.md`, section "Session 4".
- **M2 starts from M1's tip.** This note was first written on the branch `claude/awesome-panini-89f869`, in the
  worktree `.claude\worktrees\awesome-panini-89f869`, fast-forwarded to `658db1c`. On 21 Nov it was carried onto
  master `7081fba` by a cherry-pick (review finding L-P6, approved by the owner); the old branch is left as it was.
- **Committed:** this note, `research/m2_counts.py` (which stories, counts only) and `research/bench_reader.py`
  (speed, value ranges and a masked-word loss pilot on real headlines) in `e883e4c`; the cutoff check, the M-3 fix
  and the start of the run in `e53c114`. Neither script prints a headline.
- **The event store** is in `D:\chrono-data\store`. Its embeddings table was written on 22 Nov (step 4 below), so
  the vintage test in `tests/test_suites.py` now runs.
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
   The owner reviews any failure or flag before step 4. Results and the rules fixed before them:
   `research/audit/cutoff.md`. Review finding M-4 (`research/review_2026-11-21.md`): the check had no outcome for
   "too weak". Until the owner rules, each vintage ends as pass, fail or too weak by the rules in `cutoff.md`, and a
   failing or too-weak vintage is reported, not replaced; the replacement rule in section 5 waits for the owner's yes.
   (The skeptic's point stands too: a failing 2015 vintage has no replacement, since 2014 can never pass.)
   **Ran on 21 Nov** (`reader/cutoff.py`, N = 2,000 a year, 41 cells, 22 probes): no vintage passes. Nine fail and
   2020 is too weak. The losses are dominated by quality shifts across the whole vintage, which the checks can't
   tell from a leak, and four probes are flagged. Nothing is replaced; step 3 waits for the owner
   (`research/audit/cutoff.md`, section 6). The owner chose a redesign. Sizing it from the saved cells
   (`research/cutoff_design.py`, `cutoff.md` section 7) showed nothing under 10 hours can decide: check B's honest
   value is about zero, and check A needs about 23 hours and more 2017 headlines than exist. No new run.
   The owner then chose "Stronger probes": the cutoff is settled on 80 new named-event probes with equal token
   counts (`reader/probes2.csv`), by rules frozen, judged and fixed before any score (`cutoff.md` section 8). The
   loss check and the first 22 probes stay as the record and decide nothing. **Ran on 21 Nov:** no vintage fails,
   2016 passes, and the other nine are too weak, since only 7 of 72 probes were informative. One flag (q2023c on
   2022) is for the owner. Nothing is replaced; step 3 waits for the owner (`cutoff.md` section 8.10).
   **The owner accepted all 11 vintages as published on 21 Nov** ("Accept, go on"; `cutoff.md` section 9). **Known
   limit:** only the 2016 vintage is supported by evidence. The other nine that read news are too weak to judge, the
   q2023c flag on the 2022 vintage was seen and accepted, and 2026 was never checked. Any result that leans on the
   news must carry this limit.
   **Two planned checks** catch a leak downstream, written with their warnings before any result
   (`cutoff.md` section 10; plans only, nothing run): an older-vintage rerun after the main run (every story read
   again by the vintage one year older, about 14 more hours, started only on the owner's word), and a switch-day
   check in M3's evaluation (the news effect in each year's first 20 sessions against the rest of the year).
3. **Before the reader job (review finding M-3):** give each embedding row its story's visible time, and serve
   embeddings to agents only through `world.view.View`, so non-interference and the planted leaks cover news
   features. This is a plan gap, not a live defect: the table doesn't exist yet. Then the reader job
   (`reader/embed.py`), tested on synthetic data.
   **Done on 21 Nov.** The M-3 fix:
   - `world/rules.py`: `embedding(updated_at)`, the story's own time (its `updated_at` plus 15 minutes).
   - Every embedding row stores that time as `available_at`. `World(..., embeddings=...)` refuses the whole table
     if a row has no kept story, repeats a story, was read by a vintage other than the rule's, or stores an
     `available_at` other than its story's. The last check catches a row left stale by a later edit, at row level
     (L-P7).
   - A view shows an embedding only once its story is visible (`View.embeddings`: rows plus two arrays, copied, so
     nothing in a view reaches later rows).
   - `eval/leaks.py` perturbs late embeddings in all three modes, so non-interference covers news features.
   - Tests: `tests/test_embeddings_wall.py` (29; without the fix the module fails at once, since
     `rules.embedding` doesn't exist). It covers an honest agent that reads embeddings, a planted leak that reads
     the next day's, and a planted wrong rule caught by an independent check. Plus `tests/test_embed.py` (7) for
     the job, whose last test feeds the job's own rows to the World.
   - `reader/vintage.py`'s `FIRST` is now 2015, so a 2015 story can't be embedded (decision 2). M-4 needs nothing
     more here: the owner accepted the vintages, so nothing is replaced. L-P8: `select`, `embed_ids` and
     `part_table` work on any set of stories, for M5's morning job. L-P5 stays with step 5.
   **The smoke run** (`python -m reader.embed smoke 128`; check: `python research/check_smoke.py`, output in
   `D:\chrono-data\reader\smoke_check.log`). 256 stories, the first 128 of the 2015 and 2024 vintages, at 8.1 to
   8.7 headlines a second.
   - Every row's vintage and `available_at` match the rules, and the World's checks find nothing.
   - Every vector is finite. `emb_last` reaches 27.3 and `emb_avg` 740.5.
   - Token counts match a fresh tokenization.
   - The headlines read again one at a time differ from the batch by at most 0.0073 and 0.124: float16 rounding
     at those magnitudes.
   - Another vintage gives other vectors.
   - The 3 pairs of identical vectors are 3 pairs of stories with identical headlines.
   **The judge** (22 Nov, Opus at high effort, at 0% of the 5-hour window; `research/audit/embed_judge.md`). No
   embedding shows before its story, and no wrong-vintage row gets past the World. One must-change:
   - J-1. Timed by its story alone, an embedding reopened M1's rejoin leak. The job reads only stories that name a
     store company, so an embedded story with no visible link names a hidden company. In a gap before a rejoin,
     that says the company rejoins. The judge counted 1,989 such stories in the store, about 6 companies (the
     same six as M1's review). Non-interference missed it (J-2). **Fixed:** an embedding now shows when its
     story's first company link shows, and never for a story with no link (`world/world.py`, `visible_at`).
     `eval/leaks.py` uses the same rule. In shift mode, a late embedding follows its story's time. Four new tests
     plant the judge's case: a world where E43 rejoins, against one where it never does. They show equal views,
     equal decisions for an agent that counts unlinked embeddings, and a gap story whose embedding stays hidden.
     All four fail under the old rule (checked by patching it back). Two tests that asserted the old behaviour
     now assert "embeddings equal the linked stories".
   - J-4. **Fixed before the run:** each vintage's `manifest.json` records the pinned weights (repo and commit), so
     a restart or a finish under other pins stops.
   - Open notes, for step 5: J-3 (`World.load` doesn't read `embeddings.parquet` yet), J-5 (an edit that keeps
     `updated_at` passes the set hash; optionally hash the headline bytes too), J-6 (a test for a refused 2015
     row; refuse repeated story ids; L-P8's later-of-two times for M5's job).
4. The run, vintage by vintage: about 14 hours, over a few nights. The first vintage (33,251 headlines, about an
   hour) checks the speed estimate.
   **Started at 20:41 New York on 21 Nov** (`python -m reader.embed run`, a detached process; log
   `D:\chrono-data\reader\run.log`, its pid in `run.pid`). The first four parts ran at 20.0 to 20.6 headlines a
   second, with the test suite running alongside, more than twice the smoke run's speed. At that speed the 502,712
   stories take about 7 hours, so it should end around 04:00 New York on 22 Nov. If it stops, the same command
   resumes at the first missing part. Then `python -m reader.embed finish`.
   **Done at 02:53 New York on 22 Nov**, about 6 hours 12 minutes. All 106 parts of the 10 vintages, 502,712 rows,
   each folder matching its manifest, no `.tmp` files left, no errors in `run.err`. **Finished on 22 Nov:**
   `store\embeddings.parquet` (502,712 rows, one per story, 1.48 GB) and `embeddings.json` (story set SHA-256
   `6e28201d...`, pins, poolings and versions). The World's checks on the table against the kept stories find
   nothing.
5. The finish: the table, `embeddings.json`, the tests on the real table, `research/audit/reader.md` (counts and
   timings only), and the PLAN (5.2, 9.3, 9.13) and README updates. Review finding L-P5: the PLAN updates also cover
   L167, L364, L434 and L548, which are stale after M2's decisions (2015 news left out, the 2014 vintage for the
   cutoff check only, 14 hours not 21). Review finding L-P7: the completeness test checks story ids only, so
   `embeddings.json` records a hash of `story_id` with `updated_at`, and the test compares it, to catch a story
   whose text changed.
   **Done on 22 Nov.** J-3: `World.load` reads the table when the store has it. The vectors are in two `.npy`
   arrays (`python -m reader.embed arrays`, also run by `finish`) that the World maps read-only, since they don't
   fit in memory twice, and a view gathers fresh copies of the visible rows. Tests on the real table
   (`tests/test_embeddings_store.py`): one row per selected story, the story set's hash, the vintage for each year,
   the availability time, the J-1 link rule on real views, EQT's gap, and the vectors a view serves. The vintage
   test in `tests/test_suites.py` now runs. A second judge (Opus, high effort) found no leak, one must-change (J3-1,
   two stale tests) and one should-change (J3-2, arrays left from before a rewrite of the table), both fixed
   (`research/audit/embed_judge.md`). Counts, timings, disk and memory: `research/audit/reader.md`. PLAN and README
   updated. The L-P7 hash is compared by the real-table test; J-5's headline hash stays an option.
6. **One review agent**, after step 5, hunting for leaks in the reader and the cutoff check, with usage checked
   before and after. M1's two reviews took about 20% and 26% of a window. Then the fixes, and the owner decides on
   the commit.

The main session builds steps 1 to 5 in order, since each needs the one before.

For M5, not M2 (review finding L-P8): M2 has no way to embed one morning's new stories for the forward test. M5
needs a small job that reads each new story with the vintage the rule names, before the morning's decision.

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
