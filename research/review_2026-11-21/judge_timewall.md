# Judge: can the time wall leak the future to an agent?

This judge ran on Opus at high effort, because Fable hit its monthly spend limit.

Read: world/clock.py, world/view.py, world/world.py, world/rules.py, world/__init__.py, eval/leaks.py,
agent/reversal.py, the digests, and a grep of tests/test_boundaries.py, tests/test_leaks.py, tests/test_world.py,
data_pipeline/store.py, data_pipeline/audit_news.py and data_pipeline/identity.py. Store queries read counts, schemas
and close ratios only. No code was changed.

## Answers in short

1. Through `View` at 9:00 New York time, nothing from after the decision reaches an agent. Every cut-off uses
   `<= t`, times are New York times converted to UTC, and a view holds detached copies with no path to the World.
   One label kind is visible before its news was public, but only between 9:30 and midday, which the 9:00 loop never
   asks for (finding L2).
2. `non_interference` catches any leak through the World or the tables it is built from. It cannot catch a leak
   through a file read, a module-level copy or the wall's own rules, because those are the same in both runs (M1, L1).
   The AST check that is meant to cover file reads can be bypassed (M1).
3. Yes. agent/reversal.py imports numpy, pandas and `View`, and reads only `v.t`, `v.today`, `v.bars`, `v.labels` and
   `v.members`.
4. Yes for every time-wall rule checked (list at the end), with the gaps below.

No high finding. One medium, five low.

## M1 (medium). A leaking agent can pass both the boundary test and non-interference by reading files

- Where: tests/test_boundaries.py:22-27 (FORBIDDEN and prefixes), 49-60 (`agent_import_problems`), 63-72
  (`agent_name_problems`); eval/leaks.py:103-115 and 137-142.
- Evidence. The boundary test's docstring (tests/test_boundaries.py:7-11) says file reads are stopped only by the
  name check. Two ways round it:
  - `from pandas import read_parquet as rp` passes: the import check accepts any name from an allowed library
    (lines 51-59 look only at the module), and the name check walks `Name` and `Attribute` nodes, never the
    `alias` in an import, so `rp(...)` is clean.
  - `np.fromregex(path, ...)` reads any text file (for example reference/price_events.csv, which lists the 2023
    bank failures) and is not in FORBIDDEN.
  And non-interference cannot catch such a read: `perturb` changes only the in-memory tables (leaks.py:47-100), so an
  agent holding future data from outside the World makes the same decisions in both runs.
- Check (run from the worktree root with D:\venvs\chrono-trader\Scripts\python.exe, on tests/synthetic.py's
  made-up world):

  ```python
  import sys, tempfile; from pathlib import Path; import numpy as np, pandas as pd
  sys.path[:0] = [".", "tests"]
  import synthetic, test_boundaries as tb
  from agent.reversal import ReversalAgent; from eval import leaks; from world.world import World
  T = synthetic.make_tables(0); lab = World(**T).labels.df   # stands in for a file on disk
  FUT = dict(zip(zip(lab.entity_id.astype(str), lab.share_class.astype(str), lab.date), lab.label))
  class OutOfBand(ReversalAgent):
      def score(self, f, v):
          return super().score(f, v) + 100 * np.array([FUT.get((e, c, v.today), 0.0) for e, c in zip(f.entity_id, f.share_class)])
  for how in leaks.HOW:
      print(how, leaks.non_interference(T, lambda: OutOfBand(warmup=15), "2017-01-03", "2017-03-15", how, seed=1))
  d = Path(tempfile.mkdtemp()); (d / "agent").mkdir(); p = d / "agent" / "evil.py"
  p.write_text("from pandas import read_parquet as rp\nx = rp('D:/chrono-data/store/labels.parquet')\n"
               "from numpy import fromregex\ny = fromregex('reference/price_events.csv', 'x', [('a', 'U9')])\n")
  tb.ROOT = d; print(tb.agent_import_problems(p), tb.agent_name_problems(p))
  ```

  Result: `[]` for scramble, shift and delete (not caught), although the agent's positions differ from the honest
  agent's on 1,345 rows; and `[] []` from both boundary checks.
- PLAN: plan_rules.md line 133 (PLAN L210: agent code imports nothing else), line 253 (PLAN L426: a test enforces
  it), line 385 (PLAN L609).
