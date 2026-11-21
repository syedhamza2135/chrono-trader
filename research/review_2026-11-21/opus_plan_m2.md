# Review: PLAN consistency, news availability and the M2 reader plan

Ran on Opus (claude-opus-5-5); the lead's brief asked for high effort. Written 2026-11-21 in the worktree
`full-review-1121-0eb11c` (HEAD 3f45e94; PLAN.md is unchanged since dd40a5f, `git diff --stat dd40a5f HEAD -- PLAN.md`
is empty).

Sources read: `docs/digests/plan_rules.md`, `research/review_2026-11-21/digest_plan_notes.md`,
`docs/digests/code_map.md`, `docs/digests/store_tables.md`, `world/rules.py`, `reader/vintage.py`, the M2 note via
`git show claude/awesome-panini-89f869:research/m2_kickoff.md`, and PLAN.md only at the cited lines. The store checks
read ids, dates and flags only, never a price, a label value or a headline. Their scripts are in
`research/review_2026-11-21/scripts/opus_plan_m2/` and run with `D:\venvs\chrono-trader\Scripts\python.exe -I <script>`.

Line references: "PLAN L" is PLAN.md; "digest" is `docs/digests/plan_rules.md`; "M2" is the M2 note's line.

## High

### H1. The embeddings table has no availability time and no way into a view

- PLAN L205-208 (digest 132): every record carries `available_at`. PLAN L210 (digest 133): the agent sees only
  `world.view(t)`. PLAN L524 (digest 322): the `embeddings` table is `story_id, vintage_year, emb_last, emb_avg`, with
  no `available_at`. The rules table PLAN L216-224 (digest 135-142) has no row for embeddings, and neither has
  `world/rules.py:3-9`.
- `View` holds `bars, labels, stories, story_entities` only (`docs/digests/code_map.md:35`), and `World.load` reads
  six store files (`code_map.md:48`). No embeddings.
- The M2 note builds `D:\chrono-data\store\embeddings.parquet` (M2 L32-33, L198-201) and says how it is tested
  (M2 L204-208), but nowhere says how it reaches a view or what time it carries
  (`git show claude/awesome-panini-89f869:research/m2_kickoff.md | grep -n -i -E "view|visible|available"` finds
  only the story-set lines 40-71 and 163-164).
- Why it matters: the news features (PLAN L546-548) are built from this table. If M3 joins it outside `World`, the
  non-interference test (PLAN L600, digest 376), which scrambles records "available after t", has nothing to scramble
  in it, and none of the planted leaks (PLAN L601) is an embedding. A `news_memory` built from the whole table would
  pass every listed test.
- Check: `grep -n -i "embedd" docs/digests/code_map.md` (only `reader/__init__.py` and `breaches`); PLAN L524.
- Fix: give each embedding row its story's `visible_at` (the later of the story rule and `known_from`, as
  `world.py:89` does for `story_entities`), load it in `World`, expose it in `View`, and include it in the
  non-interference scramble. Add a planted leak "an embedding of a story not yet available", in M2 step 5 or before
  M3 reads the table.

## Medium

### M1. PLAN's claim that the backtest "sees exactly what the live job will see" does not hold

- PLAN L218 (digest 135) justifies the news rule: the text is the latest version and the free plan delivers news about
  15 minutes late, "so the backtest sees exactly what the live job will see".
- Edited stories break this. Live, a story shows at its first `updated_at` with its first text. In the replay it shows
  only at its final `updated_at` (`world/rules.py:26-27`), with its final text. And the live job cannot know that a
  story will be edited more than 3 days later, so it cannot apply the drop rule (`rules.py:30-32`). The audit puts
  edits more than 15 minutes after publishing at 0.0% to 2.5% of stories a year (`research/audit/audit.md:18`).
  The replay is the more conservative side, so this is not a leak.
- The 15 minutes itself is not shown for news. PLAN L149 lists "the latest 15 minutes of data held back" as a
  free-plan property in general. `grep -n -i -E "15 min|latency|delay" research/audit/news.md research/audit/audit.md`
  finds no measurement of news delivery delay. The only fetch code holds back 20 minutes, not 15
  (`code_map.md:139` and `:270`, `data_pipeline/news.py:31-36`). If the M5 job fetches with that margin, at 9:00 it
  sees stories updated up to 8:40, while the replay shows those updated up to 8:45. That would make the replay a
  little better informed than live.
- Fix: reword PLAN L218 to say the replay is at most as informed as live, not equal to it. In M5, measure the live
  delay, make the live fetch cutoff and `NEWS_DELAY` the same number, and log the `updated_at` of each story version
  the live job read.

### M2. The cutoff check has no outcome for "too weak", so M2's done-when may be unreachable

- PLAN L434 (digest 258): M2 is done when "the cutoff check passes (or any failing vintage is replaced)".
- The M2 note adds a third outcome: if a vintage's gains on its own year cannot be told from zero, "the check is
  reported as too weak to pass anything, not as a pass" (M2 L227-229). No line says what M2 does then. Replacement
  (M2 L241-242) applies only to a failed check, and a too-weak older vintage cannot be shown to pass either.
