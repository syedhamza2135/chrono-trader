import pandas as pd, glob, pyarrow.parquet as pq
pe = pd.read_csv("reference/price_events.csv", dtype=str)
for s, d in (("EQT", "2018-11-13"), ("DPS", "2018-07-10"), ("CCE", "2016-05-31")):
    x = pe[(pe.symbol == s) & (pe.date == d)]
    print(s, d, "rows", len(x), "actions", x.action.tolist())
for s, d in (("WYN", "2018-06-01"), ("WH", "2018-06-01"), ("HLT", "2017-01-04"), ("FTI", "2021-02-16")):
    print("left open, rows for", s, d, len(pe[(pe.symbol == s) & (pe.date == d)]))
st = pq.read_table("D:/chrono-data/store/stories.parquet", columns=["created_at"]).column(0)
import pyarrow.compute as pc
mm = pc.min_max(st); print("stories created_at min/max", mm["min"].as_py().date(), mm["max"].as_py().date())
m = pd.read_parquet("D:/chrono-data/store/membership.parquet")
print("membership member_to min (non-null)", m.member_to.min().date(), "member_from max", m.member_from.max().date())
bs = pq.read_table("D:/chrono-data/store/bars.parquet", columns=["date"]).column(0); mm = pc.min_max(bs); print("bars date min", mm["min"].as_py().date())
