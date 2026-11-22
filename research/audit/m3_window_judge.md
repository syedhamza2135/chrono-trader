# M3 embedding window: the judge's findings (22 Nov 2026)

The question: does M3's embedding window (decision 1: a view serves only the embeddings whose visible_at falls in the
90 days of 24 hours up to t) keep the time wall sound, and do its tests show it? Also: can an agent reach the new SPY
and sector tables?

Verdict: the window is sound. No must-change. Two should-change items make the tests prove more; the rest are notes.

## What I read and ran

- `git diff` of `world/world.py`, `world/view.py`, `eval/leaks.py`, `sim/simulator.py`, `research/world_memory.py`, and
  the three M2 test files; `tests/test_embedding_window.py` in full; `eval/benchmarks.py` in full;
  `data_pipeline/benchmarks.py` (imports and paths only); `tests/test_boundaries.py` (rules only); `sim/seal.py`
  (check only); `tests/test_embeddings_wall.py` lines 1-28 and 176-250.
- `pytest tests/test_embedding_window.py -k "not real_store"`: 25 passed, 7 deselected (270 s). I did not run the 7
  real-store tests or the whole suite.
- Two scripts on the made-up world (`tests/synthetic.py`), given below so anyone can rerun them.

## Q1. Can the window show a row early, or tell of records after t?

No. The reasoning, then the checks.

- `_SortedEmbeddings.upto` (`world/world.py:244-251`) takes `k` = rows with visible_at <= ns, exactly as M2 did, and
  `j` = rows with visible_at <= since, where `since = ns - days * DAY_NS` (`world/world.py:342`). `since` depends only
  on t. `j` is capped at `k`. So the window serves rows `j..k-1` of the sorted order: a contiguous tail of the full
  M2 view, in the same order, with nothing added. A windowed view is therefore a function of the full view and t,
  and can hold no information the full view does not. Rows that drop out are ones visible more than 90 days before t:
  past facts. Rows never visible (`NEVER`) sort last and never enter.
- `reset_index(drop=True)` gives every view a 0-based index, so the index no longer tells how many rows are older
  than the window. Without it the index would reveal only a count of past rows, not anything after t.
- The boundary is half open, (t - 90 days, t]. A row with visible_at exactly t is in; one at exactly t - 90 days is
  out. 90 days of 24 hours means the edge moves by an hour in New York clock time across a DST change. That is a
  fixed rule, not a leak.
- A rejoining company's old stories (visible_at long after available_at) are windowed on visible_at, so they show for
  90 days from the rejoin. They tell nothing the full view would not.
- Check A (rerun below): on all 337 sessions from 2016-03-01 to 2017-06-29, the windowed view's rows and both vector
  arrays equal the ordered tail of the full view, its index is a RangeIndex from 0, every served row has visible_at in
  (t - 90 d, t], and every dropped row has visible_at <= t - 90 d. Result: 0 days differ.
- Check A also tried windows of 10^8 and 10^9 days (so `since` is far below the int64 range): no error, and the view
  equals the full one.

## Q2. Is the window applied the same way everywhere, and is it sealed?

Yes. `World.__init__`, `World.load` and both `eval.leaks` functions default to the one constant
`EMBEDDING_WINDOW_DAYS` (`world/world.py:292, 349`; `eval/leaks.py:137, 173`), and `World.load` passes it on
(`world/world.py:359`). `decisions_until` builds its World with the window and loops as `sim.run` does
(`eval/leaks.py:141-146` against `sim/simulator.py:131-132`). `sim.run` puts `embedding_window_days` into the settings
dict that `seal.check` hashes (`sim/simulator.py:121-124`), so a sealed run with another window fails the seal.

Because a windowed view is a function of the full view and t (Q1), a leak test passed under one window implies none
under any other, given the full views are unchanged by the perturbation. So a run whose window differs from the leak
test's is not a gap in soundness.

## Q3. Do the new tests show it, and are any vacuous?

What they show, and correctly:
- `test_the_windowed_view_is_the_full_view_cut_by_visible_at` (6 days) and the boundary test to the nanosecond
  (lines 72-79) pin the rule. The `0 < len(windowed) < len(full)` guard (line 64) keeps the cut from being trivial.
- The rejoin test (lines 82-93) asserts there are rows shown more than a window after their story, so it is not
  vacuous.
- `WindowCount` reads `len(v.embeddings)`, so it moves whenever a row enters or leaves the window, and
  `test_the_window_changes_what_an_agent_sees` proves it does. That makes the non-interference tests sensitive to the
  window, not only to the 3-day `NewsAgent`.

Findings:

- **W-1, should-change. No planted wrong window.** Nothing shows that `non_interference` catches a window that uses
  information after t. `tests/test_embedding_window.py:127-140`. Check B (rerun below) plants a window anchored on the
  table's last finite visible_at instead of on t; `non_interference` with `WindowCount` catches it in `shift` and
  `delete` (not `scramble`, which keeps times). Fix: add Check B as a test asserting `caught`, as
  `test_non_interference_catches_the_planted_embedding_leak` does for M2.
- **W-2, note. Order and index are not asserted.** `assert_window_cuts_the_full_view` sorts both sides by story_id and
  resets the index (`tests/test_embedding_window.py:32-43`), so it does not check that the windowed rows keep the full
  view's order or that the index starts at 0. Neither could leak (Q1), and Check A shows both hold. Fix: compare the
  windowed view with `full.rows.iloc[len(full) - n:].reset_index(drop=True)` directly, and assert a RangeIndex.
