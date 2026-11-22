# The reader: M2's embeddings table

22 Nov 2026 (New York). The run that read every story with its vintage, the table it wrote, and what it costs. Counts,
times and sizes only, never a headline. Each number names the file or command it comes from.

## What was read

- **Which stories.** Every story in `story_entities` from New York year 2016 on, kept by `rules.keep_story`
  (decision 2 in `research/m2_kickoff.md`). That is 502,712 stories. Source: `reader.embed.select`, the first line
  of `D:\chrono-data\reader\run.log`, and `embeddings.json` (`rows`).
- **Which vintage.** A story from New York year Y is read by the vintage trained to the end of Y-1, and 2025 and 2026
  by 2024 (`reader/vintage.py`). The 2014 vintage reads nothing; it serves only the cutoff check.
- **What each row holds.** `story_id`, `vintage_year`, `available_at` (the story's `updated_at` plus 15 minutes,
  `rules.embedding`), and two float16 vectors of 768 values: `emb_last` (the token mean of the last layer) and
  `emb_avg` (the mean over the 22 layers of the token mean). Source: the schema of `embeddings.parquet` and
  `embeddings.json` (`poolings`).

## Counts and timings

From `python research/reader_stats.py` (output saved in `D:\chrono-data\reader\stats.log`), which reads `run.log`,
each vintage's `manifest.json` and the store's files.

| Vintage | Stories | Parts | Headlines a second (mean, min, max) | Last part done (New York) |
|---|---|---|---|---|
| 2015 | 33,251 | 7 | 21.3, 20.0, 23.7 | 21 Nov 21:08 |
| 2016 | 23,910 | 5 | 22.8, 21.7, 23.5 | 21 Nov 21:25 |
| 2017 | 27,013 | 6 | 21.1, 20.3, 21.8 | 21 Nov 21:46 |
| 2018 | 28,807 | 6 | 21.4, 20.9, 22.1 | 21 Nov 22:09 |
| 2019 | 36,455 | 8 | 23.1, 22.0, 24.1 | 21 Nov 22:35 |
| 2020 | 47,607 | 10 | 24.5, 23.8, 26.7 | 21 Nov 23:08 |
| 2021 | 58,380 | 12 | 25.8, 24.2, 27.0 | 21 Nov 23:45 |
| 2022 | 65,544 | 14 | 23.5, 14.1, 26.2 | 22 Nov 00:32 |
| 2023 | 65,110 | 14 | 21.4, 18.6, 22.7 | 22 Nov 01:23 |
| 2024 | 116,635 | 24 | 21.4, 17.6, 23.6 | 22 Nov 02:53 |
| **All** | **502,712** | **106** | **22.6** | |

- Every vintage has all its parts, and each folder's rows equal its manifest's count. No `.tmp` file was left.
- The run started at 20:41 New York on 21 Nov (the creation time of `run.pid`) and ended at 02:53 on 22 Nov (the
  last write to `run.log`): 6 hours 12 minutes. The parts' own reading time adds up to 6.19 hours.
- That is under half the 14 hours planned. The plan's speed came from the smoke run (8.1 to 8.7 a second), which
  shared the laptop with other work. The slowest parts (14.1 in 2022, 17.6 in 2024) ran while the test suite did.
- The run ran once, with no stop or restart. `run.err` holds only the model-loading progress bars.

## The finish and the table

- `python -m reader.embed finish` checked every part's story ids and `available_at` against the current store,
  then wrote `D:\chrono-data\store\embeddings.parquet` (502,712 rows, 1,480,328,055 bytes) and `embeddings.json`
  (3,108 bytes then; 3,281 after the arrays step added its `arrays` entry, review finding D-1). The story set's
  SHA-256, a hash of each `story_id` with its `updated_at` (review finding L-P7), is `6e28201d...` both in the
  run's first log line and in `embeddings.json`.
- `embeddings.json` also records each vintage's pinned repo, commit and weights hash, the cap (256 tokens), the
  part size, and the versions (torch 2.15.0+cpu, transformers 5.22.0). Each vintage's `manifest.json` records the
  pinned repo and commit that read it (judge J-4).
- `python -m reader.embed arrays` wrote the vectors again as `embeddings_last.npy` and `embeddings_avg.npy`
  (772,165,760 bytes each), in the table's row order, and recorded their story ids' hash in `embeddings.json`.
  `World.load` maps them read-only (judge J-3; see below).

