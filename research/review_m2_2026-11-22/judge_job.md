# Judge: the embedding job (M2 review, 22 Nov 2026)

Question: is each story read by the right ChronoBERT vintage, with pinned weights, and is the embedding run
reproducible and resumable without silent gaps?

Scope: commit 3d1df9b, `git diff 7081fba..3d1df9b` for reader/embed.py, reader/vintage.py, reader/vintages.json and
tests/test_embed.py, plus the store and logs on D:. Read: docs/digests/m2_job.md, the J-4, J-5, J-6 and J3-3 lines of
docs/digests/m2_prior_findings.md, embed.py in full, vintage.py in full, cutoff.py:50-76 and 158-184,
download.py:35-56, transformers' modernbert and output_capturing code in the venv, the folder listing of
D:\chrono-data\reader and smoke_check.log. No headline text was printed. No file was changed outside this one and the
scratchpad.

Scripts (scratchpad, read-only, rerun with `D:\venvs\chrono-trader\Scripts\python.exe <script>` from the repo root):
- `check_job.py`: counts and hashes on the store, the manifests and the parts.
- `reembed.py`: re-reads 20 stories (2 per vintage, one of them a 1 January story where the vintage has one) with
  `E.load_model` and `E.embed_ids(batch=1)` and compares with embeddings.parquet.
Both are in C:\Users\syedh\AppData\Local\Temp\claude\166f9164ebdccd7e\9de82187-73a0-485c-b919-d5de64e3fe28\scratchpad\.

Verdict: yes for the table on disk. Every row has the vintage the rule names, the weights match the pins, every
selected story is in the table exactly once, and 20 re-read stories match to float16 rounding. The findings below are
gaps in what a restart or a later run (M5) would notice, not errors in the current table. None is high.

## Findings

### E-1 (medium): a restart or a later run under another library version mixes vectors silently
- Where: reader/embed.py:94-103 (`manifest`), 166-175 (`check_manifest`), 183-184 (skip a part because its file
  exists), 271-278 (versions recorded at `finish`, not at run time).
- Evidence: the manifest holds vintage, repo, commit, counts and id hashes only. It holds no cap, batch, tokenizer
  id, pooling, dtype, torch or transformers version, or code version. So a restart after an upgrade of transformers or
  an edit to `embed_ids` keeps the old parts and writes new ones under the new definition, and `check_manifest` passes.
  `finish` then records the versions that are installed at finish time. This matters because emb_avg depends on
  library behaviour, not on embed.py: transformers' `capture_outputs` replaces the last entry of `hidden_states` with
  `last_hidden_state` (site-packages/transformers/utils/output_capturing.py:296-305, `tie_last_hidden_states`
  defaults to True). `reembed.py` confirms 23 hidden states with the last one equal to `last_hidden_state` (after the
  final norm), so embed.py:129-130 averages 21 layer outputs before the final norm with 1 after it. A version that
  does not tie the last entry would give other emb_avg values with no error. The same holds for the M5 morning job,
  which reuses `embed_ids` (embed.py:28-29).
- Current table: not affected. run.log shows one pass with no restart (digest m2_job.md:93), and the re-read below
  matches.
- Fix: add cap, batch, pooling text, `tok` file ids, torch and transformers versions (and a hash of embed.py's
  `embed_ids` source) to the manifest so `check_manifest` refuses a mixed restart; assert them in the M5 job.

### E-2 (low): the tokenizer the run uses is never checked against the pins
- Where: reader/cutoff.py:180-183 (`tokenizer` loads from `snapshot(2014)` with no `problems` call); reader/embed.py:204.
- Evidence: `load_vintage(v)` checks the small files of vintage v's folder (cutoff.py:171-173), but the tokenizer
  comes from the 2014 folder, which `cmd_run` never checks. `reembed.py` ran `download.problems(snapshot(2014), pin)`
  and got an empty list, so today it matches.
- Fix: call `download.problems` on the 2014 folder inside `tokenizer()`, or load the tokenizer from the vintage
  folder just checked.

### E-3 (low): the manifest pins the commit, not the weights hash
- Where: reader/embed.py:100 (manifest `weights` holds repo and commit only); 277 (embeddings.json copies
  `weights_sha256` from `cutoff.PINS` at finish time).
- Evidence: the weights are checked by SHA-256 at load (download.py:46-49, cutoff.py:171-173), and the run stops on a
  mismatch before any part is written (embed.py:215 evaluates `load_model(v)` before `run_vintage`). But if
  vintages.json's `weights_sha256` were edited with the commit kept, a restart or `finish` would pass, and
  embeddings.json would record a hash no run verified. `finish` itself never re-hashes the weights. `check_job.py`:
  embeddings.json `vintages` equals vintages.json for all ten vintages, and every manifest's weights equal the pins.
- Fix: put `weights_bytes` and `weights_sha256` in the manifest's `weights`.

### E-4 (low): the New York year edge is right in code but tested by nothing
- Where: reader/vintage.py:15-18, reader/embed.py:64-66; tests/test_embed.py:40 draws hourly times, with no fixed
  edge case.
