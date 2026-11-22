# Judge: the embeddings time wall (review findings M-3, L-P7, L-P8, M-4)

22 Nov 2026. Worktree `reverent-sanderson-da34d6`, uncommitted changes against e883e4c. Opus judge, one narrow
question: can an agent see a story's embedding before the story, or an embedding from a vintage the rule does not
allow?

**Verdict: no on both counts as asked. But an embedding row reopens the M1 rejoin leak (PLAN L29): one must-change.**
No row is ever visible before its story, and no wrong-vintage row gets past the World. But a row's presence tells the
agent that its story names a store company, while the World hides that company's story links during a gap. So 1,989
real stories, about 6 companies in the gap before they rejoin, tell the agent the company rejoins later. These are
the same six companies as M1 review item 1: EQT, PCG, FSLR, KDP, ILMN and CHK. No leak test catches it.

Scripts (made-up frames, plus counts only from the store) are in the judge's scratchpad:
`C:\Users\syedh\AppData\Local\Temp\claude\cf84e2c349003aec\02716c9f-1496-493f-91dc-73ce9b15ce62\scratchpad\judge\`
(`rejoin_leak.py`, `edges.py`, `store_counts.py`). The named tests pass: `tests/test_embeddings_wall.py`,
`tests/test_embed.py` and `tests/test_boundaries.py`, 42 passed.

## J-1. An embedding's presence shows a rejoin early (must-change)

- Where: `world/world.py:104-107` times an embedding by its story alone. `reader/embed.py:55-65` (`select`) embeds
  every story in `story_entities`. `story_entities` holds only stories that name a store company (746 companies,
  all members at some time since 2015). The rows are gated by membership (`world/world.py:108-113`, `known_from`).
  The whole Benzinga feed is in `stories` (2,239,859 rows, against 534,619 stories with a company).
- So at time t, a visible story that has an embedding and no visible link names a store company whose links are
  hidden. In the gap before a rejoin, that means "this company rejoins later". `stories.n_companies` does not give
  this away: it counts a tag outside the identity table as one company (`data_pipeline/audit_news.py:41-60`).
- PLAN: L29 [digest 39]: "a view shows a company's records only near its memberships, so the agent cannot learn it
  joins or rejoins later". The World's own docstring says the same (`world/world.py:4-11`).
- Check 1, made-up frames (`rejoin_leak.py`). World A is `tests/synthetic.py` with 400 feed stories added that
  name no store company. World B is the same, except that E43 never rejoins. At 2016-12-30 the two views have equal
  bars, labels, stories, story_entities, members and joined. Only the embeddings differ: 1,969 rows against 1,951.
  In A, 18 embedded stories with no link name E43; in B, none do. A planted agent reads only the view and adds
  1e-6 times the count of unlinked embedded stories. It decides differently in A and B: 3,150 predictions differ.
  Non-interference passes it in all three modes (scramble, shift, delete: no differences).
- Check 2, the store (`store_counts.py`, counts only). 502,712 stories are selected for embedding. 2,314 have an
  embedding visible before any link. 1,989 of those name a company whose membership starts later. These are 6
  companies, each a rejoin: 33213, 895126, 1004980, 1110803, 1274494 and 1418135. They are visible in every year
  from 2017 to 2026 (65 to 487 a year). The rest (325) belong to past members long after they left. That is only
  history, not a leak.
- Test: none. `tests/test_embeddings_wall.py:38-44` and `tests/test_embed.py:142` assert the leaky property: every
  visible story has its embedding visible.
- Fix: in the `embeddings` branch of `visible_at`, take the max of the story's time and the earliest `visible_at`
  of its `story_entities` rows, and use NEVER for a story with no link. `late_rows` then perturbs these rows too.
  Add the A-against-B case above as a test.

## J-2. The leak checks cannot see J-1 (should-change; closed by J-1's fix)

- Where: `eval/leaks.py:50-51` marks an embedding late only when its story is late. Delete mode drops later joins
  (`eval/leaks.py:96-97`) and their links, but keeps the embeddings of those companies' stories. So the perturbed
  world is not the world in which the company never rejoins.
- Check: `rejoin_leak.py`, the three `non_interference` lines (all empty).
- Fix: none apart from J-1's. Once `visible_at` gates on links, `late_rows` follows. Then replace the
  "embeddings == stories" assertions (`tests/test_embeddings_wall.py:42`, `tests/test_embed.py:142`) with
  "embeddings == linked stories". The synthetic world needs feed stories that name no store company, or
  presence carries no signal there.

## J-3. The real table has no way into the World yet (note)

- Where: `World.load` (`world/world.py:265-273`) does not read `embeddings.parquet`. Until it does, the World's
  checks run only in tests, and `cmd_finish`'s output is never checked by the World. This is step 5's work, not a
  leak today.
- Fix: load `embeddings.parquet` in `World.load` when it exists, so the refusal checks run on every real run.

## J-4. Which weights read each part is not recorded at run time (note)

- Where: `reader/embed.py:269` writes `cutoff.PINS` at finish time. Neither `manifest` (`reader/embed.py:91-96`) nor
  a part records the revision that `load_model(v)` used. The World checks only the `vintage_year` label
  (`world/world.py:185-187`), so it cannot tell if a folder was read by other weights. `cmd_run` loads model v for
  folder v (`reader/embed.py:199-208`), so this is right by construction today.
- Fix: put the vintage's pinned revision in `manifest.json`, and have `cmd_finish` compare it with `PINS`.

## J-5. L-P7 still misses an edit that keeps `updated_at` (note)

- Where: both the row check (`world/world.py:188-191`) and `set_hash` (`reader/embed.py:84-88`) use
  `updated_at` only. A headline that changes with the same `updated_at` passes both. The store has no evidence that
  this happens (PLAN L129: the API returns the latest version), so this stays a note.
- Fix: optionally, also hash the headline bytes into `embeddings.json` (a hash, not text). Compare it in step 5's
  test.

## J-6. Smaller edges (notes)

- A row for a 2015 story is refused, but by `vintage_for`'s own ValueError (`reader/vintage.py:118-119`), not by
  the World's "refused" message. No test covers it. Fix: add one test.
- A repeated `story_id` in `stories` is accepted (`edges.py`). `world/world.py:105`, `:178` and
  `reader/embed.py:60` all take the first row. The store has 0 repeats, and every direction of the timing stays
  safe, so this has no effect today. Fix: refuse repeated story ids in `World.__init__`.
- `visible_at`'s `.map` turns float64 if an id is missing (`world/world.py:107`). That would round nanoseconds.
  `embedding_problems` refuses missing ids first, so the map stays int64 (checked). No effect.
- L-P8: an M5 morning job reads a story after it arrives. So a row's true time is the later of the story's time
  and the time its vector was computed. Today's equality check (`world/world.py:188-191`) has no room for that.
  Fix: note it in the M5 item, next to J-1's link gate.
- M-4: nothing in the code ties the reader run to the cutoff outcome. `research/m2_kickoff.md` step 3 says the
  owner accepted the vintages. That is a process gate, not code, which is fine.

## Checked and found right

- Timing. Visibility comes from the rule on the kept story's `updated_at`, never from the stored `available_at`
  (`world/world.py:104-107`). The stored value must equal it to the nanosecond (`world/world.py:188-191`). A row
  1 ns early or late, a NaT, or naive New York wall time are each refused. Naive UTC times and microsecond units are
  accepted and equal. Covered by `test_an_embedding_shows_15_minutes_after...` and `test_a_row_timed_before...`.
  The rest is covered by `edges.py` only.
- Ties. Views use `side="right"` for stories and embeddings alike, so both show at the same nanosecond (tested).
- Stories. A story dropped by `keep_story`, a story with NaT times (also dropped by `keep_story`) and an unknown or
  string `story_id` are each refused. A repeated row and a stale `updated_at` are refused (tested, except NaT and
  dtype: `edges.py`). Store counts: 0 repeated ids, 0 NaT `created_at` or `updated_at`.
- Vintage, from the New York `created_at` year. A story created at 23:50 New York time on 2019-12-31 is accepted
  only with 2018. One created at 00:10 on 2020-01-01 is accepted only with 2019. A 2027 story is accepted only with
  2024 (`edges.py`; the wrong-vintage test covers +1 only). Selected counts by vintage run from 33,251 (2015) to
  116,635 (2024), so no 2014 vintage reads news.
- Memory. A view's arrays and rows are fresh copies (`world/world.py:208-211`; tested with `shares_memory` and
  `.base`). An agent cannot reach `world.world` through `type(view.embeddings)` without a dunder name, and the
  boundary test forbids dunders (`tests/test_boundaries.py:65-67`).
- Leak modes for reading early. The planted `FutureEmbedding` is caught. Perturbed embeddings at t equal the
  originals in all modes, and later rows do change (tested).
- `cmd_finish` against the World. It checks each part's ids and `available_at` against the current store
  (`reader/embed.py:247-254`), the same tests the World runs. The vintage is right by folder. I found no output the
  World would accept that disagrees with the store, beyond J-4 and J-5.

## What changed after this review (22 Nov, main session)

- J-1 and J-2: fixed. `visible_at`'s embeddings branch takes the earliest `visible_at` of the story's links (never
  earlier than the story's own time), and NEVER for a story with no link. `World.__init__` and `eval/leaks.py`'s
  `late_rows` pass `story_entities`. In shift mode a late embedding's `available_at` follows its story. New tests
  in `tests/test_embeddings_wall.py`: the rejoin pair (equal views, equal decisions for the counting agent), a gap
  story whose embedding stays hidden, and the independent early check now against links. All four fail under the
  old rule. The "embeddings equal stories" assertions now read "embeddings equal linked stories".
- J-4: fixed. `manifest.json` records each vintage's pinned repo and commit, before the full run started.
- J-3, J-5 and J-6: left as notes for step 5 (`research/m2_kickoff.md`, step 3).


## Second judge: World.load and the mapped arrays (J-3)

Scope: the uncommitted change against e53c114 (`world/world.py`, `reader/embed.py`, `tests/test_embed.py`, the new
`tests/test_embeddings_store.py`). The question: through the time wall, can an agent reach an embedding row or vector
not visible at t, or the World's arrays? Scripts (made-up frames from `tests/synthetic.py`, and counts only on the
store) are in the session scratchpad as `j3_checks.py` and `j3_store_arrays.py`.

Verdict: no leak through the wall. A view holds only gathered copies of the rows visible at t, aligned with their
vectors, and nothing in it reaches a map or the World. Two things must or should change first: two wall tests now
fail, and the arrays check binds the vectors to the story ids only, not to the rows' content.

### J3-1. Two wall tests fail after the rename (must-change)

- Where: `tests/test_embeddings_wall.py:69-72` and `:149-151` use `w.embeddings.last`. The class now keeps
  `_last` and `_avg` in store order (`world/world.py:217-221`). Both tests raise AttributeError. So the DataFrame
  path's "a view shares no memory with the World" test and the planted `FutureEmbedding` leak test (`:212-215`) no
  longer run. The suite is red (2 failed, 45 passed for test_embed, test_embeddings_wall and test_boundaries).
- Check: `python -m pytest tests/test_embed.py tests/test_embeddings_wall.py tests/test_boundaries.py -q`.
- Fix: use `w.embeddings._last` and `_avg` in the memory test. In `FutureEmbedding`, take
  `e._last[e.order, 0]`, since `e.rows` is sorted and `e._last` is not; `e._last[:, 0]` would pair a row with
  another story's vector.

### J3-2. The arrays check covers the story ids, not the vectors (should-change)

- Where: `load_embeddings` accepts the .npy files when the parquet's story-id sequence hashes to
  `arrays.ids_sha256` and the lengths match (`world/world.py:254-258`). `cmd_finish` replaces the parquet
  (`reader/embed.py:269`) before it rewrites `embeddings.json` (`:270-278`, with `import torch`, `transformers`
  and `cutoff.PINS` lookups in between). If finish stops there, the old json keeps its old `arrays` entry. A rerun
  over the same story set gives the same id sequence, so the World serves the old vectors with the new rows. A rerun
  after a vintage repin (the reason one would rerun) would then show vectors read by the old weights. The same holds
  if `cmd_arrays` replaces one .npy and not the other (`:308`), as the json still carries the old entry.
- Check: `j3_checks.py` part 3 rewrites the parquet with the same ids in the same order and other vectors, and keeps
  the json. `load_embeddings` accepts it and returns the old vectors. Part 4: the same ids reversed are refused, so
  order is covered.
- Fix: in `cmd_finish`, drop `arrays` from `embeddings.json` before `os.replace` of the parquet, and in `cmd_arrays`
  before the first `os.replace`; better also record the parquet's size and footer hash in `arrays` and check them.
- No test covers it.

### J3-3. The leak tools need the DataFrame path (note)

- Where: `eval/leaks.py:63` calls `.copy()` on each table and `late_rows` (`:50-52`) reads `story_id` from it.
  Given an `Embeddings`, `perturb` raises AttributeError (`j3_checks.py` part 6). The real-store non-interference
  tests build their tables without embeddings (`tests/test_leaks.py:283-286`), and the full vectors as DataFrame
  columns do not fit in memory. So non-interference with embeddings runs on synthetic frames only.
- This is safe today: after construction both paths use the same `_SortedEmbeddings.upto`, and
  `test_the_world_maps_the_stores_arrays_and_serves_the_same_views` shows equal views. Fix, later: let `perturb`
  take an `Embeddings` and write the scrambled late rows into an in-memory copy, for a short window of the store.

### J3-4. Smaller edges (notes)

- `load_embeddings` does not check the arrays' dtype or width. The store's are float16 by 768, as the World's test
  checks (`tests/test_embeddings_store.py`). Fix: compare `last.shape[1]` and dtype with `embeddings.json`.
- On Windows an open map locks the file. With a World loaded, `cmd_arrays` stops with PermissionError at the
  first replace, so the old arrays and json stay consistent (`j3_checks.py` part 5). It leaves two `.tmp` files
  (about 772 MB each on the real store) on D:.
- A view late in the data gathers nearly every row: 502,712 rows by 768 in float16 is about 772 MB per array, so
  about 1.5 GB per view on top of the World. Not a leak; a memory note for M3.
- The refusals: `embedding_problems` runs on the mapped path's rows (`world/world.py:286`), the same function as
  before. The real table passes it (the `world` fixture of `tests/test_embeddings_store.py` loads). No test plants
  a bad row in a mapped store, but the input is the same rows DataFrame, so the DataFrame tests cover the logic.

### Checked and found right

- Alignment. `self.rows` is `rows.iloc[order]` and `upto` gathers `order[:k]` from the unsorted vectors
  (`world/world.py:222-241`), so row i of a view and vector i come from the same store row. Ties on `visible_at`
  keep store order in both. `j3_checks.py` part 1: 68 days, 270 tied rows, 0 mismatched rows. The new store test
  checks 50 rows against the parquet; covered.
- The real store. Every row of both .npy files equals the parquet's vectors: 502,712 rows compared, 0 differ
  (`j3_store_arrays.py`). `tests/test_embeddings_store.py`: 10 passed.
- No shared memory. `_gather` writes into a fresh `np.empty` with `np.take(out=...)`. The view's arrays are plain
  ndarrays with no base (covered by both new tests). The rows are `copy(deep=True)`.
- No path to the maps or the World. A walk of `gc.get_referents` from a view (3,900 objects, types and modules
  skipped) finds no memmap, no World, no `_SortedEmbeddings`, and no array with a base (`j3_checks.py` part 2;
  no test does this walk). `Embeddings` holds only `rows`, `last` and `avg`. The maps live only on
  `World.embeddings._last` and `_avg`. An agent never gets the World, and the boundary test forbids `memmap`,
  `mmap`, `load`, `load_*`, `base`, `World` and dunders (`tests/test_boundaries.py:24-32`; PLAN 9.1). The map's
  `.filename` names the store file, but nothing an agent holds reaches the map.
- Order of rows against arrays. `cmd_arrays` writes the arrays in the parquet's batch order and hashes the same ids
  (`reader/embed.py:286-312`); `load_embeddings` hashes the parquet's ids in read order. A reorder is refused
  (part 4; `test_arrays_written_for_other_rows_are_refused` covers a changed hash and a missing entry).
- The seal and the J-1 link rule are unchanged: `view()` checks the seal first, and `visible_at` gets the parquet
  rows (`world/world.py:289`). The EQT gap test passes on the real store.

### What changed after the second judge (22 Nov, main session)

- J3-1: fixed. The two tests use the World's `_last` and `_avg`, and the planted `FutureEmbedding` pairs rows with
  vectors through `e.order` (`tests/test_embeddings_wall.py`). Both pass, and the planted leak is still caught.
- J3-2: fixed. `cmd_finish` and `cmd_arrays` drop the `arrays` entry from `embeddings.json` before they replace a
  file it vouches for (`reader/embed.py`, `drop_arrays`). The entry now records the Parquet file's size and the
  SHA-256 of its footer, and `load_embeddings` refuses arrays written for another file. New tests in
  `tests/test_embed.py`: a table rewritten over the same story ids with the old entry is refused, and served again
  once the arrays are rewritten.
- J3-4: the arrays' dtype and width are checked on load. The leftover `.tmp` files after a PermissionError stay a
  note.
- J3-3: stays a note. Non-interference with embeddings runs on the DataFrame form, which serves the same views.
- The real store's arrays were written again with the new entry (`python -m reader.embed arrays`).
