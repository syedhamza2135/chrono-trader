"""How the M-2 fix moves the stored labels, read-only: for each labels row that ends on a price_events.csv ex-date with
an open_value, the label with the open-valued last piece, against the stored one. Counts and points, no prices.

Usage: python research/review_2026-11-21_fixes/m2_label_changes.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data_pipeline.settings import DATA_DIR, ROOT  # noqa: E402

store = DATA_DIR / "store"
bars = pd.read_parquet(store / "bars.parquet", columns=["entity_id", "share_class", "symbol", "date", "close", "ret",
                                                        "member"])
opens = pd.read_parquet(store / "opens.parquet", columns=["entity_id", "share_class", "date", "open"])
lab = pd.read_parquet(store / "labels.parquet")
ev = pd.read_csv(ROOT / "reference" / "price_events.csv", dtype=str, keep_default_na=False)
ev = ev[(ev.action == "total_return") & (ev.open_value != "")][["symbol", "date", "open_value"]]
ev = ev.assign(date=pd.to_datetime(ev.date))
bars = bars.sort_values(["entity_id", "share_class", "date"], ignore_index=True)
bars["prev_close"] = bars.groupby(["entity_id", "share_class"], sort=False).close.shift(1)
b = bars.sort_values("member").drop_duplicates(["symbol", "date"], keep="last")
x = ev.merge(b, on=["symbol", "date"]).merge(opens, on=["entity_id", "share_class", "date"])
x = x.merge(lab[~lab.at_close].rename(columns={"date": "start", "end": "date"}),
            on=["entity_id", "share_class", "date"])
start_member = x.merge(bars[["entity_id", "share_class", "date", "member"]].rename(
    columns={"date": "start", "member": "start_member"}), on=["entity_id", "share_class", "start"]).start_member
new = (1 + x.label) * (x.open_value.astype(float) / x.prev_close) * x.close / ((1 + x.ret) * x.open) - 1
x["move_pp"] = 100 * (new - x.label)
print(f"rows with an open_value: {len(ev)}; labels ending on one: {len(x)} "
      f"({int(start_member.sum())} start on a member day)")
for lo, hi in ((0, 0.1), (0.1, 1), (1, 3), (3, np.inf)):
    print(f"  moved {lo} to {hi} points: {int(((x.move_pp.abs() >= lo) & (x.move_pp.abs() < hi)).sum())}")
print("largest moves (points):")
for r in x.reindex(x.move_pp.abs().sort_values(ascending=False).index).head(8).itertuples():
    print(f"  {r.symbol} {r.date.date()}: {r.move_pp:+.2f}")
for sym, d in (("AIV", "2020-11-03"), ("NLOK", "2020-02-03"), ("EQT", "2018-11-13")):
    r = x[(x.symbol == sym) & (x.date == d)]
    print(f"  review's rows: {sym} {d}: {r.move_pp.iloc[0]:+.2f}")
