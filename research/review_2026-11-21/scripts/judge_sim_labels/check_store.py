"""Judge check on the store's labels and opens (D:\\chrono-data\\store). Prints counts, ids, dates and return
differences only, never a price.

Run from the worktree root (PowerShell):
  $env:CHRONO_ENV_FILE = "C:\\Users\\syedh\\dev\\chrono-trader\\.env"
  D:\\venvs\\chrono-trader\\Scripts\\python.exe research\\review_2026-11-21\\scripts\\judge_sim_labels\\check_store.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from data_pipeline import store  # noqa: E402
from world import rules  # noqa: E402
from world.clock import nyse  # noqa: E402

S = store.STORE
lab = pd.read_parquet(S / "labels.parquet")
opn = pd.read_parquet(S / "opens.parquet", columns=["entity_id", "share_class", "date", "open", "open_time"])
bars = pd.read_parquet(S / "bars.parquet", columns=["entity_id", "share_class", "symbol", "date", "close", "ret",
                                                     "volume", "member", "no_trade"])
counts = json.loads((S / "counts.json").read_text())
data_end = pd.Timestamp(counts["data_end"])
K = ["entity_id", "share_class"]
sessions = nyse().sessions
sidx = pd.Series(np.arange(len(sessions)), index=sessions.tz_localize(None) if sessions.tz else sessions)
print("rows: labels", len(lab), "opens", len(opn), "bars", len(bars), "data_end", data_end.date())

# Q1. Official opens with no label starting on them, by reason.
o = opn.dropna(subset=["open"])
m = o.merge(lab[K + ["date"]].assign(has=True), on=K + ["date"], how="left")
nol = m[m.has.isna()].copy()
last_open = o.groupby(K).date.max().rename("last_open")
nol = nol.merge(last_open, left_on=K, right_index=True)
nol["is_last_open"] = nol.date.eq(nol.last_open)
nol = nol.merge(bars[K + ["date", "member", "volume"]], on=K + ["date"], how="left")
print("Q1 opens with an official open:", len(o), "with no label:", len(nol))
print("   on data_end:", int((nol.date == data_end).sum()),
      "| last open of its series, before data_end:", int((nol.is_last_open & (nol.date < data_end)).sum()),
      "| not the last open (a later open exists):", int((~nol.is_last_open).sum()),
      "| of those, member days:", int((~nol.is_last_open & nol.member).sum()))

# Q2. A label that doesn't end at a close ends at the next official open of the same listing.
o = o.sort_values(K + ["date"])
o["next_open"] = o.groupby(K).date.shift(-1)
o["next_time"] = o.groupby(K).open_time.shift(-1)
nc = lab[~lab.at_close].merge(o[K + ["date", "next_open", "next_time"]], on=K + ["date"], how="left")
print("Q2 open-to-open labels:", len(nc), "end != next official open:", int((nc.end != nc.next_open).sum()))
print("Q3 end_open_time != the end open's open_time:", int((nc.end_open_time != nc.next_time).sum()))

# Q4. Sessions spanned by a label.
span = sidx.reindex(lab.end).to_numpy() - sidx.reindex(lab.date).to_numpy()
print("Q4 sessions spanned (end minus start):", pd.Series(span).value_counts().sort_index().to_dict())
cal = (lab.end - lab.date).dt.days
print("   labels over 7 calendar days:", int((cal > 7).sum()), "| over 30:", int((cal > 30).sum()))

# Q5. at_close labels and failures.
ac = lab[lab.at_close]
print("Q5 at_close labels:", len(ac), "| label == -1:", int((ac.label == -1).sum()),
      "| -1 anywhere:", int((lab.label == -1).sum()))
lb = bars[bars.volume > 0].groupby(K).date.max().rename("last_traded")
acx = ac.merge(lb, left_on=K, right_index=True)
print("   at_close end != series' last traded bar:", int((acx.end != acx.last_traded).sum()))
vis = rules.label(ac.end.reset_index(drop=True), ac.at_close.reset_index(drop=True))
nxt = sessions[sessions.searchsorted(ac.end.to_numpy(), side="right")]
print("   at_close visible at 9:30 on the next session:", bool((vis.dt.tz_convert("America/New_York").dt.normalize()
      .dt.tz_localize(None).to_numpy() == np.asarray(nxt.tz_localize(None) if nxt.tz else nxt)).all()))
for r in ac[ac.label == -1].itertuples():
    print(f"   failed exit: entity {r.entity_id} start {r.date.date()} end {r.end.date()}")
near = ac[ac.end >= sessions[sessions.searchsorted(data_end) - 10]]
print("   at_close ending in the last 10 sessions before data_end:", len(near))

# Q6. no_trade bars.
nt = bars[bars.no_trade].merge(opn[K + ["date", "open"]], on=K + ["date"], how="left")
nt = nt.merge(lab[K + ["date"]].assign(lab=True), on=K + ["date"], how="left")
print("Q6 no_trade bars:", len(nt), "| volume > 0:", int((nt.volume > 0).sum()),
      "| with an official open:", int(nt.open.notna().sum()), "| a label starts there:", int(nt.lab.notna().sum()))

# Q7. Zero-volume bars with an official open, and labels starting there.
zv = bars[bars.volume == 0].merge(opn.dropna(subset=["open"])[K + ["date"]], on=K + ["date"])
zl = zv.merge(lab[K + ["date"]], on=K + ["date"])
print("Q7 zero-volume bars:", int((bars.volume == 0).sum()), "| with an official open:", len(zv),
      "| a label starts there:", len(zl), "| member days among those:", int(zl.member.sum()))

# Q8. Labels whose end day carries a total_return event (a distribution's ex-date).
ev = pd.read_csv(ROOT / "reference" / "price_events.csv", dtype=str)
tr = ev[ev.action == "total_return"].assign(date=lambda e: pd.to_datetime(e.date))
tr = tr.merge(bars[K + ["symbol", "date", "member"]], on=["symbol", "date"])
end_on = lab[~lab.at_close].merge(tr[K + ["date"]].rename(columns={"date": "end"}), on=K + ["end"])
print("Q8 total_return events in the store:", len(tr), "| open-to-open labels ending on one:", len(end_on))

# Q9. EQT 2018-11-13 (price_events.csv): the label's overnight piece against the open-based total return.
row = ev[(ev.symbol == "EQT") & (ev.date == "2018-11-13") & (ev.action == "total_return")].iloc[0]
spin_open = float(re.search(r"\+ 0\.8 x (\d+\.\d+) = ", row.evidence).group(1))
b = bars[(bars.symbol == "EQT") & bars.date.isin(pd.to_datetime(["2018-11-12", "2018-11-13"]))].sort_values("date")
ent, cls = b.entity_id.iat[1], b.share_class.iat[1]
oj = opn[(opn.entity_id == ent) & (opn.share_class == cls) & (opn.date == "2018-11-13")].open.iat[0]
piece = (1 + b.ret.iat[1]) * oj / b.close.iat[1]
truth = (oj + 0.8 * spin_open) / b.close.iat[0]
l = lab[(lab.entity_id == ent) & (lab.share_class == cls) & (lab.date == "2018-11-12")]
print(f"Q9 EQT label 2018-11-12 to {l.end.iat[0].date()}: overnight piece minus open-based total return = "
      f"{100 * (piece - truth):+.2f} percentage points; stored label minus open-based label = "
      f"{100 * (l.label.iat[0] - ((1 + l.label.iat[0]) / piece * truth - 1)):+.2f} pp")

# Q10. Rebuild the labels from the stored bars and opens with store.labels and compare.
bars_s = bars.sort_values(K + ["date"]).reset_index(drop=True)
failed = store.failures(bars_s, ev)
re_lab = store.labels(bars_s, opn, data_end, failed)
j = lab.merge(re_lab, on=K + ["date"], how="outer", suffixes=("", "_re"), indicator=True)
both = j[j._merge == "both"]
print("Q10 rebuilt labels:", len(re_lab), "| only stored:", int((j._merge == "left_only").sum()),
      "| only rebuilt:", int((j._merge == "right_only").sum()),
      "| end differs:", int((both.end != both.end_re).sum()),
      "| at_close differs:", int((both.at_close != both.at_close_re).sum()),
      "| label differs by > 1e-9:", int((abs(both.label - both.label_re) > 1e-9).sum()),
      "| failed series:", len(failed))
