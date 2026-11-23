"""The trial ledger (PLAN 5.5, step 2): every dev run is logged with a hash of its settings in runs/trials.csv, so
the deflated Sharpe (PLAN 9.10) can count the trials.

runs/trials.csv (in git) holds one row per run. Its columns:
- run_id, and logged_at (New York time);
- commit, and dirty (uncommitted changes in the tree);
- settings_hash (sim.seal.settings_hash), first and last;
- agents (names, joined by spaces), and out_dir, where the run's decisions and equity went;
- trial: the trial's name, such as T01, or empty for a run that is not a trial, such as the comparison pass;
- status: "planned" for a trial fixed before it runs, "run" once it has run, "dropped" for a planned trial taken
  out before any run.
Rows are only ever added. The trial count is the number of distinct trial names whose latest row is not "dropped",
so a planned row and its run count once (the owner, 23 Nov: one row per variant). runs/settings/<settings_hash>.json
(in git) holds the settings themselves. Both hold names, dates and parameters only, never a price or a return. The outputs go to DATA_DIR/runs/<run_id>, on D:
and outside git, since they hold returns.
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sim import seal

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["run_id", "logged_at", "commit", "dirty", "settings_hash", "first", "last", "agents", "out_dir", "trial",
           "status"]


def record(settings, first, last, agents, out_dir, runs=ROOT / "runs", git=None, now=None, trial="",
           status="run"):
    """Append one row to runs/trials.csv and write the settings file. Returns the row."""
    if status not in ("planned", "run", "dropped"):
        raise ValueError("status is planned, run or dropped")
    git = git or seal.Git(ROOT)
    h = seal.settings_hash(settings)
    stamp = (now or datetime.now(ZoneInfo("America/New_York"))).strftime("%Y-%m-%dT%H:%M:%S")
    row = {"run_id": f"{stamp.replace(':', '').replace('-', '')}_{h[:8]}", "logged_at": stamp,
           "commit": git.head(), "dirty": git.dirty(), "settings_hash": h, "first": str(first),
           "last": str(last), "agents": " ".join(agents), "out_dir": str(out_dir), "trial": trial, "status": status}
    (runs / "settings").mkdir(parents=True, exist_ok=True)
    (runs / "settings" / f"{h}.json").write_text(json.dumps(settings, sort_keys=True, indent=1, default=str) + "\n",
                                                 encoding="utf-8")
    path = runs / "trials.csv"
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)
    return row


def rows(runs=ROOT / "runs"):
    path = runs / "trials.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def count(runs=ROOT / "runs"):
    """How many trials the ledger holds: distinct trial names whose latest row is planned or run."""
    latest = {r["trial"]: r["status"] for r in rows(runs) if r.get("trial")}
    return sum(1 for s in latest.values() if s != "dropped")
