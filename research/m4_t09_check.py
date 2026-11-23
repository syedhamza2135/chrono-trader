"""M4 step 2: T09 rerun on the dev years at the current commit, through the dev path, against step 6's T09 run.

  python research/m4_t09_check.py

It runs exactly what research/m3_dev_runs.py's run_trial ran for T09 (the same agent, dates, costs and caller
settings), stops on 2019-12-31, and compares the decisions with D:/chrono-data/runs/m3_dev/T09 day by day: the same
decision days, and on each day the same rows, predictions and positions. It also compares the equity rows. The run
is a ledger row with no trial name, so the trial count stays 8. Outputs go to DATA_DIR/runs/m4_dev/T09_check.
Nothing from 2020 on is read.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
import pandas as pd  # noqa: E402

import m3_dev_runs as dev  # noqa: E402
from agent.track_a import TrackA  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from eval import trials  # noqa: E402
from sim import seal, simulator  # noqa: E402
from world.world import World  # noqa: E402

OUT = DATA_DIR / "runs" / "m4_dev" / "T09_check"


def compare(old, new):
    """Day-by-day comparison of two decision tables, and of the equity rows."""
    a, b = old.decisions, new.decisions
    days_a, days_b = set(pd.to_datetime(a.date)), set(pd.to_datetime(b.date))
    ga = {d: g.drop(columns="date").reset_index(drop=True) for d, g in a.groupby(pd.to_datetime(a.date))}
    gb = {d: g.drop(columns="date").reset_index(drop=True) for d, g in b.groupby(pd.to_datetime(b.date))}
    differ = [str(d.date()) for d in sorted(days_a & days_b) if not ga[d].equals(gb[d])]
    return {"decision_days_old": len(days_a), "decision_days_new": len(days_b),
            "days_only_old": sorted(str(d.date()) for d in days_a - days_b),
            "days_only_new": sorted(str(d.date()) for d in days_b - days_a),
            "days_that_differ": differ,
            "decisions_equal": a.reset_index(drop=True).equals(b.reset_index(drop=True)),
            "equity_equal": old.equity.reset_index(drop=True).equals(new.equity.reset_index(drop=True)),
            "stats_old": old.stats, "stats_new": new.stats}


def main():
    s2 = json.loads((dev.OUT / "stage2.json").read_text(encoding="utf-8"))
    trial, kw = s2["winner"], s2["chosen_kw"]
    world = World.load()
    agent = TrackA(**kw)
    s = dev.settings_of(trial, 2, kw, agent)
    t0 = time.time()
    r = simulator.run(world, agent, dev.FIRST, dev.LAST, cost_bps=dev.COST,
                      settings={"trial": trial, "plan_sha256": s["plan_sha256"]})
    dev.save(r, OUT)
    out = {"trial": trial, "chosen_kw": kw, "commit": seal.Git().head(), "minutes": (time.time() - t0) / 60,
           **compare(dev.load(dev.OUT / trial), r)}
    (OUT / "compare.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    trials.record({**s, "check": "m4 step 2, T09 rerun at the M4 commit"}, dev.FIRST, dev.LAST, ["live"], OUT,
                  trial="", status="run")
    print(json.dumps(out, default=str), flush=True)


if __name__ == "__main__":
    from reader.embed import stay_awake
    stay_awake()
    main()
