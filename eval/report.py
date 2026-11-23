"""The dev report writer (PLAN 9.2's M3 "done when" and 9.10; M3 step 5): research/m3_dev_report.md from the dev runs.

It takes finished runs ({name: sim.simulator.Run}) and the eval tables, and writes markdown plus SVG charts. It runs
nothing and reads no view. The run names it knows:
- "live": the chosen configuration's long-short book; "live_long_only": its long-only book (optional);
- "price_only"; "placebo_<seed>"; "random_<seed>"; "momentum"; "reversal"; "equal_weight";
- "live_frozen_<year>": the twins.
`replays` ({name: {bps: equity rows}}, from sim.simulator.replay) give each book before costs (0 bps) and the
cost table (0, 5, 10 and 20 bps for "live" and "live_long_only"). `variants` ({name: Run}) are the other trials
(holding periods, the band, and so on), shown side by side; with the chosen one, their Sharpe ratios give the
deflated Sharpe's spread.

The report's sections, in order:
- the trials, IC by quarter, the frozen-twin gaps, and the price-only twin and the placebo;
- the matched baselines for both books, the variants, and costs at 0, 5, 10 and 20 bps;
- beta and sector tilt, the deflated Sharpe and the seed spread;
- regimes and shocks, coefficient life, the switch-day check and the charts.
H1 to H3 are not tested here. They are tested on the sealed years only (PLAN 9.10).
"""
import csv
import math
from pathlib import Path

import numpy as np
import pandas as pd

from data_pipeline.settings import DATA_DIR

from . import charts, metrics, stats
from .benchmarks import spy_buy_and_hold
from .switch_day import switch_day


