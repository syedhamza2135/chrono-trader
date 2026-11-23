"""Two tables for the evaluation only (M3 step 1, decision 4 in research/m3_kickoff.md): SPY's daily bars and each
company's GICS sector. The World never loads them, so no view holds them, and an agent can't read files
(tests/test_boundaries.py). Only `eval` reads them (eval/benchmarks.py).

- spy: SPY's daily bars from Alpaca, the same source and feed as the companies' bars (data_pipeline/bars.py), raw and
  fully adjusted, from 2016 to the store's last day (reference/split.json, data_through). One row per session: date
  (the bar's New York date), open, close and volume (raw), adj_open and adj_close (adjusted for splits and
  dividends), and ret, the close-to-close total return from the adjusted closes (empty on the first row).
  Raw files: DATA_DIR/bars/benchmark/SPY__<adjustment>.parquet.
- sectors: the GICS sector Wikipedia's list showed for each company, from the monthly revisions the identity table
  already uses (the revision in force on the 1st of each month from January 2015, cached under
  DATA_DIR/membership/wikipedia/revisions, so nothing is fetched again). One row per company and run of months with
  the same sector: entity_id, sector, valid_from (the New York date of the first revision showing it), valid_to (the
  last revision showing it). A company is matched by its CIK (reference/entities.csv). Wikipedia's dates lag S&P's
  own reclassifications, so the table is close to point in time, not exact: the report says so.

research/audit/benchmarks.md gets the counts (no prices).

Usage: python -m data_pipeline.benchmarks
"""
import json
import re
from datetime import date
from zoneinfo import ZoneInfo

import pandas as pd

from . import alpaca
from . import bars as bars_mod
from . import wikipedia as wp
from .settings import DATA_DIR, ROOT

NY = ZoneInfo("America/New_York")
SYMBOL = "SPY"
RAW = DATA_DIR / "bars" / "benchmark"
STORE = DATA_DIR / "store"
SINCE = date(2015, 1, 1)  # the identity table's first monthly revision (data_pipeline/identity.py)


def data_through(root=ROOT):
    return date.fromisoformat(json.loads((root / "reference" / "split.json").read_text(encoding="utf-8"))["data_through"])


# SPY
def fetch_spy(adjustment, end):
    rows = []
    for body in alpaca.pages("/v2/stocks/bars", symbols=SYMBOL, timeframe="1Day", start=bars_mod.START, end=end,
                             adjustment=adjustment, feed="sip", limit=10000):
        rows += body.get("bars", {}).get(SYMBOL, [])
    return rows


def _ny_date(t):
    return pd.to_datetime(t, utc=True).dt.tz_convert(NY).dt.tz_localize(None).dt.normalize()


def spy_table(raw, adjusted):
    """The spy table from the raw and the adjusted bar files (both as saved by bars.save)."""
    r = raw.assign(date=_ny_date(raw.t))[["date", "open", "close", "volume"]]
    a = adjusted.assign(date=_ny_date(adjusted.t))[["date", "open", "close"]]
    a = a.rename(columns={"open": "adj_open", "close": "adj_close"})
    if r.date.duplicated().any() or a.date.duplicated().any():
        raise ValueError("SPY has two bars on one date")
    out = r.merge(a, on="date", how="inner", validate="one_to_one").sort_values("date", ignore_index=True)
    if len(out) != len(r) or len(out) != len(a):
        raise ValueError("SPY's raw and adjusted bars cover different dates")
    out["ret"] = out.adj_close / out.adj_close.shift(1) - 1.0
    return out.astype({"open": "float64", "close": "float64", "volume": "int64", "adj_open": "float64",
                       "adj_close": "float64", "ret": "float64"})


# Sectors
def _clean(cell):
    cell = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", cell)
    cell = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", cell)  # a link becomes its text
    cell = re.sub(r"\{\{[^}]*\}\}|'''?|<[^>]+>", "", cell)
    return re.sub(r"\s+", " ", cell).strip()


def sectors_in(wikitext):
    """[(cik, sector)] from one revision of the list. Rows without a CIK or a sector are left out."""
    table = wp._table(wikitext, "Central Index Key")
    cols = wp._header(table)
    i_sector = next((i for i, c in enumerate(cols) if "gics sector" in c), None)
    i_cik = next((i for i, c in enumerate(cols) if "cik" in c or "central index" in c), None)
    if i_sector is None or i_cik is None:
        raise ValueError(f"no GICS sector or CIK column in {cols}")
    out = []
    for cells in wp._rows(table):
        if len(cells) <= max(i_sector, i_cik):
            continue
        cik = re.sub(r"\D", "", re.sub(r"<ref.*?</ref>|<ref[^>]*/>", "", cells[i_cik]))
        sector = _clean(cells[i_sector])
        if cik and sector:
            out.append((cik.zfill(10), sector))
    return out


