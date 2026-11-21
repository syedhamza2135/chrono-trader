# Skeptic: PLAN consistency, news availability and the M2 reader plan

Ran on Opus (claude-opus-5-5) at high effort, 2026-11-21, in the worktree `full-review-1121-0eb11c` (HEAD 3f45e94).
It checks the findings in `research/review_2026-11-21/opus_plan_m2.md` and answers one open question.

Sources read: that review and its three scripts; PLAN.md only at the cited lines; the M2 note only at cited lines
(from `git show claude/awesome-panini-89f869:research/m2_kickoff.md`); `world/rules.py` and `reader/vintage.py`; the
digests `plan_rules.md`, `code_map.md` and `store_tables.md`. No price, label value or headline was printed. New
scripts are in `research/review_2026-11-21/scripts/skeptic_plan_m2/` and run with
`D:\venvs\chrono-trader\Scripts\python.exe -I <script> <worktree path>`.

"PLAN L" is PLAN.md; "M2 L" is the M2 note; "digest" is `docs/digests/plan_rules.md`.

## H1. The embeddings table has no availability time and no way into a view

- Verdict: PARTLY. The facts hold. The severity does not.
- Severity I'd give: Medium (was High).
- Checks:
  - PLAN L205-208 put `available_at` on every record. PLAN L524 gives `embeddings` as `story_id, vintage_year,
    emb_last, emb_avg`, no `available_at`. PLAN L216-224 has no embeddings row. `world/rules.py:3-9` has none.
  - `grep -rn -i embedd world sim eval agent tests reader` finds only `tests/test_suites.py:91-95` (skips: "no
    embeddings yet (M2)"), `reader/vintage.py:21-24` (`breaches`) and `reader/__init__.py:1`. Nothing in `world`.
  - `ls D:/chrono-data/store` has no embeddings file. The store schemas list seven tables, none of them embeddings.
  - The M2 note grep for `view|visible|available` hits only lines 13, 40-71, 163-164, 254 and 260, none about the
    embeddings' timing. M2 L198-208 describes the table and its tests with no time column.
  - PLAN L600-601: the scramble covers records "available after t", and no planted leak is an embedding.
- Why not High: nothing is built and nothing leaks today. PLAN L210 already says the agent only ever calls
  `world.view(t)`, so a `news_memory` that joins the whole table outside `World` would break a rule that exists. The
  gap is that the plan does not say how the table reaches a view, and the tests would not catch the breach. That is a
  plan gap to close before M3 reads the table, best in M2 step 5. The fix in the review (each row takes its story's
  `visible_at`, loaded in `World`, in the scramble, plus a planted leak) is right.

## M1. PLAN's claim that the backtest "sees exactly what the live job will see" does not hold

- Verdict: PARTLY.
- Severity I'd give: Low (was Medium).
- Checks:
  - PLAN L218 says "sees exactly what the live job will see". `world/rules.py:26-27` uses `updated_at` plus 15
    minutes, and `rules.py:30-32` drops stories edited more than 3 days later. `research/audit/audit.md:18` gives
    0.0% to 2.5% a year edited more than 15 minutes later. So edited stories make "exactly" false, and the replay is
    the less informed side. Confirmed.
  - `grep -n -i -E "15 min|latency|delay|late" research/audit/news.md research/audit/audit.md` finds no measured news
    delivery delay. Confirmed.
  - `grep -n -i minute data_pipeline/news.py` prints line 34: the free plan "refuses the latest 15 minutes, so the
    current month stops 20 minutes ago", and line 36 uses `timedelta(minutes=20)`. So the 15 minutes is the API's
    refusal window (also PLAN L149), not a free guess. The 20 minutes is a margin in the bulk download.
- Why partly: the "replay better informed than live" case needs an M5 job that copies the 20-minute margin, which does
  not exist yet. What stays open is Alpaca's own lag after `updated_at`, which nobody has measured. The rewording of
  L218 and the M5 measurement are both worth doing, but nothing in M1 to M4 is affected.

## M2. The cutoff check has no outcome for "too weak", so M2's done-when may be unreachable

- Verdict: CONFIRMED.
- Severity I'd give: Medium (unchanged).
- Checks:
  - PLAN L434: done when "the cutoff check passes (or any failing vintage is replaced)".
  - M2 L227-229 adds "too weak to pass anything, not as a pass". M2 L239-242: only a failed loss check fails a
    vintage, and replacement is "the newest earlier vintage that passes". No line says what a too-weak result does.
  - M2 L219 and L221: check A for V 2015 to 2023 (9), check B for 2015 to 2024 (10), so 19 checks, as the review says.
- One more gap the review missed: M2 L174 says 2014 serves only as the 2015 vintage's predecessor, and M2 L165-166
  says the store has no 2014 headlines, so 2014 can never pass. If the 2015 vintage fails, there is no earlier passing
  vintage to read 2016's news. The owner's decision before the pilot should cover that case too.

## L1. PLAN's status line is stale: M1 is built

- Verdict: CONFIRMED.
- Severity I'd give: Low (unchanged).
- Checks: PLAN L3 ends "The time wall, the reader and the learner aren't built yet." `git log --oneline master`
  shows 93d8f70 "Build M1", 90ecb8a, 658db1c, dd40a5f, then 3f45e94. PLAN L24-30 are dated 7 and 8 Nov, and L497
  contains "On 8 Nov M1 added three rows".

## L2. The label rule in PLAN 5.1 and the "k-2" rule miss days with no official open

- Verdict: CONFIRMED.
- Severity I'd give: Low (unchanged).
- Checks:
  - PLAN L221: "The open on day d+1". PLAN L230 and L535: day k-2 labels are known at 9:00 on day k. PLAN L26: a
    label runs from one official open to the next.
  - Reran `opus_plan_m2/label_span_counts.py`: 1,419,403 labels, 1,419,181 not at a close; spans of 1 session
    1,418,656 and 2 sessions 525.
  - New `skeptic_plan_m2/l2_k2_rule.py` applies `rules.label` itself: 525 labels dated day k-2 are not visible at
    9:00 on day k (0 of them at a close), on 16 distinct dates from 2018-01-23 to 2023-06-08.
- Views follow `rules.label` (`world/rules.py:43-55`), so nothing leaks. The risk is only M3 building training rows by
  date from the PLAN wording.

## L3. PLAN 9.4's table list does not match the store

- Verdict: CONFIRMED.
- Severity I'd give: Low (unchanged).
- Checks: PLAN L521-526 against the Parquet schemas (`pq.read_schema`, names only). The store has `bars` (one table,
  with `ret`, `incomplete`, `member`, `no_trade`), `opens`, `labels`, `stories` (`story_id, created_at, updated_at,
  headline, symbols, n_companies`), `story_entities`, `membership` and `identity`. No `bars_raw` or `bars_adj`, and
  `stories` has no `available_at`, `summary`, `has_content`, `source` or `n_symbols`. The review missed two more:
  `membership` is `entity_id, member_from, member_to`, not PLAN L525's `date, entity_id`, and `identity` also has
  `share_class`.

## L4. PLAN still describes reading 2015 news and the 30 Oct speed; M2's update list misses some lines

- Verdict: PARTLY. All cited lines check out, but one of the four fixes is already covered.
- Severity I'd give: Low (unchanged).
- Checks:
  - M2 L165-168 and L278 leave 2015's 31,907 stories out; M2 L174 keeps 2014 for the check only. PLAN L434 says
    "Every filtered story", L548 gives `news_memory` no start, and L627 lists "2014 to 2024" with no role for 2014.
  - M2 L121: 10 a second, about 14 hours. PLAN L167, L364, L513 and L628 say about 21 hours.
  - M2 L258-259 updates PLAN 5.2, 9.3 and 9.13. From the headings, L167 is in section 3 (L79), L364 in 6 (L360), L434
    in 9.2 (L428), L548 in 9.6 (L542), L513 in 9.3 and L628 in 9.13. So 3, 6, 9.2 and 9.6 are missing, as the review
    says.
- Why partly: the Brexit probe is PLAN L283, inside 5.2 (L269-290), which M2's update list already covers. That part
  of the fix only needs a note to change the probe, not a new section.

## L5. The M2 note's starting point is stale, and its branch lacks dd40a5f

- Verdict: CONFIRMED.
- Severity I'd give: Low (unchanged).
- Checks:
  - `git merge-base claude/awesome-panini-89f869 master` prints 658db1c. The branch tip is 2ace1c3.
    `git log --oneline master ^claude/awesome-panini-89f869` prints dd40a5f and 3f45e94.
  - M2 L13-16 cite `b2b9441`, `c9c09cf`, `87bacdc` and master `7b4a200`. `git branch -a --contains` puts the first
    three only on `backup/pre-rewrite/m1` and `backup/pre-rewrite/m2`, and `7b4a200` also on
    `backup/pre-rewrite/master`. So the note cites pre-rewrite ids even though its branch sits on the rewritten
    history.
  - M2 L22 lists failed-bank exits as open; dd40a5f closed them.
  - `git diff --stat claude/awesome-panini-89f869 master -- world data_pipeline reader`: `world/rules.py` 2 lines,
    `data_pipeline/store.py` 39 lines, plus the branch's own `reader/download.py` and `reader/vintages.json`. The
    `reader/vintage.py` diff is empty.

## L6. The embeddings completeness test checks ids, not text

- Verdict: CONFIRMED.
- Severity I'd give: Low (unchanged).
- Checks: M2 L204-208: the completeness test is "exactly one row" per `story_entities` story from 2016 on. M2 L201:
  `embeddings.json` holds "the count and a hash of the story set". Neither names `updated_at` or the text. The M2
  note grep for `updated_at|hash` hits only line 201. It is staleness, not a leak, and only stories edited near a
  fetch's end could change.

## L7. M2 has no daily path for the forward test

- Verdict: CONFIRMED.
- Severity I'd give: Low (unchanged).
- Checks: M2 L155-156 says M5 reads each day's news "with the same code". M2 L186-201: a batch by vintage, parts of
  5,000, and a finish that writes the whole table. The note grep for `append|daily|each day` hits only line 156. PLAN
  L178 and L336 need the day's decisions before the open. It is an M5 item, not an M2 defect.

## L8. The plan digest's line numbers are one too high in two places

- Verdict: CONFIRMED, and wider than stated.
- Severity I'd give: Low (unchanged).
- Checks:
  - `grep -n "1,371,723\|511,678\|GitHub Actions" PLAN.md`: L18, L25, L178. The digest cites them as L19, L26 and
    L179 (digest 13, 30, 114).
  - New `skeptic_plan_m2/l8_digest_offsets.py` scores each of the digest's 351 "L" cites against PLAN lines n-1, n
    and n+1 (word overlap; prints line numbers only). Runs at offset -1: digest 8-58 (PLAN L11-L68 cited), 62-66,
    72-78, 81-86 and 90-118 (L141-L186 cited). By hand: digest 50 (L41), 75 (L109), 84 (L128), 100 (L154), 115
    (L183) and 118 (L186) each match the PLAN line one earlier. So the off-by-one covers most of digest 8-118, not
    only 8-43 and 106-114. A few single +1 hits later in the digest are likely wrapped lines and were not checked.
- Fix: regenerate digest lines 8 to 118, not just the two ranges.

## Open question: a label ending on an ex-date, seen between 9:30 and 16:00

Question: a label whose end day is a distribution's ex-date uses that day's close (another skeptic, at
`data_pipeline/store.py:188`; `store_tables.md:51` says the last factor is "last day open/close"). Can it show in a view
taken between 9:30 and 16:00 New York on the ex-date?

- Answer: yes, in a view taken at that time. No decision sees it, because the simulator and the leak test only take
  views at 9:00.
- Severity I'd give: Low. A latent leak in `World.view(t)` for mid-session times, not in any run today.
- The rule: `world/rules.py:43-55`. A label not at a close is available at 9:30 on its end date, or at the later
  printed open time (line 54). Nothing in it waits for the end day's close.
- Check: new `skeptic_plan_m2/oq_exdate_label_visibility.py` (`World.load()`, dev years only):
  - 58 `total_return` events in `reference/price_events.csv` (the distributions), all 58 matched to a store bar, and
    58 labels not at a close end on those ex-dates.
  - By `rules.label`, all 58 are available before 16:00 on the ex-date (0 at or after). The times are 09:30 (43),
    09:31 (6), 09:32 (4), 09:33 (2), 09:37 (2), and one more.
  - 24 of them are in the dev years (before the sealed start, 2020-01-02). All 24 are in a real 12:00 New York view
    on the ex-date. None is in the 9:00 view that day. Examples: 2016-04-08 entity 0001336917, 2016-05-13 entity
    0000316206.
  - `grep -rn "\.view(" world sim eval agent` finds only `sim/simulator.py:129` and `eval/leaks.py:110`, both at
    `world.clock.decision_time(day)`, which is 9:00 (`world/clock.py:14`). The next 9:00 view is the next session's,
    after the close has printed.
- Not checked: I did not read `store.py` (outside this brief), so the dependence on the close comes from the other
  skeptic and the digest. I counted only the 58 events in `price_events.csv`. If the bars' `ret` also carries ordinary
  dividends, more labels are affected. Counting them would need prices, which this check does not read.
- Fix: any view other than 9:00 (for example an M5 intraday check) should not see these labels early. Either make
  `rules.label` wait for 16:00 on the end day when a distribution falls on it, or build the last factor without that
  day's close.
