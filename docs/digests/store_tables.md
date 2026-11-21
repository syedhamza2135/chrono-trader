Store: D:\chrono-data\store. Rules from data_pipeline/store.py (commit dd40a5f). Date: 2026-11-21. Counts only, no prices or headlines.

File modified times (local time, +0500, all 2026-11-08): bars 22:43:08, opens 22:43:09, labels 22:43:10, stories 22:45:30, story_entities 22:45:31, membership 22:45:31, identity 22:45:31, counts.json 22:45:31.

Rule lines are in data_pipeline/store.py. Module doc is lines 1-31. `KEY` is entity_id, share_class, date (line 50).

## bars
- Path: D:\chrono-data\store\bars.parquet. Written at store.py:243-244 from `s[BAR_COLUMNS]` (line 234).
- Rows: 1,420,646. Dates 2016-01-04 to 2026-10-28. Distinct entity_id: 719. Distinct symbol: 768.
- Member days 1,371,711. Non-member days 48,935 (counts.json).
- Columns:
  - entity_id (large_string, nulls 0): company id. Key column (50). Comes from `prices.load`; store.py only lists it (56).
  - share_class (large_string, nulls 0): key column (50). One row per company, share class and session (6).
  - symbol (large_string, nulls 0): listed in BAR_COLUMNS (56). No further rule found in store.py.
  - date (timestamp[ns], nulls 0): session date. Cut at the data's last session, the AAPL member max (226, 228). Member bars win; other days are kept 400 days before and 14 days after a row (55, 70-83).
  - open (double, nulls 0): raw price from the file that served the bar (61-62). Replaced on an `override_bar` event (123-124).
  - high (double, nulls 0): same rule as open (61-62, 123-124).
  - low (double, nulls 0): same rule as open (61-62, 123-124).
  - close (double, nulls 0): raw price (61-62). Moved by `override_close` and `override_bar` events (105-110, 122, 126-127).
  - volume (int64, nulls 0): raw volume (61-62). Non-member days need volume above 0 (75). `override_bar` sets it (125).
  - trades (int64, nulls 0): listed in BAR_COLUMNS (56). No rule found in store.py.
  - vwap (double, nulls 0): replaced on an `override_bar` event (123-124). Otherwise no rule found in store.py.
  - ret (double, nulls 921): close-to-close total return of Alpaca's adjusted bars, stitched where a company changes rows, undefined where the previous bar is not the company's own (10-12, 62-65). A non-member day's return stands only where the day before is the same file's previous bar (87-89). Price events correct it: close moves change the returns into and out of the day (105-110), `total_return` replaces it (128-129). Of the nulls, 717 are on member days (counts.json).
  - incomplete (bool, nulls 0; true 1,059): listed in BAR_COLUMNS (56). No rule found in store.py.
  - member (bool, nulls 0; true 1,371,711): true where the bar is the member bar of a plan row (6, 74, 84).
  - no_trade (bool, nulls 0; true 2): set false for all rows (96), true where a `no_trade` event applies (130-131). Halts are marked this way (14).

## opens
- Path: D:\chrono-data\store\opens.parquet. Written at store.py:243-244 from `opens_out` (235).
- Rows: 1,420,626. Dates 2016-01-04 to 2026-10-28. Distinct entity_id: 719.
- One row per company, class and session that has an official print (15-16). Built by `official_opens` (136-143): the series keys inner-joined to `DATA_DIR/auctions/official.parquet` on symbol, asof and date.
- Columns:
  - entity_id (large_string, nulls 0): key from the series (140).
  - share_class (large_string, nulls 0): key from the series (140).
  - date (timestamp[ns], nulls 0): official file's date as datetime64[ns] (139).
  - open (double, nulls 525): the listing exchange's official opening print (15). Rows with a null open are dropped before labels (165). Where it comes from in the auctions file is not in store.py.
  - open_time (timestamp[ns, tz=UTC], nulls 525; 2016-01-04 14:30:00 to 2026-10-28 13:32:45 UTC): when the open printed. Labels use it as `end_open_time` (165, 171, 191). Its own rule is in auctions.py, not store.py.
  - listing_exchange (large_string, nulls 0): copied from the auctions file (235). No rule found in store.py.
  - official_close (double, nulls 535): the auctions file's `close`, renamed (143). The module doc calls it the official closing print (15).
- The official file's `n_open_prints` and `n_close_prints` columns are dropped before the join (141).

## labels
- Path: D:\chrono-data\store\labels.parquet. Written at store.py:243-244 from `lab` (233, built by `labels` at 162-194).
- Rows: 1,419,403. `date` 2016-01-04 to 2026-10-27. `end` 2016-01-05 to 2026-10-28. Distinct entity_id: 719.
- One row per company, class and session with an official open that has a later end (17-23). Opens with no end are skipped (183-185).
- Columns:
  - entity_id (large_string, nulls 0): from the series (192).
  - share_class (large_string, nulls 0): from the series (192).
  - date (timestamp[ns], nulls 0): the day of the starting official open (191, `dates[i]`).
  - end (timestamp[ns], nulls 0): the day of the ending open, or of the last traded close when `at_close` (191, `dates[j]`).
  - label (double, nulls 0): total return from the open to the next official open of the same listing. First day close/open, corrected close-to-close returns between, last day open/close (17-19, 188). Closes cancel, so a wrong close cannot move a label (19). Skipped if a day between has no return (186-187). It is -1 for a failed company's exit (21-23, 189-190).
  - at_close (bool, nulls 0; true 222): true where no official open follows and the company stopped trading before the data end, so the label ends at its last traded close (19-21, 177, 181-182). Of the 222: 103 stopped trading, 119 window cut, 3 of the exits failed (counts.json).
  - end_open_time (timestamp[ns, tz=UTC], nulls 222; 2016-01-05 14:30:00 to 2026-10-28 13:32:45 UTC): when the ending open printed, for the availability rule (17-18). Null where `at_close` (191).
