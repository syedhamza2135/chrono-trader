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