- Evidence: made-up frame (command in the section below): 2017-01-01 03:00 UTC (31 Dec 2016 in New York) gets 2015;
  2017-01-01 05:00 UTC gets 2016; 2016-01-01 04:59 UTC (2015 in New York) raises ValueError in `vintage_for` and is
  dropped by `select`; 2025 and 2026 get 2024. All as the rule says. But the real data never hits the edge either:
  `check_job.py` finds 0 rows whose UTC year differs from the New York year (no linked story after 18:00 New York on
  31 December), so a slip to UTC years would pass every test and every check on this table. A regression would leak:
  the vintage of year Y read a story it may have trained on.
- Fix: add a test with fixed times at 31 Dec 23:30 and 1 Jan 00:30 New York, and one 2015 story to `select`.

### E-5 (info): manifest.json is not written atomically
- Where: reader/embed.py:175.
- Evidence: `path.write_text` straight to the final name. A stop mid-write leaves cut-off JSON; the next run raises
  JSONDecodeError at embed.py:170. Loud, not silent, so no gap.
- Fix: write it with a temporary name and `os.replace`, as `write_atomic` does.

### E-6 (info): a rerun gives the same table only within float16 rounding, and threads are not recorded
- Where: reader/embed.py:115-130 (batches by token count, so a story's padding width depends on its neighbours);
  cutoff.py:68 and 176 (4 threads, not in embeddings.json).
- Evidence: `reembed.py` read each story alone against the table: emb_last max abs difference 0.0004 to 0.0071,
  emb_avg 0.018 to 0.125 (relative to the row's largest value 7e-5 to 4.5e-4, which is float16 rounding), cosine
  1.000000 for all 20. smoke_check.log shows another vintage gives differences of 0.63 to 0.69, so the match does
  identify the vintage. A rerun with the same code, PART and BATCH builds the same batches, so it should agree at
  this level; bit equality is not promised.
- Fix: record `THREADS` in embeddings.json and state the tolerance (for example cosine above 0.99999) as the
  reproduction test.

## Checked and found right
- Year rule: 0 rows break it (`check_job.py`, own merge and `V.breaches`); rows per vintage match run.log; New York
  created years 2016 to 2026; 139 rows created on 1 January all carry the previous year (capped at 2024).
- Story set: stories.parquet has 2239859 rows and 0 repeated ids. The selection rebuilt from the store has 502712
  ids, equal to embeddings.parquet's ids, each once, and equal to embeddings.json `rows`. 31907 linked stories before
  2016 are left out by design; 0 are dropped by `keep_story`; 0 linked ids lack a story row.
- `set_hash` recomputed equals `story_set_sha256`; `available_at` equals `rules.embedding(updated_at)` for every row.
- Every manifest equals `E.manifest(v, current selection)`; no extra or `.tmp` files in any v folder; part rows sum
  to 502712; every part's `vintage_year` equals its folder.
- Truncation: max n_tokens 176 across all parts, 0 at the cap of 256. The model loads as float32 (config says
  float32; `reembed.py` prints `torch.float32`). Padding is masked out of both poolings.
- Resume: parts are written under a temporary name and renamed (embed.py:159-163); `finish` reads every part by its
  expected name (a missing part raises), checks its ids and `available_at` against the current store (embed.py:254-261),
  and a changed story set or pin stops it (embed.py:253). Duplicate rows cannot pass this check, and the World also
  refuses them (world/world.py:195-196) and checks the vintage again (world/world.py:198-200).
- The story set hash is enough to name which stories went in and when each was last edited; with the per-vintage id
  hashes it also fixes which vintage read each. It does not cover the headline text (J-5, below).

Made-up frame for E-4:
```
from reader import vintage as V
V.vintage_for(pd.to_datetime(['2016-01-01 05:00','2017-01-01 03:00','2017-01-01 05:00','2025-06-01 12:00'], utc=True))
# -> 2015, 2015, 2016, 2024; '2016-01-01 04:59' UTC raises ValueError
```

## Earlier fixes

| Id | Holds? | Where |
|---|---|---|
| J-4 | Fix holds: manifests record repo and commit, checked on restart and finish; all ten match the pins today (but see E-3) | reader/embed.py:98-103, 166-175, 211, 253 |
| J-5 | Note holds: the hash still covers story_id and updated_at only | reader/embed.py:87-91 |
| J-6a | Note holds: 2015 stories raise, still no test (see E-4) | reader/vintage.py:17-18 |
| J-6b | Note holds: repeats still dropped, not refused; 0 repeats in the store today | reader/embed.py:63, world/world.py:111 |
| J-6c | Holds: reindex and get_indexer, no float cast | world/world.py:116-120 |
| J-6d | Note holds: L-P8 named in the docstring, equality check unchanged | reader/embed.py:28-29, world/world.py:201-204 |
| J-6e | Holds as a process gate | no code |
| J3-3 | Note holds: `perturb` still copies DataFrames only | eval/leaks.py:63 |
