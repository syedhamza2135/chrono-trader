"""The trial ledger (PLAN 5.5, step 2): every dev run is logged with a hash of its settings in runs/trials.csv, so
the deflated Sharpe (PLAN 9.10) can count the trials.

runs/trials.csv (in git) holds one row per run: run_id, logged_at (New York), commit, dirty (uncommitted changes in
the tree), settings_hash (sim.seal.settings_hash), first, last, agents (names, joined by spaces) and out_dir, where
the run's decisions and equity went. runs/settings/<settings_hash>.json (in git) holds the settings themselves. Both
hold names, dates and parameters only, never a price or a return. The outputs go to DATA_DIR/runs/<run_id>, on D:
and outside git, since they hold returns.
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sim import seal

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["run_id", "logged_at", "commit", "dirty", "settings_hash", "first", "last", "agents", "out_dir"]


def record(settings, first, last, agents, out_dir, runs=ROOT / "runs", git=None, now=None):
    """Append one row to runs/trials.csv and write the settings file. Returns the row."""
    git = git or seal.Git(ROOT)
    h = seal.settings_hash(settings)
    stamp = (now or datetime.now(ZoneInfo("America/New_York"))).strftime("%Y-%m-%dT%H:%M:%S")
    row = {"run_id": f"{stamp.replace(':', '').replace('-', '')}_{h[:8]}", "logged_at": stamp,
           "commit": git.head(), "dirty": git.dirty(), "settings_hash": h, "first": str(first),
           "last": str(last), "agents": " ".join(agents), "out_dir": str(out_dir)}
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


def count(runs=ROOT / "runs"):
    """How many trials the ledger holds."""
    path = runs / "trials.csv"
    if not path.exists():
        return 0
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))
