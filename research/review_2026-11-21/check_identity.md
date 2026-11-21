# Check of the membership and identity tables

Date: 2026-11-21. Worktree: full-review-1121-0eb11c. Tables read from `D:\chrono-data\store` (built 2026-11-08): membership 799 rows, identity 814 rows, bars 1,420,646 rows, opens 1,420,626 rows. `counts.json` gives data_end 2026-10-28. Only counts, ids, symbols and dates are shown.

Commands, all run from the repo root with `D:\venvs\chrono-trader\Scripts\python.exe -W ignore <script>`. Scripts are in `research/review_2026-11-21/scripts/check_identity/`, with the saved output next to each:

- `check_identity.py` (checks 1 to 5, about 15 seconds), output in `output.txt`.
- `check_identity_detail.py` (who the overlaps are, the low-count sessions, symbols for the no-bar list), output in `output_detail.txt`.
- `check_identity_gaps.py` (where the no-bar days sit in each span), output in `output_gaps.txt`.
- `check_identity_open.py` (open identity rows against null member_to), output in `output_open.txt`.

Meaning of the date columns, from `data_pipeline/identity.py:376`: membership `member_to` is exclusive (the first day after). Identity `valid_to` is inclusive (the last member day). Empty `valid_to` means still open. Session days are the 2,721 distinct bar dates, 2016-01-04 to 2026-10-28.

## Summary

| Check | Result |
|---|---|
| 1. member_from <= member_to; null member_to | PASS |
| 2. No overlapping spans; 500 to 505 members a day | FAIL, minor: 8 overlapping pairs (all two-class companies); 41 sessions at 498 or 499 members |
| 3. Identity spans, no symbol held twice | PASS |
| 4. Joins in both directions | PASS (0 misses) |
| 5. Member days with no bar or no open | 64 with no bar, 519 with no open; both match the PLAN counts. PASS against the plan |

## 1. Membership dates and null member_to: PASS

Command: `check_identity.py`, section CHECK 1.

Printed:
- 296 rows have a member_to. Rows with member_from > member_to: 0. Rows with member_from == member_to: 0.
- 503 rows have a null member_to, for 500 distinct entities. Their member_from runs 1996-01-02 to 2026-10-06.
- Rows active on data_end (2026-10-28): 503 rows, 500 entities. All 503 have a null member_to; none has a member_to present. member_to max is 2026-10-06; no row has a member_to after data_end.
- The index file `D:\chrono-data\membership\components_extended.csv` has its last snapshot on 2026-10-06 with 503 distinct tickers. PLAN L476 says the membership ends with 503 members.

Answer to what the nulls are: they are the members still in the index at data_end. 503 null rows equal the 503 tickers of the last snapshot. The 503 rows are 500 companies, because three companies hold two rows each (two share classes): 0001564708 (NWSA, NWS), 0001652044 (GOOGL, GOOG) and 0001754301 (FOX, FOXA). Each null row of these three starts after the first, and the second row is a second class, not a rejoin.

Does any code read a null member_to as something else? No. Every site that reads it treats null as open-ended (still a member):
- `world/world.py:46` fills null with the far future for spells; line 145 makes leave events only for rows where member_to is present.
- `eval/leaks.py:43` treats null as no leave event.
- `data_pipeline/audit_prices.py:61` (`member_to.isna() | ...`) and `audit_news.py:67` (fillna with Timestamp.max).
- `data_pipeline/bars.py:85-90` uses `last_day`; `split.py:40` uses the last day.
- `data_pipeline/identity.py:376` makes valid_to empty for a null member_to.

One fragile line: `identity.py:460` uses `r.member_to or date.max`. That works for None but not for a float NaN, which counts as true. I did not check which type reaches it. It sits in `compare`, a report-only function, so it cannot change a table.

## 2. Membership overlaps and daily member counts: FAIL (minor)

Command: `check_identity.py`, section CHECK 2; `check_identity_detail.py` for the explanations.

