"""M3 step 6, phase 1: the frozen trial plan's hash and its planned rows in the ledger.

The plan is the block of research/m3_kickoff.md from the line "<!-- M3 trial plan: start -->" to the line
"<!-- M3 trial plan: end -->", inclusive. Its SHA-256 is taken over those lines, each ending in LF, in UTF-8, so a
checkout with CRLF line endings gives the same hash.

Usage:
  python research/m3_trial_plan.py          prints the hash
  python research/m3_trial_plan.py --log    also adds one "planned" row per trial to runs/trials.csv (once)
  python research/m3_trial_plan.py --drop   adds a "dropped" row for each trial in DROPPED (once each)
No data is read: the settings are the agent's parameters and the plan's dates.
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.track_a import TrackA  # noqa: E402
from eval import trials  # noqa: E402
from world.world import EMBEDDING_WINDOW_DAYS  # noqa: E402

NOTE = ROOT / "research" / "m3_kickoff.md"
START, END = "<!-- M3 trial plan: start -->", "<!-- M3 trial plan: end -->"
FIRST, LAST = "2016-01-04", "2019-12-31"
STAGE1 = {"T01": {}, "T02": {"coefficients": "averaged"}, "T03": {"half_life_days": 252}}
DROPPED = {"T04": {"ranking": "sector_neutral"}}  # the owner, 23 Nov: sectors stay eval-only
STAGE2 = {"T05": {"hold": 3}, "T06": {"hold": 5}, "T07": {"band": 15}, "T08": {"band": 15, "hold": 3},
          "T09": {"band": 15, "hold": 5}}


def block(text):
    lines = text.splitlines()
    i, j = lines.index(START), lines.index(END)
    return "".join(line + "\n" for line in lines[i:j + 1])


def plan_hash(path=NOTE):
    return hashlib.sha256(block(path.read_text(encoding="utf-8")).encode("utf-8")).hexdigest()


def planned_settings(h):
    """{trial: settings} for the ledger. Stage 2 names its change on top of stage 1's winner, not yet known."""
    base = {"agent": "TrackA", "agent_params": TrackA().params, "cost_bps": 5.0,
            "embedding_window_days": EMBEDDING_WINDOW_DAYS, "first": FIRST, "last": LAST, "plan_sha256": h}
    out = {t: {**base, "trial": t, "stage": 1, "variant": v} for t, v in STAGE1.items()}
    out.update({t: {**base, "trial": t, "stage": 1, "variant": v, "dropped": True} for t, v in DROPPED.items()})
    out.update({t: {**base, "trial": t, "stage": 2, "model": "stage 1 winner", "variant": v}
                for t, v in STAGE2.items()})
    return out


def main():
    h = plan_hash()
    print(f"plan SHA-256: {h}")
    if "--log" in sys.argv:
        if trials.count() > 0:
            print("the ledger already holds trials; nothing added")
            return
        for t, s in planned_settings(h).items():
            trials.record(s, FIRST, LAST, ["live"], "not yet run", trial=t, status="planned")
        print(f"planned rows added: {trials.count()} trials in runs/trials.csv")
    if "--drop" in sys.argv:
        latest = {r["trial"]: r["status"] for r in trials.rows() if r.get("trial")}
        for t in DROPPED:
            if latest.get(t) == "dropped":
                continue
            s = planned_settings(h)[t]
            trials.record(s, FIRST, LAST, ["live"], "dropped by the owner on 23 Nov", trial=t, status="dropped")
        print(f"trials now in runs/trials.csv: {trials.count()}")


if __name__ == "__main__":
    main()