## Disk

All on D: (`D:\chrono-data`), from `research/reader_stats.py`:
- the run's parts, `reader\v2015` to `reader\v2024`: 1,480,941,174 bytes;
- the table: 1,480,328,055 bytes, and the two arrays: 1,544,331,520 bytes in all.
So M2 uses about 4.5 GB of D:. The parts duplicate the table and can go to the Recycle Bin once the owner is happy
with it; nothing has been removed.

## The time wall

- **Rows.** The World refuses the whole table if a row has no kept story, repeats a story, was read by a vintage
  other than the rule's, or stores an `available_at` other than its story's (review finding M-3). On the real
  table it finds nothing (`tests/test_embeddings_store.py`).
- **When a row shows.** When its story's first company link shows, never before its story, and never for a story
  with no link (judge J-1). So an embedding never tells of a company the view hides, such as EQT in its 2018 to
  2022 gap (`test_no_embedding_tells_of_eqts_rejoin_during_its_gap`).
- **Memory (judge J-3).** Held in memory, the vectors would take 1.5 GB in the World and up to as much again in each
  view, on a laptop with 7.8 GB. So `World.load` maps the two arrays read-only from D:, and a view gathers fresh
  copies of the rows visible at t. From `python research/world_memory.py` (output in
  `D:\chrono-data\reader\world_memory.log`), with the store's files already in the disk cache:

  | | Time | Process memory (peak) | Embeddings in the view | Their vectors |
  |---|---|---|---|---|
  | `World.load` | 17 s | 2.50 GB (2.88) | | |
  | View on 2016-12-30, the last warm-up session | 0.2 s | 2.63 GB (2.88) | 33,227 | 102 MB |
  | View on 2019-12-31, the last dev session | 0.6 s | 2.94 GB (3.10) | 112,309 | 345 MB |
  | View on 2026-10-28, the last sealed session | 10.2 s | 4.29 GB (5.01) | 499,809 | 1,535 MB |

  A first load, with a cold cache, took 50 s. The same script found the arrays equal to the Parquet table on its
  first, middle and last row groups, and the second judge compared all 502,712 rows. The dev years fit easily. A
  view late in the sealed years costs 10 seconds and 1.5 GB, so a run through all of them would be slow; M3 or M4
  should decide whether a view needs every past embedding or only a recent window.

## The vintage decision and its known limit

From `research/audit/cutoff.md`, sections 8.9 and 9. The owner accepted all 11 vintages as published on 21 Nov
("Accept, go on"). Only the 2016 vintage is supported by evidence: it passed the stronger probes, at the edge. The
other nine vintages that read news are too weak to judge: the probes could not tell whether they knew the year they
read, and none failing is not evidence that they are clean. The 2022 vintage's flag on probe q2023c was seen and
accepted. 2026, which the 2024 vintage also reads, was never checked. This is a known limit of M2.

## Two planned checks downstream

Plans only, with their warning rules fixed before any result (`research/audit/cutoff.md`, section 10):
1. **The older-vintage rerun.** Read every story again with the vintage one year older than the rule's, and rerun
   the M3 agent unchanged. A warning if the news effect with the older vintage is under half the rule's, and the
   paired daily IC difference is above zero at one-sided 5%. About 6 to 14 hours on the laptop, at this run's speed
   and the plan's; it starts only on the owner's word, after M3 has a result.
2. **The switch-day check.** In M3's evaluation, compare the news effect in each year's first 20 sessions with the
   rest of the year. A warning if the pooled difference is above zero at one-sided 5% (Newey-West), or if in at
   least half the years the first-20 mean is above the rest by more than two standard errors.

## The reviews

- First judge (22 Nov, Opus at high effort): no embedding before its story, no wrong-vintage row; one must-change,
  J-1, fixed. See `research/audit/embed_judge.md`.
- Second judge, on J-3 (22 Nov, Opus at high effort): no leak through the wall; a view holds only gathered copies
  of the rows visible at t, each with its own vector. One must-change, J3-1 (two tests used the old attribute
  names), and one should-change, J3-2 (arrays left from before a rewrite of the table could be served); both are
  fixed. See `research/audit/embed_judge.md`, "Second judge".
