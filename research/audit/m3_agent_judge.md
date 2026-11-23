# M3 judge: can Track A's agent learn about the future?

Scope: `agent/track_a.py` (whole file), `tests/test_track_a.py`, `world/view.py`, `agent/reversal.py` lines 1-60.
Date: 22 Nov 2026. I did not read PLAN.md, `world/world.py`, the store or other notes. PLAN rules are as the brief
summarised them.

## Verdict

No must-change finding. I found no path by which a record after t, or a label before it was realized, reaches a
decision. Every input comes from the view at t, and all state comes from earlier views. Five should-change items: one
is a gap edge case in validation, one is a missing-value mismatch, and three are about weak tests.

## What I ran

- Fast tests (8 passed, 3.3 s): `-k "hand_computation or 200_days or memory_kept or target_is or standardized_ridge
  or rank_ic or ranks_holds"`.
- `judge_checks.py` (made-up frames; copy kept below). It gave two results:
  - check1: the scaler mean from the sums is 2.25, but the mean of the observed values is 3.0. A missing row scales to
    -1.17 in training and to 0.0 at scoring.
  - check2: the last training day is 27 Jun, the gap is 28 Jun and validation starts 29 Jun. A training label visible
    at 13:30 UTC on 29 Jun is after the first validation decision (13:00 UTC). It is still trained on, and the
    embargo test's condition still holds.
- Not run (per the brief, or not needed): the non_interference, real_store and same_output tests, and the
  validation-split, embargo, six-months and hold tests. I make no claim about their results.

## Should-change

S1. The gap is one lived day, not a time rule. `agent/track_a.py:296-300`; the docstring at 26-27 says "every
training label was realized before the first validation decision". If a training day's label ends more than one
session later (no official open on the gap day), it becomes visible after the first validation decision, and it
still trains the model that validation scores. Rerun: check2. Effect: only the choice of penalty and pooling is
touched, and only a little. Live decisions are unaffected, because every label used is in the view at t.
Answer to question 2: the date order is right (`recent` is sorted at 282 and `held` is its tail). One day is enough
for a one-session label, but not for a longer one. Fix: store each block's latest label `visible_at` in `recent`, and
also hold out every block whose latest `visible_at` is at or after the first validation day's 9:00.

S2. A missing feature counts as raw 0 in training, but as the mean at scoring. The sums add `np.nan_to_num(x)` at
276 and 303. Validation and scoring use `np.nan_to_num((X - mean) / std)` at 308 and 326. The docstring (32) says a
missing value counts as the mean. Rerun: check1. This is not a leak, but it changes results wherever a price feature
is NaN: a pick with no bars, vol20 with fewer than 2 returns, or dvol_ratio. One-line fix: apply `np.nan_to_num` to
the raw X before scaling at 308 and 326 (and say "counts as 0" in the docstring), or keep nan-aware counts in `Sums`.

S3. The embargo test is close to a tautology. `tests/test_track_a.py:243-246` does check every refit. But
`latest_label` is the maximum `visible_at` of labels already in the view (`track_a.py:277`), and those are at or
before t by the View's construction, so the test only checks the View. It does not test the validation boundary.
Fix: record in `fits` the latest label `visible_at` of the training blocks (outside `held`) and the first validation
day, and assert that the first is before that day's 9:00.

S4. The validation-split test checks only a lower bound. `tests/test_track_a.py:237` asserts that the subtracted rows
are more than `20 * val_days`. It would still pass if the gap day were missing or the wrong days were held out. Fix:
record the held row count and dates in `fits`, then assert that they equal the last `val_days + 1` blocks.

S5. The same-output test fixes the hash seed in both runs (`tests/test_track_a.py:316`), so it cannot catch any
dependence on set or dict order. From reading the code I see none: sets are used only inside `isin` (152, 174);
memory dict order follows sorted groupbys (211); and the decay loop (201) does not depend on order. Fix: run the
second process with `PYTHONHASHSEED=1`. Not run.

## Notes

N1. `settle` runs only inside `refit` (293), so once a month. The 10-session rule therefore means "at the first
refit after 10 sessions", and rows whose labels arrive between session 10 and that refit are kept. This is not a
leak, because the labels come from the view. Call `settle` on every decision, or document the monthly timing.
N2. Ties: the loop at 302-314 visits pooling first, so on a tie "last" at any penalty beats "avg" at a larger one.
The docstring (29-30) puts the penalty first. It hardly matters.
N3. Watch-only: `self.positions` keeps the targets from before the zeroing (381-383). The band and the hold in
January 2017 therefore carry on from the virtual 2016 book. Not a leak. Check it against PLAN 5.5.
N4. News is keyed by entity only (211, 233). That is fine, because the pick keeps one class per entity
(`reversal.py:46`).
N5. `_session_index` (180-184) assumes t is 9:00 exactly. A story available after the last session's 9:00 would get
age -1 and a weight above 1. That cannot happen if the clock decides at 9:00, but I did not check `world/clock.py`.
N6. Not checked: whether labels are unique per (entity, class, date), since duplicates would break `x[have]` at 263
to 272. Also not checked: whether story_entities and embeddings are unique per story, since duplicates would double
count at 175.
N7. The memory on the first decision depends on the run's start (the 90-day window). The leak tests start on
2016-10-03, not on the production start. Both runs of a leak test share a start, so equality is not affected.
N8. Float32 rounding happens once (252), and the same X is stored and scored. Nothing in the agent is random.

## Checked and found right

- Price features use bars before today, within 200 days (150). This is confirmed by the hand test with today's bar
  set to 0.5.
- A news pair is available at the later of the embedding's and the link's `visible_at` (176). Stories new since the
  last decision use `last_t` (198); on the first decision they use the previous session's 9:00 (195, 223). Ages are
  in sessions. The memory kept day by day equals the memory started from the view (test passed).
- Labels are read only from `v.labels` (257). The target is the log label minus the mean over the present rows
  (270-271). A block enters only when all its labels are present or 10 sessions have passed (265).
- The validation scaler comes from the training sums only (306). The final fit uses all the sums, so labels from day
  k-2 and earlier (316-317). Validation predictions use the features stored at their own decisions.
- There is no fit before 6 lived months (366) or with fewer than 20 training days (297). Positions are 0 before
  `trade_from` (382). The policy uses only predictions and its own past positions.
- The hand tests use independent arithmetic: price, news, memory, target, the ridge algebra and the rank IC.

## Rerun script (judge_checks.py)

It is kept in the judge's scratchpad. Its logic, for rerunning:
- check1: put rows 1, 3, NaN, 5 into `Sums(1)` through `np.nan_to_num`, then compare `scaled()[0]` with
  `np.nanmean`.
- check2: build 5 stocks on business days from 4 Jan to 30 Sep 2016 and make each day's labels visible at 9:30 the
  next session. Find T, the last training day, from a dry `settle` and `_val_days`. Make one of T's labels visible at
  9:30 on the first validation day, call `refit`, and see that T's rows are trained on (965 rows in the sums, 630
  training rows).
