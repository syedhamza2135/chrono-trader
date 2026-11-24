"""M4: the sealed run (research/m4_kickoff.md; PLAN 5.5 items 3 to 5 and 9.12). Built in M4 step 1. Nothing here has
run in the sealed years.

One step per call, one job at a time, each holding the PC awake in its own process (reader.embed.stay_awake):
  python research/m4_sealed_run.py settings           prints each part's settings hash (reads no data)
  python research/m4_sealed_run.py dev-check          M4 step 2: the main part's agents to 2019-12-31 at this commit,
                                                      no seal needed, and live's decisions against the dev run's
  python research/m4_sealed_run.py seal               writes seal.lock for HEAD (needs PREREG.md and a clean tree;
                                                      commit the lock alone straight after)
  python research/m4_sealed_run.py run main [--again]
  python research/m4_sealed_run.py run older_vintage [--again]
  python research/m4_sealed_run.py replay             after both parts: every book at 0, 5, 10 and 20 bps
  python research/m4_sealed_run.py ledger             after the last sealed part: copies the sealed ledger rows into
                                                      runs/trials.csv and runs/settings/, for one commit
The two parts are those of sim/seal.py. "main" runs the chosen configuration (stage2.json), its twins, the price-only
twin, the 5 placebo seeds and the baselines, as M3's comparison pass did (research/m3_dev_runs.py), from 2016-01-04 to
the sealed end in reference/split.json. "older_vintage" runs the live agent alone on the older table
(DATA_DIR/reader_older) through a World with vintage_offset 1 (M4 decision 2; its price-only twin is main's, which
reads no news). Each sealed run is refused unless seal.lock matches, and runs once per part: --again allows a second,
which is logged as another trial (PLAN 9.12). Outputs go to DATA_DIR/runs/m4_sealed, outside git. While the sealed
parts run, their ledger rows go to DATA_DIR/sealed/ledger, outside git too: a row in the repo would dirty the tree and
the seal would refuse the next part (M4 judge J4-1). `ledger` copies them into the repo's ledger at the end.

The settings each part is sealed on hold the chosen configuration, the frozen M3 plan's hash, the dates and a
fingerprint of the data: each store table's size and Parquet footer hash, and the embeddings' arrays record. So the
seal also covers which data the run reads. Nothing here reads a sealed outcome: the report is M4 step 6.
"""
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import m3_dev_runs as dev  # noqa: E402
import m3_trial_plan as plan  # noqa: E402
from agent.track_a import TrackA  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from eval import trials  # noqa: E402
from sim import seal, simulator  # noqa: E402
from world.world import EMBEDDING_WINDOW_DAYS, _parquet_footer  # noqa: E402

OUT = DATA_DIR / "runs" / "m4_sealed"
STORE = DATA_DIR / "store"
OLDER = DATA_DIR / "reader_older"
FIRST = plan.FIRST  # 2016-01-04: the agent lives through the warm-up and the dev years first, as on dev
LEDGER = DATA_DIR / "sealed" / "ledger"  # runs/trials.csv and runs/settings/ for the sealed parts, outside git
TABLES = ("bars", "labels", "opens", "stories", "story_entities", "membership")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sealed_end(root=None):
    return seal._split(root)["end"]


def chosen():
    s2 = json.loads((dev.OUT / "stage2.json").read_text(encoding="utf-8"))
    return s2["winner"], s2["chosen_kw"]


def fingerprint(embeddings_store):
    """The data a part reads, by size and footer hash: no row is read."""
    meta = json.loads((Path(embeddings_store) / "embeddings.json").read_text(encoding="utf-8"))
    return {"tables": {t: _parquet_footer(STORE / f"{t}.parquet") for t in TABLES},
            "embeddings": {"store": Path(embeddings_store).name, "arrays": meta.get("arrays")}}


def agents_of(part, kw):
    if part == "main":
        return dev.comparison_agents(kw), ("live",)
    if part == "older_vintage":
        return {"live_older_vintage": TrackA(**kw)}, ()
    raise SystemExit(f"the parts are {seal.PARTS}")


def caller_settings(part, last=None, data=None):
    """What the runner passes as `settings`; sim.simulator.settings_many adds the costs, the window, the agents and
    the offset. `last` is the sealed end unless given (the dev check)."""
    winner, kw = chosen()
    s = {"m4": "sealed run", "chosen": winner, "chosen_kw": kw, "plan_sha256": plan.plan_hash(), "first": FIRST,
         "last": last or sealed_end(), "data": data if data is not None else
         fingerprint(OLDER if part == "older_vintage" else STORE)}
    if last is None:
        s["sealed_part"] = part
    return s


def full_settings(part):
    """The whole settings a part is sealed on, as run_many will compute them from the real World. A World that
    differs (another window, another offset) changes the hash, and the seal refuses the run."""
    _, kw = chosen()
    agents, freeze = agents_of(part, kw)
    like = SimpleNamespace(embedding_window_days=EMBEDDING_WINDOW_DAYS,
                           vintage_offset=1 if part == "older_vintage" else 0)
    return simulator.settings_many(like, agents, dev.COST, caller_settings(part), freeze)


