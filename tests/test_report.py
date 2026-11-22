"""M3 step 5: the dev report's statistics, metrics, switch-day check, charts and writer, each against a small
hand-worked case. Only made-up data: no real dev result is computed here."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from agent.baselines import Reversal  # noqa: E402
from eval import charts, metrics, report, stats  # noqa: E402
from eval.switch_day import switch_day  # noqa: E402
from sim import simulator  # noqa: E402
from sim.simulator import Run  # noqa: E402
from world.clock import Clock  # noqa: E402
from world.world import World  # noqa: E402


def series(values, start="2017-01-02"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


# Statistics

def test_the_newey_west_lag_rule():
    # floor(4 (n / 100) ^ (2 / 9)): n = 4 gives 4 * 0.04 ^ 0.2222 = 1.96, so 1; n = 100 gives 4; n = 754 gives 6.27
    assert [stats.nw_lag(n) for n in (0, 4, 100, 754)] == [0, 1, 4, 6]


def test_a_newey_west_mean_by_hand():
    # x = 1, 2, 3, 4: mean 2.5, residuals -1.5, -0.5, 0.5, 1.5; sum of squares 5; lag-1 products 0.75 - 0.25 + 0.75
    # = 1.25 with weight 1 - 1/2. S = 5 + 2 * 0.5 * 1.25 = 6.25, se = sqrt(6.25) / 4 = 0.625, t = 4.
    m = stats.nw_mean([1, 2, 3, 4], lag=1)
    assert (m["n"], m["mean"], m["lag"]) == (4, 2.5, 1)
    assert m["se"] == pytest.approx(0.625) and m["t"] == pytest.approx(4.0)
    assert m["p"] == pytest.approx(1 - stats.norm_cdf(4.0))
    assert stats.nw_mean([1, 2, 3, 4], lag=0)["se"] == pytest.approx(math.sqrt(5) / 4)
    assert stats.nw_mean([1, 2, 3, 4])["lag"] == 1  # the rule's lag for 4 days
    assert math.isnan(stats.nw_mean([1.0])["se"])


def test_a_difference_of_means_with_newey_west_by_hand():
    # y = 1, 2, 3, 4 on [1, d], d = 1, 1, 0, 0: the slope is mean(1, 2) - mean(3, 4) = -2. Residuals -0.5, 0.5,
    # -0.5, 0.5. (X'X)^-1 = [[0.5, -0.5], [-0.5, 1]], S = [[1, 0.5], [0.5, 0.5]], so V = [[0.125, -0.125],
    # [-0.125, 0.25]] and the slope's se is 0.5 with lag 0.
    b, se, lag = stats.nw_ols([1, 2, 3, 4], np.array([[1, 1], [1, 1], [1, 0], [1, 0]]), lag=0)
    assert b == pytest.approx([3.5, -2.0]) and se == pytest.approx([math.sqrt(0.125), 0.5]) and lag == 0


def test_the_normal_distribution():
    assert stats.norm_cdf(0.0) == 0.5
    assert stats.norm_cdf(1.959963985) == pytest.approx(0.975, abs=1e-9)
    assert stats.norm_ppf(0.975) == pytest.approx(1.959963985, abs=1e-8)
    assert stats.norm_ppf(0.95) == pytest.approx(1.644853627, abs=1e-8)
    with pytest.raises(ValueError):
        stats.norm_ppf(1.0)


def test_book_statistics_by_hand():
    # +10% then -10%: wealth 1, 1.1, 0.99; total -1%; drawdown 0.99 / 1.1 - 1 = -10%; mean 0, so Sharpe 0; the
    # daily standard deviation is sqrt((0.1^2 + 0.1^2) / 1) = 0.1414.
    s = stats.book_stats([0.1, -0.1])
    assert s["days"] == 2 and s["total"] == pytest.approx(-0.01) and s["max_drawdown"] == pytest.approx(-0.1)
    assert s["sharpe"] == pytest.approx(0.0) and s["annual_vol"] == pytest.approx(math.sqrt(0.02) * math.sqrt(252))
    assert s["annual_return"] == pytest.approx(0.99 ** 126 - 1)
    assert stats.max_drawdown([0.01, 0.02]) == 0.0


def test_moments_by_hand():
    # 1, 2, 3, 4: deviations -1.5, -0.5, 0.5, 1.5; m2 = 1.25, m3 = 0, m4 = (2 * 5.0625 + 2 * 0.0625) / 4 = 2.5625,
    # so kurtosis 2.5625 / 1.5625 = 1.64; Sharpe 2.5 / 1.29099 (the sample standard deviation).
    sr, skew, kurt = stats.moments([1, 2, 3, 4])
    assert sr == pytest.approx(2.5 / math.sqrt(5 / 3)) and skew == pytest.approx(0.0) and kurt == pytest.approx(1.64)


def test_the_probabilistic_and_deflated_sharpe_by_hand():
    # SR 0.1 over 101 days, normal returns: z = 0.1 * 10 / sqrt(1 + 0.5 * 0.01) = 0.997509; Phi(1) = 0.841345 and
    # phi(1) = 0.241971, so Phi(0.997509) = 0.841345 - 0.002491 * 0.241971 = 0.840742, to about 1e-6.
    assert stats.psr(0.1, 101, 0.0, 3.0) == pytest.approx(0.840742, abs=2e-6)
    assert stats.expected_max_sharpe(1, 4.0) == 0.0
    # N = 2: Z(1 - 1/2) = 0, so the expected maximum is sqrt(V) * gamma * Z(1 - 1/(2e))
    e2 = stats.expected_max_sharpe(2, 1.0)
    assert stats.norm_cdf(e2 / stats.EULER) == pytest.approx(1 - 1 / (2 * math.e), abs=1e-9)
    r = np.array([0.01, -0.004, 0.006, 0.002, -0.001, 0.008, -0.003, 0.004])
    one = stats.deflated_sharpe(r, 1, [stats.moments(r)[0]])
    assert one["sr0"] == 0.0 and one["dsr"] == pytest.approx(stats.psr(one["sr"], 8, one["skew"], one["kurt"]))
    many = stats.deflated_sharpe(r, 10, [0.05, -0.02, 0.1, 0.0])
    v = np.var([0.05, -0.02, 0.1, 0.0], ddof=1)
    assert many["var_trials"] == pytest.approx(v) and many["sr0"] == pytest.approx(stats.expected_max_sharpe(10, v))
    assert many["dsr"] < one["dsr"]  # more trials, a higher bar


# IC and twin gaps

def test_rank_ic_by_hand():
    d = pd.DataFrame({"date": ["2017-01-03"] * 3, "entity_id": ["A", "B", "C"], "share_class": ["X"] * 3,
                      "prediction": [3.0, 2.0, 1.0], "position": [0.0] * 3})
    lab = d[["date", "entity_id", "share_class"]].assign(label=[0.1, 0.3, 0.2])
    # ranks 3, 2, 1 against 1, 3, 2: Spearman 1 - 6 * (4 + 1 + 1) / (3 * 8) = -0.5
    assert metrics.daily_rank_ic(d, lab, min_stocks=3).iloc[0] == pytest.approx(-0.5)
    assert metrics.daily_rank_ic(d, lab, min_stocks=4).empty


def test_ic_by_quarter_by_hand():
    ic = pd.Series([0.1, 0.3, -0.2, 0.0, 0.2],
                   index=pd.to_datetime(["2017-01-03", "2017-03-31", "2017-04-03", "2017-05-01", "2017-06-30"]))
    t = metrics.ic_by_quarter(ic)
    assert list(t.index) == ["2017Q1", "2017Q2", "all"]
    assert t.loc["2017Q1", "days"] == 2 and t.loc["2017Q1", "mean"] == pytest.approx(0.2)
    assert t.loc["2017Q2", "mean"] == pytest.approx(0.0) and t.loc["all", "mean"] == pytest.approx(0.08)
    assert t.loc["2017Q1", "se"] == pytest.approx(stats.nw_mean([0.1, 0.3])["se"])
    assert list(metrics.ic_by_quarter(ic, first="2017-04-01").index) == ["2017Q2", "all"]


def test_twin_gaps_start_the_year_after_the_snapshot():
    days = pd.to_datetime(["2017-06-01", "2018-03-01", "2018-09-03", "2019-02-01"])
    live = pd.Series([0.3, 0.2, 0.4, 0.1], index=days)
    twin = pd.Series([0.1, 0.1, 0.1, 0.2], index=days)
    g = metrics.twin_gaps(live, {2017: twin})
    # the 2017 twin starts in 2018: 2018 gaps 0.1 and 0.3 (mean 0.2), 2019 gap -0.1; all three mean 0.1
    assert list(g.year) == ["2018", "2019", "all"] and list(g.twin.unique()) == ["end of 2017"]
    assert g.set_index("year").loc["2018", "mean"] == pytest.approx(0.2)
    assert g.set_index("year").loc["all", "mean"] == pytest.approx(0.1)
    assert g.set_index("year").loc["2019", "days"] == 1


# Books and costs

def test_book_returns_and_turnover_by_hand():
    # from 1.0 of cash: buy 2.0 of value at 5 bps (cost 0.001), earn 1% of the pre-trade 1.0, then sell 2.02
    eq = pd.DataFrame({"date": pd.to_datetime(["2017-01-03", "2017-01-04", "2017-01-05"]),
                       "equity": [0.999, 1.009, 1.009 - 0.00101], "cost": [0.001, 0.0, 0.00101],
                       "gross": [2.0, 2.0, 0.0], "traded": [2.0, 0.0, 2.02]})
    r = metrics.book_returns(eq)
    assert r.to_numpy() == pytest.approx([-0.001, 1.009 / 0.999 - 1, -0.00101 / 1.009])
    assert list(metrics.book_returns(eq, first="2017-01-04").index) == list(eq.date[1:])
    # traded over pre-trade equity (equity + cost): 2 / 1, 0 / 1.009, 2.02 / 1.009
    assert metrics.turnover(eq) == pytest.approx((2.0 + 0.0 + 2.02 / 1.009) / 3)


@pytest.fixture(scope="module")
def reversal_runs():
    tables = synthetic.make_tables(0)
    world = World(**tables)
    runs = {c: simulator.run(World(**tables), Reversal(trade_from="2016-05-02"), "2016-04-01", "2016-12-30",
                             cost_bps=c) for c in (0.0, 5.0, 20.0)}
    return runs, simulator.replay(world, runs[5.0])


def test_replay_is_the_run_at_each_cost_exactly(reversal_runs):
    runs, rp = reversal_runs
    assert sorted(rp) == [0.0, 5.0, 10.0, 20.0]
    for c in (0.0, 5.0, 20.0):
        pd.testing.assert_frame_equal(rp[c], runs[c].equity)
    assert runs[5.0].equity.traded.sum() > 0
    assert rp[5.0].cost.sum() < rp[10.0].cost.sum() < rp[20.0].cost.sum() and rp[0.0].cost.sum() == 0.0


class FreezableReversal(Reversal):
    def freeze(self):
        return FreezableReversal(trade_from="2016-05-02")


def test_replay_of_a_frozen_twin_starts_on_its_own_first_session():
    tables = synthetic.make_tables(0)
    world = World(**tables)
    runs = {c: simulator.run_many(World(**tables), {"rev": FreezableReversal(trade_from="2016-05-02")},
                                  "2016-11-01", "2017-02-28", cost_bps=c, freeze=("rev",)) for c in (5.0, 20.0)}
    twin = runs[5.0]["rev_frozen_2016"]
    assert twin.equity.date.iloc[0] == pd.Timestamp("2017-01-03")  # the twin's first session
    rp = simulator.replay(world, twin, costs=(5.0, 20.0))
    pd.testing.assert_frame_equal(rp[5.0], twin.equity)
    pd.testing.assert_frame_equal(rp[20.0], runs[20.0]["rev_frozen_2016"].equity)
    pd.testing.assert_frame_equal(simulator.replay(world, runs[5.0]["rev"], costs=(20.0,))[20.0],
                                  runs[20.0]["rev"].equity)


def test_the_cost_table_and_the_book_table(reversal_runs):
    runs, rp = reversal_runs
    t = metrics.cost_table(rp, "2016-05-02", "2016-12-30")
    assert list(t.index) == ["0 bps", "5 bps", "10 bps", "20 bps"]
    assert t.loc["5 bps", "total"] == pytest.approx(stats.book_stats(
        metrics.book_returns(runs[5.0].equity, "2016-05-02", "2016-12-30").to_numpy())["total"])
    assert t["total"].is_monotonic_decreasing  # more cost, less return
    b = metrics.book_table({"rev": runs[5.0].equity}, "2016-05-02", "2016-12-30", before={"rev": rp[0.0]})
    assert b.loc["rev", "sharpe_before_costs"] > b.loc["rev", "sharpe_after_costs"]
    assert b.loc["rev", "sharpe_before_costs"] == pytest.approx(stats.book_stats(
        metrics.book_returns(runs[0.0].equity, "2016-05-02", "2016-12-30").to_numpy())["sharpe"])
    assert math.isnan(metrics.book_table({"rev": runs[5.0].equity}, None, None).loc["rev", "sharpe_before_costs"])


def test_beta_by_hand():
    mkt = series([0.01, -0.02, 0.005, 0.0, 0.015, -0.01])
    b = metrics.beta(2.0 * mkt + 0.001, mkt)
    assert b["beta"] == pytest.approx(2.0) and b["alpha_daily"] == pytest.approx(0.001) and b["days"] == 6
    spy = pd.DataFrame({"date": pd.to_datetime(["2017-01-03", "2017-01-04"]), "adj_open": [100.0, 101.0]})
    assert metrics.spy_open_returns(spy).to_numpy() == pytest.approx([0.01])


SECTORS = pd.DataFrame({"entity_id": ["A", "A", "B", "C"], "sector": ["Energy", "Utilities", "Energy", "Financials"],
                        "valid_from": pd.to_datetime(["2017-03-01", "2017-06-01", "2016-01-01", "2016-01-01"]),
                        "valid_to": pd.to_datetime(["2017-05-31", "2026-01-01", "2026-01-01", "2026-01-01"])})


def test_sectors_follow_each_date():
    p = pd.DataFrame({"entity_id": ["A", "A", "A", "B", "Z"],
                      "date": pd.to_datetime(["2017-01-03", "2017-04-03", "2017-07-03", "2017-01-03", "2017-01-03"])})
    # A before its first run takes its first sector; later its runs in turn; Z is never listed
    assert list(metrics.sectors_for(p, SECTORS)) == ["Energy", "Energy", "Utilities", "Energy", "Unknown"]


def test_sector_tilt_by_hand():
    d = pd.DataFrame({"date": pd.to_datetime(["2017-07-03"] * 3 + ["2017-07-04"] * 3),
                      "entity_id": ["A", "B", "C"] * 2, "share_class": ["X"] * 6, "prediction": [0.0] * 6,
                      "position": [0.5, -0.5, 0.0, 0.5, 0.0, -0.5]})
    t = metrics.sector_tilt(d, SECTORS)
    # day 1: Utilities +0.5, Energy -0.5; day 2: Utilities +0.5, Financials -0.5 (Energy 0)
    assert t.loc["Utilities", "mean_net"] == pytest.approx(0.5)
    assert t.loc["Energy", "mean_net"] == pytest.approx(-0.25) and t.loc["Energy", "mean_abs_net"] == 0.25
    assert t.loc["Financials", "mean_net"] == pytest.approx(-0.25)
    assert t.loc["all", "mean_net"] == pytest.approx(0.0) and t.loc["all", "mean_abs_net"] == pytest.approx(1.0)


def test_seed_spread_by_hand():
    ics = {"1": series([0.1, 0.3]), "2": series([0.0, 0.0]), "3": series([-0.1, 0.1])}
    t = metrics.seed_spread(ics, {}, None, None)
    assert list(t.index) == ["1", "2", "3", "min", "max", "mean", "std"]
    assert t.loc["max", "mean_ic"] == pytest.approx(0.2) and t.loc["min", "mean_ic"] == pytest.approx(0.0)
    # the seeds' means are 0.2, 0 and 0: mean 0.2 / 3; sample sd sqrt((0.1333^2 + 2 * 0.0667^2) / 2) = 0.2 / sqrt(3)
    assert t.loc["mean", "mean_ic"] == pytest.approx(0.2 / 3)
    assert t.loc["std", "mean_ic"] == pytest.approx(0.2 / 3 ** 0.5)


def test_regimes_by_hand():
    closes = [100, 102, 104, 103, 92, 91, 95, 106, 97, 96]
    days = pd.bdate_range("2017-01-02", periods=len(closes))
    spy = pd.DataFrame({"date": days, "adj_close": [float(c) for c in closes]})
    r = metrics.regimes(spy, days, trend_days=3, vol_days=2, fall=0.10, after=2)
    # trend on day i uses closes up to i - 1: day 3 (index 3) sees 104 against mean(100, 102, 104) = 102: up;
    # day 5 sees 92 against mean(104, 103, 92) = 99.67: down
    assert r.trend.iloc[:3].isna().all() and r.trend.iloc[3] == "up" and r.trend.iloc[5] == "down"
    # the peak 104 is first beaten by 10% at the close of 92 (day 4), so days 5 and 6 are after the shock; 106 is a
    # new high, and 97 and 96 are not 10% below it (95.4 is the line)
    assert list(r.shock) == ["none"] * 5 + ["after shock"] * 2 + ["none"] * 3
    assert r.vol.iloc[:3].isna().all() and set(r.vol.dropna()) <= {"high", "low"}
    # vol on day 3 sees the log returns of days 1 and 2 (0.019803, 0.019418): sd 0.000272; it is the first value, so it
    # is its own median: "low" (not above). Day 4 sees days 2 and 3 (0.0194, -0.0097): sd 0.0206, above the median
    # of (0.000272, 0.0206): "high"
    assert r.vol.iloc[3] == "low" and r.vol.iloc[4] == "high"


def test_regime_labels_use_no_later_close():
    rng = np.random.default_rng(3)
    closes = 100 * np.cumprod(1 + rng.normal(0, 0.02, 80))
    days = pd.bdate_range("2017-01-02", periods=80)
    spy = pd.DataFrame({"date": days, "adj_close": closes})
    later = spy.assign(adj_close=np.r_[closes[:50], closes[50:] * 0.5])  # a crash after day 49
    a = metrics.regimes(spy, days, trend_days=10, vol_days=5)
    b = metrics.regimes(later, days, trend_days=10, vol_days=5)
    pd.testing.assert_frame_equal(a.iloc[:51], b.iloc[:51])  # day 50 sees the close of day 49 only
    # a window that opens inside a fall still sees the earlier peak
    fall = pd.DataFrame({"date": days[:6], "adj_close": [100.0, 105.0, 99.0, 93.0, 92.0, 91.0]})
    w = metrics.regimes(fall, days[3:6], trend_days=2, vol_days=2, after=2)
    assert list(w.shock) == ["none", "after shock", "after shock"]  # 93 is first 10% below 105, seen on day 4


def test_regime_table_and_coefficient_life_by_hand():
    ic = series([0.1, 0.2, 0.3, 0.4])
    labels = pd.DataFrame({"trend": ["up", "up", "down", "down"]}, index=ic.index)
    t = metrics.regime_table(ic, ic * 0.01, labels).set_index("value")
    assert t.loc["up", "mean_ic"] == pytest.approx(0.15) and t.loc["down", "mean_ic"] == pytest.approx(0.35)
    tw = pd.Series([0.5, 0.1, 0.2, 0.3], index=pd.to_datetime(["2017-12-29", "2018-01-02", "2018-03-30",
                                                                "2018-04-02"]))
    c = metrics.coefficient_life({2017: tw})
    # quarter 1 since the end of 2017 is 2018 Q1 (0.1 and 0.2), quarter 2 is 2018 Q2; 2017's own day is left out
    assert list(c.quarter) == [1, 2] and c.mean_ic.iloc[0] == pytest.approx(0.15) and c.days.iloc[1] == 1


# The switch-day check (cutoff.md 10.2)

SESSIONS = Clock().between("2017-01-01", "2019-12-31")


def effects(first20, other, years=(2017, 2018, 2019), drop=()):
    """Live and price-only ICs whose difference is first20(i) on each year's first 20 sessions and other(i) after."""
    live, po = {}, {}
    for y in years:
        days = SESSIONS[SESSIONS.year == y]
        for i, d in enumerate(days):
            if d in drop:
                continue
            e = first20(i) if i < 20 else other(i)
            live[d], po[d] = 0.05 + e, 0.05
    return pd.Series(live), pd.Series(po)