Overlaps. 46 entities have more than one row. Touching spans (next member_from equals the earlier member_to, not an overlap): 39. Overlapping pairs for one entity: 8, across 7 entities. Every one is a company with two share classes:
- 0001166691 Comcast: CMCSA from 1996-01-02, CMCSK 2015-09-21 to 2015-12-14.
- 0001308161 21st Century Fox: FOXA from 2004-12-20 and FOX from 2015-09-21, both to 2019-03-19; plus two one-day rows (TFCFA and TFCF, "added: missing from the membership file") on 2019-03-19, which overlap each other.
- 0001336917 Under Armour: UAA from 2014-05-01 and UA from 2016-04-08, both to 2022-06-21.
- 0001437107 Discovery: DISCA from 2010-03-01 and DISCK from 2014-08-07, both to 2022-04-11.
- 0001564708 News Corp: NWSA from 2013-07-01 and NWS from 2015-09-21, both open.
- 0001652044 Alphabet: GOOGL from 2006-04-03 and GOOG from 2014-04-03, both open.
- 0001754301 Fox: FOX and FOXA both from 2019-03-19, open.

These are the seven two-class companies PLAN L491 lists. `world/world.py:41` merges overlapping memberships of one entity, so the overlaps do no harm there. The rule as written ("no overlapping spans for the same entity") fails; the meaning ("no company is a member twice over, apart from two classes") holds.

Daily counts. 2,721 sessions, 2016-01-04 to 2026-10-28, counting distinct entities with member_from <= day < member_to:
- Min 498 (2018-11-29 and 2018-11-30). Max 502 (2020-04-03).
- Sessions per count: 498 on 2, 499 on 39, 500 on 2,667, 501 on 12, 502 on 1.
- Sessions outside 500 to 505: 41, all below 500, all in 2016 (13), 2017 (12) and 2018 (16). None above 505.
- Counting rows instead of entities: min 503, max 507 (the extra rows are second classes).
- The index file's own snapshots on those 41 dates hold 503 to 505 tickers. I did not check how many two-class pairs each snapshot holds, so I cannot say whether the 1 to 2 shortfall is already in the source file or came from a table step.

Cross-check with the store: the number of distinct entities with a member-flag bar per session is 498 to 501. It differs from the membership table on 62 sessions, which is the days with no bar (check 5).

## 3. Identity spans: PASS

Command: `check_identity.py`, section CHECK 3.

Printed: 814 rows. Empty valid_from: 0. Empty valid_to: 505 (open). Empty share_class: 795; share classes present: A 10, B 4, C 4, "A Special" 1.
- valid_from > valid_to: 0. One-day spans (valid_from == valid_to): 3. Duplicate rows: 0.
- Overlapping spans for the same entity and share class (inclusive ends): 0.
- Symbols held by two entities on the same day: 0. Overlapping spans of one symbol inside one entity: 0.
- Entities with two or more share classes listed: 7 (matches PLAN L491).

Note, not a failure: 505 identity rows are open but only 503 membership rows have a null member_to (`check_identity_open.py`). The difference is Under Armour (0001336917): its two open identity rows (UAA class A, UA class C, both from 2016-12-07) outlast its membership, which ended 2022-06-21 (the company still trades). Every other open identity row belongs to an entity with a null member_to row, and every null-member_to entity has an open identity row.

## 4. Joins: PASS

Command: `check_identity.py`, section CHECK 4.

- Entities: 746 in membership, 746 in identity. In membership but not identity: 0. In identity but not membership: 0.
- (4a) Each of the 799 membership rows was expanded to calendar days (to data_end) and to store sessions, and tested against that entity's identity spans. Calendar days with no covering identity row: 0. Store sessions with none: 0. Rows affected: 0.
- (4b) Bars entity-days: 1,409,333 (to data_end). Flagged member: 1,360,407. Covered by a membership row: 1,360,407.
  - Member-flag entity-days with no membership row: 0.
  - Entities in bars but not in membership: 0.
  - Entity-days covered by a membership row but flagged non-member: 0.

