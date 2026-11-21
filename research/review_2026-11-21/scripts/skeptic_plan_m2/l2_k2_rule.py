# L2: count labels dated day k-2 that are not yet visible by rules.label at 9:00 on day k. Counts and dates only.
import sys, pandas as pd, pyarrow.parquet as pq
root = sys.argv[1]; sys.path.insert(0, root)
from world import rules
from world.clock import nyse
NY = "America/New_York"
l = pq.read_table("D:/chrono-data/store/labels.parquet", columns=["date", "end", "at_close", "end_open_time"]).to_pandas()
s = pd.DatetimeIndex(nyse().sessions)
d = pd.to_datetime(l.date).dt.tz_localize(None).dt.normalize()
i = s.searchsorted(d.to_numpy())
ok = i + 2 < len(s)
k = pd.Series(pd.NaT, index=l.index, dtype="datetime64[ns]"); k[ok] = s[i[ok] + 2]
nine = k.dt.tz_localize(NY) + pd.Timedelta(hours=9)
r = rules.label(l["end"].to_numpy(), l.at_close.to_numpy(), l.end_open_time.to_numpy())
late = ok & (r.to_numpy() > nine.dt.tz_convert("UTC").to_numpy())
print("labels", len(l), "with a session k = date + 2", int(ok.sum()))
print("day k-2 labels NOT visible at 9:00 on day k by rules.label:", int(late.sum()),
      "of which at_close", int((late & l.at_close).sum()))
print("their date range", d[late].min().date(), "to", d[late].max().date(), "; distinct dates", d[late].nunique())