- Fix: in `agent_import_problems`, check every imported name and its alias against FORBIDDEN and the prefixes, and
  replace the deny list for numpy and pandas members with an allow list. For a real guarantee, run `decide()` in a
  subprocess that cannot read DATA_DIR or reference/, as the test's own docstring proposes.

## L1 (low). Non-interference trusts the wall's own availability rules

- Where: eval/leaks.py:30-44. `late_rows` classifies records with `world.world.visible_at`, the same function the
  World uses.
- Evidence: with `rules.bar` swapped for the vendor's midnight stamp (a leak in the wall), the 9:00 view on
  2017-03-15 holds 56 bars dated that day, and an honest agent still passes `non_interference` (scramble).
- Check: set `rules.bar = lambda d: pd.to_datetime(pd.Series(d)).dt.tz_localize("UTC")`, build
  `World(**synthetic.make_tables(0))`, count `v.bars.date >= v.today` in the view at 9:00 on 2017-03-15, then run
  `leaks.non_interference(..., "2017-01-03", "2017-03-15", "scramble", seed=1)`.
- Cover: this is by design (PLAN L251 perturbs by `available_at`), and the wall's rules have their own tests
  (tests/test_world.py:37-125, 200-206; tests/test_leaks.py:242-253 catches the midnight stamp). Nothing is wrong
  today; the point is that non-interference alone never proves the wall right.
- PLAN: plan_rules.md line 156 (PLAN L251), line 379 (PLAN L603).
- Fix: say so in eval/leaks.py's docstring, so no one reads a passing non-interference run as a check of the rules.

## L2 (low). A failed company's exit label is visible at 9:30, before the failure was public

- Where: world/rules.py:43-55, and the claim in its docstring at rules.py:8.
- Evidence: the store's at_close label for SVB Financial (entity 0000719739) is dated 2023-03-09 with end 2023-03-09,
  so `rules.label` makes it visible at 9:30 New York time on 2023-03-10. For a failure the label is -1
  (data_pipeline/store.py:20-23). The evidence row in reference/price_events.csv (line 119) cites Benzinga story
  31299421 at 11:47 ET on 2023-03-10 for the closure, and only a halt (story 31295313, 08:41 ET) before the open. So
  a view between 9:30 and 11:47 that day would show a total loss that was not yet public.
- Not reachable today: the loop and non-interference ask only for 9:00 views, and the first 9:00 view to show the
  label is 2023-03-13. The rule matters if an agent or report ever takes a view at another time.
- Check: `pd.read_parquet("D:/chrono-data/store/labels.parquet")` filtered to `at_close` and entity 0000719739 gives
  the date and end above; `rules.label(pd.Series([pd.Timestamp("2023-03-09")]), [True])` gives 14:30 UTC on
  2023-03-10.
- PLAN: plan_rules.md lines 34-35 (PLAN L27, L28: a failure halted before the next open is not known early).
- Fix: make a failure label visible at the time of its public evidence (store it in price_events.csv), or at the
  next session's decision time after the failure date; and reword rules.py:8 to match.

## L3 (low). The news rule uses `updated_at` only

- Where: world/rules.py:26-27.
- Evidence: in the store, 4 of 2,239,859 stories have `updated_at` before `created_at`, none by more than 15
  minutes, so no story is visible before it was created. A refreshed month could bring one that is.
- Check: on stories.parquet, count `updated_at < created_at` (4) and `updated_at + 15 min < created_at` (0).
- PLAN: plan_rules.md line 135 (PLAN L218).
- Fix: available at `max(created_at, updated_at) + 15 minutes`. It changes nothing on today's data.

## L4 (low). Non-interference covers less than PLAN 9.11 asks

- Where: tests/test_leaks.py:55-59 (3 random days, all in the first half of 2017, on the made-up world) and 302-305
  (the real store: one window, 2017-02-01 to 2017-03-15, scramble only).
- PLAN: plan_rules.md line 376 (PLAN L600: random days inside the dev years, scramble, shift and delete). The dev
  years are 2017 to 2019 (reference/split.json).
- Fix: add an opt-in slow test on the real store over random days across 2017 to 2019, with all three
  perturbations and at least one January pick day.

## L5 (low). The View docstring omits two columns the view carries

- Where: world/view.py:7-13. The store's labels also carry `end_open_time`, and stories carry `n_companies`
  (schemas of labels.parquet and stories.parquet). The World passes every column through.