- With 19 one-sided checks at 95% (check A for 2015 to 2023, check B for 2015 to 2024, M2 L217-222), some intervals
  may touch zero by chance. A false fail only moves a year to an older model, which is safe, but it can cascade.
- Check: `git show claude/awesome-panini-89f869:research/m2_kickoff.md | sed -n 224,242p`.
- Fix: before the pilot (M2 step 2), the owner decides what a too-weak result means for M2's done-when (for example:
  keep the vintage and report it, or read that year with the newest vintage that passes). Write it into M2 and
  PLAN L434.

## Low

### L1. PLAN's status line is stale: M1 is built

- PLAN L3 (digest 4): "The time wall, the reader and the learner aren't built yet." PLAN's own decisions describe M1
  work (L24-L30, all 7 to 8 Nov) and L497 says "On 8 Nov M1 added three rows". `git log --oneline master` shows
  93d8f70 "Build M1" through dd40a5f. PLAN L386 and L433 are milestone definitions, so they are fine.
- Fix: update L3 to "M0 and M1 are done; M2, the reader, is under way".

### L2. The label rule in PLAN 5.1 and the "k-2" rule miss days with no official open

- PLAN L221 (digest 139): a day-d label is available at "the open on day d+1". PLAN L230 and L535 (digest 145, 331):
  at 9:00 on day k, labels to day k-2 are known.
- But a label runs to the next official open (PLAN L26, digest 33), and 519 member stock-days have none (PLAN L25).
  In the store, 525 labels that do not end at a close span two sessions, so a day k-2 label of that kind ends at day
  k's open, after the 9:00 decision. `rules.label` gets this right (`world/rules.py:43-55`), and views only show what
  is visible, so nothing leaks today.
- Check: `scripts/opus_plan_m2/label_span_counts.py` prints 1,418,656 labels spanning one session and 525 spanning two
  (of 1,419,181 not at a close).
- Fix: make L221 say "the next official open", and make L230 and L535 say "labels visible in the view" rather than
  "day k-2 and earlier", so M3 does not build training rows by date.

### L3. PLAN 9.4's table list does not match the store

- PLAN L521-522 (digest 319-320): `bars_raw` and `bars_adj`, and a `stories` table with `available_at, summary,
  has_content, source, n_symbols`.
- The store has one `bars` table with `ret`, `incomplete`, `member` and `no_trade`, plus `opens` and `labels`, which
  PLAN 9.4 omits. `stories` has `story_id, created_at, updated_at, headline, symbols, n_companies` and no
  `available_at`, which `World` computes (`docs/digests/store_tables.md:7-66`, `code_map.md:42`).
- Fix: rewrite PLAN 9.4 from `store_tables.md`, and say that availability is computed by `world/rules.py` at load,
  not stored.

### L4. PLAN still describes reading 2015 news and the 30 Oct speed; M2's update list misses some lines

- The owner left 2015's 31,907 stories out (M2 L161-168, L278) and kept the 2014 vintage for the cutoff check only
  (M2 L174). PLAN L434 still says "every filtered story", PLAN L548 gives `news_memory` no start date (M2 L167 says
  news features start on 2016-01-01), and PLAN L627 lists 2014 to 2024 with no role for 2014.
- M2 measured 10 headlines a second, about 14 hours for 502,712 (M2 L121). PLAN L167, L364, L513 and L628 say about
  21 hours. M2 step 5 updates PLAN 5.2, 9.3 and 9.13 (M2 L258-259), which leaves L167 (section 3), L364 (section 6),
  L434 (9.2) and L548 (9.6).
- PLAN L283 uses "Brexit" as a pre-2016 probe. M2 L236-237 notes the word dates from 2012 and changes the probe.
- Fix: add sections 3, 6, 9.2 and 9.6 and the Brexit probe to M2 step 5's PLAN update.

### L5. The M2 note's starting point is stale, and its branch lacks dd40a5f

- M2 L13-16 cites commits `b2b9441`, `c9c09cf`, `87bacdc` and master `7b4a200`, and M2 L22-23 lists failed-bank exits
  as open. `git branch --contains 87bacdc` shows only `backup/pre-rewrite/m1` and `backup/pre-rewrite/m2`: these are
  pre-rewrite ids. `git merge-base claude/awesome-panini-89f869 master` is 658db1c, so the branch lacks dd40a5f, which
  changed `world/rules.py:8` and `data_pipeline/store.py` (`git diff claude/awesome-panini-89f869 master --stat`).
- The store counts M2 uses still match the current store (534,619 stories in `story_entities`,
  `store_tables.md:70`), and `reader/vintage.py` is the same on both.
- Fix: rebase the M2 branch on master before building, and refresh "Where things stand".

### L6. The embeddings completeness test checks ids, not text

- M2 L204-208: the test checks that every `story_entities` story from 2016 on has exactly one row, and
  `embeddings.json` records "the count and a hash of the story set" (M2 L200-201). If news is downloaded again (M5 or
  a refresh), a story edited within 3 days keeps its id but gets a new headline and `updated_at`. Its old embedding
  would pass. The old text was public earlier, so this is staleness, not a leak.
