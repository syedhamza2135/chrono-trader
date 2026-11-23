"""M3 step 6, phase 2: the dev runs under the frozen trial plan (research/m3_kickoff.md, "The M3 trial plan").

One step per call, one job at a time, each holding the PC awake in its own process (reader.embed.stay_awake):
  python research/m3_dev_runs.py stage1    runs T01 to T03 with sim.simulator.run and applies stage 1's rule
  python research/m3_dev_runs.py stage2    runs T05 to T09 on stage 1's winner and applies stage 2's rule
  python research/m3_dev_runs.py compare   the comparison pass, the cost replays and the check of the live agent
  python research/m3_dev_runs.py report    writes research/m3_dev_report.md (charts to D:)
Every run is a row of runs/trials.csv. Outputs go to DATA_DIR/runs/m3_dev, outside git. Only the dev years are
measured: a day's IC counts only if its label ends by 2019-12-31, and book returns end on 2019-12-31. The runs
stop at 2019-12-31, so no view reaches 2020.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import m3_trial_plan as plan  # noqa: E402
from agent.baselines import EqualWeight, Momentum, RandomRanking, Reversal  # noqa: E402
from agent.placebo import Placebo  # noqa: E402
from agent.track_a import TrackA  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from eval import benchmarks, metrics, report, stats, trials  # noqa: E402
from reader.embed import stay_awake  # noqa: E402
from sim import simulator  # noqa: E402
from sim.simulator import Run  # noqa: E402
from world.world import World  # noqa: E402

OUT = DATA_DIR / "runs" / "m3_dev"
FIRST, LAST = plan.FIRST, plan.LAST
DEV_FIRST, IC_LAST = "2017-01-03", "2019-12-30"  # IC days whose labels end by 2019-12-31; books to LAST
COST = 5.0
SEEDS = (1, 2, 3, 4, 5)
IC_TIE, SHARPE_TIE = 0.001, 0.05
STAGE1 = {"T01": {}, "T02": {"coefficients": "averaged"}, "T03": {"half_life_days": 252}}
STAGE2 = plan.STAGE2


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def dev_labels(world):
    """The labels that end by 2019-12-31, so 2019-12-30 is the last IC day (IC_LAST)."""
    lab = world.labels.df
    return lab[pd.to_datetime(lab.end) <= pd.Timestamp(LAST)]


def save(run, d):
    d.mkdir(parents=True, exist_ok=True)
    run.decisions.to_parquet(d / "decisions.parquet", index=False)
    run.equity.to_parquet(d / "equity.parquet", index=False)
    (d / "stats.json").write_text(json.dumps(run.stats), encoding="utf-8")


def load(d):
    return Run(pd.read_parquet(d / "decisions.parquet"), pd.read_parquet(d / "equity.parquet"),
               json.loads((d / "stats.json").read_text(encoding="utf-8")))


def settings_of(trial, stage, kw, agent):
    return {"trial": trial, "stage": stage, "variant": kw, "plan_sha256": plan.plan_hash(), "agent": "TrackA",
            "agent_params": agent.params, "cost_bps": COST,
            "embedding_window_days": 90, "first": FIRST, "last": LAST}


def run_trial(world, trial, stage, kw):
    agent = TrackA(**kw)
    s = settings_of(trial, stage, kw, agent)
    t0 = time.time()
    r = simulator.run(world, agent, FIRST, LAST, cost_bps=COST, settings={"trial": trial, "plan_sha256":
                                                                          s["plan_sha256"]})
    d = OUT / trial
    save(r, d)
    trials.record(s, FIRST, LAST, ["live"], d, trial=trial, status="run")
    log(f"{trial} {kw}: {(time.time() - t0) / 60:.1f} min, {r.decisions.date.nunique()} decision days, "
        f"forced sales {r.stats['forced_sales']}, unmarked {r.stats['unmarked']}, fits {len(agent.fits)}")
    return r


def measures(r, labels):
    ic = metrics.within(metrics.daily_rank_ic(r.decisions, labels), DEV_FIRST, IC_LAST)
    m = stats.nw_mean(ic.to_numpy())
    ret = metrics.book_returns(r.equity, DEV_FIRST, LAST)
    st = stats.book_stats(ret.to_numpy())
    early = r.decisions[pd.to_datetime(r.decisions.date) < pd.Timestamp(DEV_FIRST)]
    return {"ic_days": m["n"], "mean_ic": m["mean"], "ic_t": m["t"], "sharpe_after_costs": st["sharpe"],
            "max_drawdown": st["max_drawdown"], "daily_turnover": metrics.turnover(r.equity, DEV_FIRST, LAST),
            "positions_before_2017": float(early.position.abs().sum())}


def stage1():
    world = World.load()
    labels = dev_labels(world)
    res = {}
    for t, kw in STAGE1.items():
        res[t] = measures(run_trial(world, t, 1, kw), labels)
        log(f"{t}: {res[t]}")
    order = list(STAGE1)
    best = max(res[t]["mean_ic"] for t in order)
    winner = next(t for t in order if res[t]["mean_ic"] >= best - IC_TIE)  # within the tie, the earlier wins
    out = {"measures": res, "winner": winner, "winner_kw": STAGE1[winner], "rule": "highest mean daily rank IC; "
           f"within {IC_TIE}, the earlier trial"}
    (OUT / "stage1.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    log(f"stage 1 winner: {winner}")


def stage2():
    s1 = json.loads((OUT / "stage1.json").read_text(encoding="utf-8"))
    world = World.load()
    labels = dev_labels(world)
    res = {s1["winner"]: measures(load(OUT / s1["winner"]), labels)}
    for t, kw in STAGE2.items():
        res[t] = measures(run_trial(world, t, 2, {**s1["winner_kw"], **kw}), labels)
        log(f"{t}: {res[t]}")
    order = [s1["winner"], *STAGE2]
    best = max(res[t]["sharpe_after_costs"] for t in order)
    close = [t for t in order if res[t]["sharpe_after_costs"] >= best - SHARPE_TIE]
    winner = min(close, key=lambda t: (res[t]["daily_turnover"], order.index(t)))
    kw = {**s1["winner_kw"], **STAGE2.get(winner, {})}
    out = {"measures": res, "winner": winner, "chosen_kw": kw, "rule": "highest long-short Sharpe after 5 bps; "
           f"within {SHARPE_TIE}, the lower daily turnover"}
    (OUT / "stage2.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    log(f"stage 2 winner (the chosen configuration): {winner} {kw}")


def comparison_agents(kw):
    hold = kw.get("hold", 1)
    a = {"live": TrackA(**kw), "live_long_only": TrackA(**{**kw, "book": "long_only"}),
         "price_only": TrackA(**{**kw, "news": False})}
    a.update({f"placebo_{s}": Placebo(TrackA(**kw), s) for s in SEEDS})
    a.update({f"random_{s}": RandomRanking(s, hold=hold) for s in SEEDS})
    a.update({"momentum": Momentum(hold=hold), "reversal": Reversal(hold=hold), "equal_weight": EqualWeight()})
    return a


def compare():
    s2 = json.loads((OUT / "stage2.json").read_text(encoding="utf-8"))
    kw = s2["chosen_kw"]
    world = World.load()
    agents = comparison_agents(kw)
    t0 = time.time()
    runs = simulator.run_many(world, agents, FIRST, LAST, cost_bps=COST, freeze=("live",))
    log(f"comparison pass: {len(runs)} agents, {(time.time() - t0) / 60:.1f} min")
    d = OUT / "compare"
    for n, r in runs.items():
        save(r, d / n)
    trials.record({"comparison_of": s2["winner"], "chosen_kw": kw, "plan_sha256": plan.plan_hash(),
                   "agents": {n: getattr(a, "params", None) for n, a in agents.items()}, "cost_bps": COST,
                   "embedding_window_days": 90, "first": FIRST, "last": LAST}, FIRST, LAST, list(runs), d)
    own = load(OUT / s2["winner"])
    same = own.decisions.reset_index(drop=True).equals(runs["live"].decisions.reset_index(drop=True))
    log(f"live decisions equal trial {s2['winner']}'s own run: {same}")
    base = simulator.Simulator(world, 0.0)
    for n, r in runs.items():
        for c, eq in simulator.replay(world, r, costs=(0.0, 5.0, 10.0, 20.0), base=base).items():
            eq.to_parquet(d / n / f"equity_{c:g}bps.parquet", index=False)
        same5 = r.equity.reset_index(drop=True).equals(pd.read_parquet(d / n / "equity_5bps.parquet"))
        log(f"replayed {n}; 5 bps equals the run: {same5}")
    for t in [*STAGE1, *STAGE2]:
        if (OUT / t).exists():
            eq = simulator.replay(world, load(OUT / t), costs=(0.0,), base=base)[0.0]
            eq.to_parquet(OUT / t / "equity_0bps.parquet", index=False)
    log("replays done")


def report_step():
    s1 = json.loads((OUT / "stage1.json").read_text(encoding="utf-8"))
    s2 = json.loads((OUT / "stage2.json").read_text(encoding="utf-8"))
    world = World.load(embeddings=False)
    labels = dev_labels(world)
    d = OUT / "compare"
    runs = {p.name: load(p) for p in sorted(d.iterdir()) if (p / "decisions.parquet").exists()}
    replays = {n: {c: pd.read_parquet(d / n / f"equity_{c:g}bps.parquet") for c in (0.0, 5.0, 10.0, 20.0)}
               for n in runs}
    names = [t for t in [*STAGE1, *STAGE2] if (OUT / t).exists()]
    variants = {t: load(OUT / t) for t in names if t != s2["winner"]}
    for t in variants:
        replays[t] = {0.0: pd.read_parquet(OUT / t / "equity_0bps.parquet")}
    rows = {}
    for t in names:
        m = {**s1["measures"].get(t, {}), **s2["measures"].get(t, {})}
        before = stats.book_stats(metrics.book_returns(pd.read_parquet(OUT / t / "equity_0bps.parquet"), DEV_FIRST,
                                                       LAST).to_numpy())["sharpe"]
        rows[t] = {"stage": 1 if t in STAGE1 else 2, "mean_ic": m["mean_ic"], "ic_t": m["ic_t"],
                   "sharpe_before_costs": before, "sharpe_after_costs": m["sharpe_after_costs"],
                   "max_drawdown": m["max_drawdown"], "daily_turnover": m["daily_turnover"],
                   "won": "stage 1" if t == s1["winner"] else ""}
        if t == s2["winner"]:
            rows[t]["won"] = (rows[t]["won"] + ", " if rows[t]["won"] else "") + "stage 2 (chosen)"
    spy = benchmarks.load_spy()
    spy = spy[spy.date <= pd.Timestamp(LAST)]
    notes = [f"The frozen trial plan's SHA-256: `{plan.plan_hash()}` (`research/m3_kickoff.md`).",
             f"Stage 1 ({s1['rule']}) chose {s1['winner']}. Stage 2 ({s2['rule']}) chose {s2['winner']}: "
             f"{json.dumps(s2['chosen_kw'])}. \"live\" below is that configuration.",
             "IC days run from 2017-01-03 to 2019-12-30, so every label ends by 2019-12-31. Book returns run to "
             "2019-12-31. Nothing from 2020 on is read.",
             "The baselines hold as long as the chosen trial; equal weight rebalances every session."]
    trial_table = pd.DataFrame(rows).T
    out = report.write(ROOT / "research" / "m3_dev_report.md", runs=runs, labels=labels, spy=spy,
                       sectors=benchmarks.load_sectors(), sessions=world.clock.between(FIRST, LAST),
                       first=DEV_FIRST, last=LAST, run_bps=COST, trials_csv=ROOT / "runs" /
                       "trials.csv", replays=replays, variants=variants, title="M3 dev report (2017 to 2019)",
                       notes=notes, trial_table=trial_table)
    log(f"wrote {out}")


if __name__ == "__main__":
    stay_awake()
    OUT.mkdir(parents=True, exist_ok=True)
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    {"stage1": stage1, "stage2": stage2, "compare": compare, "report": report_step}[step]()