def test_the_switch_day_difference_is_the_mean_of_first_20_days_minus_the_rest():
    live, po = effects(lambda i: 0.1 + 0.01 * (i % 3), lambda i: 0.02 * (i % 2))
    out = switch_day(live, po, SESSIONS, [2017, 2018, 2019])
    eff = (live - po)
    first = [d for y in (2017, 2018, 2019) for d in SESSIONS[SESSIONS.year == y][:20]]
    want = eff[eff.index.isin(first)].mean() - eff[~eff.index.isin(first)].mean()
    assert out["pooled"]["difference"] == pytest.approx(want)
    assert out["pooled"]["first20_days"] == 60 and out["pooled"]["other_days"] == len(eff) - 60
    X = np.column_stack([np.ones(len(eff)), eff.index.isin(first).astype(float)])
    assert out["pooled"]["se"] == pytest.approx(stats.nw_ols(eff.to_numpy(), X)[1][1])
    assert out["warning_a"] and out["warning_b"] and out["warning"] and out["years_counted"] == 3
    assert out["years"].above_by_two_se.all()


def test_no_switch_effect_gives_no_warning():
    rng = np.random.default_rng(0)
    live, po = effects(lambda i: rng.normal(0, 0.1), lambda i: rng.normal(0, 0.1))  # a new draw for every day
    out = switch_day(live, po, SESSIONS, [2017, 2018, 2019])
    assert out["pooled"]["p"] > 0.05 and not out["warning_a"]