(The 1,371,711 member bars in the store are class-level rows; the entity-level figure is 1,360,407, and 1,360,471 membership entity-days exist, a gap of 64: check 5.)

## 5. Member days with no bar or no open: PASS against the plan

Command: `check_identity.py`, section CHECK 5; `check_identity_detail.py` and `check_identity_gaps.py` for the symbols and positions.

Membership entity-days (store sessions 2016-01-04 to data_end): 1,360,471.

No bar of any kind: 64 entity-days, 28 entities. PLAN L477 says 64 member sessions have no bar (58 acquisition closings, 6 failed-bank halts). The count matches. All 64 sit at the end of a membership span (0 in the middle, 0 at the start, 0 for a company still a member at data_end). By year: 2017 2, 2019 8, 2020 12, 2021 7, 2022 4, 2023 8, 2024 8, 2025 9, 2026 6. First 20 (entity, date, symbol):

0000004447 2025-07-18 HES; 0000004447 2025-07-21 HES; 0000004447 2025-07-22 HES; 0000072207 2020-10-05 NBL; 2020-10-06; 2020-10-07; 2020-10-08; 2020-10-09 (NBL); 0000101778 2024-11-22 MRO; 2024-11-25 (MRO); 0000203527 2021-04-15 VAR; 2021-04-16; 2021-04-19 (VAR); 0000718877 2023-10-16 ATVI; 2023-10-17 (ATVI); 0000719739 2023-03-10 SIVB; 2023-03-13; 2023-03-14 (SIVB); 0000721683 2019-09-18 TSS; 2019-09-19 (TSS).

The 28 runs (entity, symbol, first day, last day, days) are in `output_detail.txt`. Run lengths are 1 to 5 days. Two I cannot tie to the digests: AVB (0000915912) on 2026-08-17 and HOLX (0000859737) on 2026-04-07 and 2026-04-08. I did not look at why. They are still at the end of their spans like the rest.

No member-flag bar: 64 entity-days (the same days).

Bar but no official open: 519 entity-days. Of these, 8 have no row in opens and 511 have a row with a null open. At class level, 519 of the 1,371,711 member bars have no non-null open; `counts.json` gives 1,371,192 with an official open, and 1,371,711 - 1,371,192 = 519. PLAN L26 also says 519. The count matches. Top dates: 2023-01-24 267, 2018-01-24 108, 2022-03-08 66, 2021-04-09 17, 2021-04-28 17, 2018-02-01 12, 2021-04-13 7, 2021-04-29 5; these three biggest dates are the ones PLAN L26 names. By year: 2018 121, 2020 1, 2021 58, 2022 68, 2023 271. First 20 (entity, date): 0000001800 2023-01-24; 0000002969 2023-01-24; 0000004281 2023-01-24; 0000004447 2023-01-24; 0000004962 2021-10-25; 0000004962 2023-01-24; 0000004977 2023-01-24; 0000005272 2023-01-24; 0000007084 2023-01-24; 0000010456 2023-01-24; 0000010795 2023-01-24; 0000012208 2022-03-08; 0000012927 2023-01-24; 0000014272 2023-01-24; 0000014693 2023-01-24; 0000016732 2023-01-24; 0000016918 2021-04-09; 0000016918 2021-04-28; 0000016918 2022-03-08; 0000016918 2023-01-24.

Neither a bar nor an open: 583 entity-days (519 + 64).

PLAN L26 says "519 of 1,371,723 member stock-days"; the store has 1,371,711 member bars. The 12 difference is in the denominator only (an earlier plan count). The 519 agrees.

## Failing cases to pass on

1. Check 2, the 41 sessions below 500 members (498 or 499), all in 2016 to 2018. Their dates are listed in `output_detail.txt`. The cause is not settled (see check 2).
2. Check 2, the rule as written: 8 overlapping row pairs, all two-class companies. This is by design and handled in `world/world.py:41`.
3. Code note: `identity.py:460` relies on `member_to` being None, not NaN (report-only function).
