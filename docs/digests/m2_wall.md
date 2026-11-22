Source commit 3d1df9b, 22 Nov 2026. Digest of how embeddings reach an agent through the time wall.
Sources: world/rules.py, world/view.py, world/world.py, eval/leaks.py, reader/embed.py, tests/test_embeddings_wall.py, tests/test_embeddings_store.py. Line numbers are in the file named in each line.

## Availability time (world/rules.py)
- rules.py:6 Table row: an embedding is available at its story's `updated_at` plus 15 minutes. The row stores this as `available_at`. The World refuses a row whose time differs from its story's.
- rules.py:18 NEWS_DELAY is 15 minutes.
- rules.py:19 MAX_EDIT_LAG is 3 days. Stories edited later than this are dropped (rules.py:36-38 `keep_story`).
- rules.py:27-28 `story(updated_at)` is updated_at plus NEWS_DELAY, in UTC.
- rules.py:31-33 `embedding(updated_at)` returns `story(updated_at)`. Cites review finding M-3.
- rules.py:6 Reason given: the vintage that reads it was trained before the story's New York year, so the vector holds nothing the story did not.

## What a View holds and returns (world/view.py)
- view.py:3-4 A view holds copies of the visible records, no reference to the World, and no array that reaches later rows. Key columns are plain strings.
- view.py:79-81 `embeddings` is an `Embeddings`: `rows` (story_id, vintage_year, available_at), plus `last` and `avg`, two arrays with one row per row of `rows`. Empty when the World has none.
- view.py:82 Every table has `visible_at`, the time its row entered the views.
- view.py:91-101 `View.__init__` stores t, today, sessions (copy, up to today), members, joined, and the six tables including `embeddings`.
- world.py:158-169 `Embeddings` class is defined in world.py, not view.py, so the agent-facing module defines View only (tests/test_boundaries.py is named as the reason).
- world.py:163-166 `Embeddings.__init__` raises ValueError unless rows, last and avg have equal length.
- world.py:171-176 `Embeddings.empty(dim=0)`: empty rows with columns story_id, vintage_year, available_at, visible_at, and two zero-row float16 arrays.

## Does a view copy? Yes
- world.py:230-234 `_gather` allocates a new array and fills it with `np.take`.
- world.py:236-241 `_SortedEmbeddings.upto(ns)`: binary search on the sorted times (side right, so a row shows at exactly its time), then `rows.iloc[:k].copy(deep=True)` plus gathered copies of last and avg.
- world.py:155 `_Sorted.upto` for other tables: `.copy(deep=True)` of the prefix.
- world.py:13-14, 213-215 Docstrings say nothing in a view shares memory with the World's arrays.
- world.py:327-329 `World.view(t)` passes `self.embeddings.upto(ns)`, or `Embeddings.empty()` when the World has none.

## Load and the .npy arrays (world/world.py)
- world.py:332-341 `World.load(store, clock, allow_sealed, embeddings=True)` reads the Parquet tables. It loads embeddings only if `embeddings=True` and `embeddings.parquet` exists (J-3).
- world.py:256-277 `load_embeddings(store)`:
  - 261-262 reads `embeddings.json`, and from `embeddings.parquet` only the columns story_id, vintage_year, available_at.
  - 263-265 refuses if `arrays` is missing in the json or either .npy file is missing. The message says to run `python -m reader.embed arrays`.
  - 266 hashes the Parquet story ids (int64 bytes, SHA-256).
  - 267-268 maps `emb_last` and `emb_avg` .npy files read-only (`mmap_mode="r"`).
  - 269-270 refuses if the id hash differs from `arrays.ids_sha256`, or if the row counts of Parquet, last, avg and `arrays.rows` are not all equal.
  - 271-273 refuses if the Parquet file's size and footer SHA-256 differ from `arrays.parquet`.
  - 274-276 refuses unless both arrays are float16, 2-D, and with width equal to `arrays.dim`.
- world.py:244-253 `_parquet_footer(path)` returns file bytes and the SHA-256 of the footer. It mirrors `reader/embed.py` `parquet_footer` (embed.py:287-296).
- world.py:23 Docstring: the .npy files are mapped read-only from D: because they do not fit in memory twice (J-3).

## Checks that refuse a table (world/world.py)
- world.py:187-205 `embedding_problems(embeddings, stories)` returns a list of reasons. The World raises ValueError "the embeddings table is refused: ..." if the list is not empty (world.py:304-306).
- world.py:192-194 Unlinked-to-story rows: any row whose story_id is not among the kept stories gives "N rows have no kept story".
- world.py:195-196 Repeated rows: any duplicate story_id gives "N rows repeat a story".
- world.py:197-200 Wrong vintage: `reader.vintage.breaches` on the known rows gives "N rows were not read by the vintage the rule names".
- world.py:201-204 Stale or mistimed rows: `rules.embedding` of the story's updated_at is compared in nanoseconds with the row's `available_at`. Any difference gives "N rows store an available_at other than their story's". This catches a row left over from before its story was edited (L-P7), and a row timed by mistake.
- world.py:297-298 The kept stories (after `keep_story`) are what rows are checked against, so a story dropped for a late edit makes its row "no kept story".
- reader/vintage.py:22-29 `breaches` merges rows with story created_at (left join). It counts a missing story and any row whose vintage_year differs from `vintage_for(created_at)`.

