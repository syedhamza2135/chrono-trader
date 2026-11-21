"""I1 follow-up: ticker changes in the index file around two low runs (2016-01-15 and 2018-11-27..2018-12-03).
Symbols and dates only. Run from the repo root with D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore <this file>.
"""
import pandas as pd

snap = pd.read_csv("D:/chrono-data/membership/components_extended.csv", parse_dates=["date"])
snap["set"] = snap.tickers.str.split(",").map(lambda x: {t.strip() for t in x if t.strip()})
for lo, hi in [("2016-01-08", "2016-01-25"), ("2018-11-20", "2018-12-10"), ("2018-10-25", "2018-11-08")]:
    part = snap[(snap.date >= lo) & (snap.date <= hi)]
    prev = snap[snap.date < lo].iloc[-1].set
    print("window", lo, hi)
    for r in part.itertuples():
        print("  ", r.date.date(), len(r.set), "removed", sorted(prev - r.set), "added", sorted(r.set - prev))
        prev = r.set
