# Rules check: licensing, style and dates

Run on 2026-11-21 in the worktree `full-review-1121-0eb11c` (branch `claude/full-review-1121-0eb11c`, tip 3f45e94).
Scripts are in `research/review_2026-11-21/scripts/check_rules/`. Run each with `D:\venvs\chrono-trader\Scripts\python.exe <script>` from the repo root.
No price row and no headline was printed. Only file names, line numbers and counts.

| Check | Result |
| --- | --- |
| 1. Tracked data files and big files | PASS, with notes (no raw data; 16 derived CSVs and 1 JSON outside the named exception) |
| 2. Secrets and keys in history | PASS |
| 3. Raw price rows and headlines in text files | PASS, with notes |
| 4. Em-dashes and en-dashes in .md files | PASS |
| 5. New York dates | FAIL on 6 minor sites in `data_pipeline/`; PASS for the time wall (`world/`, `sim/`, `eval/`, `agent/`, `reader/`) |

## Check 1: tracked files, risky types, big files

Commands:
- `git ls-files` (counted by extension in `check1_files.py`)
- `git log --all --diff-filter=A --name-only --pretty=format:` (all 16 refs, including `claude/awesome-panini-89f869`)
- `git rev-list --all --objects` piped to `git cat-file --batch-check` for blob sizes

Printed:
- 99 tracked files: 56 .py, 22 .md, 17 .csv, 1 .txt, 1 .json, 1 .gitignore, 1 .env.example.
- No tracked .parquet, .jsonl, .zip, .gz, .feather or .pkl.
- No tracked file over 200 KB. The biggest are `reference/identity.csv` (76,433 bytes), `research/audit/news_by_day.csv` (75,252), `PLAN.md` (74,221) and `reference/price_events.csv` (50,541).
- No blob over 200 KB in any commit on any ref.
- 105 distinct paths were ever added on any ref. Beyond the tracked ones, two risky-extension files appear only on other branches: `reader/vintages.json` (3,398 bytes on `claude/awesome-panini-89f869`; a list of model file hashes, no data) and `research/audit/identity_multi_spell.csv` (a header of ticker, spells, first_bar_each, verdict; removed later).

Tracked CSV and JSON files other than `reference/price_events.csv` (rows excluding the header, columns by header only):

| File | Lines | What the columns hold |
| --- | --- | --- |
| reference/entities.csv | 747 | company id, name, CIKs, member dates |
| reference/identity.csv | 815 | symbol spells and dates |
| reference/identity_fixes.csv | 98 | hand fixes with evidence |
| reference/memberships.csv | 800 | membership spans |
| reference/split.json | 40 | counts per period (it says no prices were read) |
| research/audit/adjustment_events.csv | 151 | per-day price ratios `r_raw`, `r_adj`, `diff` |
| research/audit/auctions_missing_opens.csv | 520 | symbol and date only |
| research/audit/identity_shared_data.csv | 1 | header only |
| research/audit/incomplete_bars.csv | 1036 | volume and trade ratios |
| research/audit/large_moves.csv | 266 | one-day return `ret`, `next_ret`, verdicts |
| research/audit/member_days_without_bars.csv | 65 | symbol, date, reason |
| research/audit/news_by_day.csv | 3947 | story counts per day |
| research/audit/news_by_year.csv | 13 | story counts per year |
| research/audit/news_reading_load.csv | 12 | counts |
| research/audit/survivorship.csv | 12 | counts |
| research/audit/universe_preview.csv | 551 | year, rank, company, median dollar volume |
| research/audit/zero_volume.csv | 9 | symbol and date only |

Verdict: PASS on the licensing rule in substance. None of these holds raw OHLC bars, raw volumes or news text. Notes for the owner:
- These 16 CSVs and 1 JSON are not on the AGENTS.md exception list, which names only `reference/price_events.csv`. A strict reading would want the rule widened to cover derived audit tables.
- Three are derived from prices and are the closest to the line: `adjustment_events.csv` (147 rows of price ratios), `large_moves.csv` (returns) and `universe_preview.csv` (median dollar volume). No raw price level appears in them.

