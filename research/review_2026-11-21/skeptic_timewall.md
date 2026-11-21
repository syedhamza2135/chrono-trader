# Skeptic: the time wall judge's findings (M1, L1 to L5)

This skeptic ran on Opus at high effort. It tried to refute each finding in `judge_timewall.md`. No code was changed.
Every check ran from the worktree root with `D:\venvs\chrono-trader\Scripts\python.exe`. The scripts are in
`research/review_2026-11-21/scripts/skeptic_timewall/`. Store reads printed counts, dates, ids and column names only.
No headline text and no prices were read.

| Id | Verdict | Judge's severity | Skeptic's severity |
|---|---|---|---|
| M1 | CONFIRMED | medium | medium |
| L1 | CONFIRMED | low | low |
| L2 | CONFIRMED (timing; story content not read) | low | low |
| L3 | CONFIRMED | low | info (low at most) |
| L4 | PARTLY | low | low |
| L5 | CONFIRMED (one supporting reason is imprecise) | low | low |

## M1. A leaking agent can pass the boundary test and non-interference by reading files

- Verdict: CONFIRMED. Severity: medium, as the judge gave it. The bypasses look deliberate rather than accidental,
  but PLAN L426 and L609 say a test enforces the boundary, and this test is the only guard on disk reads.
- Command: `scripts/skeptic_timewall/m1_boundary.py`. Part A puts each snippet in its own file under a temp `agent/`
  and runs both AST checks. Part B is a stronger check than the judge's: the agent reads a real parquet file on disk
  (written from the synthetic labels) through an aliased `read_parquet`, instead of an in-memory dict.
