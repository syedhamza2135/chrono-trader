Source commit 3d1df9b, 22 Nov 2026. Digest of the embedding job.
Sources: reader/embed.py, reader/vintage.py, reader/vintages.json, reader/cutoff.py (pin checks only), reader/download.py (pin check), tests/test_embed.py, and in D:\chrono-data: store\embeddings.json, reader\run.log, reader\finish.log, reader\run.err, reader\v*\manifest.json. Line numbers are in the file named in each line.

## What the job is
- embed.py:1-4 Every story in story_entities from New York year 2016 on is read by the vintage the rule names, into two float16 vectors of 768 values. It is a pipeline job: it reads headlines as text only and never prints or saves one. It writes to D: only.
- embed.py:6-12 Each row: story_id, vintage_year, available_at, n_tokens, emb_last, emb_avg. Cap of 256 tokens, above the longest headline (176 per the docstring).
- embed.py:10-11 emb_last is the token mean of the last layer (after the final norm), [CLS] and [SEP] included, padding left out. emb_avg is the mean over the 22 layers of the same token mean.
- embed.py:28-29 For M5 (L-P8): `embed_ids` and `read_stories` work on any set of stories.
- embed.py:47-53 Constants: FIRST_YEAR 2016, PART 5000, BATCH 64, CAP 256, DIM 768. OUT is DATA_DIR/reader, STORE is DATA_DIR/store.

## Commands (embed.py:20-26, 348-361)
- `run` (cmd_run, embed.py:201-216, main 349-351): every vintage, resuming. Calls `stay_awake` first (embed.py:340-345, Windows SetThreadExecutionState, no setting changed).
- `smoke N` (embed.py:219-225): first N stories of each of the 2015 and 2024 vintages into DATA_DIR/reader/smoke. Stops if that folder is not empty.
- `finish` (embed.py:240-281): checks every part, writes embeddings.parquet and embeddings.json, then runs `arrays`.
- `arrays` (embed.py:308-337): writes the two .npy files from embeddings.parquet and records them in embeddings.json.
- Any other argument prints the docstring and returns 2 (embed.py:358-360).

## How each story picks its vintage
- embed.py:58-68 `select`: stories in story_entities, first copy of each story_id, New York year of created_at at least 2016, kept by `rules.keep_story`. Adds vintage_year from `V.vintage_for(created_at)` and available_at from `rules.embedding(updated_at)`. Sorted by story_id.
- vintage.py:1-5 Rule: the vintage from the year before the story was published, in New York time. The year comes from created_at, not from availability.
- vintage.py:8 FIRST 2015 and LAST 2024. The 2014 vintage reads no news and serves only the cutoff check.
- vintage.py:12-19 `vintage_for`: New York year of created_at minus 1, capped at 2024 (so 2025 and 2026 stories use 2024). Raises ValueError if any result is below 2015.
- vintage.py:22-29 `breaches`: rows whose vintage differs from the rule, and rows with no story.
- embed.py:206-207 `cmd_run` loops over the vintages found in the selection, oldest first, and takes each vintage's stories.

## How weights are pinned and checked
- vintages.json holds the pins. cutoff.py:76 loads it as PINS. embed.py:98 reads the pin for the vintage.
- cutoff.py:161-163 `snapshot(v)`: the pinned snapshot folder under DATA_DIR/hf/hub, named by repo and commit.
- cutoff.py:166-177 `load_vintage(v)`: runs `download.problems` on the folder against the pin. Any difference raises SystemExit. Then loads offline (cutoff.py:54-55 set HF_HOME and HF_HUB_OFFLINE), with 4 threads (cutoff.py:68, 176).
- download.py:40-56 `problems`: weights file must exist, match the pinned byte size, and match the SHA-256 (weights_bytes and weights_sha256). The four small files must match the shared git object ids in vintages.json `files`.
- embed.py:195-198 `load_model(v)` returns the encoder of the checked masked-word model, in eval mode.
- embed.py:94-103 `manifest` records the pinned repo and commit with the story-set counts (judge J-4).
- embed.py:166-175 `check_manifest`: writes manifest.json if absent. If one exists and differs from the one wanted, stops with SystemExit ("describes another story set"). Because the manifest holds the pin, a changed pin stops a restart or `finish` (embed.py:94-95 docstring).
- embed.py:253 `finish` calls `check_manifest` for each vintage, so a manifest written under other pins stops it.
- embed.py:277 embeddings.json records each vintage's pin from `cutoff.PINS`.

