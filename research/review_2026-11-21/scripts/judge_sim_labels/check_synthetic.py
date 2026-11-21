"""Judge check on made-up frames: data_pipeline.store.labels and sim.simulator.Simulator.

Run from the worktree root (PowerShell):
  $env:CHRONO_ENV_FILE = "C:\\Users\\syedh\\dev\\chrono-trader\\.env"
  D:\\venvs\\chrono-trader\\Scripts\\python.exe research\\review_2026-11-21\\scripts\\judge_sim_labels\\check_synthetic.py
All prices are invented. Check 5 is expected to FAIL: it shows the closes do not cancel on a distribution day.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from data_pipeline.store import labels  # noqa: E402
from sim.simulator import Simulator  # noqa: E402

D = pd.to_datetime(["2020-01-06", "2020-01-07", "2020-01-08", "2020-01-09", "2020-01-10", "2020-01-13"])
ok = True


def series(ent, close, ret, volume, oo):
    s = pd.DataFrame({"entity_id": ent, "share_class": "", "date": D[:len(close)], "close": close, "ret": ret,
                      "volume": volume})
    o = s[["entity_id", "share_class", "date"]].assign(open=oo)
    o["open_time"] = pd.to_datetime([d + pd.Timedelta(hours=14, minutes=30) for d in o.date], utc=True)
    return s, o


def check(name, cond):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


# 1. A 2-for-1 split on the end day: label = 2 * open_j / open_i - 1.
close = [100.0, 102.0, 51.5, 52.0]
ret = [np.nan, 0.02, 51.5 * 2 / 102 - 1, 52 / 51.5 - 1]
oo = [99.0, 101.0, 50.5, 51.0]
s, o = series("A", close, ret, [1, 1, 1, 1], oo)
lab = labels(s, o, D[-1])
check("1 split on end day: label is the split-adjusted open to open",
      abs(lab[lab.date == D[1]].label.iat[0] - (50.5 * 2 / 101 - 1)) < 1e-12)

# 2. A missing official open in the middle: the label spans to the next one.
s, o = series("A", close, ret, [1, 1, 1, 1], [99.0, np.nan, 50.5, 51.0])
r = labels(s, o, D[-1]).query("date == @D[0]")
check("2 missing open: label from day 0 ends on day 2", r.end.iat[0] == D[2] and
      abs(r.label.iat[0] - (50.5 * 2 / 99 - 1)) < 1e-12)

# 3. Undefined return between two opens: no label.
s, o = series("A", close, [np.nan, 0.02, np.nan, 0.01], [1, 1, 1, 1], oo)
check("3 undefined return: no label from day 1", (labels(s, o, D[-1]).date == D[1]).sum() == 0)

# 4. Stopped trading before the data end: the last label ends at the last traded close; -1 if failed.
s, o = series("B", [10.0, 11.0, 12.0], [np.nan, 0.1, 12 / 11 - 1], [1, 1, 1], [10.5, 11.5, np.nan])
r = labels(s, o, D[-1]).query("date == @D[1]")
check("4a acquired: last label at_close, ends at the last close", r.at_close.iat[0] and r.end.iat[0] == D[2] and
      abs(r.label.iat[0] - (12 / 11.5 - 1)) < 1e-12)
lab_f = labels(s, o, D[-1], failed={("B", "")})
check("4b failed: exit label is -1", lab_f[lab_f.at_close].label.iat[0] == -1.0)

# 5. A distribution on the end day (made up: 0.5 spinco share per share). The vendor-style ex-date total return is
#    (close_j + 0.5 * spin_close) / close_{j-1}. The open-to-open truth is (open_j + 0.5 * spin_open) / close_{j-1}.
c_prev, o_j, c_j, spin_open, spin_close = 40.0, 21.0, 20.0, 38.0, 40.0
s, o = series("C", [c_prev, c_j], [np.nan, (c_j + 0.5 * spin_close) / c_prev - 1], [1, 1], [40.0, o_j])
got = labels(s, o, D[-1]).label.iat[0]
truth = (o_j + 0.5 * spin_open) / c_prev - 1
print(f"  5 distribution on end day: label minus open-to-open truth = {100 * (got - truth):+.2f} percentage points")
c_j2 = c_j * 1.05
s2, o2 = series("C", [c_prev, c_j2], [np.nan, (c_j2 + 0.5 * spin_close) / c_prev - 1], [1, 1], [40.0, o_j])
got2 = labels(s2, o2, D[-1]).label.iat[0]
check("5 distribution on end day: the end day's close cancels (expected to FAIL)", abs(got2 - got) < 1e-12)


# ---- Simulator ----
def world(lab, opens):
    return SimpleNamespace(opens=opens, labels=SimpleNamespace(df=lab))


def tgt(*rows):
    return pd.DataFrame(rows, columns=["entity_id", "share_class", "position"])


# 6. One long at weight 1 for four sessions: equity matches a hand book of label growth and 5 bps per side.
opens = pd.DataFrame({"entity_id": "A", "share_class": "", "date": D[:5], "open": 1.0})
lab = pd.DataFrame({"entity_id": "A", "share_class": "", "date": D[:4], "end": D[1:5],
                    "label": [0.01, -0.02, 0.03, 0.0], "at_close": False})
sim = Simulator(world(lab, opens))
for d in D[:4]:
    sim.step(d, tgt(("A", "", 1.0)))
cash, val, exp = 1.0, 0.0, []
for k in range(4):
    if k:
        val *= 1 + lab.label.iat[k - 1]
    e = cash + val
    ch = e - val
    cash -= ch + abs(ch) * 5e-4
    val = e
    exp.append(cash + val)
check("6 long, weight 1: equity matches a hand book", np.allclose([r["equity"] for r in sim.rows], exp, atol=1e-15))

# 7. A failed company: a long loses all of it, a short gains all of it, booked on the session after the last close.
opens = pd.DataFrame({"entity_id": ["F", "G"] * 2, "share_class": "", "date": [D[0], D[0], D[1], D[1]], "open": 1.0})
lab = pd.DataFrame({"entity_id": ["F", "G", "F", "G"], "share_class": "", "date": [D[0], D[0], D[1], D[1]],
                    "end": [D[1], D[1], D[1], D[2]], "label": [0.0, 0.0, -1.0, 0.0],
                    "at_close": [False, False, True, False]})
for w, want in ((0.5, 0.5), (-0.5, 1.5)):
    sim = Simulator(world(lab, opens), cost_bps=0)
    sim.step(D[0], tgt(("F", "", w), ("G", "", 0.5)))
    sim.step(D[1], tgt(("F", "", w), ("G", "", 0.5)))
    e1 = sim.rows[-1]["equity"]
    sim.step(D[2], tgt(("G", "", 0.5)))
    check(f"7 failed exit, weight {w}: not booked on the end day, booked the next session",
          abs(e1 - 1.0) < 1e-12 and abs(sim.rows[-1]["equity"] - want) < 1e-12 and ("F", "") not in sim.values)

# 8. No official open today: the holding is not traded and keeps its value until its next open.
opens = pd.DataFrame({"entity_id": "A", "share_class": "", "date": [D[0], D[2]], "open": 1.0})
lab = pd.DataFrame({"entity_id": "A", "share_class": "", "date": [D[0], D[2]], "end": [D[2], D[3]],
                    "label": [0.10, 0.0], "at_close": False})
sim = Simulator(world(lab, opens), cost_bps=0)
sim.step(D[0], tgt(("A", "", 1.0)))
sim.step(D[1], tgt(("A", "", 0.0)))
held = sim.values.get(("A", ""))
sim.step(D[2], tgt(("A", "", 0.0)))
check("8 no open: kept on day 1 despite a zero target, marked and sold on day 2",
      held == 1.0 and abs(sim.rows[-1]["equity"] - 1.10) < 1e-12 and not sim.values)

# 9. An open with no label from it (not the data's last day): the holding is sold at today's open.
#    Whether a label exists depends on later data (the next open, the returns up to it).
opens = pd.DataFrame({"entity_id": "A", "share_class": "", "date": D[:3], "open": 1.0})
lab = pd.DataFrame({"entity_id": ["A", "Z"], "share_class": "", "date": [D[0], D[0]], "end": [D[1], D[3]],
                    "label": [0.0, 0.0], "at_close": False})
sim = Simulator(world(lab, opens), cost_bps=0)
sim.step(D[0], tgt(("A", "", 1.0)))
sim.step(D[1], tgt(("A", "", 1.0)))
check("9 no label from today's open: forced sale", sim.forced_sales == 1 and not sim.values)

# 10. An at_close exit: the sale's cost is charged but its value is not counted in `traded`.
opens = pd.DataFrame({"entity_id": ["B", "B"], "share_class": "", "date": [D[0], D[1]], "open": 1.0})
lab = pd.DataFrame({"entity_id": ["B", "B", "Z"], "share_class": "", "date": [D[0], D[1], D[0]],
                    "end": [D[1], D[1], D[4]], "label": [0.0, 0.0, 0.0], "at_close": [False, True, False]})
sim = Simulator(world(lab, opens))
sim.step(D[0], tgt(("B", "", 1.0)))
sim.step(D[1], tgt(("B", "", 1.0)))
sim.step(D[2], None)
r = sim.rows[-1]
print(f"  10 at_close exit day: cost {r['cost']:.6f}, traded {r['traded']:.6f}")
check("10 at_close exit: traded value includes the exit sale (expected to FAIL)", r["traded"] > 0)

print("ALL PASS" if ok else "SOME CHECKS FAILED (checks 5 and 10 are expected to fail)")
