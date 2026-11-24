"""M4: the sealed report's writer, the scoring code PREREG.md names (sections 3 to 7). It is written and tested on
made-up records before the seal (tests/test_m4_sealed_report.py), committed in the code commit, and run unchanged on
the sealed outputs (PLAN 5.5, rule C-1). Nothing here has read a sealed outcome.

  python research/m4_sealed_report.py      writes research/m4_sealed_report.md

Run it only after both sealed parts and their replays (research/m4_sealed_run.py), and before `ledger`. It reads the
runs from DATA_DIR/runs/m4_sealed, the labels and sessions from the store, `seal.lock`, the run log and the sealed
ledger. It scores exactly what PREREG fixes, and nothing else:
- H1, H2 and H3 (H3 as two paired tests, its p the larger of the two), one-sided, Newey-West with lag 6, Holm at 5%;
- the switch-day check on 2020 to 2025, with 2026 shown apart and outside the rule;
- the older-vintage check, with the point-estimate gate, (a), (b) and the power note;
- the outcome: Success, "H3 not claimed", Failure or Void;
- the deflated Sharpe as PREREG section 4 fixes it, with the two other versions beside it.
Everything else in the report is descriptive (eval/report.py with sealed=True: no p-values, no other test).
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
import pandas as pd  # noqa: E402

from eval import metrics, report, stats  # noqa: E402
from eval.switch_day import switch_day  # noqa: E402

SEALED_FIRST = "2020-01-02"  # the first sealed session (reference/split.json)
LAG = 6  # PREREG section 3: every test of H1 to H3 (the owner's decision 5)
ROBUST_LAGS = (7, 21)  # shown, not tested: the 1994 rule's lag for the sealed length, and 21
ALPHA = 0.05
SWITCH_YEARS = (2020, 2021, 2022, 2023, 2024, 2025)  # PREREG section 5; 1 January 2026 is not a switch
APART_YEARS = (2026,)
SEEDS = (1, 2, 3, 4, 5)
H2_TWIN = "live_frozen_2019"
DEV_TRIALS = 8  # runs/trials.csv before the seal (research/m3_dev_report.md, "Deflated Sharpe")
DEV_VAR_PRINTED = "0.0013"  # var_trials as research/m3_dev_report.md:199 prints it
OUT_MD = ROOT / "research" / "m4_sealed_report.md"


def nan1(p):
    """A missing or NaN p counts as 1 (PREREG section 3)."""
    return 1.0 if p is None or (isinstance(p, float) and math.isnan(p)) else float(p)


def holm(p, alpha=ALPHA):
    """{name: held}: Holm's step-down over the p-values, unrounded. The smallest must be at most alpha/m, the next at
    most alpha/(m-1), and so on; a p equal to its bound passes; the first failure stops it. Ties don't change the
    result."""
    order = sorted(p, key=lambda k: nan1(p[k]))
    held = {k: False for k in p}
    for i, k in enumerate(order):
        if nan1(p[k]) <= alpha / (len(order) - i):
            held[k] = True
        else:
            break
    return held


def paired(a, b):
    """a minus b on the days both have a value."""
    return (a - b).dropna().sort_index()


def placebo_mean(ic):
    """The placebo's daily IC: the mean of the 5 seeds' ICs on the days all 5 have one (M4 entry rule 3)."""
    missing = [s for s in SEEDS if f"placebo_{s}" not in ic]
    if missing:
        raise ValueError(f"placebo seeds missing: {missing}")
    return pd.concat([ic[f"placebo_{s}"] for s in SEEDS], axis=1).dropna().mean(axis=1).sort_index()


def _monthly(x):
    """t of the series' monthly means, with no lag: shown as robustness, not tested."""
    m = x.groupby(x.index.to_period("M")).mean()
    return stats.nw_mean(m.to_numpy(), lag=0)["t"]


