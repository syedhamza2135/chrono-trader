"""Skeptic checks for L2, L3 and L5 on the real store. Prints dates, counts, ids and column names only."""
import sys
from pathlib import Path
import pandas as pd, pyarrow.parquet as pq
ROOT = Path.cwd(); sys.path[:0] = [str(ROOT)]
from world import rules
from world.clock import Clock, NY
S = Path("D:/chrono-data/store")

print("== L2")
lab = pd.read_parquet(S / "labels.parquet")
ac = lab[lab.at_close.astype(bool)]
print("at_close labels:", len(ac), "| with label == -1:", int((ac.label == -1).sum()))
fail = ac[ac.label == -1].copy()
fail["vis"] = rules.label(fail.end, fail.at_close, fail.end_open_time).dt.tz_convert(NY)
clk = Clock()
for r in fail.itertuples():
    v = pd.Timestamp(r.vis); vd = v.tz_localize(None).normalize()
    nxt = next(d for d in clk.between(vd, vd + pd.Timedelta(days=10))
               if clk.decision_time(d) >= v)
    print(f"  entity {r.entity_id} class {r.share_class}: date {r.date.date()} end {r.end.date()} visible {v} first 9:00 view {nxt.date()}")
st = pd.read_parquet(S / "stories.parquet", columns=["story_id", "created_at", "updated_at"])
for sid in (31295313, 31299421):
    hit = st[st.story_id.astype(str) == str(sid)]
    for r in hit.itertuples():
        print(f"  story {sid}: created {pd.Timestamp(r.created_at).tz_convert(NY)} updated {pd.Timestamp(r.updated_at).tz_convert(NY)}")
    if hit.empty:
        print(f"  story {sid}: not in stories.parquet")

print("== L3")
c, u = pd.to_datetime(st.created_at, utc=True), pd.to_datetime(st.updated_at, utc=True)
print("stories:", len(st), "| updated<created:", int((u < c).sum()), "| updated+15min<created:", int((u + rules.NEWS_DELAY < c).sum()),
      "| max gap minutes:", float(((c - u)[u < c]).max().total_seconds() / 60) if (u < c).any() else 0.0)
print("  ids with updated<created:", sorted(st.story_id[u < c].astype(str).tolist()))

print("== L5")
for n in ("bars", "labels", "stories", "story_entities"):
    print(f"  {n} columns:", pq.read_schema(S / f"{n}.parquet").names)
lv = rules.label(lab.end, lab.at_close, lab.end_open_time)
eot = pd.to_datetime(lab.end_open_time, utc=True)
print("  labels with end_open_time set:", int(eot.notna().sum()), "| end_open_time later than visible time:", int((eot > lv).sum()),
      "| of them at_close:", int(((eot > lv) & lab.at_close.astype(bool)).sum()))