## reader/vintages.json fields (79 lines)
- Top level: `source` (Hugging Face API, read on 2026-11-08, see research/m2_kickoff.md), `weights` ("model.safetensors, checked by SHA-256"), `files` (four small files with git object ids: config.json, tokenizer.json, tokenizer_config.json, special_tokens_map.json), `files_note`, `vintages`.
- Each vintage has `repo`, `commit`, `weights_bytes` (598635032 for all), `weights_sha256`.
- Pinned revisions, one line per vintage (vintages.json line of the `commit` entry in brackets):
  - 2014: manelalab/chrono-bert-v1-20141231, commit 9e61adb8d6674d363f14d0d4a3153e4fea3ebefd [14]
  - 2015: manelalab/chrono-bert-v1-20151231, commit 01122aa3fd7a07879a524b6897c41e55c1db091a [20]
  - 2016: manelalab/chrono-bert-v1-20161231, commit 89dff1bb2043cc929c00756002469dfa9482f280 [26]
  - 2017: manelalab/chrono-bert-v1-20171231, commit 02bde7f9d3d8c55c1e44d7e3ee071f374a1b9bb4 [32]
  - 2018: manelalab/chrono-bert-v1-20181231, commit e716596f5c90945781e74e78ab90c591b9b46080 [38]
  - 2019: manelalab/chrono-bert-v1-20191231, commit 33a5fc6e87910b614cf4319eb995301195d9a99d [44]
  - 2020: manelalab/chrono-bert-v1-20201231, commit 8402477b6b77b799ee220665fcb258939eaf7455 [50]
  - 2021: manelalab/chrono-bert-v1-20211231, commit 2d187f3f29b1071392b546fa1195d6b55036ae9b [56]
  - 2022: manelalab/chrono-bert-v1-20221231, commit 58bdf9ce273a6744bf8c8acda2df56655e7f1f51 [62]
  - 2023: manelalab/chrono-bert-v1-20231231, commit d1cbfa139a61b067ce0089c12d93f196798ad6b1 [68]
  - 2024: manelalab/chrono-bert-v1-20241231, commit 2478c3bd4a676e2e7bdc72f8100262b39bde4b0d [74]
- The commits above equal the ones in embeddings.json for 2015 to 2024, and in the 2024 manifest.json.

## Batching and the model call
- embed.py:108-131 `embed_ids`: headlines sorted by token count (stable), read in batches of 64, padded with the pad id, attention 0 on padding. Calls the model with `output_hidden_states=True` under `inference_mode`. emb_last is the masked token mean of the last hidden state. emb_avg is the mean over layers 1 to 22 of the masked token mean (embed.py:129-130 skips the input layer). Returns float32 arrays in input order.
- embed.py:134-136 `encode`: tokenizer with truncation at 256.
- embed.py:141-156 `part_table`: casts to float16, raises ValueError if any value is not finite in float16, stores vintage_year as int16, n_tokens as int16.

## Parts, resume and merge
- embed.py:14-18, 78-80 A vintage's stories, in story_id order, are cut into parts of 5000.
- embed.py:178-192 `run_vintage`: check manifest, then for each part skip it if its file exists, else encode, embed, write atomically, log one line.
- embed.py:159-163 `write_atomic`: writes `part.parquet.tmp`, then `os.replace`. A stop loses at most one part (embed.py:16).
- embed.py:209-213 `cmd_run` on a vintage whose parts all exist re-checks the manifest and logs "all N parts done".
- embed.py:94-103 manifest.json: vintage, weights (repo and commit), count, part_size, ids_sha256, and per part n, count, first, last, ids_sha256.
- embed.py:83-84 `ids_hash`: SHA-256 of story ids as int64 bytes.
- embed.py:228-237 `read_part`: returns the other columns and two 2-D float16 arrays.

## What `finish` checks (embed.py:240-281)
- 245 Re-reads the store's current stories.
- 250-253 For each vintage: manifest must match the current selection and pins.
- 255-257 Each part's story ids must equal the expected ids, else SystemExit "holds other stories".
- 258-261 Each part's stored available_at must equal `rules.embedding` of the current updated_at, else SystemExit "a story changed after it was read".
- 262-265 Drops n_tokens, streams every part through one ParquetWriter to `embeddings.parquet.tmp`.
- 269 `drop_arrays(store)` before replacing the file (J3-2).
- 270 `os.replace` the tmp file into embeddings.parquet.
- 271-279 Writes embeddings.json: rows, story_set_sha256, first_year, cap, batch, part, poolings, vintages (pins), versions of torch and transformers.
- 281 Runs `cmd_arrays`.

## The story set hash (embed.py:87-91)
- `set_hash(story_ids, updated_at)`: SHA-256 over each story_id paired with its updated_at in nanoseconds (int64). Changes if a story's updated_at is edited (L-P7). Does not cover headline text (judge J-5, left as a note).
- cmd_run logs it first (embed.py:205). embeddings.json holds it as `story_set_sha256`.