## Check 2: .env and key-like material

Commands (in `check2_secrets.py`):
- `git log --all --name-only --pretty=format:` filtered for `.env`, `.pem`, `.key`, `secret`, `credential`
- `git ls-files` filtered for `.env`
- `git grep -n -I -E "APCA|ALPACA_API|ALPACA_SECRET|SECRET|key_id|api_key|apikey|AKIA|sk-...|ghp_...|PK..."` at the tip of each of the 16 refs, file:line only
- `git log --all -G <same pattern> --name-only` and a scan of every added diff line for a key-like name assigned a literal of 16 or more characters

Printed:
- Paths matching an env or key pattern anywhere in history: 1, `.env.example`. No `.env` was ever committed.
- Tracked env files now: `.env.example` only. Its key fields (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`) have length-0 values.
- Pattern hits at ref tips: 23 distinct file:line, all in 4 files: `.env.example` (lines 2, 3, 6, 9), `data_pipeline/settings.py` (20, 23, 24, 27, 30, 31, 34), `research/alpaca_check.py` (39 to 43, 48), `tests/test_settings.py` (15, 24, 29, 35, 37, 38).
- Only 2 of these assign a literal, `tests/test_settings.py:24` and `:35`. By their length and form they are made-up test strings ("made-up-id" style), not keys.
- History scan for assigned literals of 16 or more characters: 0.

Verdict: PASS.

## Check 3: raw price rows and headline-like lines

Commands (in `check3_raw_data.py`): scan every tracked text file for lines with a date plus three or more decimals, lines with four or more decimals, quoted spans in the evidence column of `price_events.csv`, and tests that read data.

Printed:
- Date plus 3 or more decimals: 208 lines in 3 files.
  - `reference/price_events.csv`: 59 of 126 lines (allowed exception).
  - `research/audit/adjustment_events.csv`: 147 of 151 lines (ratios `r_raw`, `r_adj`, `diff`, not price levels).
  - `research/m1_kickoff.md`: 2 lines, 183 to 184. These are prose about two corporate-action cases with a dividend amount and percent returns. Not a data table.
- Bare number rows (4 or more decimals, no date): `research/audit/news_by_year.csv` lines 2 to 13 (12 lines). They are word-count averages by year, not prices.
- `reference/price_events.csv`: 125 rows, 106 symbols, dates 2016-02-08 to 2026-10-14. Evidence field is up to 896 characters; 62 rows are over 300 characters. No double-quoted span at all. 10 single-quoted spans of 15 or more characters, longest 11 words. Only 1 row uses the word "headline". So quotes stay short.
- Headline-like text elsewhere in tracked .md: 2 quoted list lines (`research/brief_check.md:62` and `:64`, 20 and 18 words). They quote a research brief, not news.
- Tests: 13 .py files, no non-.py file under `tests/`, no fixtures or conftest. No test embeds data. `tests/test_suites.py` (lines 30, 43, 47, 52, 58, 68, 96, 97) and `tests/test_leaks.py` (284, 293) read parquet and audit CSVs from the data store at run time. Nothing is copied into git.

Verdict: PASS. Note: `test_suites.py:68` reads the `headline` column from the local stories store. That stays off git.

## Check 4: em-dashes and en-dashes in .md files

Command (in `check4_dashes.py`): scan U+2014 and U+2013 in every .md file from `git ls-files`, and in every .md from `git ls-files -o --exclude-standard`.

Printed:
- 22 tracked .md files: 0 em-dash lines, 0 en-dash lines.
- 14 untracked .md files (`docs/digests/` 3 files, 11 in the review folder): 0 em-dash lines, 0 en-dash lines. This report (the 15th) was also checked and has none.
- Extra: the only dash character in any other tracked file is one en-dash in `reference/entities.csv` (inside a data field, not a doc).

Verdict: PASS.

## Check 5: New York dates

Commands (in `check5_dates.py`): `git grep -nE` over `world sim eval agent reader data_pipeline` for `utcnow`, `datetime.now(`, `date.today(`, `Timestamp.now(`, `timezone.utc`, `utc=True`, `tz_localize`, `tz_convert`, `.date()`, `.dt.date`, and `fromisoformat` with `Z`. I read the context of each site.

Printed: `utcnow` 0 sites. Naive now or today 11. UTC named 27. `tz_localize` 5. `tz_convert` 8. `.date()` or `.dt.date` 23. 14 code files have no date handling at all, including `agent/reversal.py`, `eval/leaks.py`, `eval/metrics.py`, `sim/simulator.py` and `sim/seal.py`.

Time wall: PASS. Every site in these directories converts to New York or keeps UTC only for stored instants.
- `world/clock.py:31,37`: builds UTC instants from a New York date and time with `tz_localize("America/New_York")` then converts to UTC. Correct.
- `world/view.py:24`: `today` is `tz_convert(NY)` first, then made naive. Converts first.
- `world/world.py:101`: story day is `tz_convert(NY)` before `.normalize()`. Converts first. Lines 128, 168 to 170: UTC instants, and the seal check at 170 converts to New York first.
- `world/rules.py:27,32,53`: UTC instants and time deltas, no calendar date taken.
- `reader/vintage.py:14`: vintage year taken after `tz_convert("America/New_York")`. Converts first.
- `sim/` and `agent/` and `eval/`: no UTC or today calls; they use `v.today` from the view.

Sites in `data_pipeline/` that do not convert to New York (FAIL list):
1. `data_pipeline/bars.py:43`: yesterday in New York is computed as UTC minus a fixed 5 hours. This is wrong by one hour in summer (daylight saving). It can give the wrong date for the hour after midnight New York time from March to November.
2. `data_pipeline/news.py:36`: the download end is `datetime.now(timezone.utc)` minus 20 minutes. It is an instant, so harmless. Line 35 sets the month window in UTC, not New York. Only the download chunking, not a date used by the agent.
3. `data_pipeline/news.py:72` and `:63,66`: `date.today()` is the local date (Pakistan runs 9 to 10 hours ahead of New York). It sets the last month to download. Edge case at month turns. Lines 63 and 66 are `datetime.now()` for timing only.
4. `data_pipeline/split.py:59`: `last_day` defaults to the local `date.today()`, not the New York date. Used as the session end for the split counts.
5. `data_pipeline/wikipedia.py:164,165`: `today()` is the local `datetime.now().date()`. It feeds `membership.py:95` and `identity.py` (the "today" snapshot) and the cache key.
6. `data_pipeline/identity.py:61` and `data_pipeline/membership.py:109`: `datetime.fromisoformat(stamp.replace("Z", "+00:00")).date()` takes the date of a Wikipedia revision from a UTC stamp without converting to New York. A revision made after about 20:00 New York time would get the next day. `wikipedia.py:52` also defines the revision cut as 00:00 UTC.
7. Report headers `data_pipeline/audit_news.py:187`, `audit_prices.py:328`, `identity.py:537`: `date.today()` printed in a "Generated on" line. Cosmetic.

Sites that look odd but are fine:
- `data_pipeline/audit_news.py:48,87,155` take `.dt.date` from a column already converted to New York (`:100`).
- `data_pipeline/audit_prices.py:71,169,294,295,370,405,417` and `split.py:46,47,64,68` call `.date()` on naive New York session dates.
- `data_pipeline/auctions.py:91,167,168` and `store.py:171,193` keep UTC for print times and compare them with UTC session opens. No date is cut from them.

Verdict: FAIL, minor. The time wall is clean. Items 1 and 6 are the ones to fix first (a fixed UTC-5 offset, and UTC `.date()` on a timestamp). Items 3, 4 and 5 use the local machine date.