def test_the_first_20_come_from_the_calendar_and_half_the_years_is_enough():
    # 2017's first 5 sessions have no prediction: its first 20 are still the calendar's, so only 15 count
    missing = set(SESSIONS[SESSIONS.year == 2017][:5])
    # a clear effect in 2018 only, pooled small: one year in three is under half, so no (b)
    live, po = effects(lambda i: 0.0, lambda i: 0.0, drop=missing)
    rng = np.random.default_rng(1)
    noise = pd.Series(rng.normal(0, 0.05, len(live)), index=live.index)
    big = live.index.isin(list(SESSIONS[SESSIONS.year == 2018][:20]))
    live = live + noise + np.where(big, 0.3, 0.0)
    out = switch_day(live, po, SESSIONS, [2017, 2018, 2019])
    y = out["years"].set_index("year")
    assert y.loc[2017, "first20_days"] == 15
    assert bool(y.loc[2018, "above_by_two_se"]) and int(y.above_by_two_se.sum()) == 1
    assert not out["warning_b"]
    # two of the three years counted are above: at least half, so (b)
    s4 = Clock().between("2016-01-01", "2019-12-31")
    big2 = live.index.isin(list(s4[s4.year == 2019][:20]))
    out2 = switch_day(live + np.where(big2, 0.3, 0.0), po, s4, [2017, 2018, 2019, 2016])
    assert out2["years_counted"] == 3  # 2016 has no days here, so it is not counted
    assert out2["warning_b"]


