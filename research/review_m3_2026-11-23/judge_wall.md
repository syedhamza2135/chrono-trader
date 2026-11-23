# M3 review, judge 1: the time wall and the agents (23 Nov 2026)

Question: can any M3 agent see anything after its decision time, and can the vintage offset or the 90-day embedding
window open a sealed date?

Scope: the 8 M3 commits, `master` (`6894217`) to `89f35f7`. I read `agent/track_a.py`, `agent/baselines.py` and
`agent/placebo.py` in full. I read `sim/simulator.py` lines 117-237, and the diffs of `world/world.py`, `world/view.py`
and `eval/leaks.py`. I also read `reader/vintage.py` (`check_offset`, `breaches`), `agent/reversal.py:39-47` (the pick),
the World and run calls in `research/m3_dev_runs.py` and `research/m3_older_vintage.py`, the names of the tests in the
M3 test files, a few test bodies, and the two earlier M3 judge notes. I did not read PLAN.md, the data or `.env`, and I
did not run the test suite.

## Verdict

None high, none medium. I found no path by which a record after t reaches a decision, and none by which the vintage
offset or the window opens a sealed date. The window can only remove rows that a view would otherwise hold. A World
with an offset refuses sealed views at three points. There are 4 low findings: one rule breach found by the grep,
one claim in the placebo that does not hold, one embargo bound that is not enforced, and one replay with no guard.
There are 5 info notes.

## The grep (exact output)

`git grep -n "allow_sealed=True"`:

```
research/m3_kickoff.md:664:  The report writer must not call `World(..., allow_sealed=True)` as the M0 preview test does
research/world_memory.py:62:    w = World.load(allow_sealed=True, embedding_window_days=window)
tests/test_embedding_window.py:164:    return World.load(allow_sealed=True, embedding_window_days=None)
tests/test_embeddings_store.py:41:    return World.load(allow_sealed=True, embedding_window_days=None)  # every row; the window's tests set their own
tests/test_leaks.py:293:    world = World(**real_tables, allow_sealed=True)
tests/test_leaks.py:324:    world = World(**real_tables, allow_sealed=True)
tests/test_vintage_offset.py:91:        World(**tables, embeddings=older(tables), vintage_offset=1, allow_sealed=True)
tests/test_world.py:89:    return World(**tables, allow_sealed=True)  # made-up records; 2021 is in the sealed years
```

The wider grep `git grep -nE "allow_sealed\s*=\s*[^F]|\.allow_sealed\s*=" -- '*.py'` finds no more truthy uses. The
only other places that set it are `sim/simulator.py:129` and `:194`, which set it to True when `last` is in the sealed
years, and `:139` and `:213`, which restore it. (The tests also set it on made-up Worlds at `tests/test_sim.py:159`,
`tests/test_world.py:194` and `tests/test_vintage_offset.py:93`, which expects a refusal.)

What each one is:
- `tests/test_leaks.py:293`: the M0 preview test, which the rule allows. `:324`, the EQT rejoin test (views in 2022),
  is from M1 and not new.
- `tests/test_world.py:89`: made-up records. `tests/test_vintage_offset.py:91`: the test expects the World to refuse it.
- `tests/test_embeddings_store.py:41`: from M2; M3 changed only the window argument. It views 2022-01-03 and
  2022-10-03 (lines 100 and 103).
- `research/world_memory.py:62`: from M2 (J-3); M3 added the window argument. It views the last session of the sealed
  period (lines 66-71).
- `tests/test_embedding_window.py:164`: **new in M3** (commit `9d04ced`). See W3-1.

Can `run_many` or a research script reach a sealed date? No. Every M3 runner ends on 2019-12-31:
`research/m3_trial_plan.py:25` has `FIRST, LAST = "2016-01-04", "2019-12-31"`, which `m3_dev_runs.py:35` and
`m3_older_vintage.py:91` use. `m3_compare_timing.py:44` and `track_a_timing.py:28` also end on 2019-12-31. The sealed
period starts on 2020-01-02 (`reference/split.json`). All of them build the World with `World.load()` and leave
`allow_sealed` at its default. `run_many` (`sim/simulator.py:190-194`) applies the same `_offset` and `seal.check`
gates as `run`, and it restores the flag in a `finally` block.