- Where none follows because the data ends, there is no label (23).

## stories
- Path: D:\chrono-data\store\stories.parquet. Written at store.py:276-277 from `st` (205-207).
- Rows: 2,239,859. created_at 2015-01-01 to 2026-10-29. Distinct story_id: 2,239,859.
- Source: Benzinga stories only (200), kept if not edited more than 3 days after publishing (24, 201), then `companies(df)` (202).
- Columns:
  - story_id (int64, nulls 0): the news `id` (205).
  - created_at (timestamp[us, tz=UTC], nulls 0): raw time, from `df.created` (3, 205).
  - updated_at (timestamp[us, tz=UTC], nulls 0): raw time, from `df.updated` (3, 206).
  - headline (large_string, nulls 0): copied from the news (206). No further rule found in store.py.
  - symbols (list of string, nulls 0): copied from the news (207). No further rule found in store.py.
  - n_companies (int64, nulls 0): from `companies` in audit_news (202, 207). Its rule is in audit_news.py, not store.py.

## story_entities
- Path: D:\chrono-data\store\story_entities.parquet. Written at store.py:276-277 from `se` (208).
- Rows: 559,526. Distinct story_id: 534,619. Distinct entity_id: 744.
- (story, company) pairs of the stories the single-firm filter keeps: 1 or 2 companies, each tag mapped by the story's New York date (25-26, 203-204).
- Columns:
  - story_id (int64, nulls 0): story `id` from the exploded pairs (208).
  - entity_id (large_string, nulls 0): one entity per pair. Null entities are dropped (204, 208).

## membership
- Path: D:\chrono-data\store\membership.parquet. Written at store.py:276-277 from `reference_tables` (212-219).
- Rows: 799. Distinct entity_id: 746. member_from 1996-01-02 to 2026-10-06. member_to 2015-01-27 to 2026-10-06.
- Source: reference/memberships.csv (27, 213).
- Columns:
  - entity_id (large_string, nulls 0): copied from the csv, read as text (213-214).
  - member_from (timestamp[us], nulls 0): csv `member_from` as a date (214-215).
  - member_to (timestamp[us], nulls 503): csv `member_to` as a date (215). store.py says nothing about what a null means.

## identity
- Path: D:\chrono-data\store\identity.parquet. Written at store.py:276-277 from `reference_tables` (216-218).
- Rows: 814. Distinct entity_id: 746. Distinct symbol: 800.
- Source: reference/identity.csv with each company's CIKs (27, 216-218). All values are read as text and empty values are filled with "" (216).
- Columns:
  - entity_id (large_string, nulls 0): copied from the csv (218).
  - symbol (large_string, nulls 0): copied from the csv (218).
  - share_class (large_string, nulls 0): copied from the csv (218).
  - valid_from (large_string, nulls 0): copied from the csv as text (218). Empty strings are not counted as nulls.
  - valid_to (large_string, nulls 0): copied from the csv as text (218). Same note.
  - cik (large_string, nulls 0): the entity's `ciks` from reference/entities.csv, mapped by entity_id (217-218).

## Columns with no rule found in store.py
- bars: symbol, trades, incomplete; vwap apart from the override_bar case. entity_id and share_class come from `prices.load`.
- opens: what open, open_time and listing_exchange mean in the auctions file. store.py only copies them.
- stories: headline and symbols (copied); n_companies (from audit_news.companies).
- membership: what a null member_to means.

## counts.json (same folder)
- Matches the row counts above. Other keys: data_end 2026-10-28, member_bars_without_return 717, member_bars_with_official_open 1,371,192, labels_at_close 222, exits_stopped_trading 103, exits_window_cut 119, exits_failed 3, failed_companies 3, override_opens_equal_to_auctions "54 of 54", stories_with_a_company 534,619.

## Python run
Run with D:\venvs\chrono-trader\Scripts\python.exe. Saved copy: C:\Users\syedh\AppData\Local\Temp\claude\65aa5f41ba798649\d8d25a76-464a-484f-b4cc-73d2501c1dc4\scratchpad\profile.py

```python
import pyarrow.parquet as pq, pyarrow as pa, pyarrow.compute as pc, datetime, os
S = "D:/chrono-data/store/"
DISTINCT = {"bars": ["entity_id", "symbol"], "opens": ["entity_id"], "labels": ["entity_id"],
            "stories": ["story_id"], "story_entities": ["story_id", "entity_id"],
            "membership": ["entity_id"], "identity": ["entity_id", "symbol"]}
for name in DISTINCT:
    p = S + name + ".parquet"
    f = pq.ParquetFile(p)
    t = pq.read_table(p)
    print("##", name, "rows", f.metadata.num_rows, "mtime",
          datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S"))
    for c in DISTINCT[name]:
        print("  distinct", c, pc.count_distinct(t[c]).as_py())
    for fld in t.schema:
        col = t[fld.name]
        s = f"  {fld.name} ({fld.type}, nulls {col.null_count})"
        if pa.types.is_temporal(fld.type):
            mm = pc.min_max(col)
            s += f" min {mm['min'].as_py()} max {mm['max'].as_py()}"
        elif pa.types.is_boolean(fld.type):
            s += f" true {pc.sum(col).as_py()}"
        elif name in ("identity",) and fld.name in ("valid_from", "valid_to"):
            s += " (string)"
        print(s)
```
