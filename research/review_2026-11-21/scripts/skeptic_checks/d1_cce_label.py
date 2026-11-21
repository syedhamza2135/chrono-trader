"""D1: CCE's labels and returns around the 2016-05-31 merger row, from the store. Dates, flags and percents only
(no prices). Checks the label against the product of the parts it is built from, using only ratios.
Run from the repo root with D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore <this file>.
"""
import pandas as pd

S = "D:/chrono-data/store/"
mem = pd.read_parquet(S + "membership.parquet")
ide = pd.read_parquet(S + "identity.parquet")
ents = sorted(set(ide[ide.symbol == "CCE"].entity_id))
print("CCE entities:", ents)
print("membership rows:", [(r.entity_id, str(r.member_from.date()), str(r.member_to.date()) if pd.notna(r.member_to) else None)
                           for r in mem[mem.entity_id.isin(ents)].itertuples()])
bars = pd.read_parquet(S + "bars.parquet", columns=["entity_id", "date", "member", "ret", "open", "close"])
b = bars[bars.entity_id.isin(ents) & (bars.date >= "2016-05-24") & (bars.date <= "2016-06-10")].sort_values("date")
print("bars (date, member, ret %):")
for r in b.itertuples():
    print("  ", r.date.date(), r.member, None if pd.isna(r.ret) else round(r.ret * 100, 2))
print("last bar date for CCE:", bars[bars.entity_id.isin(ents)].date.max().date())
lab = pd.read_parquet(S + "labels.parquet")
l = lab[lab.entity_id.isin(ents) & (lab.date >= "2016-05-24")].sort_values("date")
print("labels (date, end, at_close, label %):")
for r in l.itertuples():
    print("  ", r.date.date(), r.end.date(), r.at_close, round(r.label * 100, 2))
# Rebuild the 2016-05-27 label from ratios: close/open on the first day, (1+ret) between, then the last day's piece.
row = l[l.date == "2016-05-27"].iloc[0]
seg = b[(b.date >= row.date) & (b.date <= row.end)].reset_index(drop=True)
first = seg.iloc[0]
g = first.close / first.open
for k in range(1, len(seg)):
    g *= 1 + seg.ret[k]
if row.at_close:
    print("rebuilt 2016-05-27 label, ending at the last close: %.2f %%" % ((g - 1) * 100))
else:
    print("label ends at an open; not rebuilt here")
ev = pd.read_csv("reference/price_events.csv", dtype=str)
print("price_events rows for CCE:", ev[ev.symbol.eq("CCE") if "symbol" in ev else ev.apply(lambda r: "CCE" in r.values, axis=1)][["date", "kind"] if "kind" in ev else ev.columns[:3]].to_string(index=False))
