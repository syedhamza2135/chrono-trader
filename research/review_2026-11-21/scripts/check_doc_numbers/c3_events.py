"""README and m1_kickoff numbers about reference/price_events.csv, the picks preview, and a few returns. No prices printed."""
import re, subprocess, pandas as pd, numpy as np
pe = pd.read_csv("reference/price_events.csv", dtype=str)
print("price_events rows", len(pe))
print("by action", pe.action.value_counts().to_dict())
print("by kind", pe.kind.value_counts().to_dict())
pc = ["open", "high", "low", "close", "volume", "vwap"]
has = pe[pc].notna().any(axis=1)
print("rows with a value in a price or volume column", int(has.sum()), "by action", pe[has].action.value_counts().to_dict())
print("rows with none of them", int((~has).sum()), "by action", pe[~has].action.value_counts().to_dict(),
      "symbols", sorted(pe[~has].symbol.tolist()))
tr = pe[pe.action == "total_return"]
print("total_return rows", len(tr), "with the word close in evidence", int(tr.evidence.str.contains("close", case=False, na=False).sum()))
print("total_return rows with a price column filled", int(tr[pc].notna().any(axis=1).sum()))
nord = pe[(pe.symbol == "JWN") & (pe.date == "2018-03-26")]
print("JWN 2018-03-26 rows", len(nord), "actions", nord.action.tolist(), "volume filled", bool(nord.volume.notna().all()))
print("by action: override_open", int((pe.action == "override_open").sum()), "override_close", int((pe.action == "override_close").sum()))
print("rows with a share quoting a headline: evidence containing a quotation mark", int(pe.evidence.str.contains('"|\u201c', na=False).sum()))
print("distinct failure kind symbols", sorted(pe[pe.kind == "failure"].symbol))
print("no_trade symbols", sorted(pe[pe.action == "no_trade"].symbol))

up = pd.read_csv("research/audit/universe_preview.csv")
print("universe_preview rows", len(up), "columns", up.columns.tolist())
yc = up.iloc[:, 0].astype(str).str[:4]
print("rows per first column value (top)", up.iloc[:, 0].value_counts().head(3).to_dict())
for c in up.columns:
    if up[c].nunique() < 20:
        print(" column", c, "distinct", up[c].nunique(), "values", sorted(up[c].unique().tolist())[:12])

# the three added rows and the labels around them (booleans only)
bars = pd.read_parquet("D:/chrono-data/store/bars.parquet")
ident = pd.read_parquet("D:/chrono-data/store/identity.parquet")
lab = pd.read_parquet("D:/chrono-data/store/labels.parquet")
def ent(sym):
    return ident[ident.symbol == sym].entity_id.unique().tolist()
def ret_on(sym, d):
    e = ent(sym)
    b = bars[bars.entity_id.isin(e) & (bars.date == d)]
    return None if b.empty else float(b.ret.iloc[0]) * 100
def lab_on(sym, d):
    e = ent(sym)
    l = lab[lab.entity_id.isin(e) & (lab.date == d)]
    return None if l.empty else float(l.label.iloc[0]) * 100
checks = [("EQT ret 2018-11-13 stated +1.82", ret_on("EQT", "2018-11-13"), 1.82),
          ("EQT last member-day label 2018-11-12 stated -0.70", lab_on("EQT", "2018-11-12"), -0.70),
          ("DPS ret 2018-07-10 stated +1.84", ret_on("DPS", "2018-07-10"), 1.84),
          ("CCE ret 2016-05-31 stated +3.41", ret_on("CCE", "2016-05-31"), 3.41),
          ("CCE last member-day label 2016-05-27 stated +0.58", lab_on("CCE", "2016-05-27"), 0.58)]
for name, got, stated in checks:
    print(name, "| reproduced within 0.01 pp:", None if got is None else abs(got - stated) < 0.011, "| diff pp", None if got is None else round(got - stated, 3))
