"""Skeptic check for L5's 'n_companies uses no future membership': do identity spans start before a company's first
S&P 500 membership day? Counts and ids only."""
from pathlib import Path
import pandas as pd
idn = pd.read_csv(Path.cwd() / "reference" / "identity.csv", dtype=str)
mem = pd.read_parquet("D:/chrono-data/store/membership.parquet")
first_mem = mem.groupby(mem.entity_id.astype(str)).member_from.min()
first_span = pd.to_datetime(idn.groupby("entity_id").valid_from.min())
j = pd.concat([first_span.rename("span"), first_mem.rename("mem")], axis=1, join="inner")
early = j[(j.span < j.mem) & (j.mem > pd.Timestamp("2015-01-01"))]
print("entities in both:", len(j), "| identity only:", len(first_span.index.difference(first_mem.index)),
      "| span starts before first membership (membership after 2015-01-01):", len(early))
print("  ids:", list(early.index[:10]))
print("  dated_by values:", idn.dated_by.value_counts().to_dict())
for e in early.index:
    rows = idn[idn.entity_id == e].sort_values("valid_from")
    print(f"  {e}: first membership {j.mem[e].date()} | spans:",
          [(r.symbol, r.valid_from, r.valid_to, r.dated_by) for r in rows.itertuples()])
