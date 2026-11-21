"""Where each run of no-bar member days sits against its membership span. Counts, ids, symbols and dates only.
Run from the repo root:
  D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore research\\review_2026-11-21\\scripts\\check_identity\\check_identity_gaps.py
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

S = "D:/chrono-data/store/"
mem = pq.read_table(S + "membership.parquet").to_pandas()
bars = pq.read_table(S + "bars.parquet", columns=["entity_id", "date"]).to_pandas()
sessions = pd.DatetimeIndex(sorted(bars.date.unique()))
have = set(zip(bars.entity_id, bars.date))
DATA_END = pd.Timestamp("2026-10-28")
sess = sessions.to_numpy().astype("datetime64[ns]")
tail, mid, other = [], [], []
for r in mem.itertuples():
    a = np.datetime64(r.member_from, "ns")
    b = np.datetime64(r.member_to if pd.notna(r.member_to) else DATA_END + pd.Timedelta(days=1), "ns")
    days = pd.DatetimeIndex(sess[(sess >= a) & (sess < b) & (sess <= np.datetime64(DATA_END, "ns"))])
    miss = [d for d in days if (r.entity_id, d) not in have]
    if not miss:
        continue
    last_member_session = days[-1]
    if miss[-1] == last_member_session:
        tail.append((r.entity_id, len(miss)))
    elif miss[0] > days[0]:
        mid.append((r.entity_id, miss[0].date().isoformat(), len(miss)))
    else:
        other.append((r.entity_id, miss[0].date().isoformat(), len(miss)))
print("rows whose missing days are at the end of the membership span (last member session is missing):", len(tail), "| days:", sum(n for _, n in tail))
print("rows with missing days in the middle of a span:", len(mid), mid)
print("rows with missing days at the start:", len(other), other)
mem_null_end = mem[mem.member_to.isna()]
print("of the tail rows, ones with member_to null (still a member at data_end):",
      sum(1 for e, _ in tail if e in set(mem_null_end.entity_id)), [e for e, _ in tail if e in set(mem_null_end.entity_id)])
