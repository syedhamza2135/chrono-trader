"""Times one pass of every comparison agent through the warm-up and dev years (M3 step 4): sim.simulator.run_many
from 2016-01-04 to 2019-12-31 on the store, each view built once. The agents: Track A (live), the price-only twin,
5 shuffled-news placebos, 5 random rankings, 12-1 momentum, 5-day reversal and equal weight, plus the live agent's
frozen twins at each year end. Prints times, counts and memory only: no IC, return or other result, so it tunes
nothing and is not logged as a trial. It also checks that the live agent's decisions equal step 3's timing run
(DATA_DIR/runs/m3_step3_timing/decisions.parquet), so step 4's changes to the agent changed none of them. Outputs go to
DATA_DIR/runs/m3_step4_timing, outside git.
Usage: python research/m3_compare_timing.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
import pandas as pd  # noqa: E402
from world_memory import memory  # noqa: E402

from agent.baselines import EqualWeight, Momentum, RandomRanking, Reversal  # noqa: E402
from agent.placebo import Placebo  # noqa: E402
from agent.track_a import TrackA  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from sim import simulator  # noqa: E402
from world.world import World  # noqa: E402

SEEDS = (1, 2, 3, 4, 5)


def comparison_agents():
    agents = {"live": TrackA(), "price_only": TrackA(news=False)}
    agents.update({f"placebo_{s}": Placebo(TrackA(), s) for s in SEEDS})
    agents.update({f"random_{s}": RandomRanking(s) for s in SEEDS})
    agents.update({"momentum": Momentum(), "reversal": Reversal(), "equal_weight": EqualWeight()})
    return agents


def main():
    t0 = time.time()
    world = World.load()
    print(f"World.load: {time.time() - t0:.0f} s, {memory()}", flush=True)
    agents = comparison_agents()
    t1 = time.time()
    runs = simulator.run_many(world, agents, "2016-01-04", "2019-12-31", freeze=("live",))
    secs = time.time() - t1
    print(f"one pass, {len(runs)} agents ({len(agents)} plus {len(runs) - len(agents)} frozen twins), 2016-01-04 to "
          f"2019-12-31: {secs / 60:.1f} min, {memory()}", flush=True)
    for name, r in runs.items():
        print(f"  {name}: {r.decisions.date.nunique()} decision days, {len(r.decisions)} rows")
    old = pd.read_parquet(DATA_DIR / "runs" / "m3_step3_timing" / "decisions.parquet")
    same = old.reset_index(drop=True).equals(runs["live"].decisions.reset_index(drop=True))
    print(f"live decisions equal step 3's timing run: {same}")
    out = DATA_DIR / "runs" / "m3_step4_timing"
    out.mkdir(parents=True, exist_ok=True)
    for name, r in runs.items():
        r.decisions.to_parquet(out / f"{name}_decisions.parquet", index=False)
        r.equity.to_parquet(out / f"{name}_equity.parquet", index=False)
    print(f"outputs saved to {out}")


if __name__ == "__main__":
    main()