## The "first link" rule (judge J-1)
- world.py:98-102 Docstring: an embedding shows when its story's first company link does. The job reads only stories that name a store company. An embedding seen before any link would tell the agent a hidden company is named. In a gap before a rejoin that says the company rejoins.
- world.py:110-120 `visible_at("embeddings", ...)`:
  - 111-112 per story: availability time from `rules.embedding(updated_at)`.
  - 113 keeps story_entities rows whose story is in the kept stories.
  - 114-115 takes each link's `visible_at` (the story_entities rule) and the minimum per story, the first link.
  - 116 the row's time is the later of the first link's time and the availability time.
  - 117-120 a row with no link and no entry gets NEVER (int64 max). An empty set gives NEVER for all.
- world.py:121-126 `story_entities` rule: later of the story's availability and `known_from` for the company on the story's New York created day.
- world.py:74-95 `known_from`: for a record of company c dated day d, the earliest time a view may show it (NEVER if not allowed). Inside a membership or up to HISTORY_AFTER (14 days) after: at the membership start. Up to HISTORY_BEFORE (400 days) before one: from that membership's start. Otherwise NEVER. (rules.py:20-24, world.py:1-11.)
- world.py:307-308 The embeddings table is sorted with `visible_at("embeddings", rows, spells, stories, se)` where `se` is the kept story_entities.

## Sorting and sealed years (world/world.py)
- world.py:213-228 `_SortedEmbeddings.__init__`: accepts an `Embeddings` or a DataFrame holding `emb_last` and `emb_avg` columns (`_vectors` stacks them into one new array). Keeps vectors in stored order, an `order` from a stable argsort of visible_at, and sorted rows with columns story_id, vintage_year (int64), available_at, visible_at.
- world.py:179-184 `_vectors(col)` returns one new 2-D array, with no row left as a view of a shared buffer.
- world.py:323-324 Views at or after the sealed start need `allow_sealed`, else PermissionError. (world.py:23-24: the runner sets it only after the seal holds, sim/seal.py.)
- world.py:318-322 `view(t)` needs a time zone, else ValueError.