def hypotheses(ic):
    """PREREG section 3 on the sealed IC days. `ic` maps run names to daily IC series already cut to the IC days."""
    live = ic["live"].dropna().sort_index()
    series = {"H1": live, "H2": paired(live, ic[H2_TWIN]), "H3 vs price-only": paired(live, ic["price_only"]),
              "H3 vs placebo mean": paired(live, placebo_mean(ic))}
    tests = {k: stats.nw_mean(v.to_numpy(), lag=LAG) for k, v in series.items()}
    p = {"H1": tests["H1"]["p"], "H2": tests["H2"]["p"],
         "H3": max(nan1(tests["H3 vs price-only"]["p"]), nan1(tests["H3 vs placebo mean"]["p"]))}
    held = holm(p)
    robust = {k: {**{f"t lag {g}": stats.nw_mean(v.to_numpy(), lag=g)["t"] for g in ROBUST_LAGS},
                  "t monthly means": _monthly(v)} for k, v in series.items()}
    return {"tests": tests, "p": p, "held": held, "robustness": robust}


def switch_check(ic, sessions):
    """PREREG section 5: the switch-day rule on 2020 to 2025; 2026 apart, outside the rule."""
    sd = switch_day(ic["live"], ic["price_only"], sessions, list(SWITCH_YEARS))
    apart = switch_day(ic["live"], ic["price_only"], sessions, list(APART_YEARS))
    return {**sd, "outcome": "warning" if sd["warning"] else "no warning", "apart": apart["years"]}


def older_check(ic, older_ic):
    """PREREG section 5: the older-vintage check. None for `older_ic` means the part did not run."""
    if older_ic is None:
        return {"outcome": "not run", "warning": False}
    live, price, older = ic["live"], ic["price_only"], older_ic
    rule = stats.nw_mean(paired(live, price).to_numpy())
    old = stats.nw_mean(paired(older, price).to_numpy())
    diff = stats.nw_mean(paired(live, older).to_numpy())
    gate = not math.isnan(rule["mean"]) and rule["mean"] > 0
    a = bool(gate and old["mean"] < 0.5 * rule["mean"])
    b = nan1(diff["p"]) < ALPHA
    warning = bool(gate and a and b)
    power_note = math.isnan(rule["t"]) or rule["t"] < 1.645
    outcome = ("warning" if warning else "no warning") if gate else "not informative"
    return {"news_effect_rule": rule, "news_effect_older": old, "rule_minus_older": diff, "gate_open": gate,
            "a": a, "b": bool(b), "warning": warning, "power_note": power_note, "outcome": outcome}


def outcome(main_complete, older_complete, held, switch_warns, older_warns):
    """PREREG section 6."""
    if not main_complete:
        return "Void: the main part did not reach its last session, so H1 to H3 are not tested"
    h2h3 = held["H2"] and held["H3"]
    if not h2h3:
        note = "" if older_complete else " (the older-vintage check did not run)"
        return "Failure: H2 or H3 does not hold" + note
    if switch_warns or older_warns:
        which = " and ".join(n for n, w in (("switch-day check", switch_warns), ("older-vintage check", older_warns))
                             if w)
        return f"H2 held; H3 held but is not claimed, because the {which} warned"
    if not older_complete:
        return "Not a success: H2 and H3 held, but the older-vintage check did not run"
    return "Success: H2 and H3 held after Holm, and neither leak check warned"


def _sr(r):
    r = pd.Series(r).dropna()
    return stats.moments(r.to_numpy())[0]


def deflated(live_after, live_before, dev_after, dev_before, n_trials):
    """PREREG section 4. `dev_after` and `dev_before` are the dev trials' daily return series over the dev years,
    after costs and at 0 bps. Stops if the dev variance doesn't print as the dev report's."""
    after_srs = [_sr(r) for r in dev_after]
    before_srs = [_sr(r) for r in dev_before]
    var = pd.Series(after_srs).var(ddof=1)
    if f"{var:.4f}" != DEV_VAR_PRINTED:
        raise ValueError(f"the dev trials' variance is {var:.6f}, not the dev report's {DEV_VAR_PRINTED}")
    return {"after costs, after-cost trial variance (the result)": stats.deflated_sharpe(
                pd.Series(live_after).to_numpy(), n_trials, after_srs),
            "after costs, before-cost trial variance (shown)": stats.deflated_sharpe(
                pd.Series(live_after).to_numpy(), n_trials, before_srs),
            "before costs, before-cost trial variance (shown)": stats.deflated_sharpe(
                pd.Series(live_before).to_numpy(), n_trials, before_srs)}