def monthly_sectors(last):
    """One row per (revision, company): stamp (the revision's New York date), cik, sector. The revisions in force on
    the 1st of each month from SINCE to `last`."""
    rows, month = [], SINCE
    while month <= last:
        stamp, text = wp.revision(wp.LIST, month.isoformat())
        stamp = pd.Timestamp(stamp).tz_convert(NY).tz_localize(None).normalize()
        rows += [{"stamp": stamp, "cik": c, "sector": s} for c, s in sectors_in(text)]
        month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    return pd.DataFrame(rows, columns=["stamp", "cik", "sector"]).drop_duplicates()


def entity_of_cik(entities):
    """{cik: entity_id} from reference/entities.csv, whose `ciks` holds one or more CIKs split by spaces."""
    out = {}
    for e, ciks in zip(entities.entity_id, entities.ciks.fillna("")):
        for c in str(ciks).split():
            if c in out and out[c] != e:
                raise ValueError(f"CIK {c} belongs to two entities")
            out[c] = e
    return out


SPELLING = {"Communications Services": "Communication Services",
            "Telecommunications Services": "Telecommunication Services"}  # one name per GICS sector


def sector_spells(monthly, cik_map):
    """Runs of months with one sector per company: entity_id, sector, valid_from, valid_to. Where one revision shows a
    company under two sectors (an editing slip: Avery Dennison on 2015-03-31), that revision is left out for that
    company, so its neighbours decide. Returns (spells, the number of (revision, company) pairs left out)."""
    m = monthly.assign(entity_id=monthly.cik.map(cik_map), sector=monthly.sector.replace(SPELLING))
    m = m.dropna(subset=["entity_id"]).drop_duplicates(["stamp", "entity_id", "sector"])
    two = m.duplicated(["stamp", "entity_id"], keep=False)
    dropped = int(m[two].drop_duplicates(["stamp", "entity_id"]).shape[0])
    m = m[~two].sort_values(["entity_id", "stamp"], ignore_index=True)
    run = (m.sector != m.groupby("entity_id").sector.shift()).cumsum()
    out = m.groupby(["entity_id", run], sort=False).agg(sector=("sector", "first"), valid_from=("stamp", "min"),
                                                        valid_to=("stamp", "max"))
    return out.reset_index(level=0).reset_index(drop=True)[["entity_id", "sector", "valid_from", "valid_to"]], dropped


def main():
    end = data_through()
    RAW.mkdir(parents=True, exist_ok=True)
    files = {}
    for adjustment in bars_mod.ADJUSTMENTS:
        path = RAW / f"{SYMBOL}__{adjustment}.parquet"
        if not path.exists():
            rows = fetch_spy(adjustment, end.isoformat())
            bars_mod.save(path, SYMBOL, "", rows)
        files[adjustment] = pd.read_parquet(path)
    spy = spy_table(files["raw"], files["all"])
    spy.to_parquet(STORE / "spy.parquet", index=False)

    entities = pd.read_csv(ROOT / "reference" / "entities.csv", dtype=str)
    monthly = monthly_sectors(end)
    cik_map = entity_of_cik(entities)
    spells, dropped = sector_spells(monthly, cik_map)
    spells.to_parquet(STORE / "sectors.parquet", index=False)

    unmatched = sorted(set(monthly.cik) - set(cik_map))
    no_sector = sorted(set(entities.entity_id) - set(spells.entity_id))
    changed = spells.groupby("entity_id").size()
    lines = [
        "# Benchmarks for the evaluation: SPY and sectors",
        "",
        f"Written by `python -m data_pipeline.benchmarks` on {date.today().isoformat()}. Counts only, no prices.",
        "",
        "## SPY",
        "",
        f"- {len(spy)} sessions, {spy.date.min().date()} to {spy.date.max().date()}, from Alpaca's SIP feed, raw and "
        "fully adjusted.",
        f"- Sessions with no return (the first): {int(spy.ret.isna().sum())}.",
        "",
        "## Sectors",
        "",
        f"- {monthly.stamp.nunique()} monthly revisions of Wikipedia's list, {monthly.stamp.min().date()} to "
        f"{monthly.stamp.max().date()}; {len(monthly)} (revision, company) rows.",
        f"- {len(spells)} sector runs for {spells.entity_id.nunique()} of the {entities.entity_id.nunique()} companies "
        f"in `reference/entities.csv`; {int((changed > 1).sum())} companies changed sector at least once.",
        f"- (Revision, company) pairs left out because one revision showed two sectors: {dropped}.",
        f"- Sector names merged across spellings: {', '.join(f'{a} as {b}' for a, b in SPELLING.items())}.",
        f"- Companies in `entities.csv` with no sector: {len(no_sector)}.",
        f"- CIKs on Wikipedia with no entity: {len(unmatched)} (companies outside the membership since 2016).",
        f"- Sectors seen: {', '.join(sorted(spells.sector.unique()))}.",
    ]
    (ROOT / "research" / "audit" / "benchmarks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
