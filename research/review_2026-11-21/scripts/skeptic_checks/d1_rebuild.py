"""D1: rebuild CCE's 2016-05-27 label from its parts (store.py rule: first day close/open, corrected returns between,
last day open/close), with official opens and with the store's 2016-05-31 return, then with the vendor return the doc
quotes (-24.70%). Prints percents only. Run from the repo root with D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore <this file>.
"""
import pandas as pd

S = "D:/chrono-data/store/"
E = "0001491675"
bars = pd.read_parquet(S + "bars.parquet", filters=[("entity_id", "=", E)]).set_index("date")
opens = pd.read_parquet(S + "opens.parquet", filters=[("entity_id", "=", E)]).set_index("date")
d0, d1 = pd.Timestamp("2016-05-27"), pd.Timestamp("2016-05-31")
o0, o1 = opens.loc[d0, "open"], opens.loc[d1, "open"]
c0, c1 = bars.loc[d0, "close"], bars.loc[d1, "close"]
for name, r in [("store return", bars.loc[d1, "ret"]), ("vendor return -24.70%", -0.2470)]:
    lab = c0 / o0 * (1 + r) * o1 / c1 - 1
    print(f"label 2016-05-27 with {name}: {lab * 100:.2f} %")
print(f"label in the store: {pd.read_parquet(S + 'labels.parquet', filters=[('entity_id', '=', E)]).set_index('date').loc[d0, 'label'] * 100:.2f} %")
print(f"plain open-to-open ratio of official opens (no corporate action): {(o1 / o0 - 1) * 100:.2f} %")
print(f"bar open to bar open: {(bars.loc[d1, 'open'] / bars.loc[d0, 'open'] - 1) * 100:.2f} %")
