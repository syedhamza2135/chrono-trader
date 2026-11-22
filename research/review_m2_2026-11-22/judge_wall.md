# Judge: the embeddings wall (M2 review, 22 Nov 2026)

Question: can an agent see any embedding, or learn anything from one, before its story is public?

Scope: commit 3d1df9b, `git diff 7081fba..3d1df9b` for world/rules.py, world/view.py, world/world.py, eval/leaks.py,
reader/embed.py, tests/test_embeddings_wall.py, tests/test_embeddings_store.py. Read with the digest
docs/digests/m2_wall.md and the J-1 to J-6 and J3-1 to J3-4 lines of docs/digests/m2_prior_findings.md.
PLAN.md was not read. Short answer: no. I found no way for an agent to see an embedding before its story and its
first company link are visible, and no way to reach a later row. One info finding on the leak check.

The three scripts are in the session scratchpad, C:\Users\syedh\AppData\Local\Temp\claude\166f9164ebdccd7e\9de82187-73a0-485c-b919-d5de64e3fe28\scratchpad
(wall_check.py on made-up frames, store_check.py on the real store with counts only and no text columns,
scramble_check.py on a made-up frame). Each check below says what it builds, so it can be rebuilt if the
scratchpad is cleared. Run each with `D:\venvs\chrono-trader\Scripts\python.exe` from the repo root.

## Findings

### W-1 Scramble keeps the sign pattern of the late vectors (info)

- File: eval/leaks.py:66-75 (`scramble_vectors`), used at eval/leaks.py:121-122.
- What: scramble permutes the late vectors among the late rows and multiplies each by a positive factor in 0.5 to
  1.5. Any statistic that ignores row order and positive scale is unchanged, for example the share of positive
  entries over the late vectors. For bars and labels the module flips signs of `ret` and `label` for exactly this
  reason (eval/leaks.py:8-10, 86-87); the vectors get no sign flip. Shift leaves the vectors unchanged too
  (eval/leaks.py:104-111 moves times and vintages only).
- Why only info: a leak that reads such a statistic over a time window is caught by shift (the window's rows move 7
  days), and one that reads it over all late rows is caught by delete (the rows go). So the "at least one of three"
  rule (eval/leaks.py:13) still holds. It only matters if someone later relies on scramble alone.
- Evidence (scramble_check.py): 200 made-up float16 vectors of width 16, rows 120 to 199 late, the function copied
  from eval/leaks.py:66-75. Share of positive entries over the late rows: 0.48203125 before and 0.48203125 after
  scramble, equal.
- Fix idea: in `scramble_vectors`, also multiply each late vector by a random sign (as SIGNED does for returns).

No high, medium or low findings.

## Checked and found right

(a) Availability time.
- world/rules.py:31-33: `embedding(updated_at)` is `story(updated_at)`, updated_at plus 15 minutes.
- world/world.py:201-204 refuses any row whose stored available_at differs from its story's, in nanoseconds;
  reader/embed.py:58-68 and 258-261 set and recheck the same time. world/world.py:116 takes the later of the first
  link and the availability, so a row can never show before its story: a link's time is itself at least the
  story's time (world/world.py:125).
- Decision time: `World.view(t)` returns only rows with visible_at at most t (world/world.py:238,
  `searchsorted(..., side="right")`).
- Real store (store_check.py, counts only): 502,712 embedding rows. 0 rows would show before their story's
  availability, 478 are held back past it by the link gate, 1,836 never show (every link hidden forever).
- The vector is a headline read by the vintage of the story's New York year minus one (world/view.py:14-16), and
  the view already shows that headline, so the vector adds nothing about the story beyond what the vintage knew.
  Whether the vintages' training really ends before that year is the cutoff review's question, not this one.

(b) The J-1 first-link rule, in every path.
- There is one path into a view: `World.__init__` builds `_SortedEmbeddings` with
  `visible_at("embeddings", rows, spells, kept stories, kept story_entities)` (world/world.py:307-308), for both the
  DataFrame form and the mapped form from `World.load` (world/world.py:339-341). `eval.leaks.decisions_until`
  builds a World the same way (eval/leaks.py:139). A search for `View(`, `Embeddings(`, `_SortedEmbeddings(` and
  `load_embeddings(` over all .py files finds no other construction; sim/ and agent/ never name `embeddings`.
