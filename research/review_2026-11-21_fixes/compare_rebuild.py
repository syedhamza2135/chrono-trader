"""After the M-2 rebuild: compare D:\\chrono-data\\store with the backup made before it (store_backup_2026-11-21).

Expected: the same rows in every table, every table but labels identical, and in labels exactly the 55 labels that
end on a price_events.csv ex-date with an open_value, each moved by the amount predicted from the old store, and
their end_open_time moved to open_value_time where that is later. Counts and points only, no prices.

Usage: python research/review_2026-11-21_fixes/compare_rebuild.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data_pipeline.settings import DATA_DIR, ROOT  # noqa: E402

NEW, OLD = DATA_DIR / "store", DATA_DIR / "store_backup_2026-11-21"
K = ["entity_id", "share_class", "date"]

for name in ("bars", "opens", "stories", "story_entities", "membership", "identity"):
    a, b = pd.read_parquet(OLD / f"{name}.parquet"), pd.read_parquet(NEW / f"{name}.parquet")
    same = a.shape == b.shape and list(a.columns) == list(b.columns) and a.equals(b)
    print(f"{name}: {len(a):,} rows before, {len(b):,} after, identical: {same}")

old, new = pd.read_parquet(OLD / "labels.parquet"), pd.read_parquet(NEW / "labels.parquet")
print(f"labels: {len(old):,} rows before, {len(new):,} after, columns equal: {list(old.columns) == list(new.columns)}")
m = old.merge(new, on=K, how="outer", suffixes=("_old", "_new"), indicator=True)
print("  rows only before:", int((m._merge == "left_only").sum()), "only after:", int((m._merge == "right_only").sum()))
m = m[m._merge == "both"]
for c in ("end", "at_close", "end_open_time"):
    print(f"  {c} differs on:", int((m[f"{c}_old"].ne(m[f"{c}_new"]) & ~(m[f"{c}_old"].isna() & m[f"{c}_new"].isna())).sum()))
moved = m.drop(columns="_merge")[~np.isclose(m.label_old, m.label_new, rtol=0, atol=1e-12)]
print("  labels whose value changed:", len(moved))

# The expected 55, and their predicted moves, from the old store's bars and opens (as m2_label_changes.py does).
bars = pd.read_parquet(OLD / "bars.parquet", columns=K[:2] + ["symbol", "date", "close", "ret", "member"])
opens = pd.read_parquet(OLD / "opens.parquet", columns=K + ["open"])
bars = bars.sort_values(K, ignore_index=True)
bars["prev_close"] = bars.groupby(K[:2], sort=False).close.shift(1)
ev = pd.read_csv(ROOT / "reference" / "price_events.csv", dtype=str, keep_default_na=False)
ev = ev[(ev.action == "total_return") & (ev.open_value != "")][["symbol", "date", "open_value", "open_value_time"]]
ev = ev.assign(date=pd.to_datetime(ev.date))
b = bars.sort_values("member").drop_duplicates(["symbol", "date"], keep="last")
x = ev.merge(b, on=["symbol", "date"]).merge(opens, on=K)
x = x.merge(old[~old.at_close].rename(columns={"date": "start", "end": "date"}), on=K)
x["predicted"] = (1 + x.label) * (x.open_value.astype(float) / x.prev_close) * x.close / ((1 + x.ret) * x.open) - 1
x["later"] = pd.to_datetime(x.open_value_time, utc=True) > x.end_open_time
x["predicted_time"] = x[["end_open_time"]].assign(v=pd.to_datetime(x.open_value_time, utc=True)).max(axis=1)
print("  of the expected, open_value_time later than the parent's open:", int(x.later.sum()))
x = x.rename(columns={"date": "end", "start": "date"})[K + ["predicted", "predicted_time"]]
got = moved.merge(x, on=K, how="outer", indicator=True)
print("  expected:", len(x), "| changed and expected:", int((got._merge == "both").sum()),
      "| changed, not expected:", int((got._merge == "left_only").sum()),
      "| expected, not changed:", int((got._merge == "right_only").sum()))
both = got[got._merge == "both"]
print("  largest gap between the new label and the predicted one (points):",
      f"{100 * (both.label_new - both.predicted).abs().max():.2e}")
times = m.merge(x, on=K, how="left")
changed_time = times.end_open_time_old.ne(times.end_open_time_new) & times.end_open_time_old.notna()
print("  end_open_time changed:", int(changed_time.sum()), "| all to the predicted time:",
      bool((times[changed_time].end_open_time_new == times[changed_time].predicted_time).all()),
      "| changed outside the expected:", int((changed_time & times.predicted.isna()).sum()))