def ics(runs, labels, sealed_end):
    """Each run's daily IC on the IC days: from 2020-01-02, labels ending by the sealed end."""
    lab = labels[pd.to_datetime(labels.end) <= pd.Timestamp(sealed_end)]
    return {n: metrics.within(metrics.daily_rank_ic(r.decisions, lab), SEALED_FIRST, sealed_end)
            for n, r in runs.items() if not r.decisions.empty}


def score(runs, older_run, labels, sessions, sealed_end, main_complete=True, older_complete=True):
    """Every scored number of PREREG sections 3, 5 and 6. A void main part is not tested at all (section 6)."""
    if not main_complete:
        return {"hypotheses": None, "switch": None, "older": None,
                "outcome": outcome(False, older_complete, None, False, False)}
    ic = ics(runs, labels, sealed_end)
    older_ic = ics({"o": older_run}, labels, sealed_end).get("o") if older_run is not None and older_complete \
        else None
    h = hypotheses(ic)
    sw = switch_check(ic, sessions)
    ov = older_check(ic, older_ic)
    return {"hypotheses": h, "switch": sw, "older": ov,
            "outcome": outcome(main_complete, older_complete, h["held"], sw["warning"], ov["warning"])}


def _num(v):
    return report._fmt(v)


def markdown(sc, ds=None, header=(), described=""):
    h, sw, ov = sc["hypotheses"], sc["switch"], sc["older"]
    md = ["# Sealed report (M4)\n\n", *[f"- {x}\n" for x in header],
          f"\n## Outcome\n\n**{sc['outcome']}.**\n\n"]
    if h is None:
        md.append("H1 to H3 and the two leak checks are not tested, since the main part is void (PREREG section 6).\n")
        return "".join(md) + described
    md += ["## The pre-registered tests (PREREG.md section 3)\n\n",
          "One-sided, Newey-West with lag 6, on the sealed IC days. Holm over H1, H2 and H3 at a family level of 5%. "
          "H3's p is the larger of its two tests' p-values.\n\n"]
    rows = []
    for k, t in h["tests"].items():
        rows.append({"test": k, "days": t["n"], "mean": t["mean"], "se": t["se"], "t": t["t"], "p": t["p"]})
    md.append(report.table(pd.DataFrame(rows), index=False) + "\n")
    hold = pd.DataFrame([{"hypothesis": k, "p": h["p"][k], "holds after Holm": h["held"][k]} for k in ("H1", "H2",
                                                                                                         "H3")])
    md.append(report.table(hold, index=False))
    md.append("\nRobustness, not tested (t-statistics only):\n\n")
    md.append(report.table(pd.DataFrame(h["robustness"]).T.rename_axis("series")))
    md.append("\n## The switch-day check (PREREG section 5)\n\n")
    md.append(report.table(sw["years"], index=False) + "\n" + report.table(pd.DataFrame([sw["pooled"]]), index=False))
    md.append(f"\nYears counted: {sw['years_counted']}. (a): {_num(sw['warning_a'])}. (b): {_num(sw['warning_b'])}. "
              f"**{sw['outcome']}**.\n\n2026, shown apart and outside the rule:\n\n" +
              report.table(sw["apart"], index=False))
    md.append("\n## The older-vintage check (PREREG section 5)\n\n")
    if ov["outcome"] == "not run":
        md.append("**not run.**\n")
    else:
        rows = [{"series": n, "days": ov[k]["n"], "mean": ov[k]["mean"], "t": ov[k]["t"],
                 "p": ov[k]["p"] if k == "rule_minus_older" else None}  # PREREG tests only (b)
                for n, k in (("news effect, the rule's vintage", "news_effect_rule"),
                             ("news effect, the older vintage", "news_effect_older"),
                             ("live minus live_older_vintage", "rule_minus_older"))]
        md.append(report.table(pd.DataFrame(rows), index=False))
        md.append(f"\nGate open (the rule's news effect has a mean above zero): {_num(ov['gate_open'])}. "
                  f"(a): {_num(ov['a'])}. (b): {_num(ov['b'])}. **{ov['outcome']}**.\n")
        if ov["power_note"]:
            md.append("\nPower note: the rule's news effect has a t below 1.645, so the check could not have seen a "
                      "small leak.\n")
    if ds is not None:
        md.append("\n## Deflated Sharpe (PREREG section 4)\n\n")
        md.append(report.table(pd.DataFrame(ds).T.rename_axis("version")))
    md.append(described)
    return "".join(md)


