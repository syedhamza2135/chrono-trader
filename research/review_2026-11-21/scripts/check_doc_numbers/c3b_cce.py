"""CCE labels near the 2016-05-31 merger row: dates, member flags and label in percent."""
import pandas as pd
bars = pd.read_parquet("D:/chrono-data/store/bars.parquet")
ident = pd.read_parquet("D:/chrono-data/store/identity.parquet")
lab = pd.read_parquet("D:/chrono-data/store/labels.parquet")
e = ident[ident.symbol == "CCE"].entity_id.unique().tolist()
print("CCE entity ids", e)
b = bars[bars.entity_id.isin(e) & (bars.date >= "2016-05-20")][["date", "member", "ret"]]
b["ret_pct"] = (b.ret * 100).round(2); print(b.drop(columns="ret").to_string(index=False))
l = lab[lab.entity_id.isin(e) & (lab.date >= "2016-05-20")].copy()
l["label_pct"] = (l.label * 100).round(2)
print(l[["date", "end", "at_close", "label_pct"]].to_string(index=False))