- Printed:
  - Caught (controls): `pd.read_parquet(...)` and `from pandas import read_parquet` used unaliased.
  - Missed: `from pandas import read_parquet as rp`, `from pandas import read_csv as rc`, `np.fromregex(...)`,
    `from numpy import fromregex`, and `from numpy import load as ld`. The last one is notable: `load` is in
    FORBIDDEN, yet the alias hides it.
  - Part B: non_interference problems = 0 for scramble, shift and delete. Over 2,467 shared decision rows, 1,345
    positions differ from the honest agent (the judge's 1,345 matches).
- Cited lines checked: tests/test_boundaries.py:7-11 (docstring: file reads stopped only by name), 22-27, 49-60 (the
  import check looks only at `module`, never at the names or aliases), 63-72 (walks only `Name` and `Attribute`
  nodes); eval/leaks.py:47-100 (perturb changes only the in-memory tables), 103-115, 137-142.
- PLAN: plan_rules.md lines 133, 253, 385 (PLAN L210, L426, L609).

## L1. Non-interference trusts the wall's own availability rules

- Verdict: CONFIRMED. Severity: low. It is a limit by design, and the bar case is caught by a separate test.
- Command: `scripts/skeptic_timewall/l1_rule_swap.py`. It swaps `rules.bar` for the midnight stamp, then runs
  non_interference in all three modes with the honest agent and with an agent that adds today's `ret` from any bar
  dated today (an agent that exploits the leak). This goes further than the judge, who ran the honest agent with
  scramble only.
- Printed: under the original rule, 0 bars dated 2017-03-15 or later in that day's 9:00 view. Under the midnight
  stamp, 56. Both agents pass all three modes under both rules (problems = 0 in all 12 runs). The separate
  `tests/test_leaks.same_day_bars` check flags 10 of 10 check days under the swapped rule.
- Cited lines checked: eval/leaks.py:30-44 (`late_rows` uses `world.world.visible_at` and `rules.*`, the same
  functions the World uses); tests/test_leaks.py:242-253 (the midnight-stamp test).
- PLAN: plan_rules.md line 156 (PLAN L251) and line 379 (PLAN L603).

## L2. A failed company's exit label is visible at 9:30, before the failure was public

- Verdict: CONFIRMED on the timing. I did not read headline text, so I could not confirm myself that story 31299421
  is the closure and 31295313 the halt; that rests on the evidence note in reference/price_events.csv line 119.
  Severity: low, since no 9:00 view shows it early.
- Note: the code follows PLAN's own wording. PLAN L27 says the last label "shows at the next session's open". The
  gap is between that rule and PLAN's claim that the failure "isn't known early". So the fix is a decision for the
  owner on the rule and the docstring, not a code bug against PLAN.
- Command: `scripts/skeptic_timewall/l2_l3_l5_store.py` (L2 part), plus a grep of line 119 for the ids and times only.
- Printed: 222 at_close labels, 3 of them a total loss. Entity 0000719739: date and end 2023-03-09, visible
  2023-03-10 09:30 New York, first 9:00 view to hold it 2023-03-13. Story 31295313 created and updated 2023-03-10
  08:41:44 New York; story 31299421 created and updated 2023-03-10 11:47:37 New York. Line 119 holds both ids with
  08:41 ET and 11:47 ET.
- The other two failures do not have the gap on the label side: entity 0001288784 (end 2023-03-10) is visible
  2023-03-13 09:30, and entity 0001132979 (end 2023-04-28) is visible 2023-05-01 09:30. I did not check when their
  failures became public.
- Cited lines checked: world/rules.py:8 and 43-55; data_pipeline/store.py:18-23.
- PLAN: plan_rules.md lines 34-35 (PLAN L27, L28). In PLAN.md itself these bullets are at lines 26 and 27: the digest is one line off here.

## L3. The news rule uses `updated_at` only

- Verdict: CONFIRMED. Severity: info, or low at most. It is hardening for data that does not exist today.
- Command: `scripts/skeptic_timewall/l2_l3_l5_store.py` (L3 part).
- Printed: 2,239,859 stories; 4 with `updated_at` before `created_at` (ids 5663495, 5663581, 5663867, 61242877); 0
  with `updated_at` plus 15 minutes before `created_at`. The largest gap is 0.48 minutes (29 seconds).
- Cited lines checked: world/rules.py:26-27.
- PLAN: plan_rules.md line 135 (PLAN L218), read at PLAN.md:218.

## L4. Non-interference covers less than PLAN 9.11 asks

- Verdict: PARTLY.
- What holds: no non-interference test runs on any day after 2017-06-30, because the made-up world ends there. On
  the real store there is one call (tests/test_leaks.py:305), for one day (2017-03-15, from 2017-02-01) and scramble
  only. No day in 2018 or 2019 is checked. PLAN L600 asks for random days inside the dev years, 2017 to 2019.
- What does not hold: the judge's "3 random days" undersells the made-up world's coverage. Besides the 3 Hypothesis
  examples, the fixed tests run 19 (day, mode) pairs over 15 days from 2017-01-03 to 2017-06-02, with every mode used
  (scramble 6, shift 7, delete 6). The January pick day 2017-01-03 already runs all three modes there
  (`test_on_the_pick_day_too`). So the fix's "at least one January pick day" is new only for the real store.
- Severity: low.
- Command: `scripts/skeptic_timewall/l4_coverage.py`.
- Printed: synthetic world 2016-01-04 to 2017-06-30; 19 fixed pairs, 15 distinct days; Hypothesis max_examples 3,
  drawn from 2017-01-03 to 2017-06-30; 6 non_interference calls in tests/test_leaks.py, 1 on real_tables (line 305);
  no other test file calls it.
- Cited lines checked: tests/test_leaks.py:27-35, 39-59, 280-305; reference/split.json (dev 2017-01-03 onward).
- PLAN: plan_rules.md line 376 (PLAN L600), read at PLAN.md:600.

## L5. The View docstring omits two columns the view carries

- Verdict: CONFIRMED. Severity: low (a doc gap, not a leak).
- Commands: `scripts/skeptic_timewall/l2_l3_l5_store.py` (L5 part), `l5_passthrough.py` and `l5_identity_spans.py`.
- Printed: the store's labels carry `end_open_time` and its stories carry `n_companies`; neither is in
  world/view.py:7-13. On the made-up world with both columns present, the 9:00 view on 2017-03-15 carries both, so
  the World passes them through. Of 1,419,181 labels with `end_open_time` set, 0 have it later than the label's own
  visible time.
- One reason in the judge's "not a leak" argument is imprecise. It says identity spans start at the first membership
  day. For 10 of 746 entities, the span in reference/identity.csv starts 1 to 4 calendar days before the store's
  first `member_from` (for example CBOE 2017-02-28 against 2017-03-01, AJG 2016-05-27 against 2016-05-31). Each is
  the last day, or weekend, before the effective date. This does not change `n_companies`: in
  data_pipeline/audit_news.py:52-54 each tag counts as one company whether it resolves to an entity or not, and these
  10 entities each have one symbol, so no two tags can merge. That last step is from reading the code, not a run.
- Cited lines checked: world/view.py:1-30; world/rules.py:52-54; data_pipeline/identity.py:410-431;
  data_pipeline/audit_news.py:41-59.
- PLAN: plan_rules.md line 42 (PLAN L30). In PLAN.md itself this bullet is at line 29: the digest is one line off here.