# Charts and the writer

def test_a_chart_is_an_svg_with_a_line_per_series(tmp_path):
    a = series([0.1, 0.2, np.nan, 0.3, 0.1])
    b = series([0.0, -0.1, 0.1, 0.2, 0.0])
    p = charts.lines({"a": a, "b": b}, "Test", tmp_path / "t.svg")
    text = Path(p).read_text(encoding="utf-8")
    assert text.startswith("<svg") and text.strip().endswith("</svg>")
    assert text.count("<polyline") == 2  # NaNs are dropped, so a has one line of 4 points
    assert ">a</text>" in text and ">b</text>" in text and ">2017</text>" in text
    assert charts.wealth(series([0.1, -0.5])).to_numpy() == pytest.approx([1.1, 0.55])


def fake_run(seed, days, ents, skill):
    """A made-up run: predictions that are skill times the made-up label plus noise, and an equity walk at 5 bps.
    Returns the Run and its equity rows at 0, 5, 10 and 20 bps (as sim.simulator.replay would)."""
    rng = np.random.default_rng(seed)
    rows = []
    for d in days:
        lab = LABELS[LABELS.date == d].set_index("entity_id").label
        pred = skill * lab.reindex(ents).to_numpy() + rng.normal(0, 0.01, len(ents))
        order = np.argsort(-pred)
        pos = np.zeros(len(ents))
        pos[order[:3]], pos[order[-3:]] = 1 / 3, -1 / 3
        rows.append(pd.DataFrame({"date": d, "entity_id": ents, "share_class": "X", "prediction": pred,
                                  "position": pos}))
    growth = rng.normal(0.0005, 0.01, len(days))
    by_cost = {}
    for c in (0.0, 5.0, 10.0, 20.0):
        e, eq = 1.0, []
        for d, g in zip(days, growth):
            pre = e * (1 + g)
            cost = 0.5 * pre * c / 1e4
            e = pre - cost
            eq.append({"date": d, "equity": e, "cost": cost, "gross": 2.0, "traded": 0.5 * pre})
        by_cost[c] = pd.DataFrame(eq)
    return Run(pd.concat(rows, ignore_index=True), by_cost[5.0], {}), by_cost