def _fmt(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return f"{v:.4f}" if abs(v) < 1000 else f"{v:.0f}"
    return str(v)


def table(df, index=True):
    """A markdown table of a DataFrame, numbers to 4 decimals."""
    if df is None or len(df) == 0:
        return "(none)\n"
    cols = ([df.index.name or ""] if index else []) + [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for i, row in df.astype(object).iterrows():
        cells = ([str(i)] if index else []) + [_fmt(v) for v in row.tolist()]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def read_trials(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _seeds(runs, prefix):
    return {n[len(prefix):]: r for n, r in runs.items() if n.startswith(prefix) and n[len(prefix):].isdigit()}


def _twins(runs):
    return {int(n.rsplit("_", 1)[1]): r for n, r in runs.items() if n.startswith("live_frozen_")}


def build(runs, labels, spy, sectors, sessions, first, last, run_bps, trials_csv, replays=None, variants=None,
          charts_dir=None, switch_years=(2017, 2018, 2019), title="M3 dev report", notes=(), trial_table=None,
          sealed=False):
    """Returns the report's markdown. Charts are written to charts_dir when given, and linked relative to it. The
    switch-day check runs on `switch_years` only (M3 decision 2: the dev years), whatever `first` is.

    sealed=True gives the descriptive part of the sealed report (research/m4_sealed_report.py, PREREG.md): no
    p-values, since PREREG tests only H1 to H3 and its two leak checks, which that writer scores itself; no reading
    table, which tests each placebo seed; and no variants, deflated Sharpe or switch-day sections, which that writer
    computes as PREREG fixes them."""
    variants = dict(variants or {})
    first, last = pd.Timestamp(first), pd.Timestamp(last)
    ic = {n: metrics.daily_rank_ic(r.decisions, labels) for n, r in {**runs, **variants}.items()
          if not r.decisions.empty}
    replays = dict(replays or {})
    before = {n: rp[0.0] for n, rp in replays.items() if 0.0 in rp}
    ret = {n: metrics.book_returns(r.equity, first, last) for n, r in {**runs, **variants}.items()}
    md = [f"# {title}\n", f"Dev years {first.date()} to {last.date()}. Costs {run_bps:g} bps per side unless a table "
          "says otherwise. Sharpe ratios are over zero, no cash rate (the store has none; the owner, 23 Nov). "
          "Every number below comes from `eval/report.py` over the runs named here. H1 to H3 are "
          "tested on the sealed years only (PLAN 9.10), so this report tests none of them. p-values use the normal "
          "distribution, which is slightly liberal for a quarter of about 63 days. The Newey-West lag follows the "
          "number of days (6 for 754), which is shorter than a 20-day first-20 block, so those errors may be low.\n"]
    md += [f"- {n}\n" for n in notes]
    if sealed:
        md[1] = (f"Sealed years {first.date()} to {last.date()}, described only: nothing in this part is a test "
                 f"(PREREG.md section 3). Costs {run_bps:g} bps per side unless a table says otherwise. Sharpe ratios "
                 "are over zero, with no cash rate, borrow fee or short rebate. Every number below comes from "
                 "`eval/report.py` over the runs named here.\n")

    def tb(df, index=True):
        return table(df.drop(columns=[c for c in df.columns if c == "p"]) if sealed else df, index)

    trials = read_trials(trials_csv)
    latest = {r["trial"]: r.get("status") for r in trials if r.get("trial")}
    names = {t for t, s in latest.items() if s != "dropped"}
    n_ledger = len(names) if latest else len(trials)  # as eval.trials.count; a ledger without trial names: rows
    shown, root = Path(trials_csv).resolve(), Path(__file__).resolve().parents[1]
    shown = shown.relative_to(root) if shown.is_relative_to(root) else shown  # a repo path anyone can check
    md.append(f"\n## Trials\n\n{n_ledger} trials in `{shown.as_posix()}` ({len(trials)} rows).\n\n")
    if trials:
        cols = [c for c in ["trial", "status", "run_id", "commit", "dirty", "settings_hash", "agents"]
                if c in trials[0]]
        md.append(tb(pd.DataFrame(trials)[cols], index=False))

    md.append("\n## Daily rank IC by quarter (live)\n\n")
    if "live" in ic:
        md.append(tb(metrics.ic_by_quarter(ic["live"], first, last).rename_axis("quarter")))

    twins = {y: ic[f"live_frozen_{y}"] for y in _twins(runs) if f"live_frozen_{y}" in ic}
    md.append("\n## Frozen-twin gaps (live minus twin, paired daily IC)\n\n")
    md.append(tb(metrics.twin_gaps(ic["live"], twins, last), index=False) if "live" in ic and twins else "(none)\n")

    if not sealed:
        md.append("\n## Reading: the price-only twin and the placebo (live minus each, paired daily IC)\n\n")
        reading = {}
        if "live" in ic and "price_only" in ic:
            reading["price_only"] = metrics.paired_gaps(ic["live"], ic["price_only"], first, last, by=None).loc["all"]
        for s in sorted(_seeds(runs, "placebo_"), key=int):
            if f"placebo_{s}" in ic and "live" in ic:
                reading[f"placebo_{s}"] = metrics.paired_gaps(ic["live"], ic[f"placebo_{s}"], first, last,
                                                              by=None).loc["all"]
        md.append(tb(pd.DataFrame(reading).T.rename_axis("against")) if reading else "(none)\n")

    md.append("\n## Matched baselines\n\nLong-short, against cash (zero) and the long-short baselines:\n\n")
    ls = {n: runs[n].equity for n in ["live", "momentum", "reversal"] + [f"random_{s}" for s in
                                                                          sorted(_seeds(runs, "random_"), key=int)]
          if n in runs}
    lst = metrics.book_table(ls, first, last, before) if ls else pd.DataFrame()
    if len(lst):
        lst["mean_ic"] = [stats.nw_mean(metrics.within(ic[n], first, last).to_numpy())["mean"] if n in ic else
                          math.nan for n in lst.index]
        lst.loc["cash"] = pd.Series({c: math.nan if c.startswith("sharpe") or c == "mean_ic" else 0.0
                                     for c in lst.columns})
    md.append(tb(lst.rename_axis("book")))
    md.append("\nLong-only, against SPY buy-and-hold and all picks equally:\n\n")
    lo = {n: runs[n].equity for n in ["live_long_only", "equal_weight"] if n in runs}
    lot = metrics.book_table(lo, first, last, before) if lo else pd.DataFrame()
    spy_r = None
    if spy is not None and len(spy):
        bh = spy_buy_and_hold(spy, first, last)
        spy_r = pd.Series(bh.equity.to_numpy(), index=pd.DatetimeIndex(bh.date)).pct_change().dropna()
        st = stats.book_stats(spy_r.to_numpy())
        lot.loc["spy_buy_and_hold", ["annual_return", "annual_vol", "sharpe_after_costs", "max_drawdown",
                                     "days"]] = [st["annual_return"], st["annual_vol"], st["sharpe"],
                                                 st["max_drawdown"], st["days"]]
    md.append(tb(lot.rename_axis("book")))

    if trial_table is not None:
        md.append("\n## Every trial, winners and losers\n\n" + tb(trial_table.rename_axis("trial")))
    if not sealed:
        md.append("\n## Variants (each a trial)\n\n")
        if variants:
            vt = metrics.book_table({n: r.equity for n, r in variants.items()}, first, last, before)
            vt["mean_ic"] = [stats.nw_mean(metrics.within(ic[n], first, last).to_numpy())["mean"] if n in ic else
                             math.nan for n in vt.index]
            md.append(tb(vt.rename_axis("variant")))
        else:
            md.append("(none)\n")

    md.append("\n## Costs (bps per side)\n\n")
    for n in ("live", "live_long_only"):
        if n in replays:
            md.append(f"{n}:\n\n" + tb(metrics.cost_table(replays[n], first, last).rename_axis(
                "cost")) + "\n")

    md.append("\n## Exposures\n\n")
    if spy is not None and len(spy):
        mkt = metrics.spy_open_returns(spy)
        bt = {n: metrics.beta(ret[n], mkt) for n in ("live", "live_long_only") if n in ret}
        md.append("Market beta against SPY's open-to-open returns (Newey-West):\n\n" +
                  tb(pd.DataFrame(bt).T.rename_axis("book")) + "\n")
    for n in ("live", "live_long_only"):
        if sectors is not None and n in runs:
            md.append(f"Sector tilt of {n}'s targets (net weight; sectors are Wikipedia's list as of each date, see "
                      "`research/audit/benchmarks.md`):\n\n" +
                      tb(metrics.sector_tilt(runs[n].decisions, sectors, first, last).rename_axis("sector")) +
                      "\n")

    if not sealed:
        md.append("\n## Deflated Sharpe (the chosen version)\n\n")
        if "live" in ret:
            srs = [stats.moments(r.dropna().to_numpy())[0] for n, r in ret.items()
                   if (n == "live" or n in variants) and r.dropna().std() > 0]
            n_trials = max(n_ledger, len(srs))  # a run in the ledger can hold several trials (judge item 1)
            ds = stats.deflated_sharpe(ret["live"].to_numpy(), n_trials, srs)
            md.append(f"Trials counted: {n_trials} (the larger of the ledger's {n_ledger} trials and the {len(srs)} "
                      "trials shown).\n\n")
            if len(srs) < 2:
                md.append("**Warning:** fewer than 2 trials' Sharpe ratios, so their spread is 0 and the deflated "
                          "Sharpe equals the probabilistic Sharpe against 0.\n\n")
            md.append(tb(pd.DataFrame([ds]), index=False))

    md.append("\n## Seed spread\n\n")
    for prefix in ("placebo_", "random_"):
        seeds = _seeds(runs, prefix)
        if seeds:
            sp = metrics.seed_spread({s: ic[prefix + s] for s in seeds if prefix + s in ic},
                                     {s: r.equity for s, r in seeds.items()}, first, last)
            md.append(f"{prefix.rstrip('_')}:\n\n" + tb(sp.rename_axis("seed")) + "\n")

    md.append("\n## Regimes and shocks (reported, not tested)\n\n")
    if spy is not None and len(spy) and "live" in ic:
        days = pd.DatetimeIndex(sessions)
        days = days[(days >= first) & (days <= last)]
        reg = metrics.regimes(spy, days)
        md.append(tb(metrics.regime_table(ic["live"], ret["live"], reg, first, last), index=False))

    md.append("\n## Coefficient life (reported, not tested)\n\nEach frozen twin's mean daily IC by quarter since "
              "its snapshot:\n\n")
    md.append(tb(metrics.coefficient_life(twins, last), index=False) if twins else "(none)\n")

    if not sealed:
        md.append("\n## The switch-day check (`research/audit/cutoff.md` 10.2)\n\n")
        if "live" in ic and "price_only" in ic:
            sd = switch_day(ic["live"], ic["price_only"], sessions, list(switch_years))
            md.append(tb(sd["years"], index=False) + "\n" + tb(pd.DataFrame([sd["pooled"]]), index=False))
            md.append(f"\nYears counted: {sd['years_counted']}. Warning (a), the pooled difference above zero at "
                      f"one-sided 5%: {_fmt(sd['warning_a'])}. Warning (b), at least half the years above by more "
                      f"than two standard errors: {_fmt(sd['warning_b'])}.\n")

    if charts_dir is not None:
        md.append("\n## Charts\n\n")
        md += _charts(Path(charts_dir), replays, ic, ret, twins, spy_r, first, last)
    return "".join(md)


def _charts(d, replays, ic, ret, twins, spy_r, first, last):
    d.mkdir(parents=True, exist_ok=True)
    out = []

    def link(path, what):
        out.append(f"- {what}: `{path.as_posix()}`\n")

    roll = {n: metrics.within(ic[n], first, last).rolling(63, min_periods=20).mean()
            for n in ("live", "price_only") if n in ic}
    pl = [metrics.within(ic[n], first, last) for n in ic if n.startswith("placebo_")]
    if pl:
        roll["placebo (seed mean)"] = pd.concat(pl, axis=1).mean(axis=1).rolling(63, min_periods=20).mean()
    if roll:
        link(charts.lines(roll, "Daily rank IC, 63-session mean", d / "ic.svg", "rank IC"), "IC over time")
    gaps = {f"end of {y}": (ic["live"] - tw).dropna().loc[pd.Timestamp(y + 1, 1, 1):last].cumsum()
            for y, tw in twins.items()} if "live" in ic else {}
    gaps = {k: v for k, v in gaps.items() if len(v)}
    if gaps:
        link(charts.lines(gaps, "Live minus frozen twin, cumulative daily IC", d / "twin_gaps.svg", "sum of IC "
                          "differences"), "Frozen-twin gaps")
    ls = {n: charts.wealth(ret[n]) for n in ret if n in ("live", "momentum", "reversal") or n.startswith("random_")}
    if ls:
        link(charts.lines(ls, "Long-short equity after costs", d / "equity_long_short.svg", "wealth", zero=False),
             "Long-short equity against the baselines")
    lo = {n: charts.wealth(ret[n]) for n in ("live_long_only", "equal_weight") if n in ret}
    if spy_r is not None:
        lo["spy_buy_and_hold"] = charts.wealth(spy_r)
    if lo:
        link(charts.lines(lo, "Long-only equity after costs", d / "equity_long_only.svg", "wealth", zero=False),
             "Long-only equity against SPY and equal weight")
    if "live" in replays:
        cs = {f"{c:g} bps": charts.wealth(metrics.book_returns(e, first, last))
              for c, e in sorted(replays["live"].items())}
        link(charts.lines(cs, "Live long-short equity by cost", d / "costs.svg", "wealth", zero=False),
             "Cost sensitivity")
    return out


CHARTS = DATA_DIR / "runs" / "m3_dev_report_charts"


def write(path, charts_dir=CHARTS, **kw):
    """Builds the report and writes it to `path` (research/m3_dev_report.md in step 6). The charts go to D: with the
    other run outputs, outside git (the owner, 23 Nov); charts_dir=None draws none."""
    path = Path(path)
    text = build(charts_dir=charts_dir, **kw)
    path.write_text(text, encoding="utf-8")
    return path
