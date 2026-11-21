"""Alpaca's adjusted close-to-close return on the three correction days, from the downloaded 'all' bar files. Returns only."""
import glob, pandas as pd, pyarrow.parquet as pq
for sym, d, stated in (("EQT", "2018-11-13", -57.15), ("DPS", "2018-07-10", 11.45), ("CCE", "2016-05-31", -24.70)):
    files = sorted(glob.glob(f"D:/chrono-data/bars/all/{sym}__*.parquet"))
    best = None
    for f in files:
        t = pq.read_table(f, columns=["t", "close"]).to_pandas()
        t["d"] = t.t.astype(str).str[:10]
        t = t.sort_values("d").reset_index(drop=True)
        i = t.index[t.d == d]
        if len(i) and i[0] > 0:
            best = (t.close[i[0]] / t.close[i[0] - 1] - 1) * 100
            break
    print(sym, d, "files", len(files), "vendor adjusted return reproduced within 0.01 pp of stated:", None if best is None else abs(best - stated) < 0.011, "diff pp", None if best is None else round(best - stated, 3))
