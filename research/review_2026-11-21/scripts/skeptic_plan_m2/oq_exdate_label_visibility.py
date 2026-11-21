# Open question: is a label whose end day is a distribution's ex-date (its value uses that day's close) visible in a
# view taken between 9:30 and 16:00 New York on the ex-date? Counts, ids and dates only; no label value or price.
import sys, pandas as pd
root = sys.argv[1]; sys.path.insert(0, root)
from world import rules
from world.world import World, sealed_start
NY = "America/New_York"
ev = pd.read_csv(root + "/reference/price_events.csv", usecols=["symbol", "date", "action"])
ev = ev[ev.action == "total_return"].assign(date=lambda d: pd.to_datetime(d.date))
w = World.load()                      # dev years only: views on sealed dates are refused
L = w.labels.df
print("total_return events (distributions)", len(ev))
# map symbol+date to entity via the store's bars (ids only)
import pyarrow.parquet as pq
b = pq.read_table(root.replace(root, "D:/chrono-data/store/bars.parquet"), columns=["entity_id", "symbol", "date"]).to_pandas()
b["date"] = pd.to_datetime(b.date).dt.tz_localize(None).dt.normalize()
m = ev.merge(b, on=["symbol", "date"], how="inner")
print("events matched to a store bar", len(m))
lab = pd.DataFrame({"entity_id": L.entity_id, "end": pd.to_datetime(L["end"]).dt.tz_localize(None).dt.normalize(),
                    "at_close": L.at_close, "end_open_time": L.end_open_time})
hit = lab.merge(m[["entity_id", "date"]].rename(columns={"date": "end"}), on=["entity_id", "end"])
hit = hit[~hit.at_close]
print("labels not at a close that end on an event's ex-date", len(hit))
r = rules.label(hit["end"].to_numpy(), hit.at_close.to_numpy(), hit.end_open_time.to_numpy()).dt.tz_convert(NY)
close16 = pd.to_datetime(hit["end"]).dt.tz_localize(NY) + pd.Timedelta(hours=16)
before = (r.to_numpy() < close16.to_numpy())
print("of those, rule time before 16:00 NY on the ex-date", int(before.sum()), "; at or after 16:00", int((~before).sum()))
print("rule time-of-day counts", r.dt.strftime("%H:%M").value_counts().head(5).to_dict())
# real views in the dev years: at 12:00 on the ex-date (mid-session) and at the simulator's 9:00
seal = sealed_start()
dev = hit[pd.to_datetime(hit["end"]) < seal.tz_localize(None) if seal.tzinfo else pd.to_datetime(hit["end"]) < seal]
print("of those in the dev years (before sealed start", str(seal.date()) + ")", len(dev))
seen_noon = seen_nine = 0; ex = []
for d, g in dev.groupby("end"):
    for hh, mm, tag in ((12, 0, "noon"), (9, 0, "nine")):
        t = pd.Timestamp(d).tz_localize(NY) + pd.Timedelta(hours=hh, minutes=mm)
        v = w.view(t).labels
        vv = v.assign(end=pd.to_datetime(v["end"]).dt.tz_localize(None).dt.normalize())
        k = vv.merge(g[["entity_id", "end"]], on=["entity_id", "end"]).shape[0]
        if tag == "noon": seen_noon += k; ex += [(str(pd.Timestamp(d).date()), e) for e in g.entity_id][:1] if k else []
        else: seen_nine += k
print("visible in a 12:00 NY view on the ex-date", seen_noon, "of", len(dev))
print("visible in the 9:00 NY view on the ex-date (the simulator's decision time)", seen_nine, "of", len(dev))
print("examples (ex-date, entity_id)", ex[:4])