## embeddings.json values (D:\chrono-data\store\embeddings.json, 86 lines)
- rows 502712. story_set_sha256 6e28201d (full value in the file). first_year 2016. cap 256. batch 64. part 5000.
- poolings: emb_last is "token mean of the last layer, after the final norm"; emb_avg is "mean over the 22 layers of the token mean".
- vintages: 2015 to 2024 (ten entries), each with repo, commit, weights_bytes 598635032 and weights_sha256 (shortened to 8 characters here): 2015 c48ea00d, 2016 4a34990e, 2017 0ccb6691, 2018 a25d806e, 2019 88eb7915, 2020 c99991a6, 2021 258d0752, 2022 8905ece0, 2023 8da109a3, 2024 f884da52.
- versions: torch 2.15.0+cpu, transformers 5.22.0.
- arrays: rows 502712, ids_sha256 0377c34e, files emb_last embeddings_last.npy and emb_avg embeddings_avg.npy, dim 768, dtype float16, parquet bytes 1480328055 with footer_sha256 61eefea5.

## Run and finish logs (D:\chrono-data\reader)
- run.log has 118 lines: 1 story-set line (502712 stories), 10 "vintage V: N stories in P parts" lines, 106 part lines, and the last line "run finished".
- Stories and parts per vintage: 2015 33251 in 7; 2016 23910 in 5; 2017 27013 in 6; 2018 28807 in 6; 2019 36455 in 8; 2020 47607 in 10; 2021 58380 in 12; 2022 65544 in 14; 2023 65110 in 14; 2024 116635 in 24. Parts sum to 106.
- No "all N parts done" line and no repeated vintage header, so the run did not restart. (reader.md:57 also says it ran once with no stop or restart.)
- Part speed in the 2024 vintage's tail lines runs from 17.6 to 23.6 headlines a second. The last part (part 23) holds 1635 headlines.
- First part log time is 21 Nov 20:46 New York. Last logged part is 22 Nov 02:53 New York (2024 part 23).
- Short status line quoted: "run finished".
- run.err is 3195 bytes, 10 lines, and holds only the model-loading progress bars ("Loading weights"). No error text was found in it. No .tmp file remains under D:\chrono-data\reader.
- finish.log has 1 line: "wrote D:\chrono-data\store\embeddings.parquet (502712 rows)". It has no line for the arrays step (the arrays entry is in embeddings.json, and it was written again per reader.md:60-61 and embed_judge.md:226).
- Folder v2024 holds manifest.json plus 24 part files (25 entries). Each v folder holds manifest.json plus its parts (v2015 8 entries, v2016 6, v2017 7, v2018 7, v2019 9, v2020 11, v2021 13, v2022 15, v2023 15, v2024 25).
- The v2024 manifest.json holds vintage 2024, the pinned repo and commit, count 116635, part_size 5000, ids_sha256 6c06bd25 and 24 parts.

## tests/test_embed.py (synthetic stories, tiny random ModernBERT, made-up tokenizer; no store, no real weights)
- :49 `select` keeps 2016 on, drops a story edited after 4 days, drops pre-2016 stories, unique and sorted ids, the rule's vintage and `rules.embedding` time.
- :64 an embedding does not depend on its batch (batch 8 against batch 1) and leaves padding out; both poolings match a direct model call.
- :78 a part round-trips in float16 and leaves no .tmp file. A value beyond float16 raises ValueError.
- :110 a run with half the parts deleted and one cut-off .tmp part restarts to the same rows as one run.
- :127 a restart on another story set stops with "another story set".
- :134 the job's own rows pass `embedding_problems` and feed a World whose view shows exactly the embedded stories among the linked ones (J-1).
- :145 the set hash changes when one story's updated_at moves by one second.
- :152 helper `_store_with_arrays` (not a test) builds a store folder and runs `cmd_arrays`.
- :169 the World's mapped path (read-only .npy maps) gives the same views as the DataFrame path, and view vectors are plain arrays with no base and no shared memory (J-3).
- :195 arrays with a wrong ids hash are refused ("other rows"), and with no `arrays` entry are refused ("missing").
- :210 a parquet rewritten over the same story ids with new vectors, with the old arrays entry, is refused ("another embeddings.parquet"). After `cmd_arrays` again it serves the new vectors (J3-2).
- :228 `drop_arrays` removes only the `arrays` entry from embeddings.json.

## Not found or not covered
- No separate log line for the `arrays` step exists in finish.log.
- The full-run hardware speed figures come from run.log lines only. research/reader_stats.py (its output is stats.log) was not digested beyond its first lines.
