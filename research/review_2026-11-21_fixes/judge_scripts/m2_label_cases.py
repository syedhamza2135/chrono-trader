"""Judge check for M-2 (a): the new last piece of data_pipeline.store.labels against open-to-open truth, on made-up
frames. Cases: a label that crosses a day with no official open and a cash dividend before it ends on a spin-off
ex-date; j = i + 1; a label that starts on the ex-date; an at_close label that ends on an ex-date; a day without a
return; the csv read as main() reads it (blank open_return is NaN). Changes no file.
Usage: python research/review_2026-11-21_fixes/judge_scripts/m2_label_cases.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data_pipeline import store  # noqa: E402

D = pd.to_datetime(["2024-03-11", "2024-03-12", "2024-03-13", "2024-03-14", "2024-03-15"]).astype("datetime64[ns]")
c = [10.0, 11.0, 12.0, 7.0, 7.5]          # closes; day 3 is a spin-off ex-date
o = [9.8, 10.8, np.nan, 6.6, 7.2]          # official opens; day 2 has none
div2, spin_open, spin_close = 0.3, 4.4, 5.1  # a cash dividend on day 2; one spin-off share per share on day 3
ret = [np.nan, c[1] / c[0] - 1, (c[2] + div2) / c[1] - 1, (c[3] + spin_close) / c[2] - 1, c[4] / c[3] - 1]


def build(ret, open_return, volume=(100,) * 5):
    s = pd.DataFrame({"entity_id": "E1", "share_class": "", "symbol": "ABC", "date": D, "member": True,
                      "close": c, "volume": list(volume), "ret": ret})
    ev = pd.DataFrame([{"symbol": "ABC", "date": "2024-03-14", "kind": "spin_off", "status": "wrong",
                        "action": "total_return", "total_return": f"{ret[3]}", "open_return": open_return}])
    path = Path(__file__).with_name("_m2_events_tmp.csv")
    ev.to_csv(path, index=False)
    ev = pd.read_csv(path, dtype=str)  # as store.main reads it: a blank open_return becomes NaN
    path.unlink()
    s, _ = store.apply_events(s, ev)
    op = pd.DataFrame({"entity_id": "E1", "share_class": "", "date": D, "open": o,
                       "open_time": [d.tz_localize("America/New_York") + pd.Timedelta("9h30m") for d in D]})
    return s, op.dropna(subset=["open"])


open_ret = (o[3] + spin_open) / c[2] - 1  # as research/ex_date_opens.py computes it: over the store's previous close
s, op = build(ret, f"{open_ret}")
lab = store.labels(s, op, data_end=D[4]).set_index("date").label
truth_1_3 = (1 + div2 / c[2]) * (o[3] + spin_open) / o[1] - 1  # dividend reinvested at day 2's close
truth_0_1 = (o[1]) / o[0] - 1
truth_3_4 = o[4] / o[3] - 1
print("open_1 -> open_3 across a no-open day and a dividend:", abs(lab[D[1]] - truth_1_3) < 1e-12)
print("j = i + 1 (day 0 -> day 1, no event):", abs(lab[D[0]] - truth_0_1) < 1e-12)
print("label that starts on the ex-date:", abs(lab[D[3]] - truth_3_4) < 1e-12)

s, op = build(ret, "")  # blank: the old close-based end piece, which uses the ex-date's closes
lab_blank = store.labels(s, op, data_end=D[4]).set_index("date").label
print("blank open_return keeps the old piece (differs from truth):", abs(lab_blank[D[1]] - truth_1_3) > 1e-6)

# at_close: the company's last traded day is the ex-date and it has no official open there.
o_keep = list(o)
o[3] = o[4] = np.nan  # no open on the ex-date or after it
s, op = build(ret, f"{open_ret}", volume=(100, 100, 100, 100, 0))
lab_close = store.labels(s, op, data_end=D[4])
row = lab_close[lab_close.date == D[1]].iloc[0]
truth_close = (1 + div2 / c[2]) * (c[3] + spin_close) / o[1] - 1
print("at_close label ending on an ex-date uses the closes:", bool(row.at_close), abs(row.label - truth_close) < 1e-12)
o[:] = o_keep

# A day without a return between: no label crosses it.
r2 = list(ret)
r2[2] = np.nan
s, op = build(r2, f"{open_ret}")
lab_nan = store.labels(s, op, data_end=D[4])
print("no label crosses a day without a return:", D[1] not in set(lab_nan.date))
