# Counts only. Reads date, end and at_close of labels; the label value is not read.
import pyarrow.parquet as pq, numpy as np, exchange_calendars as xc
l = pq.read_table("D:/chrono-data/store/labels.parquet", columns=["entity_id", "date", "end", "at_close"]).to_pandas()
s = xc.get_calendar("XNYS").sessions_in_range("2015-12-01", "2026-12-31").tz_localize(None).normalize()
i0 = s.searchsorted(l.date.dt.normalize()); i1 = s.searchsorted(l.end.dt.normalize())
span = i1 - i0
o = l[~l.at_close]
sp = span[~l.at_close.to_numpy()]
print("labels", len(l), "not at_close", len(o))
print("sessions from start to end (not at_close):", dict(zip(*np.unique(sp, return_counts=True))))
