"""Open identity rows (empty valid_to) against active memberships. Ids, symbols and dates only.
Run from the repo root:
  D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore research\\review_2026-11-21\\scripts\\check_identity\\check_identity_open.py
"""
import pandas as pd
import pyarrow.parquet as pq

S = "D:/chrono-data/store/"
mem = pq.read_table(S + "membership.parquet").to_pandas()
ide = pq.read_table(S + "identity.parquet").to_pandas()
op = ide[ide.valid_to == ""]
act = mem[mem.member_to.isna()]
print("open identity rows:", len(op), "| entities:", op.entity_id.nunique(), "| null member_to rows:", len(act), "| entities:", act.entity_id.nunique())
print("open identity entities with no null member_to row:", sorted(set(op.entity_id) - set(act.entity_id)))
print("null member_to entities with no open identity row:", sorted(set(act.entity_id) - set(op.entity_id)))
per = op.groupby("entity_id").size()
pa = act.groupby("entity_id").size()
j = pd.concat([per.rename("open_identity"), pa.rename("null_member_to")], axis=1).fillna(0).astype(int)
d = j[j.open_identity != j.null_member_to]
print("entities where the two counts differ:")
for e, r in d.iterrows():
    g = op[op.entity_id == e]
    print("  ", e, dict(r), list(zip(g.symbol, g.share_class, g.valid_from)))