## eval/leaks.py: what non_interference perturbs, and are embeddings covered? Yes
- leaks.py:1-13 The check: perturb every record not visible at t, run again, compare every decision up to t. Three ways: scramble, shift, delete. A planted leak must be caught by at least one.
- leaks.py:15-17 Embeddings: a late row is one whose story is late. Scramble swaps and scales the late vectors. Shift moves the late rows' available_at with their stories, and gives a row whose story moved into a new year that year's vintage. Delete drops them with their stories.
- leaks.py:30-32 HOW is scramble, shift, delete. SHIFT is 7 days. SIGNED columns (ret, label) get random sign flips.
- leaks.py:35-53 `late_rows` builds a mask per table: bars, labels, opens, stories, story_entities, joins, leaves. When `tables["embeddings"]` is present (50-52), it adds an embeddings mask using the world's own `visible_at("embeddings", ...)` greater than t.
- leaks.py:66-75 `scramble_vectors`: for late rows, permutes the vectors among them, then multiplies each by a random factor in 0.5 to 1.5. Applied to `emb_last` and `emb_avg` (leaks.py:121-122).
- leaks.py:95-96 delete: late embedding rows are dropped.
- leaks.py:104-111 shift: late embedding rows get `available_at` recomputed from their moved story (so it still equals the story's), and `vintage_year` recomputed with `vintage_for` of the moved created_at. A row late only through its links keeps its story's time (leaks.py:105-107).
- leaks.py:125-132 After scramble or shift, a late bars, labels or story_entities row that becomes visible is dropped. The embeddings table is not in this loop (its tuple is bars, labels, story_entities). Delete drops everything late at 92-98.
- leaks.py:136-148 `decisions_until` builds a World from `**tables`, so the embeddings go through the World's checks. The agent gets no World unless `give_world`.
- leaks.py:151-167 `compare`: rows in one run only, different positions, predictions apart by more than 1e-12 (NaN against number counts).
- leaks.py:170-179 `non_interference`: runs, perturbs, runs again, compares. Docstring 173-175: "not visible" comes from the wall's own rules, so a wrong rule passes this check. The rules have their own tests (L-T1).

## reader/embed.py: availability per row and the `arrays` command
- embed.py:6-9 Each row: story_id, vintage_year, available_at, n_tokens, emb_last, emb_avg. available_at is `rules.embedding` of updated_at at the time of reading (M-3).
- embed.py:58-68 `select`: every story in story_entities created in New York year 2016 or later and kept by `keep_story`; adds vintage_year (`V.vintage_for(created_at)`) and available_at (`rules.embedding(updated_at)`). Sorted by story_id.
- embed.py:141-156 `part_table`: writes available_at as UTC time, vintage_year as int16, n_tokens as int16, vectors as float16 fixed-size lists. Raises if a value is not finite in float16.
- embed.py:258-261 `finish` re-computes `rules.embedding(updated_at)` per part from the current stories and refuses ("a story changed after it was read") if any stored available_at differs.
- embed.py:284-337 `arrays` (`cmd_arrays`): reads `embeddings.parquet` one batch at a time, writes `embeddings_last.npy` and `embeddings_avg.npy` as float16, 768 wide, under temporary names, then renames. Records in `embeddings.json` under `arrays`: rows, ids_sha256, files, dim, dtype, parquet footer (bytes, footer_sha256).
- embed.py:316 uses `open_memmap`. embed.py:324-325 stops if the rows read differ from the row count.
- embed.py:299-306 `drop_arrays` removes the `arrays` entry before a vouched file is replaced.
- embed.py:269, 329 Both `finish` and `arrays` call `drop_arrays` first, so a stop between steps leaves no entry vouching for old arrays (J3-2).
- embed.py:287-296 `parquet_footer` is the same size-plus-footer hash that world.py checks.
- embed.py:281 `finish` calls `cmd_arrays` at its end.

## tests/test_embeddings_wall.py (made-up world from tests/synthetic.py, 5 sample days)
- :32 every row's available_at equals `rules.story` of its story's updated_at.
- :39 for each of 5 days, the set of embedded stories in a view equals the set of stories in its story_entities, they are a subset of its stories, visible_at is at most t, and the arrays have 8 columns and one row per row.
- :49 an embedding is absent one nanosecond before its story's time plus 15 minutes, and present at that time.
- :59 for three rows (first, middle, last) the view's last and avg vectors equal the source vectors for that story.
- :69 view arrays own their memory (`base is None`), share none with the World's arrays, and are shorter than the World's.
- :77 a World built without embeddings gives a view with zero embedding rows.
- :91 a row timed one hour before its story is refused (message names available_at).
- :98 a story edited 2 hours later after reading makes its old row stale and the World refuses (available_at).
- :105 a row with the wrong vintage (plus 1 year) is refused (vintage).
- :112 a row whose story was dropped for a 4-day edit lag is refused, and so is a row with a story_id that does not exist (both "no kept story").
- :124 a repeated story is refused ("repeat").
- :163 the honest news agent decides differently from the plain agent, so the leak checks test a reader of embeddings.
- :171 for each of scramble, shift, delete, `non_interference` with the news agent returns no differences.
- :177 for each of 3 methods and 2 days, the view at t from perturbed tables equals the original view (rows, last, avg), sorted by story_id.
- :187 the perturbation changes the late embeddings: delete leaves only visible rows. Shift moves available_at exactly for rows whose story is late, and no late story's embedding is in the view. Scramble changes more than 90 percent of late vectors.
- :212 the planted `FutureEmbedding` leak (reads the World's embeddings of the next day) is caught by at least one method.
- :229 on 5 days, no view holds an embedding whose story it does not show (independent of leaks.py).
- :233 a planted wrong wall (embeddings timed an hour before the story, no link gate) is caught by the independent check, over 2016-03-01 to 2016-06-30.
- :281 a World with company E43's rejoin and one without give views on 2016-12-30 with equal story_entities and equal embedding rows (rejoin not revealed).
- :297 an agent counting visible embeddings with no visible link decides the same in both worlds, 2016-10-03 to 2016-12-30.
- :304 a story linked only to E43 from its gap shows in stories on 2016-12-30 but its embedding does not.

## tests/test_embeddings_store.py (real store; skipped if no embeddings table; counts, ids and times only)
- :44 one row per selected story and no other: row counts of Parquet, selection, embeddings.json `rows` and `arrays.rows` are equal, ids unique, same id set.
- :50 `set_hash` of the current selection equals `story_set_sha256` in embeddings.json (L-P7).
- :55 every row's vintage equals `vintage_for(created_at)` and equals min(New York year minus 1, 2024). The vintages present are 2015 to 2024, and equal the keys of `vintages` in embeddings.json.
- :64 every row's available_at equals `rules.embedding` of its story's updated_at.
- :70 `World.load` has embeddings, the row count matches, and `_last` is shape (rows, 768) float16.
- :77 for 3 days (2016-06-30, 2018-03-01, 2019-12-31), the embeddings in a view are exactly the embedded stories among its linked ones, each visible and available by t, arrays have no base, and width 768 (J-1).
- :89 EQT (left 2018-11-13, rejoined 2022-10-03): embedded stories only linked to EQT from the gap are absent from the view on 2022-01-03 though the stories show, and present on 2022-10-03.
- :107 for 50 stories from the first row group, the view's last and avg equal the stored values.

## Not covered by this digest
- tests/test_boundaries.py and tests/test_leaks.py were not read (named in comments only).