DAYS = Clock().between("2017-01-03", "2018-06-29")
ENTS = [f"E{i}" for i in range(12)]
_rng = np.random.default_rng(7)
LABELS = pd.DataFrame([{"date": d, "entity_id": e, "share_class": "X", "label": _rng.normal(0, 0.02)}
                       for d in DAYS for e in ENTS])


def test_the_report_writer_covers_every_section(tmp_path):
    made = {"live": fake_run(1, DAYS, ENTS, 1.0), "price_only": fake_run(2, DAYS, ENTS, 0.5),
            "placebo_1": fake_run(3, DAYS, ENTS, 0.0), "placebo_2": fake_run(4, DAYS, ENTS, 0.0),
            "random_1": fake_run(5, DAYS, ENTS, 0.0), "momentum": fake_run(6, DAYS, ENTS, 0.1),
            "reversal": fake_run(7, DAYS, ENTS, 0.1), "equal_weight": fake_run(8, DAYS, ENTS, 0.0),
            "live_long_only": fake_run(9, DAYS, ENTS, 1.0),
            "live_frozen_2017": fake_run(10, DAYS[DAYS.year == 2018], ENTS, 0.3)}
    runs = {n: m[0] for n, m in made.items()}
    hold_3, hold_3_costs = fake_run(12, DAYS, ENTS, 0.8)
    replays = {**{n: m[1] for n, m in made.items()}, "hold_3": hold_3_costs}
    spy_days = Clock().between("2016-01-04", "2018-06-29")
    walk = 100 * np.cumprod(1 + np.random.default_rng(11).normal(0.0003, 0.01, len(spy_days)))
    spy = pd.DataFrame({"date": spy_days, "adj_open": walk, "adj_close": walk * 1.001})
    sectors = pd.DataFrame({"entity_id": ENTS, "sector": ["Energy", "Utilities", "Financials"] * 4,
                            "valid_from": pd.Timestamp("2016-01-01"), "valid_to": pd.Timestamp("2026-01-01")})
    trials_csv = tmp_path / "trials.csv"
    trials_csv.write_text("run_id,logged_at,commit,dirty,settings_hash,first,last,agents,out_dir\n"
                          "r1,t,abc,False,h1,2017-01-03,2018-06-29,live,x\n"
                          "r2,t,abc,False,h2,2017-01-03,2018-06-29,hold_3,y\n", encoding="utf-8")
    out = report.write(tmp_path / "report.md", charts_dir=tmp_path / "charts", runs=runs, labels=LABELS, spy=spy,
                       sectors=sectors, sessions=Clock().between("2017-01-01", "2018-12-31"), first="2017-01-03",
                       last="2018-06-29", run_bps=5.0, trials_csv=trials_csv, replays=replays,
                       variants={"hold_3": hold_3})
    text = Path(out).read_text(encoding="utf-8")
    for heading in ["## Trials", "## Daily rank IC by quarter", "## Frozen-twin gaps", "## Reading", "## Matched "
                    "baselines", "## Variants", "## Costs", "## Exposures", "## Deflated Sharpe", "## Seed spread",
                    "## Regimes and shocks", "## Coefficient life", "## The switch-day check", "## Charts"]:
        assert heading in text, heading
    for row in ["| 2017Q1 |", "| end of 2017 | 2018 |", "| placebo_2 |", "| cash |", "| spy_buy_and_hold |",
                "| hold_3 |", "| 20 bps |", "| Utilities |", "2 trials"]:
        assert row in text, row
    # the live book's Sharpe before costs is its 0 bps rows'
    gross = stats.book_stats(metrics.book_returns(replays["live"][0.0], "2017-01-03", "2018-06-29").to_numpy())
    line = next(x for x in text.splitlines() if x.startswith("| live |"))
    assert f"{gross['sharpe']:.4f}" in line
    assert "\u2014" not in text
    assert "Sharpe ratios are over zero, no cash rate" in text
    root = Path(__file__).resolve().parents[1]
    assert report.CHARTS.is_relative_to(report.DATA_DIR) and not report.CHARTS.resolve().is_relative_to(root)
    assert sorted(p.name for p in (tmp_path / "charts").iterdir()) == [
        "costs.svg", "equity_long_only.svg", "equity_long_short.svg", "ic.svg", "twin_gaps.svg"]
    ic = metrics.daily_rank_ic(runs["live"].decisions, LABELS)
    want = metrics.ic_by_quarter(ic, "2017-01-03", "2018-06-29").loc["2017Q1", "mean"]
    assert f"| 2017Q1 | {stats.nw_mean(ic.loc[:'2017-03-31'].to_numpy())['n']} | {want:.4f} |" in text