- Not a leak: `end_open_time` is never later than the label's own visible time (rules.py:52-54), and `n_companies`
  depends only on identity spans that start at the first membership day (data_pipeline/identity.py:410-431,
  audit_news.py:41-59), so it uses no future membership.
- PLAN: plan_rules.md line 42 (PLAN L30: views hold copies with plain keys).
- Fix: list both columns in the docstring, or drop them from the view if agents should not use them.

## Checked and found sound

- Cut-off operators. `_Sorted.upto` (world.py:130-132) and `members_at` (world.py:159-163) use `searchsorted(...,
  side="right")`, so a row shows when its time is `<= t`; `late_rows` uses `> t` (leaks.py:37-43). This matches PLAN
  L210 (plan_rules.md line 133).
- Rules against PLAN. News at `updated_at` + 15 minutes and stories edited more than 3 days later dropped
  (rules.py:26-32; line 135-136, PLAN L218). Bars at 16:00 New York, also on early closes (rules.py:35-36; line 137,
  PLAN L219). Opens only in the World, never in a View (world.py:156, view.py:22; line 138, PLAN L220). Labels at the
  9:30 open that ends them, or later if it printed later, and at-close labels at the next session's open
  (rules.py:43-55; line 139 and 31, PLAN L221 and L31). Membership at 0:00 on the effective date (rules.py:58-59;
  line 140, PLAN L222). At 9:00 on day k the newest label is day k-2's (line 145, PLAN L230; tests/test_world.py:97).
- The 3-day rule leaks nothing: a story's fate depends on its final `updated_at`, and it shows only after that time.
- Time zones. `at` and `at_each` localize to New York and convert to UTC; `view(t)` refuses a naive time
  (world.py:167-168); `today` and the story day are New York dates (view.py:24, world.py:101). DST changes happen at
  2:00 and never touch 0:00, 9:00, 9:30 or 16:00 (line 144, PLAN L229).
- On the made-up world, every 9:00 view from 2017-01-03 to 2017-06-30 holds 0 bars dated today or later, 0 labels
  ending today or later, 0 stories past their available time and 0 sessions after today.
- `known_from` (world.py:65-86). A membership end that lies after t cannot change whether a record dated on or before
  t shows, since such a record is inside the spell either way; a later join only makes records show at that join. A
  rejoin gap stays hidden (EQT test, tests/test_world.py:179). Matches PLAN L30 (lines 39-41).
- Detached views. Mutating a view's bars and labels changes neither the World nor the next view; a view's attributes
  are `bars, joined, labels, members, sessions, stories, story_entities, t, today`, none of them a World; members are
  frozensets, keys plain strings, list columns tuples (world.py:107-118). Matches PLAN L30 (line 42).
- Sealed years refused unless `allow_sealed` (world.py:170-171).
- Splits. Bars hold raw prices: close ratios across the AAPL 2020-08-31, NVDA 2024-06-10 and TSLA 2022-08-25 splits
  are 0.258, 0.101 and 0.332, while `ret` stays a total return. No future split reaches a past price level (PLAN
  L231, line 146).
- Identity. `entity_id` is a CIK; bar symbols are the ones in use at the time: all 1,620 Facebook bars before
  2022-06-09 say FB, and likewise PCLN (541), DPS (633) and DLPH (485) before their renames (PLAN L205-208, line 132).
- News selection. data_pipeline/news.py downloads every Benzinga story, with no symbol list, so the stories table is
  not chosen by future membership. No duplicate story ids and no duplicate story-company pairs in the store.
  story_entities is gated twice: identity spans start at the first membership day, and `known_from` applies.
- Delistings and failures. A failed company's bars stop at its last trade (SVB's last bar is 2023-03-09); its exit
  label shows at the next open (see L2 for the 9:30 caveat).
- `perturb` keeps the view at t identical: changed records that would show by t are dropped (leaks.py:92-99), deleted
  joins and open-ended leaves only hide records that were already late. The planted leaks are caught
  (tests/test_leaks.py:215-229).
- agent/reversal.py. Picks on the year's first decision from bars dated in `[today - 1 year, today)`, members only,
  raw close times volume, best class per company; in 2016 on 2016-04-01 from January to March (PLAN L233, line 148).
  Features from bars up to the last close. Refits use only rows it has lived, joined to labels in the view, and fit
  the scaler on those rows (PLAN L232, line 147). It imports only numpy, pandas and `View` (PLAN L426, line 253).
