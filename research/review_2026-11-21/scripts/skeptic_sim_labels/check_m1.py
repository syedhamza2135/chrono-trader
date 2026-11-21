r"""Skeptic check of M1: does a total_return ex-date at a label's end keep the end-day close in the label?
Prints counts, ids, dates and return differences in percentage points only, never a price.

Run from the worktree root (PowerShell):
  $env:CHRONO_ENV_FILE = "C:\Users\syedh\dev\chrono-trader\.env"
  D:\venvs\chrono-trader\Scripts\python.exe research\review_2026-11-21\scripts\skeptic_sim_labels\check_m1.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from data_pipeline import store  # noqa: E402

K = ["entity_id", "share_class"]

# S. Synthetic, independent of the judge's frames. Day 0: one share at 100. Day 1 is the ex-date of a spin-off.
# At day 1's open the parent is 50 and the spun-off share 50 (true open-to-open: 0%). Only the closes on day 1 vary.
def synth(parent_close, spin_close):
    d = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"])
    s = pd.DataFrame({"entity_id": "E", "share_class": "A", "date": d, "close": [100.0, parent_close, 50.0],
                      "ret": [np.nan, (parent_close + spin_close) / 100.0 - 1, 0.0], "volume": [1, 1, 1]})
    o = pd.DataFrame({"entity_id": "E", "share_class": "A", "date": d, "open": [100.0, 50.0, 50.0],
                      "open_time": pd.to_datetime(["2020-01-02 14:30", "2020-01-03 14:30", "2020-01-06 14:30"],
                                                  utc=True)})
    lab = store.labels(s, o, pd.Timestamp("2020-01-06"))
    return 100 * lab[lab.date == d[0]].label.iat[0]
for pc, sc in [(50, 50), (55, 55), (50, 60), (45, 50)]:
    print(f"S synthetic: day-1 closes parent {pc} spin {sc} -> label day0->day1 {synth(pc, sc):+.2f} pp "
          f"(true open-to-open +0.00)")

# Store.
S = store.STORE
lab = pd.read_parquet(S / "labels.parquet")
opn = pd.read_parquet(S / "opens.parquet", columns=K + ["date", "open"])
bars = pd.read_parquet(S / "bars.parquet", columns=K + ["symbol", "date", "close", "ret", "member"])
bars = bars.sort_values(K + ["date"]).reset_index(drop=True)
bars["prev_close"] = bars.groupby(K).close.shift(1)
ev = pd.read_csv(ROOT / "reference" / "price_events.csv", dtype=str)
tr = ev[ev.action == "total_return"].copy()
tr["date"] = pd.to_datetime(tr.date)
x = tr.drop(columns=["open", "high", "low", "close", "volume", "vwap"]).merge(bars, on=["symbol", "date"], how="left")
print("E total_return rows:", len(tr), "| matched to a store bar:", int(x.entity_id.notna().sum()),
      "| store ret equals the csv total_return (1e-12):",
      int((abs(x.ret - x.total_return.astype(float)) < 1e-12).sum()))
x = x.merge(opn.rename(columns={"open": "oo"}), on=K + ["date"], how="left")
print("   ex-date has an official open:", int(x.oo.notna().sum()))
# Labels that end on the ex-date (open-to-open) and labels that pass through it (end later).
e = lab[~lab.at_close].merge(x[K + ["date", "kind"]].rename(columns={"date": "end"}), on=K + ["end"])
e = e.merge(bars[K + ["date", "member"]].rename(columns={"member": "start_member"}), on=K + ["date"])
print("   open-to-open labels ending on an ex-date:", len(e), "| distinct events:",
      len(e.drop_duplicates(K + ["end"])), "| start day a member day:", int(e.start_member.sum()),
      "| ex-date bar a member day:", int(x.member.sum()))
ac = lab[lab.at_close].merge(x[K + ["date"]].rename(columns={"date": "end"}), on=K + ["end"])
print("   at_close labels ending on an ex-date:", len(ac))
print("   by kind:", e.kind.value_counts().to_dict())

# Size where the truth is known without a spin-off price.
# Cash kinds: D_open = D_close = D = (1 + ret_j) * close_{j-1} - close_j, so truth end piece = (oo_j + D) / close_{j-1}.
x["piece"] = (1 + x.ret) * x.oo / x.close
x["D"] = (1 + x.ret) * x.prev_close - x.close
cash = x[x.kind.isin(["special_dividend", "dividend"])].copy()
cash["err"] = 100 * (cash.piece - (cash.oo + cash.D) / cash.prev_close)
print("C cash kinds:", len(cash), "| |error| pp: max", round(abs(cash.err).max(), 3),
      "| over 1 pp:", int((abs(cash.err) > 1).sum()))
# Spin-offs and others whose evidence gives the opening value "The opening prints agree with the ratio: ... = V".
pat = re.compile(r"opening prints?[^:]*:\s*[^=]*=\s*(\d+(?:\.\d+)?)", re.I)
x["open_value"] = x.evidence.map(lambda t: float(m.group(1)) if (m := pat.search(t)) else np.nan)
w = x[x.open_value.notna() & ~x.kind.isin(["special_dividend", "dividend"])].copy()
w["err"] = 100 * (w.piece - w.open_value / w.prev_close)
print("O rows whose evidence gives an opening total value:", len(w))
for r in w.sort_values("date").itertuples():
    print(f"   {r.symbol} {r.date.date()} {r.kind}: end piece minus open-based = {r.err:+.2f} pp")
# Share of the distribution in the ex-date return, as the judge measured it.
d = (1 + x.ret) - x.close / x.prev_close
print("D distribution share d: <2%", int((d < .02).sum()), "2-10%", int(((d >= .02) & (d < .1)).sum()),
      "10-30%", int(((d >= .1) & (d < .3)).sum()), ">=30%", int((d >= .3).sum()), "nan", int(d.isna().sum()))
# How far the ex-date's intraday move (close/open) runs: an upper-bound driver of the error for spin-offs.
print("I |close_j/open_j - 1| on the ex-dates: median", round(100 * abs(x.close / x.oo - 1).median(), 2),
      "pp, max", round(100 * abs(x.close / x.oo - 1).max(), 2), "pp")
print("L per-row (kind, d share, intraday move, error in pp), cash kinds:")
for r in cash.sort_values("date").itertuples():
    print(f"   {r.symbol} {r.date.date()} {r.kind}: d {100 * r.D / r.prev_close:.1f}% "
          f"close/open-1 {100 * (r.close / r.oo - 1):+.2f} pp err {r.err:+.2f} pp member {r.member}")
