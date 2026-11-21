"""Judge check for M-2 (b): the 3 total_return rows left without an open_return. On a plain price ratio the old end
piece oo_j / close_j * (1 + ret_j) cancels the ex-date's close only if (1 + ret_j) equals ratio x close_j / close_j-1
in the store. Prints that gap in points, and the label each row ends. No prices. Changes no file.
Usage: python research/review_2026-11-21_fixes/judge_scripts/m2_blank_rows.py"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data_pipeline.settings import DATA_DIR  # noqa: E402

ev = pd.read_csv(ROOT / "reference" / "price_events.csv", dtype=str, keep_default_na=False)
b = pd.read_parquet(DATA_DIR / "store" / "bars.parquet", columns=["entity_id", "share_class", "symbol", "date",
                                                                   "close", "member"])
b = b.sort_values(["entity_id", "share_class", "date"], kind="stable", ignore_index=True)
b["prev_close"] = b.groupby(["entity_id", "share_class"], sort=False).close.shift(1)
for sym, date, ratio in (("JCI", "2016-09-06", 0.955), ("IR", "2020-03-02", 1.0), ("GE", "2019-02-25", 1.0)):
    r = ev[(ev.symbol == sym) & (ev.date == date) & (ev.action == "total_return")].iloc[0]
    p = b[(b.symbol == sym) & (b.date == pd.Timestamp(date))].sort_values("member", kind="stable").iloc[-1]
    gap = (1 + float(r.total_return)) / (ratio * p.close / p.prev_close) - 1
    print(f"{sym} {date}: (1 + ret) against ratio x close / previous close in the store: {gap * 100:+.4f} points")