def settings_step():
    for part in seal.PARTS:
        log(f"{part}: settings hash {seal.settings_hash(full_settings(part))}")


def seal_step():
    lock = seal.write({part: full_settings(part) for part in seal.PARTS})
    log(f"wrote seal.lock for commit {lock['commit']}: commit it alone now, and nothing else after it")


def world_of(part):
    from world.world import World
    if part == "older_vintage":
        return World.load(embeddings_store=OLDER, vintage_offset=1)
    return World.load()


def run_step(part, again=False):
    winner, kw = chosen()
    agents, freeze = agents_of(part, kw)
    world = world_of(part)
    s = caller_settings(part)
    last = s["last"]
    t0 = time.time()
    runs = simulator.run_many(world, agents, FIRST, last, cost_bps=dev.COST, settings=s, freeze=freeze, again=again)
    d = OUT / part
    for n, r in runs.items():
        dev.save(r, d / n)
    n = sum(1 for e in seal.started() if e["part"] == part)
    trials.record(simulator.settings_many(world, agents, dev.COST, s, freeze), FIRST, last, list(runs), d,
                  runs=LEDGER, trial=f"sealed_{part}_{n}" if again else "", status="run")
    log(f"sealed {part} run of {winner} {kw}: {len(runs)} agents, {(time.time() - t0) / 60:.1f} min")


def replay_step():
    """PREREG section 2: after both parts, each book of each part traded again at 0, 5, 10 and 20 bps
    (sim.simulator.replay, which needs the seal and a logged start with the part's settings). Before the writer and
    `ledger`, so the tree is still clean."""
    winner, kw = chosen()
    for part in seal.PARTS:
        d = OUT / part
        if not d.exists():
            log(f"{part}: no runs to replay")
            continue
        agents, freeze = agents_of(part, kw)
        world = world_of(part)
        full = simulator.settings_many(world, agents, dev.COST, caller_settings(part), freeze)
        base = simulator.Simulator(world, 0.0)
        for p in sorted(d.iterdir()):
            if (p / "decisions.parquet").exists():
                for c, eq in simulator.replay(world, dev.load(p), costs=(0.0, 5.0, 10.0, 20.0), base=base,
                                              settings=full).items():
                    eq.to_parquet(p / f"equity_{c:g}bps.parquet", index=False)
                log(f"replayed {part}/{p.name}")


def ledger_step(ledger=LEDGER, repo_runs=ROOT / "runs"):
    """Copy the sealed ledger's rows and settings files into the repo's runs/trials.csv and runs/settings/, once every
    sealed part has run. Rows already there (same run_id) are skipped. Commit the result: it is the only change after
    the seal's commit, and it lands after the sealed runs, so it can't break their seal."""
    import csv
    import shutil
    new = trials.rows(ledger)
    have = {r["run_id"] for r in trials.rows(repo_runs)}
    add = [r for r in new if r["run_id"] not in have]
    (repo_runs / "settings").mkdir(parents=True, exist_ok=True)
    for r in add:
        shutil.copyfile(ledger / "settings" / f"{r['settings_hash']}.json",
                        repo_runs / "settings" / f"{r['settings_hash']}.json")
    path = repo_runs / "trials.csv"
    fresh = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=trials.COLUMNS)
        if fresh:
            w.writeheader()
        w.writerows(add)
    log(f"copied {len(add)} sealed ledger rows into {path}")
    return add


def dev_check():
    """M4 step 2: the main part's agents to 2019-12-31 at this commit (no seal: no sealed date), and live's
    decisions against the dev comparison pass's (research/m3_dev_runs.py compare)."""
    winner, kw = chosen()
    agents, freeze = agents_of("main", kw)
    from world.world import World
    world = World.load()
    t0 = time.time()
    runs = simulator.run_many(world, agents, FIRST, plan.LAST, cost_bps=dev.COST,
                              settings=caller_settings("main", last=plan.LAST, data={}), freeze=freeze)
    d = OUT / "dev_check"
    same = {}
    for n, r in runs.items():
        dev.save(r, d / n)
        old = dev.OUT / "compare" / n
        if (old / "decisions.parquet").exists():
            same[n] = dev.load(old).decisions.reset_index(drop=True).equals(r.decisions.reset_index(drop=True))
    (OUT / "dev_check.json").write_text(json.dumps({"same_decisions": same}, indent=1), encoding="utf-8")
    log(f"dev check: {(time.time() - t0) / 60:.1f} min; decisions equal the dev pass's: {same}")


if __name__ == "__main__":
    args = sys.argv[1:]
    step = args[0] if args else ""
    if step not in ("settings", "dev-check", "seal", "run", "replay", "ledger"):
        print(__doc__)
        raise SystemExit(1)
    from reader.embed import stay_awake
    stay_awake()
    OUT.mkdir(parents=True, exist_ok=True)
    if step == "settings":
        settings_step()
    elif step == "dev-check":
        dev_check()
    elif step == "seal":
        seal_step()
    elif step == "replay":
        replay_step()
    elif step == "ledger":
        ledger_step()
    else:
        if len(args) < 2 or args[1] not in seal.PARTS:
            raise SystemExit(f"run takes a part: {seal.PARTS}")
        run_step(args[1], again="--again" in args[2:])