## Findings

**W3-1, low. A new M3 test opens a sealed-date view on the real store.** `tests/test_embedding_window.py:164`
builds `World.load(allow_sealed=True, embedding_window_days=None)`. The test at lines 167-178 then views 2026-10-28,
which is in the sealed years. It compares only embedding rows: story ids, times and the cut. It reads no prices,
labels or outcomes, so nothing about results leaks. But it breaks the review's rule ("no `World(...,
allow_sealed=True)` outside the M0 preview test"). The World's docstring is looser: it allows "a data audit". Check:
the grep above, and `sed -n 167,178p tests/test_embedding_window.py`. Fix: replace `"2026-10-28"` with a dev date
(for example `"2019-06-28"`), and build that fixture with `allow_sealed=False`. Or the owner states that data audits
may use the flag, and the review rule names them. `research/world_memory.py:62` and
`tests/test_embeddings_store.py:41` are older uses of the same kind, which M3 re-touched. The owner should rule on all
three together.

**W3-2, low. The placebo does not shuffle a pair the same way in every later view, once the window cuts into its
group.** `agent/placebo.py:13-14` claims "the same pair is shuffled the same way in every later view". The groups are
the decisions that pairs first reach (`placebo.py:30-33`). The window's edge is t minus 90 times 24 hours, so
it falls at 9:00 on a calendar day (8:00 or 10:00 New York time across a DST change), not at a group boundary. When
the edge falls on a weekend or a holiday, or across a DST change, it drops part of a group. `rng.permutation` then
permutes a shorter array, and the pairs left in the group get new companies. Check:
`judge_wall_check1b.py` in the judge's scratchpad, on made-up frames. Four pairs fall in Monday's group, the first
from Friday 10:00, and the window drops that one. Over seeds 1 to 50, the 3 pairs left got a different company in 49
of them. `tests/test_comparison.py:171` compares two views 14 days apart, so the window never cuts and the test
cannot see this. Effect: none on Track A's runs. After its first decision, Track A uses only pairs that are new since
`last_t` (`track_a.py:233-235`), and those always form today's whole group. The first decision's memory is built from
one view, so it is consistent too. This is not a leak, because every pair comes from the view at t. Fix: shuffle
each group from a key fixed when the group is complete, such as the sorted (story_id, entity_id) pairs in the group,
not their positions. Or correct the docstring and the test, and say that the claim holds only for today's group.

**W3-3, low. The label embargo is not enforced for days already dropped from `recent`.** `split`
(`track_a.py:387-397`) holds out every kept day whose latest label showed at or after the first validation decision.
This fix for S1 holds. But the training sums also contain days already trimmed from `recent`
(`track_a.py:368-369`, `keep = n_val + 64`). The code cannot take those out, and `train_latest` does not look at
them. The docstring at line 391 says that days no longer kept "are over a year older". On the dev years that is not
true: early on, `keep` is about 127 lived days. In the steady state the gap cannot be crossed. A day settles at the
first monthly refit where it is at least 10 sessions old (`track_a.py:302`), so its latest label shows at most about
33 sessions after its date. And a day trimmed at one refit is at least about 80 lived days before the next refit's
first validation day: n_val plus 64, plus about 21 new days, minus n_val's growth of about 5. The one gap is the
first refit (October 2016). It settles every day from April 2016 at once, so a day trimmed a month later could hold a
label that showed months after its date. That needs a pick with no official open for about 5 months. On the top 50
by volume this is very unlikely, but the code does not rule it out. It only affects which penalty and pooling are
chosen, and only in 2016. Check: the arithmetic above against `track_a.py:302, 338, 368`. A count on the real labels
(the longest gap from a pick's label date to its `visible_at` in 2016) would settle it. I did not run that count,
since the brief keeps the data out. Fix: keep `self.trimmed_latest`, the largest `r[3]` among trimmed days. Put it
into `train_latest`, and assert that it is below `first_val_t`. Also correct the docstring at line 391.

**W3-4, low. `replay` has no seal guard.** `sim/simulator.py:223-237` (new in M3) trades a run's targets through a
fresh simulator. It works on any dates in `run.equity` and reads the full labels table, sealed years included
(`Simulator.__init__`, line 43). No agent or view is involved, so no agent can see the future through it. But a
hand-made `Run` with dates from 2020 on would give sealed-year returns with no seal check. Today the only callers are
`research/m3_dev_runs.py:161` and `:167`, both on dev runs. `Simulator.step` from M1 has the same gap. Check:
`sed -n 223,237p sim/simulator.py`, which has no `seal` call. Fix: in `replay`, call
`seal.check(first, last, None)` on the run's first and last equity dates, so that sealed dates are refused unless a
seal holds.

## Info notes

- **W3-5. An agent can undo `_own_view`'s read-only flag.** `sim/simulator.py:172-173` marks the vector *views*
  read-only, but the base arrays stay writeable. NumPy then lets an agent set `flags.writeable = True` again and
  write to the shared base. Check: `a=np.zeros(3); v=a.view(); v.flags.writeable=False; v.flags.writeable=True;
  v[0]=7` changes `a`; I ran this in the project's environment. The damage is limited to that one day: the next
  agents in the loop would see changed vectors, and the next day's view is a fresh copy (`world.py:256`). It carries
  no later information, and no agent in the repo does this. Fix: also set `v.embeddings.last` and `.avg` read-only
  (the base arrays) before the loop over agents.
- **W3-6. The window can hide a later link for good.** A pair's availability is the later of its embedding and
  its link (`track_a.py:211`). If a second company's link shows more than 90 days after the story's embedding (a
  rejoin), the embedding has already left the window. The agent never gets that pair. This loses data and leaks
  nothing. Without the window, such a pair would arrive as fresh news months late. Fix: none needed; one line in
  the World's docstring would do.
- **W3-7. Shuffled links can repeat a pair.** The placebo permutes companies within a group, so a story with two
  links can end up with the same company twice. `_pairs` then drops the copy (`track_a.py:214`), and the placebo
  sees slightly less news than the live agent. That contradicts "the same amount of news each day"
  (`placebo.py:9-10`). This is not a leak. Fix: correct the docstring, or permute stories rather than companies.
- **W3-8. Private fields are writable.** `World._offset` and `World._window` are plain attributes behind read-only
  properties. `tests/test_embedding_window.py:172` and `:176` write `_window` directly. Writing `_offset = 0` would
  drop the offset from the settings, and the view's offset check would no longer refuse sealed dates. This needs
  deliberate code, and `seal.check` still guards sealed dates. Fix: none needed, or a grep for `\._offset\s*=` in the
  boundary test.
- **W3-9. The window's edge moves by an hour across DST.** `since = ns - window * DAY_NS` (`world.py:365`) counts
  days of 24 hours in UTC. Across a DST change, the edge falls at 8:00 or 10:00 New York time. It is always before t,
  so it is not a leak. It is one cause of W3-2.

## Checked and found right

- **The window counts visible time, and it only removes rows.** `_SortedEmbeddings.upto` (`world.py:250-257`) keeps
  the rows with `since < visible_at <= t`. `visible_at` is the World's own time: the later of `available_at` and the
  story's first visible link (J-1). `j <= k` always holds, and a window must be a positive whole number
  (`world.py:306-308`), so `since < t`. The window cannot add a row or reach past t, and it changes nothing about
  sealed dates, which `view` checks before any table is cut (`world.py:357-361`). Tests cover the cut, the exact
  90-day edge, a late rejoin, and a planted window anchored after t: `test_embedding_window.py:60, 72, 82, 135`.
  W-1 and W-3 from `m3_window_judge.md` are fixed.
- **The vintage offset.** `check_offset` accepts only the allowed offsets and refuses a bool (`vintage.py:17-21`).
  `embedding_problems` refuses any row whose vintage is not exactly Y-1-offset (`vintage.py:36-43`), so an offset
  World refuses the rule's own table, and the default World refuses the older table. A vintage a year older can only
  know less. The offset is a read-only property (`world.py:341-344`; `test_vintage_offset.py:80`). The sealed years
  are shut at three points: the constructor refuses `allow_sealed` with an offset (`world.py:302-303`); `view`
  refuses a sealed t even after `allow_sealed` is set, because the offset check comes first (`world.py:358-359`); and
  `_offset` refuses `run` and `run_many` for a sealed `last` (`simulator.py:145-153`). Tests:
  `test_vintage_offset.py:88, 109`. `replay` uses no World view, so the offset does not apply to it (see W3-4).
  `World.load(embeddings_store=..., vintage_offset=0)` on the older table is refused by the vintage check.
  `research/m3_older_vintage.py:86` uses offset 1 and ends on 2019-12-31.
- **What each agent in `run_many` sees.** Each session's view is built once, from deep copies of the World's tables
  (`world.py:167`) and fresh gathers of the vectors (`world.py:256`). Each agent gets `_own_view`: shallow DataFrame
  copies (pandas 3.1.0 here, where copy-on-write is always on), frozensets for members, a copy of the sessions, and
  read-only vector views (but see W3-5). A View holds no reference to the World. Agents keep separate simulators
  (`_fresh`) and separate state. `comparison_agents` (`m3_dev_runs.py:131-139`) builds a new `TrackA` for each
  entry, so no two entries share an agent.
- **Frozen twins share nothing mutable.** `freeze` (`track_a.py:371-385`) copies the arrays in the memory and the fit
  and builds new lists and dicts. The shared items are immutable or never written: tuples, Timestamps, and the dicts
  inside `fits`. A twin never refits (`learning=False`), so it never calls `settle`, and its empty `pending`,
  `recent` and `sums` stay empty. A twin is built at the first session of a new year, before any decision that day
  (`simulator.py:201-205`), so it holds only state from earlier views. Test: `test_comparison.py:96`.
- **Track A reads only the view.** Price features use bars dated before today, within 200 days (`track_a.py:185`).
  The pick uses bars from before today (`reversal.py:42`). A news pair is available at the later of its embedding
  and its link. New pairs are those after `last_t`, and ages are clamped at 0 (`track_a.py:231, 242`). Labels come
  only from `v.labels` (`track_a.py:294`). The validation scaler comes from the training sums alone
  (`track_a.py:348-349`). Fixes S1 (the time-based gap), S2 (0 before scaling, `track_a.py:285`), S3 (`fits`
  records `first_val_t` and `train_latest_label`), N3 (watch-only clears the book, `track_a.py:465-466`), N5 (the
  age clamp) and N6 (one row per pair, `track_a.py:214`) from `m3_agent_judge.md` are in place, with W3-3 as the
  exception.
- **The placebo uses only links visible on that day.** `shuffled_links` (`placebo.py:22-43`) merges the view's
  `story_entities` with the view's embedding rows, groups the pairs by the first 9:00 at or after their
  availability (capped at today), and permutes companies only within each group. Every company in a group comes from
  a visible link. Today's group holds exactly the pairs that showed between yesterday's 9:00 and t. Stories and times
  never move.
- **The baselines use only bars visible at the decision.** `returns` takes bars dated before today, within 400 days
  (`baselines.py:50`). Momentum uses `[-252:-21]`, and reversal uses the last 5 bars. Random is seeded by
  (seed, date) and reads no data. Equal weight reads nothing. A hold longer than one session reuses the agent's own
  past targets (`baselines.py:81-85`). All of them are 0 before `trade_from`. The test of the matched-hold baselines
  against a hand computation is `test_comparison.py:203`, and their non-interference test is
  `test_comparison.py:243`.
- **The leak harness.** `eval/leaks.py` now passes the window and the offset to both Worlds. A shifted embedding
  takes the older vintage under offset 1, so the perturbed table is still one the offset World accepts. Tests:
  `test_vintage_offset.py:162` and `test_embedding_window.py:129`. Note that `decisions_until` drives one agent
  through `world.view`, not through `run_many` or `_own_view`. Agents are kept apart within one pass by the
  separate tests at `test_comparison.py:61` and `:86`.

## Rerun scripts (in the judge's scratchpad, made-up frames only)

- `judge_wall_check1b.py <repo root>`: W3-2, the placebo group cut by the window (it prints 49 of 50 seeds).
- `judge_wall_checks.py <repo root>`: the same question on `tests/synthetic.py` tables over 2017 (it prints 0 days
  changed). The synthetic stories never put a group across the window's edge, so it does not show the case.
- W3-5: the one-line NumPy check quoted above.