# The real run: after both sealed parts and their replays. Nothing below has run.

def _load_all():
    import m3_dev_runs as dev
    import m4_sealed_run as R
    from eval import benchmarks, trials
    from sim import seal
    from world.world import World
    end = R.sealed_end()
    main_dir, older_dir = R.OUT / "main", R.OUT / "older_vintage"
    runs = {p.name: dev.load(p) for p in sorted(main_dir.iterdir()) if (p / "decisions.parquet").exists()}
    older = dev.load(older_dir / "live_older_vintage") if (older_dir / "live_older_vintage" /
                                                           "decisions.parquet").exists() else None

    def complete(r):
        return r is not None and len(r.equity) and pd.Timestamp(r.equity.date.max()) == pd.Timestamp(end)
    world = World.load(embeddings=False)
    labels = world.labels.df
    sessions = world.clock.between(R.FIRST, end)
    replays = {n: {c: pd.read_parquet(main_dir / n / f"equity_{c:g}bps.parquet") for c in (0.0, 5.0, 10.0, 20.0)}
               for n in runs}
    names = ["T01", "T02", "T03", "T05", "T06", "T07", "T08", "T09"]  # the 8 dev trials; a missing one stops it
    dev_after = [metrics.book_returns(dev.load(dev.OUT / t).equity, dev.DEV_FIRST, dev.LAST) for t in names]
    dev_before = [metrics.book_returns(pd.read_parquet(dev.OUT / t / "equity_0bps.parquet"), dev.DEV_FIRST, dev.LAST)
                  for t in names]
    if trials.count() != DEV_TRIALS:
        raise ValueError(f"runs/trials.csv counts {trials.count()} trials, not {DEV_TRIALS}")
    log = seal.started()
    n_trials = DEV_TRIALS + sum(1 for e in log if e["part"] == "main" and e["again"])
    return dict(dev=dev, R=R, seal=seal, trials=trials, benchmarks=benchmarks, end=end, runs=runs, older=older,
                main_complete=complete(runs.get("live")), older_complete=complete(older), labels=labels,
                sessions=sessions, replays=replays, dev_after=dev_after, dev_before=dev_before, n_trials=n_trials,
                log=log)


def main():
    x = _load_all()
    end = x["end"]
    sc = score(x["runs"], x["older"], x["labels"], x["sessions"], end, x["main_complete"], x["older_complete"])
    ds = None
    if x["main_complete"]:
        live_after = metrics.book_returns(x["runs"]["live"].equity, SEALED_FIRST, end)
        live_before = metrics.book_returns(x["replays"]["live"][0.0], SEALED_FIRST, end)
        ds = deflated(live_after, live_before, x["dev_after"], x["dev_before"], x["n_trials"])
    spy = x["benchmarks"].load_spy()
    lab = x["labels"][pd.to_datetime(x["labels"].end) <= pd.Timestamp(end)]
    described = report.build(runs=x["runs"], labels=lab, spy=spy[spy.date <= pd.Timestamp(end)],
                             sectors=x["benchmarks"].load_sectors(), sessions=x["sessions"], first=SEALED_FIRST,
                             last=end, run_bps=5.0, trials_csv=ROOT / "runs" / "trials.csv", replays=x["replays"],
                             title="The sealed years, described (not tested)", sealed=True)
    lock = json.loads((ROOT / "seal.lock").read_text(encoding="utf-8"))
    header = [f"PREREG.md SHA-256: `{x['seal'].prereg_hash()}`", f"seal.lock: `{json.dumps(lock, sort_keys=True)}`",
              *[f"Run log: `{json.dumps(e, sort_keys=True)}`" for e in x["log"]],
              *[f"Sealed ledger row: `{json.dumps(r, sort_keys=True)}`" for r in x["trials"].rows(x["R"].LEDGER)],
              f"Main part complete: {_num(x['main_complete'])}. Older-vintage part complete: "
              f"{_num(x['older_complete'])}."]
    OUT_MD.write_text(markdown(sc, ds, header, "\n" + described.replace("# ", "## ", 1)), encoding="utf-8")
    print(f"wrote {OUT_MD}: {sc['outcome']}", flush=True)


if __name__ == "__main__":
    main()