- Fix: hash `story_id` with `updated_at` (or a headline hash) per row in `embeddings.json`, and test it.

### L7. M2 has no daily path for the forward test

- M2 L155-156 says M5 will read each day's news with the same code. The job's shape (M2 L184-201) is a batch run by
  vintage plus a finish step that rewrites the whole table. PLAN L178 and L336 require the day's decisions before
  the open. Nothing yet embeds one morning's new stories and appends them.
- Fix: note this as an M5 item in M2, or give `reader.embed` an append mode for one day's stories.

### L8. The plan digest's line numbers are one too high in two places

- `docs/digests/plan_rules.md` lines 8-43 cite PLAN L11 to L31, but the text is one line earlier, at PLAN L10 to L30 (for example digest 30
  says L26 for the 519 of 1,371,723; it is PLAN L25). Digest 106-114 cite L166-L179 for lines at L165-L178.
- Check: `grep -n "1,371,723\|511,678\|GitHub Actions" PLAN.md`.
- Fix: regenerate those digest lines, since later agents cite them.

## Questions answered

**(3) News availability.** PLAN L218, L603 and `world/rules.py:17-32` agree: `updated_at` plus 15 minutes, and stories
edited more than 3 days after publishing are dropped. The vintage comes from `created_at`'s New York year
(PLAN L279, `reader/vintage.py:11-18`), and visibility from `updated_at`. That pairing is safe: vintage Y-1 ends before
any year-Y story is created, and the story shows no earlier than its creation. Checks from
`scripts/opus_plan_m2/news_timing_counts.py`: 0 stories in the store are edited more than 3 days later, and 0
`story_entities` stories have a New York creation year different from their availability year, so the 31 December
case in L279 does not occur and no 2015 story becomes visible in 2016. 4 stories have `updated_at` up to 29 seconds
before `created_at` (ids 5663867, 5663581, 5663495, 61242877; one is in `story_entities`). `keep_story` has no lower
bound, but all 4 still become available after their creation, so it is harmless. The gaps are M1 (live versus replay)
and H1 (embeddings).

**(4) The M2 plan.** It follows PLAN on vintage selection (M2 L29-31 equals PLAN L279 and `vintage.py`), the table
schema (M2 L32, L198-201 equals PLAN L524), the poolings (M2 L192-195 equals PLAN L280), and the cutoff check's V-1 to
V+2 cells. Its 41 cells check out: 2 for 2014, 3 for 2015, and 4 each for 2016 to 2024. Its counts add up: 534,619
minus 31,907 is 502,712; 63,553 plus 53,082 is 116,635; and 502,712 at 10 a second is 13.96 hours. The reader works
offline, so the 9:00 decision only matters through H1 and L7. A model never sees text after the decision day,
provided H1 is fixed so features use only embeddings of stories already visible.

## Flagged passages judged fine (one line each)

1. PLAN L3 against L386 and L433: L3 is stale (finding L1). L386 and L433 are milestone definitions and are fine.
2. L18 (511,678, about 22 hours) against L19, L167, L364, L513, L628 (500,745, about 21 hours): L18 is the dated
   30 Oct count by ticker, and L19 (31 Oct) gives the count by company. Both times fit 6 to 7 a second. Fine as dated;
   the 21 hours lines are now stale against M2's measured 14 hours (finding L4).
3. L25 (1,371,723 member stock-days) against L475 (1,360,471 company member days): different units. The store has
   1,371,711 member bars by company and share class and 1,360,407 by company; 11,304 days are a second class
   (`member_day_counts.py`). 1,360,407 plus L477's 64 member sessions with no bar is 1,360,471. 1,371,711 minus
   `member_bars_with_official_open` 1,371,192 is L25's 519. A 12-day gap between L25 and the store is not explained by
   this check.
4. L279 (2016 news to the 2015 vintage) against L627 (2014 to 2024, 11 models): consistent. 2014 would read 2015 news,
   and M2 gives it the cutoff check instead (finding L4 for the wording).
5. L191 and L533 (picked each January) against L233 and L329 (April 2016): L233, L329 and L533 all state the 2016
   exception; L191 is a summary. Fine.
6. L21 (1,035 flagged bars), L21's 326 to 356 a day, and L482: 356 plus 326 plus 352 plus 1 is 1,035. The store has
   exactly 1,035 incomplete member bars with those four dates (`member_day_counts.py`; 1,059 including non-member
   days). Fine.
7. L22 and L497 (54 opening corrections) against L480 (55 corrections): L480 says 54 opening prints plus Nordstrom's
   bar. `price_events.csv` has 54 `open_print` rows and 1 `bad_print`, and `counts.json` says
   `override_opens_equal_to_auctions` "54 of 54". Fine.
8. L497 (122 rows, then 125) and L3, L5 dated 30 Oct and 5 Nov: L497 states both counts and the 8 Nov change.
   `price_events.csv` has 125 rows (54 + 7 + 1 + 2 + 3, plus 58 distributions = 55 + 3). L5 is a version date. Fine,
   though "holds 122" could read "held 122".
