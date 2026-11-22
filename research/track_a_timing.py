"""Times one full run of Track A's agent through the warm-up and dev years (M3 step 3): sim.simulator.run from
2016-01-04 to 2019-12-31 on the store, with the embeddings and the default 90-day window. Prints times, counts and
the process's memory only: no IC, return or other result, so this run tunes nothing. The decisions are saved on D:
(DATA_DIR/runs/m3_step3_timing), outside git.
Usage: python research/track_a_timing.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
from world_memory import memory  # noqa: E402

from agent.track_a import TrackA  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from sim import simulator  # noqa: E402
from world.world import World  # noqa: E402


def main():
    t0 = time.time()
    world = World.load()
    print(f"World.load: {time.time() - t0:.0f} s, {memory()}", flush=True)
    agent = TrackA()
    t1 = time.time()
    run = simulator.run(world, agent, "2016-01-04", "2019-12-31")
    secs = time.time() - t1
    days = run.decisions.date.nunique()
    print(f"run 2016-01-04 to 2019-12-31: {secs / 60:.1f} min, {days} decision days, {len(run.decisions)} rows, "
          f"{len(agent.fits)} refits, {memory()}", flush=True)
    for f in agent.fits[:2] + agent.fits[-1:]:
        print(f"refit at {f['t']}: {f['rows']} rows, latest label {f['latest_label']}, val days {f['val_days']}")
    out = DATA_DIR / "runs" / "m3_step3_timing"
    out.mkdir(parents=True, exist_ok=True)
    run.decisions.to_parquet(out / "decisions.parquet", index=False)
    print(f"decisions saved to {out}")


if __name__ == "__main__":
    main()
