"""The sealed report's writer (research/m4_sealed_report.py), the scoring code PREREG.md names, on made-up records
only: Holm, H1 to H3 with lag 6 and H3 as the larger of its two p-values, the placebo's daily mean, both leak checks,
every outcome, the deflated Sharpe's guard, and the report without any test PREREG doesn't name. Nothing here reads
the store or the sealed years: the dates are the real calendar's, and every number is drawn here."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import m4_sealed_report as W  # noqa: E402
from eval import report, stats  # noqa: E402
from sim.simulator import Run  # noqa: E402
from world.clock import Clock  # noqa: E402

END = "2026-10-28"


def days(n=400, first="2020-01-02"):
    return pd.DatetimeIndex(Clock().between(first, END)[:n])


def noise(seed, n=400, mean=0.0, sd=0.1):
    return pd.Series(np.random.default_rng(seed).normal(mean, sd, n), index=days(n))


def made_up_ic(live_mean=0.05, price_mean=0.0, placebo_mean=0.0, twin_mean=0.0):
    ic = {"live": noise(1, mean=live_mean), "price_only": noise(2, mean=price_mean),
          W.H2_TWIN: noise(3, mean=twin_mean)}
    ic.update({f"placebo_{s}": noise(10 + s, mean=placebo_mean) for s in W.SEEDS})
    return ic


def test_holm_steps_down_at_five_percent():
    assert W.holm({"H1": 0.01, "H2": 0.02, "H3": 0.04}) == {"H1": True, "H2": True, "H3": True}
    assert W.holm({"H1": 0.02, "H2": 0.001, "H3": 0.03}) == {"H1": True, "H2": True, "H3": True}
    assert W.holm({"H1": 0.02, "H2": 0.02, "H3": 0.02}) == {"H1": False, "H2": False, "H3": False}
    assert W.holm({"H1": 0.001, "H2": 0.03, "H3": 0.04}) == {"H1": True, "H2": False, "H3": False}  # stops at 0.03
    assert W.holm({"H1": 0.05 / 3, "H2": 0.05 / 2, "H3": 0.05})["H3"] is True  # equal to the bound passes
    assert W.holm({"H1": float("nan"), "H2": 0.001, "H3": 0.001}) == {"H1": False, "H2": True, "H3": True}


def test_the_hypotheses_use_lag_6_and_h3_takes_the_larger_p():
    h = W.hypotheses(made_up_ic())
    assert all(t["lag"] == 6 for t in h["tests"].values())
    assert set(h["tests"]) == {"H1", "H2", "H3 vs price-only", "H3 vs placebo mean"}
    assert h["p"]["H3"] == max(h["tests"]["H3 vs price-only"]["p"], h["tests"]["H3 vs placebo mean"]["p"])
    assert h["held"] == {"H1": True, "H2": True, "H3": True}
    live = made_up_ic()["live"]
    assert h["tests"]["H1"]["mean"] == pytest.approx(live.mean())
    assert h["tests"]["H1"]["p"] == pytest.approx(stats.nw_mean(live.to_numpy(), lag=6)["p"])
    reading_fails = W.hypotheses(made_up_ic(price_mean=0.05))  # the price-only twin as good as live
    assert reading_fails["held"]["H3"] is False and reading_fails["held"]["H2"] is True
    assert reading_fails["p"]["H3"] == reading_fails["tests"]["H3 vs price-only"]["p"]
    assert set(h["robustness"]["H2"]) == {"t lag 7", "t lag 21", "t monthly means"}


def test_the_placebo_is_the_seeds_daily_mean_on_days_all_five_have():
    ic = made_up_ic()
    ic["placebo_3"] = ic["placebo_3"].drop(ic["placebo_3"].index[5])
    m = W.placebo_mean(ic)
    assert ic["live"].index[5] not in m.index and len(m) == len(ic["live"]) - 1
    day = ic["live"].index[7]
    assert m[day] == pytest.approx(np.mean([ic[f"placebo_{s}"][day] for s in W.SEEDS]))
    del ic["placebo_5"]
    with pytest.raises(ValueError, match="placebo seeds missing"):
        W.placebo_mean(ic)


def test_the_older_vintage_check_follows_prereg():
    ic = made_up_ic(live_mean=0.03)
    assert W.older_check(ic, None) == {"outcome": "not run", "warning": False}
    closed = W.older_check(made_up_ic(live_mean=-0.02), noise(30))
    assert closed["outcome"] == "not informative" and closed["warning"] is False and closed["gate_open"] is False
    drop = W.older_check(ic, noise(30, mean=-0.03))  # the older reader does far worse: (a) and (b)
    assert drop["outcome"] == "warning" and drop["a"] and drop["b"]
    same = W.older_check(ic, ic["live"] + noise(31, sd=0.001))
    assert same["outcome"] == "no warning" and not same["a"]
    assert drop["rule_minus_older"]["lag"] == stats.nw_lag(400)  # the code's own lag, not 6
    assert same["power_note"] == (same["news_effect_rule"]["t"] < 1.645)


def test_every_outcome():
    yes = {"H1": True, "H2": True, "H3": True}
    assert W.outcome(True, True, yes, False, False).startswith("Success")
    assert W.outcome(False, True, yes, False, False).startswith("Void")
    assert W.outcome(True, True, {**yes, "H2": False}, False, False).startswith("Failure")
    assert W.outcome(True, True, {**yes, "H3": False}, True, True).startswith("Failure")
    assert "not claimed, because the switch-day check warned" in W.outcome(True, True, yes, True, False)
    assert "older-vintage check warned" in W.outcome(True, True, yes, False, True)
    assert W.outcome(True, False, yes, False, False).startswith("Not a success")
    assert "did not run" in W.outcome(True, False, {**yes, "H2": False}, False, False)
    assert W.outcome(True, True, {**yes, "H1": False}, False, False).startswith("Success")  # H1 is not required


def test_the_deflated_sharpe_stops_on_another_dev_variance(monkeypatch):
    dev_after = [noise(40 + i, n=500, mean=0.0005, sd=0.01) for i in range(8)]
    dev_before = [noise(60 + i, n=500, mean=0.0007, sd=0.01) for i in range(8)]
    with pytest.raises(ValueError, match="not the dev report's"):
        W.deflated(noise(80, mean=0.001, sd=0.01), noise(81, mean=0.001, sd=0.01), dev_after, dev_before, 8)
    var = pd.Series([W._sr(r) for r in dev_after]).var(ddof=1)
    monkeypatch.setattr(W, "DEV_VAR_PRINTED", f"{var:.4f}")
    ds = W.deflated(noise(80, mean=0.001, sd=0.01), noise(81, mean=0.001, sd=0.01), dev_after, dev_before, 9)
    assert len(ds) == 3 and all(d["n_trials"] == 9 for d in ds.values())
    first = next(iter(ds.values()))
    assert first["var_trials"] == pytest.approx(var)


def made_up_runs():
    """Fifteen made-up stocks over the sealed calendar, with labels; live reads them a little."""
    sessions = pd.DatetimeIndex(Clock().between("2019-12-02", END))
    rng = np.random.default_rng(7)
    ents = [f"E{i:02d}" for i in range(15)]
    lab = pd.DataFrame([(e, "", d) for d in sessions for e in ents], columns=["entity_id", "share_class", "date"])
    lab["label"] = rng.normal(0, 0.02, len(lab))
    lab["end"] = lab.groupby("entity_id").date.shift(-1)
    lab = lab.dropna(subset=["end"])
    lab["at_close"] = False

    def run(signal, seed):
        r = np.random.default_rng(seed)
        d = lab[["date", "entity_id", "share_class"]].copy()
        d["prediction"] = signal * lab.label.to_numpy() + r.normal(0, 0.02, len(lab))
        d["position"] = 0.0
        eq = pd.DataFrame({"date": sessions, "equity": np.cumprod(1 + r.normal(0.0002, 0.005, len(sessions))),
                           "cost": 0.0, "gross": 1.0, "traded": 0.1})
        return Run(d.reset_index(drop=True), eq, {"forced_sales": 0, "unmarked": 0})
    runs = {"live": run(0.3, 1), "price_only": run(0.0, 2), W.H2_TWIN: run(0.0, 3), "momentum": run(0.0, 4),
            "live_long_only": run(0.2, 5), "equal_weight": run(0.0, 6)}
    runs.update({f"placebo_{s}": run(0.0, 10 + s) for s in W.SEEDS})
    runs.update({f"random_{s}": run(0.0, 20 + s) for s in W.SEEDS})
    return runs, run(0.3, 30), lab, sessions


def test_the_whole_report_on_made_up_runs_tests_only_what_prereg_names():
    runs, older, lab, sessions = made_up_runs()
    sc = W.score(runs, older, lab, sessions, END)
    ic = W.ics(runs, lab, END)
    assert ic["live"].index.min() >= pd.Timestamp("2020-01-02")
    assert ic["live"].index.max() == pd.Timestamp("2026-10-27")  # the last label ending by the sealed end
    assert sc["outcome"].startswith("Success") and sc["hypotheses"]["held"]["H1"]
    assert list(sc["switch"]["years"].year) == list(W.SWITCH_YEARS)
    assert list(sc["switch"]["apart"].year) == [2026]
    described = report.build(runs=runs, labels=lab, spy=None, sectors=None, sessions=sessions, first="2020-01-02",
                             last=END, run_bps=5.0, trials_csv=Path("no-such-ledger.csv"), sealed=True,
                             title="The sealed years, described (not tested)")
    for gone in ("## Reading", "## Variants", "## Deflated Sharpe", "## The switch-day check", "H1 to H3 are"):
        assert gone not in described
    assert not any(line.startswith("|") and " p |" in line for line in described.splitlines())
    md = W.markdown(sc, None, ["made up"], described)
    for part in ("## Outcome", "## The pre-registered tests", "holds after Holm", "## The switch-day check (PREREG",
                 "## The older-vintage check (PREREG", "2026, shown apart"):
        assert part in md
    void = W.score(runs, None, lab, sessions, END, main_complete=False, older_complete=False)
    assert void["outcome"].startswith("Void") and void["hypotheses"] is None and void["older"] is None
    assert "are not tested, since the main part is void" in W.markdown(void) and "holds after" not in W.markdown(void)
    older_rows = [ln for ln in md.splitlines() if ln.startswith("| news effect")]
    assert len(older_rows) == 2 and all(ln.rstrip().endswith("|  |") for ln in older_rows)  # no p: not tested
    dev = report.build(runs=runs, labels=lab, spy=None, sectors=None, sessions=sessions, first="2020-01-02", last=END,
                       run_bps=5.0, trials_csv=Path("no-such-ledger.csv"))
    assert "## Reading" in dev and "## Deflated Sharpe" in dev  # the dev report is unchanged
    assert math.isfinite(sc["hypotheses"]["tests"]["H2"]["t"])
