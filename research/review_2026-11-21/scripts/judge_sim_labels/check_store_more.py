"""Judge follow-up on the store: at_close labels by kind, labels with no later label, and the size of the
distribution share on the 58 total_return end days. Counts, ids and dates only, never a price.

Run from the worktree root (PowerShell):
  $env:CHRONO_ENV_FILE = "C:\\Users\\syedh\\dev\\chrono-trader\\.env"
  D:\\venvs\\chrono-trader\\Scripts\\python.exe research\\review_2026-11-21\\scripts\\judge_sim_labels\\check_store_more.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from data_pipeline import store  # noqa: E402
from world.clock import nyse  # noqa: E402

S = store.STORE
K = ["entity_id", "share_class"]
lab = pd.read_parquet(S / "labels.parquet")
opn = pd.read_parquet(S / "opens.parquet", columns=K + ["date", "open"])
bars = pd.read_parquet(S / "bars.parquet", columns=K + ["symbol", "date", "close", "ret", "volume", "member"])
data_end = pd.Timestamp(json.loads((S / "counts.json").read_text())["data_end"])
ev = pd.read_csv(ROOT / "reference" / "price_events.csv", dtype=str)
sessions = nyse().sessions
sessions = sessions.tz_localize(None) if sessions.tz else sessions

# A. at_close labels: is the end bar a member day, is the start bar a member day, and the one near data_end.
ac = lab[lab.at_close].merge(bars[K + ["date", "member", "symbol"]].rename(columns={"date": "end", "member": "end_member"}),
                             on=K + ["end"])
ac = ac.merge(bars[K + ["date", "member"]].rename(columns={"member": "start_member"}), on=K + ["date"])
print("A at_close:", len(ac), "| end bar a member day:", int(ac.end_member.sum()),
      "| start bar a member day:", int(ac.start_member.sum()),
      "| end bar non-member (series cut by the 14-day window or stopped after leaving):", int((~ac.end_member).sum()))
near = ac[ac.end >= sessions[sessions.searchsorted(data_end) - 10]]
for r in near.itertuples():
    kinds = sorted(set(ev[ev.symbol == r.symbol].kind))
    print(f"  near data_end: entity {r.entity_id} {r.symbol} end {r.end.date()} end_member {r.end_member} "
          f"price_events kinds for symbol: {kinds}")

# B. Official opens with no label that are not the series' last open: what follows them.
o = opn.dropna(subset=["open"]).sort_values(K + ["date"])
o["next_open"] = o.groupby(K).date.shift(-1)
m = o.merge(lab[K + ["date"]].assign(has=True), on=K + ["date"], how="left")
nol = m[m.has.isna() & m.next_open.notna()].merge(bars[K + ["date", "member"]], on=K + ["date"])
gap = (nol.next_open - nol.date).dt.days
print("B opens with no label and a later open:", len(nol), "| member days:", int(nol.member.sum()),
      "| calendar days to the next open: min", int(gap.min()), "median", int(gap.median()),
      "| next open within 7 days:", int((gap <= 7).sum()))
for r in nol[nol.member].itertuples():
    print(f"  member day with no label: entity {r.entity_id} {r.date.date()} next open {r.next_open.date()}")

# C. The distribution share of the ex-date return on the 58 total_return end days:
#    d = (1 + ret_j) - close_j / close_{j-1}. Large d means a large spin-off, where the closes stop cancelling.
b = bars.sort_values(K + ["date"]).copy()
b["prev_close"] = b.groupby(K).close.shift(1)
tr = ev[ev.action == "total_return"].assign(date=lambda e: pd.to_datetime(e.date))
x = tr[["symbol", "date"]].merge(b, on=["symbol", "date"])
d = (1 + x.ret) - x.close / x.prev_close
print("C total_return end days:", len(x), "| member days:", int(x.member.sum()),
      "| distribution share d: <2%", int((d < 0.02).sum()), "2-10%", int(((d >= 0.02) & (d < 0.10)).sum()),
      "10-30%", int(((d >= 0.10) & (d < 0.30)).sum()), ">=30%", int((d >= 0.30).sum()),
      "| undefined:", int(d.isna().sum()))