- **W-3, note. The window can be changed after the World is built.** `embedding_window_days` is a plain attribute,
  checked only in `__init__` (`world/world.py:295-298`); the real-store test sets it directly
  (`tests/test_embedding_window.py:155-159`). `sim.run` records it once at the start (`sim/simulator.py:123`) while
  `view` reads it every call (`world/world.py:341`). Agents never get the World, so this is not a leak; a caller could
  only make the recorded settings wrong. Fix: make it a read-only property, and build two Worlds in that test (or
  accept the memory cost note there).

## Q4. Did moving the three M2 tests to `embedding_window_days=None` lose coverage?

No. Those tests assert the full visible set (equality), which a window rightly breaks. The direction that matters for
the wall, no embedding without its company link (judge J-1), is still checked under the default window by
`early_embeddings` in `test_no_embedding_is_ever_in_a_view_before_its_story` and its planted-rule test
(`tests/test_embeddings_wall.py:221-248`, both `world()` with the default). With the cut test, J-1 under the window
follows from J-1 on the full view.

- **W-4, should-change. One M2 check now compares only windowed views.**
  `test_the_perturbed_embeddings_at_t_are_the_original_ones` (`tests/test_embeddings_wall.py:178-185`) builds both
  Worlds with the default window, so rows visible at t but older than 90 days are no longer compared before and after
  the perturbation. This is the test behind the Q2 argument (full views unchanged by the perturbation). Fix: pass
  `embedding_window_days=None` to both Worlds there (or parametrize it over 90 and None).

## Q5. Can an agent reach SPY or the sectors?

No, as far as the code shows.
- `World.load` reads only bars, labels, opens, stories, story_entities, membership and embeddings by name
  (`world/world.py:353-359`); `View` has fixed fields and `world/view.py` imports only `world.clock`
  (`tests/test_boundaries.py:108-114`). `grep -rn "spy|sector" world/ agent/` finds nothing.
- `spy.parquet` and `sectors.parquet` sit in the same store folder, but an agent may import only `world.view.View`
  from the project, so not `eval.benchmarks`; and `read_*`, `load_*`, `pyarrow`, `Path`, `open` and the rest are
  forbidden names (`tests/test_boundaries.py:3-32`).
- `grep` shows `eval/benchmarks.py` and the two tables are used by no other module yet.
- **W-5, note.** `sector_on` gives a company first listed after `day` its first listed sector
  (`eval/benchmarks.py:23-35`): a look-ahead, fine for the evaluation only. Keep it out of anything an agent's
  features are built from.

## Notes outside the questions

- **W-6, note.** No code writes `seal.lock`; whoever writes it must build the same dict `sim.run` builds, now with the
  window too (`sim/simulator.py:121-123`). A helper shared by `run` and the seal writer would stop a mismatch. This was
  so before M3 (cost_bps, agent, agent_params).
- `getattr(world, "embedding_window_days", None)` records None both for "every row" and for an object with no window.
  Only test doubles lack it. No action.

## Check A: the window is the ordered tail of the full view

```python
import sys
from pathlib import Path
WT = Path(r"C:\Users\syedh\dev\chrono-trader\.claude\worktrees\m3-kickoff-56264f")
sys.path.insert(0, str(WT)); sys.path.insert(0, str(WT / "tests"))
import numpy as np, pandas as pd
import synthetic
from world.clock import Clock
from world.world import World

BASE = synthetic.make_tables(0)
T = {**BASE, "embeddings": synthetic.make_embeddings(BASE)}
full_w, win_w = World(**T, embedding_window_days=None), World(**T)
days = Clock().between("2016-03-01", "2017-06-29")
bad = 0
for d in days:
    t = Clock().decision_time(d)
    f, w = full_w.view(t).embeddings, win_w.view(t).embeddings
    n = len(w)
    tail = f.rows.iloc[len(f) - n:].reset_index(drop=True)
    ok = (tail.equals(w.rows) and np.array_equal(f.last[len(f) - n:], w.last)
          and np.array_equal(f.avg[len(f) - n:], w.avg)
          and isinstance(w.rows.index, pd.RangeIndex) and w.rows.index.start == 0
          and ((w.rows.visible_at > t - pd.Timedelta(days=90)) & (w.rows.visible_at <= t)).all()
          and (f.rows.iloc[:len(f) - n].visible_at <= t - pd.Timedelta(days=90)).all())
    bad += not ok
print(f"days checked: {len(days)}, days where windowed != ordered tail of full view: {bad}")
t = Clock().decision_time("2017-03-15")
for wd in (10**8, 10**9):
    print(wd, len(World(**T, embedding_window_days=wd).view(t).embeddings), len(full_w.view(t).embeddings))
```

Output on 22 Nov: `days checked: 337, ... : 0`; both huge windows gave 2344 rows, as the full view did.

## Check B: a planted future-anchored window is caught

```python
import sys
from pathlib import Path
WT = Path(r"C:\Users\syedh\dev\chrono-trader\.claude\worktrees\m3-kickoff-56264f")
sys.path.insert(0, str(WT)); sys.path.insert(0, str(WT / "tests"))
import world.world as ww
from eval import leaks
from test_embedding_window import WindowCount, TABLES

real = ww._SortedEmbeddings.upto
def wrong(self, ns, since=None):
    if since is not None:
        since = int(self.at[self.at < ww.NEVER].max()) - 400 * ww.DAY_NS  # anchored on the table's end
    return real(self, ns, since)
ww._SortedEmbeddings.upto = wrong
print([h for h in leaks.HOW if leaks.non_interference(TABLES, lambda: WindowCount(warmup=15),
                                                      "2017-01-03", "2017-03-15", h, seed=4)])
```

Output on 22 Nov: `['shift', 'delete']`. Run from the worktree root with `D:\venvs\chrono-trader\Scripts\python.exe`.