- wall_check.py on made-up frames (A a member from 2016-01-01; B a member to 2016-06-01, rejoins 2018-01-01):
  a story linked to A and B on 2017-03-01 shows at its own time (A's link); one linked only to B on 2017-03-01
  shows at 2018-01-01 00:00 New York (the rejoin start, within 400 days); one linked only to B on 2016-09-01
  (more than 400 days before) never shows; one with no link never shows. No row shows before its story.
- tests/test_embeddings_wall.py:229 checks the stronger property that every embedding in a view has a visible
  link, independently of the rules, and :233 shows a planted early rule is caught. :281, :297, :304 and
  tests/test_embeddings_store.py:89 cover the rejoin.
- Kept stories with no link in the real store: 1,705,240 of 2,239,859, so a story's presence in `stories` says
  little about the store's companies; with the gate, an embedding's presence says only what the visible links say.

(c) The two .npy arrays.
- world/world.py:266-276 refuses the arrays unless the Parquet's story-id hash, all four row counts, the Parquet
  size and footer hash, dtype float16, 2-D and width 768 all match the `arrays` entry. reader/embed.py:308-336
  writes the arrays in the Parquet's own row order (`iter_batches`), and `ids_hash` (reader/embed.py:83-84) hashes
  the same int64 bytes the World hashes. `drop_arrays` runs before either file is replaced (reader/embed.py:269,
  329), so a stop leaves the World refusing, not using stale arrays.
- Real store: both files are (502712, 768) float16, mapped with mode "r" and `writeable` False.
- Alignment: rows are sorted by `order`, and `upto` gathers `order[:k]` from the unsorted arrays
  (world/world.py:222-224, 239-241). wall_check.py checks that each view row's vector is its own story's vector.
  A view holds no index into the World's arrays, only gathered copies.

(d) Copies per view.
- `upto` returns `rows.iloc[:k].copy(deep=True)` and two arrays from `np.empty` filled by `np.take`
  (world/world.py:231-241). wall_check.py: the view's array has `base` None and `np.shares_memory` with the World's
  array is False. The view's arrays are writable, but they are the agent's own copy, and a new view is built each
  day, so a kept handle never grows.
- `type(view.embeddings)` is `world.world.Embeddings`, whose functions' `__globals__` hold `World` and
  `load_embeddings`. I probed this: a made-up agent file reaching `World` through
  `type(v.embeddings).__init__.__globals__` and `__dict__` is flagged by `tests.test_boundaries.agent_name_problems`
  ("__globals__ on line 6", "__dict__ on line 8"), because every dunder name but `__init__` and `__name__` is
  forbidden (tests/test_boundaries.py:68-70). So the boundary holds for this new type.

(e) eval/leaks.py.
- `late_rows` marks an embedding late with the World's own `visible_at("embeddings", ...)` (eval/leaks.py:50-52),
  so a row late only through its links is included. Scramble changes the late vectors (:121-122), shift moves the
  late rows' available_at and vintage with their stories (:104-111), delete drops them (:95-96).
- The post-change loop (eval/leaks.py:125-132) does not refilter embeddings, and does not need to: a shifted story
  moves later, scrambled vectors keep their times, and the embedding's time follows its remaining links, which the
  loop does refilter. tests/test_embeddings_wall.py:177 checks that the view at t is unchanged under all three, and
  :212 that the planted `FutureEmbedding` leak is caught.
- A leaking agent that reads the World's embeddings therefore fails the check. One that reads files from disk would
  not, since both runs read the same disk; that is the boundary test's job (see (d)), not this check's.

## Earlier fixes

| Item | Holds? | Where |
|---|---|---|
| J-1 first-link gate | Holds | world/world.py:110-120, 307-308; eval/leaks.py:50-52, 104-111; wall_check.py; store: 0 early rows |
| J-2 leak checks see J-1 | Holds | tests/test_embeddings_wall.py:229 (subset of visible links), eval/leaks.py:50-52 |
| J-3 real table into the World | Holds | world/world.py:256-277, 332-341; store arrays load read-only |
| J-4 weights recorded per vintage | Not a wall item, not checked | reader/embed.py:98-103, 166-175 |
| J-5 edit that keeps updated_at | Still a note, unchanged | reader/embed.py:87-91 |
| J-6a 2015 row, no test | Still a note | reader/vintage.py:17-18 |
| J-6b repeated story_id in stories | Still a note, unchanged | world/world.py:111, 191 (`drop_duplicates`) |
| J-6c float64 map | Holds | world/world.py:116-117 (`reindex`, `get_indexer`, int64) |
| J-6d L-P8 compute time | Still a note for M5 | world/rules.py:31-33, world/world.py:201-204 |
| J-6e M-4 process gate | Not a code item | none |
| J3-1 tests after the rename | Holds | tests/test_embeddings_wall.py:151 (`e._last[e.order, 0]`), :212 |
| J3-2 stale arrays entry | Holds | reader/embed.py:269, 329, 299-306; world/world.py:271-273 |
| J3-3 leak tools need the DataFrame form | Still a note, unchanged | eval/leaks.py:63 |
| J3-4a dtype and width | Holds | world/world.py:274-276; store: float16, width 768 |
| J3-4b to d | Still notes | reader/embed.py:315-331; world/world.py:236-241; world/world.py:304-306 |
