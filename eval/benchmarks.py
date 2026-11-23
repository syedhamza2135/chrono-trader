"""The evaluation's own tables: SPY's bars and each company's sector (data_pipeline/benchmarks.py builds them).

Only `eval` reads these. The World never loads them, so no view holds them and no agent decides with them. They serve
the long-only baseline (SPY buy-and-hold), the book's market beta and its sector tilt (PLAN 5.3, 9.8, 9.10).
"""
import pandas as pd

from data_pipeline.settings import DATA_DIR

STORE = DATA_DIR / "store"


def load_spy(store=STORE):
    """SPY's sessions: date, open, close, volume, adj_open, adj_close, ret."""
    return pd.read_parquet(store / "spy.parquet")


def load_sectors(store=STORE):
    """Sector runs: entity_id, sector, valid_from, valid_to."""
    return pd.read_parquet(store / "sectors.parquet")


def sector_on(sectors, entity_ids, day):
    """{entity_id: sector} on `day`: the run whose valid_from is the latest on or before `day`. A company first shown
    after `day` gets its first run's sector (Wikipedia listed it later), and one never shown gets None."""
    day = pd.Timestamp(day)
    out = {}
    for e in entity_ids:
        runs = sectors[sectors.entity_id == e].sort_values("valid_from")
        if runs.empty:
            out[e] = None
            continue
        before = runs[runs.valid_from <= day]
        out[e] = (before.iloc[-1] if len(before) else runs.iloc[0]).sector
    return out


def spy_buy_and_hold(spy, first, last):
    """SPY bought at the open of `first` and held (PLAN 5.3, the long-only baseline): date and equity, its value at
    each session's open from Alpaca's adjusted opens (the bar's first trade; SPY has no official auction prints in the
    store), so it lines up with the simulator's marks at the open. Starts at 1.0."""
    s = spy[(spy.date >= pd.Timestamp(first)) & (spy.date <= pd.Timestamp(last))].sort_values("date")
    if s.empty:
        return pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"), "equity": pd.Series(dtype=float)})
    return pd.DataFrame({"date": s.date.to_numpy(), "equity": (s.adj_open / s.adj_open.iloc[0]).to_numpy()})
