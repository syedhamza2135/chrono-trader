# checker_docs: M2 review, mechanical checks (22 Nov 2026, commit 3d1df9b)

Counts, dates, symbols and hashes only. No headline or price text was read or printed. No code or data was changed.
Scratch scripts: `C:\Users\syedh\AppData\Local\Temp\claude\166f9164ebdccd7e\9de82187-73a0-485c-b919-d5de64e3fe28\scratchpad\checker\`
(`c1.py` store and run checks, `c2.py` probe report, `c3.py` full array compare). Python is
`D:\venvs\chrono-trader\Scripts\python.exe`. `.env` was not read.

Totals: part 1 has 57 MATCH, 5 MISMATCH (the `embeddings.json` size and four load or view times), 1 UNVERIFIED
cause, 2 NOT RUN (cold-cache load, tests). Part 2 has 29 MATCH, 1 split result (cutoff.py hash: MATCH on disk,
MISMATCH in git) and 1 NOT RUN (the Fitch fact from memory). Part 3 has no rule break.

## Part 1. research/audit/reader.md

Commands used (C1 to C8):
- C1 `python research/reader_stats.py` (rerun; diffed against `D:\chrono-data\reader\stats.log`: identical except the size of `embeddings.json`)
- C2 `c1.py`: runs `reader.embed.select` on `stories.parquet` and `story_entities.parquet` (no headline column read), reads only `story_id`, `vintage_year`, `available_at` from `embeddings.parquet`, reads the `.npy` headers, the manifests and the part files' row counts
- C3 `c3.py`: all 502,712 rows of `embeddings.parquet` against both `.npy` files
- C4 `python research/world_memory.py` (rerun, about 3 minutes)
- C5 `D:\chrono-data\reader\run.log`, `run.err`, `smoke.log` read with grep and counts
- C6 `membership.parquet` and `identity.parquet`, symbol EQT
- C7 hidden size and layers from the pinned `config.json` in `D:\chrono-data\hf`
- C8 `os.path` sizes and `Get-CimInstance Win32_ComputerSystem`

### 1a. What was read (lines 8 to 16)

| Line | Doc value | My value | Command | Result |
|---|---|---|---|---|
| 9 | 502,712 stories | 502,712 from `select()` and from the table | C2 | MATCH |
| 11 | `embeddings.json` rows = 502,712 | 502,712 | C2 | MATCH |
| 12-13 | NY year Y read by vintage Y-1; 2025 and 2026 by 2024 | cross-tab of NY year of `created_at` against `vintage_year`: 2016->2015 ... 2024->2023; 2025 (63,553) and 2026 (53,082) -> 2024; no other cell | C2 | MATCH |
| 13 | 2014 vintage reads nothing | no 2014 row in the table or in `reader\` | C2 | MATCH |
| 14-15 | columns story_id, vintage_year, available_at, emb_last, emb_avg; 768 values; float16 | same, `fixed_size_list<halffloat>[768]` (the saved parts also hold `n_tokens`, dropped at finish) | C2 | MATCH |
| 14 | available_at = updated_at + 15 min | difference is exactly 0:15:00 on all 502,712 rows, and equals `rules.embedding` | C2 | MATCH |
| 16 | 22 layers | `num_hidden_layers` 22, `hidden_size` 768 | C7 | MATCH |

### 1b. Counts and timings (lines 23 to 42)

| Line | Doc value | My value | Command | Result |
|---|---|---|---|---|
| 25 | 2015: 33,251 stories, 7 parts, 21.3 / 20.0 / 23.7, 21 Nov 21:08 | 33,251 (table and manifest), 7 part files, same speeds and time | C1, C2 | MATCH |
| 26 | 2016: 23,910, 5, 22.8 / 21.7 / 23.5, 21 Nov 21:25 | same | C1, C2 | MATCH |
| 27 | 2017: 27,013, 6, 21.1 / 20.3 / 21.8, 21 Nov 21:46 | same | C1, C2 | MATCH |
| 28 | 2018: 28,807, 6, 21.4 / 20.9 / 22.1, 21 Nov 22:09 | same | C1, C2 | MATCH |
| 29 | 2019: 36,455, 8, 23.1 / 22.0 / 24.1, 21 Nov 22:35 | same | C1, C2 | MATCH |
| 30 | 2020: 47,607, 10, 24.5 / 23.8 / 26.7, 21 Nov 23:08 | same | C1, C2 | MATCH |
| 31 | 2021: 58,380, 12, 25.8 / 24.2 / 27.0, 21 Nov 23:45 | same | C1, C2 | MATCH |
| 32 | 2022: 65,544, 14, 23.5 / 14.1 / 26.2, 22 Nov 00:32 | same | C1, C2 | MATCH |
| 33 | 2023: 65,110, 14, 21.4 / 18.6 / 22.7, 22 Nov 01:23 | same | C1, C2 | MATCH |
| 34 | 2024: 116,635, 24, 21.4 / 17.6 / 23.6, 22 Nov 02:53 | same | C1, C2 | MATCH |
| 35 | All: 502,712 stories, 106 parts, 22.6 a second | 502,712, 106 files (106 row groups in the table), 22.6 | C1, C2 | MATCH |
| 37 | every vintage has all its parts, rows equal manifest, no `.tmp` | parts on disk equal manifest parts for all 10; part rows sum to 502,712; `.tmp` count 0 | C1, C2 | MATCH |
| 38 | run started 20:41 NY 21 Nov (`run.pid`) | `run.pid` written 2026-11-22 06:41 +05:00 = 20:41 NY (UTC-5) | C5 | MATCH |
| 38 | ended 02:53 NY 22 Nov (last write to `run.log`) | `run.log` last write 12:53 +05:00 = 02:53 NY; last line "run finished" | C5 | MATCH |
| 38 | 6 h 12 min | 20:41 to 02:53 = 6 h 12 min | C5 | MATCH |
| 39 | reading time 6.19 hours | 6.19 | C1 | MATCH |
| 40 | under half the 14 hours planned | 6.19 or 6.2 h against 14 h (the 14 is in `m2_kickoff.md` lines 124, 156, 328) | C1, grep | MATCH |
| 40-41 | smoke run 8.1 to 8.7 a second | `smoke.log`: 8.7 (2015) and 8.1 (2024) | C5 | MATCH |
| 41 | slowest parts 14.1 (2022) and 17.6 (2024) | 14.1 and 17.6 are the lowest two speeds in `run.log` | C5 | MATCH |
| 41-42 | "ran while the test suite did" | not checkable from any log. Both are short last parts (544 and 1,635 headlines), where start-up lowers the rate; 2023 part 0 (18.6) and 2023's 110-headline tail (18.7) are also slow | C5 | UNVERIFIED (cause) |
| 42 | one run, no stop or restart | `run.log`: one first line, one "run finished", 106 part lines, no repeated vintage-part pair, 10 vintage lines | C5 | MATCH |
| 42 | `run.err` holds only model-loading progress bars | 20 pieces, all "Loading weights" bars (10 vintages, 137 weights each); no other text | C5 | MATCH |

### 1c. The finish and the table (lines 46 to 55)

| Line | Doc value | My value | Command | Result |
|---|---|---|---|---|
| 47 | `embeddings.parquet` 502,712 rows | 502,712 | C2 | MATCH |
| 47 | 1,480,328,055 bytes | 1,480,328,055 | C1, C8 | MATCH |
| 47-48 | `embeddings.json` 3,108 bytes | 3,281 bytes now (`embeddings.json` was rewritten at 14:33 +05:00 by `arrays`, which adds the `arrays` entry; `stats.log` was saved at 14:25 and shows 3,108). The doc's line 54-55 says the arrays were "recorded in `embeddings.json`", so the final file is 3,281 | C1 | MISMATCH (stale: 3,108 before `arrays`, 3,281 after) |
| 49 | story-set SHA-256 `6e28201d...` | `6e28201d6634ee065a9c5d3ce443c76b654fc3ac39d32c340e529ee147507d3c`, recomputed with `set_hash` over the current store; same in `run.log` line 1 and `embeddings.json` | C2, C5 | MATCH |
| 51 | cap 256 | `cap` 256 | C1 | MATCH |
| 51 | torch 2.15.0+cpu, transformers 5.22.0 | same | C1 | MATCH |
| 51 | each vintage's repo, commit and weights hash recorded | 10 vintages in `embeddings.json`, each with repo, commit, `weights_sha256`; commits equal `reader/vintages.json` and the manifests | C1, C2 | MATCH |
| 53-54 | arrays 772,165,760 bytes each | 772,165,760 and 772,165,760; shape (502712, 768), float16 | C2 | MATCH |
| 54-55 | ids hash recorded in `embeddings.json` | `arrays.ids_sha256` `0377c34e...` equals the hash I recompute from the table's `story_id`; the footer hash `61eefea5...` and size also equal | C2 | MATCH |

### 1d. Disk (lines 59 to 63)

| Line | Doc value | My value | Command | Result |
|---|---|---|---|---|
| 60 | parts `v2015` to `v2024`: 1,480,941,174 bytes | 1,480,941,174 | C1, C2 | MATCH |
| 61 | table 1,480,328,055 | 1,480,328,055 | C8 | MATCH |
| 61 | two arrays 1,544,331,520 in all | 2 x 772,165,760 = 1,544,331,520 | C8 | MATCH |
| 62 | about 4.5 GB of D: | 4,505,600,749 bytes = 4.5 GB (4.2 GiB) | C8 | MATCH |

### 1e. The time wall (lines 67 to 88)

| Line | Doc value | My value | Command | Result |
|---|---|---|---|---|
| 71-72 | EQT has a 2018 to 2022 gap | `membership.parquet`: entity 0000033213 (EQT) member 2008-12-19 to 2018-11-13, then from 2022-10-03 | C6 | MATCH |
| 74 | laptop with 7.8 GB | 7.78 GiB (8.36 GB) of RAM | C8 | MATCH |
| 74 | vectors take 1.5 GB in the World | 2 x 772 MB = 1.54 GB | C8 | MATCH |
| 80 | `World.load` 17 s | 31 s | C4 | MISMATCH (load dependent; the doc's was a warm run, and the laptop was in use) |
| 80 | `World.load` memory 2.50 GB (peak 2.88) | 2.52 (2.90) | C4 | MATCH (within 0.02 GB) |
| 81 | view 2016-12-30: 0.2 s | 0.8 s | C4 | MISMATCH (load dependent) |
| 81 | view 2016-12-30: 2.63 GB (2.88) | 2.65 (2.90) | C4 | MATCH (within 0.02 GB) |
| 81 | 33,227 embeddings, 102 MB | 33,227; 102,073,344 bytes | C4 | MATCH |
| 82 | view 2019-12-31: 0.6 s | 3.2 s | C4 | MISMATCH (load dependent) |
| 82 | view 2019-12-31: 2.94 GB (3.10) | 2.96 (3.12) | C4 | MATCH (within 0.02 GB) |
| 82 | 112,309 embeddings, 345 MB | 112,309; 345,013,248 bytes | C4 | MATCH |
| 83 | view 2026-10-28: 10.2 s | 23.1 s | C4 | MISMATCH (load dependent) |
| 83 | view 2026-10-28: 4.29 GB (5.01) | 4.31 (5.03) | C4 | MATCH (within 0.02 GB) |
| 83 | 499,809 embeddings, 1,535 MB | 499,809; 1,535,413,248 bytes | C4 | MATCH |
| 85 | first, middle, last row groups equal the arrays | True (106 row groups) | C4 | MATCH |
| 85-86 | second judge compared all 502,712 rows | I compared all 502,712 rows, both vectors: equal | C3 | MATCH |
| 85 | cold-cache first load took 50 s | needs a cold disk cache; not reproducible now | none | NOT RUN |
| 87-88 | "10 seconds and 1.5 GB" late in the sealed years | 23.1 s and 1.54 GB on my run; the 10 s is the doc's own number, see the timing rows above | C4 | covered above |

The four timing rows are counted as MISMATCH only because the printed values differ. Everything else in the run
(counts, bytes, memory within 0.02 GB) matches. The timings depend on the cache and the load on the laptop (my run
was about 2 to 5 times slower). The doc does say "with the store's files already in the disk cache".

### 1f. Vintage decision, planned checks, reviews (lines 92 to 116)

| Line | Doc value | My value | Command | Result |
|---|---|---|---|---|
| 92-93 | 11 vintages accepted | `reader/vintages.json` lists 2014 to 2024 = 11 | grep | MATCH |
| 95 | "other nine vintages that read news" | the table holds 10 vintages that read news (2015 to 2024); 10 minus 2016 = 9 | C2 | MATCH |
| 96 | 2022 flag on q2023c | flag list in section 2 (`report.json`) | see 2 | MATCH |
| 104 | rerun "about 6 to 14 hours" | 502,712 / 22.6 a second = 6.18 h at this run's speed; 14 h is the plan's (`cutoff.md` 10.1, line 766) | C1, grep | MATCH |
| 105-108 | "under half", one-sided 5%, first 20 sessions, two standard errors, Newey-West | the same words are in `cutoff.md` section 10 (lines 759 to 794) | grep | MATCH |
| 111-116 | judge findings J-1, J3-1, J3-2; tests pass | not a number; `tests/` were not run (brief) | none | NOT RUN |

## Part 2. research/audit/cutoff.md section 8.9 (lines 603 to 734)

Method. `python -m reader.cutoff report-probes2` reads `probes2\scores.json` and `scores.parquet` and `probes2.csv`,
then **overwrites `probes2\report.json`**. To change no data I did not run that command. `c2.py` imports
`reader.cutoff` and calls the same functions on the same saved scores, printing to my scratch folder. No model ran.
I diffed the output against the doc and against the saved `D:\chrono-data\reader\cutoff\report_probes2.md`.

| Line | Doc value | My value | Result |
|---|---|---|---|
| 606-607 | scores: 880 rows, 80 probes, 11 vintages | 880, 80, 11 | MATCH |
| 610 | T = 1.631 | 1.631224835... (`report.json` equal to the digit) | MATCH |
| 611 | q = 0.097 (7 of 72) | 0.0972222 = 7/72; the 7 informative probes are q2016b, q2017c, q2017e, q2017f, q2021e, q2023b, q2023c | MATCH |
| 611 | 72 probes of 2016 to 2024 | 72 (8 a year, 9 years); 8 more for 2025 | MATCH |
| 615 | 2015: 8 probes, 1 informative, no flags, later q2018b, too weak | same | MATCH |
| 616 | 2016: 8, 3, flag q2017f, later q2018b q2019e, pass | same | MATCH |
| 617 | 2017: 8, 0, none, later q2019e q2024g, too weak | same | MATCH |
| 618 | 2018: 8, 0, none, none, too weak | same | MATCH |
| 619 | 2019: 8, 0, none, none, too weak | same | MATCH |
| 620 | 2020: 8, 1, none, none, too weak | same | MATCH |
| 621 | 2021: 8, 0, none, none, too weak | same | MATCH |
| 622 | 2022: 8, 2, flag q2023c, none, too weak | same | MATCH |
| 623 | 2023: 8, 0, none, none, too weak | same | MATCH |
| 624 | 2024: 0.292 (3 usable), none, too weak | 0.292 = q x 3 (usable: q2025b, q2025f, q2025g) | MATCH |
| 626 | "no vintage fails, 2016 passes, the other nine too weak" | outcomes: 0 fail, 1 pass (2016), 9 too weak | MATCH |
| 630-632 | Maria q2017c -8.79 at 2016, -3.14 at 2017 | -8.79, -3.14 | MATCH |
| 631 | Harvey q2017e -12.07 at 2016, -0.50 at 2017 | -12.07, -0.50 | MATCH |
| 631-632 | Bard q2023b -6.96 at 2022, -3.21 at 2023 | -6.96, -3.21 | MATCH |
| 632 | Colonial q2021e -5.82 at 2020, -3.44 at 2021 | -5.82, -3.44 | MATCH |
| 633-634 | only 7 of 72 informative (list of 7) | the same 7 | MATCH |
| 634-635 | 9 probes where every score is above log(1/5) = -1.61: q2018e q2018g q2019g q2020c q2020d q2022d q2022f q2023h q2025c | the same 9 | MATCH |
| 636 | 18 probes where no vintage scores above -3 | 18 (q2016g q2017g q2018d q2020f q2021b q2021c q2021d q2021g q2021h q2022a q2022c q2023c q2023d q2023e q2024c q2024d q2024f q2024g) | MATCH |
| 638-640 | Equifax q2017f flags 2016 at -4.92, lo -7.10, hi -3.10; 2014 to 2017 -8.23, -5.98, -4.92, -4.99 | the same | MATCH |
| 640-641 | Fitch q2023c: -6.23 at 2021, -3.07 at 2022, -3.24 at 2023, -3.76 at 2024 | the same | MATCH |
| 641 | "Bard scores -6.96 at 2022" | -6.96 | MATCH |
| 641-643 | Fitch rating watch May 2023, cut August "(from memory, not checked)" | not checkable from the store; the doc marks it unchecked | NOT RUN |
| 644-646 | later-year flags: q2018b on 2015 and 2016, scores -8.06, -4.76, -2.76; q2019e on 2016 and 2017; q2024g on 2017 | table of later flags: 2015 q2018b; 2016 q2018b, q2019e; 2017 q2019e, q2024g; scores the same | MATCH |
| 654-733 | full score table: 80 rows x (11 scores, lo, hi, informative, flag) | all 80 rows identical, byte for byte, to my output and to `report_probes2.md` | MATCH (80 rows, counted as one) |
| 598 | `reader/probes2.csv` SHA-256 `eed31d91...5bd` | git blob at 3d1df9b: `eed31d911b049213de6d53f71a0f56a2b38618183e3fc9bf0936d6305c1bd5bd`; disk: the same; `scores.json` (at the run): the same | MATCH |
| 599 | `reader/cutoff.py` SHA-256 `8bae55f5...3b` | disk: `8bae55f5b4ecc5a499e2bab767c27de273f85b2cc8322da9af7dc41c3e153b3e` (equals the doc and `scores.json`). git blob at 3d1df9b (`git show 3d1df9b:reader/cutoff.py \| sha256sum`): `7004534124287875504bd044498c0d36696d3adbc3ffb3ece99c32b1418336ce` | MATCH on disk, MISMATCH in git (see below) |
| 608 | "same hashes at the run and at the report" | `report_probes2.md` header: probes2.csv unchanged; cutoff.py at the run equals now | MATCH |

The cutoff.py hash difference. The disk file has CRLF line endings (`git ls-files --eol`: index `i/lf`, working tree
`w/crlf`, `core.autocrlf=true`). With the CRs removed the disk file hashes to the git value, and the git text with
CRs added hashes to `8bae55f5`. So the doc's hash is the hash of the CRLF checkout on this laptop. Anyone who checks
`reader/cutoff.py` out with LF (another machine, or a clone without autocrlf) or hashes the git blob gets
`70045341...`, not the doc's hash. `.gitattributes` protects only `reader/*.csv` (`-text`), which is why `probes2.csv`
is the same in git and on disk. Only commit e53c114 ever touched `reader/cutoff.py`, so the file did not change after
the freeze; the issue is only that the recorded hash is not reproducible from git bytes.

## Part 3. Style and licensing

Scope: the 34 files in `git diff --name-only 7081fba..3d1df9b`, read as stored at 3d1df9b.

### 3a. Em-dashes (U+2014)

| Files | Em-dashes |
|---|---|
| all 34 files in the diff (listed in the diff: `.gitattributes`, `AGENTS.md`, `PLAN.md`, `README.md`, `eval/leaks.py`, 5 `reader/*.py`, `reader/probes.csv`, `reader/probes2.csv`, `reader/vintages.json`, 5 `research/audit/*.md`, 8 `research/*.py`, `research/m2_kickoff.md`, 5 `tests/*.py`, 3 `world/*.py`) | 0 in every file; total 0 |

Side note, not a rule: 10 en-dashes (U+2013), all inside names of Wikipedia articles ("2015–16", "Russia–Saudi
Arabia", "North Korea–United States", "Will Smith–Chris Rock"): `research/audit/cutoff.md` lines 364, 381, 395, 396,
415 and `reader/probes2.csv` lines 4, 21, 35, 36, 55. They copy article titles, so I do not count them as a break.

### 3b. Raw news text or prices in git

| Check | Result |
|---|---|
| `reader/probes.csv` columns | probe_id, event_year, event_month, sentence, answer, wrong, source; 22 rows |
| `reader/probes2.csv` columns | probe_id, event_date, sentence, answer, wrong, source; 80 rows |
| Longest `sentence` | 115 characters (`probes.csv`), 107 characters (`probes2.csv`), at most 19 words; every sentence holds a `{}` blank |
| Other longest fields | `wrong` 39 and 55 characters (four wrong answers joined with `\|`), `source` 78 and 89 characters (a Wikipedia article title), `answer` 13 and 19 |
| What they are | short, self-written one-sentence statements of a public event with the answer blanked, plus a Wikipedia title as source. Not full headlines and not article body text. No Dow Jones or other news-feed column |
| Doc scan, 7 changed docs plus README and PLAN, for quoted strings of 9 words or more | one hit: `cutoff.md` line 591, a probe sentence we wrote ("Sales figures showed that {} had overtaken Bud Light"). No quoted headline |
| Code scan, same test over `.py` files | hits are only docstrings and format strings |
| Tracked CSVs at HEAD (19) | headers hold ids, symbols, dates, counts and derived ratios. Only `reference/price_events.csv` carries prices (open, high, low, close, volume, vwap), which is the allowed exception. `research/audit/adjustment_events.csv` and `large_moves.csv` hold returns (`r_raw`, `r_adj`, `ret`), not prices. None has a headline or body column. These audit CSVs are older than 7081fba and not in the diff |

### 3c. .gitattributes and tracked data

| Check | Result |
|---|---|
| `.gitattributes` covers `reader/*.csv` | yes: `reader/*.csv -text`; `git check-attr` shows `text: unset` for `probes.csv`, `probes2.csv` and a hypothetical `reader/new.csv`. It does not cover `reader/cutoff.py` (see part 2) |
| Data files tracked (parquet, npy, npz, pkl, feather, h5, zip, gz, safetensors, bin, db) | none (230 tracked files) |
| Large files | none above 200 KB at HEAD. The largest tracked CSV is `reference/identity.csv` at 76,433 bytes |

## MISMATCH and rule breaks

| Where | What |
|---|---|
| `research/audit/reader.md:47-48` | `embeddings.json` is said to be 3,108 bytes. It is 3,281 bytes now, after `python -m reader.embed arrays` added the `arrays` entry (14:33 on 22 Nov, after `stats.log` was saved at 14:25). The doc's own line 54-55 describes that entry. Fix: write 3,281 or drop the size |
| `research/audit/reader.md:80-83` | Load and view times (17 s, 0.2 s, 0.6 s, 10.2 s) did not reproduce: 31 s, 0.8 s, 3.2 s, 23.1 s on 22 Nov with the laptop in use. Memory and all counts reproduced. The timings are load dependent and the doc says "cache"; it is a note, not an error |
| `research/audit/reader.md:41-42` | "ran while the test suite did": no log supports it, and the two slowest parts are the short last parts of their vintages. Unverified |
| `research/audit/cutoff.md:599` | The `reader/cutoff.py` hash `8bae55f5...` is the hash of the CRLF checkout. The git blob hashes to `70045341...`. `.gitattributes` covers only `reader/*.csv`. Fix: add `reader/*.py -text` (and record the hash of the git blob), or say "CRLF checkout" in the doc |

Rule breaks (secrets, licensing, em-dashes, tracked data): none found.
