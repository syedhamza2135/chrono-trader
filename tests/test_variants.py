"""M3 step 6: the dev variants. T02 (averaged coefficients), T03 (recency weighting) and the baselines that hold as
long as the chosen trial, each against a hand-worked case, and each passing non-interference on the made-up world."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from agent.baselines import EqualWeight, Momentum, RandomRanking, Reversal  # noqa: E402
from agent.track_a import Sums, TrackA  # noqa: E402
from eval import leaks  # noqa: E402
from sim import simulator  # noqa: E402
from test_track_a import nine, sessions  # noqa: E402
from world.view import View  # noqa: E402
from world.world import Embeddings, World  # noqa: E402

BASE = synthetic.make_tables(0)
TABLES = {**BASE, "embeddings": synthetic.make_embeddings(BASE)}


def track(**kw):
    return TrackA(fit_after_months=2, min_val_months=1, **kw)


# Recency weighting (T03)

def test_weighted_and_decayed_sums_by_hand():
    # rows x = 1 (y = 1), then x = 2 (y = 3) a lived day later, with the first row's weight halved:
    # n = 0.5 + 1, sum x = 0.5 + 2, sum x^2 = 0.5 + 4, sum y = 0.5 + 3, sum xy = 0.5 + 6
    s = Sums(1)
    s.add(np.array([[1.0]]), np.array([1.0]))
    s.decay(0.5)
    s.add(np.array([[2.0]]), np.array([3.0]))
    assert (s.n, s.sx[0], s.sxx[0, 0], s.sy, s.sxy[0]) == pytest.approx((1.5, 2.5, 4.5, 3.5, 6.5))
    w = Sums(1)
    w.add(np.array([[1.0], [2.0]]), np.array([1.0, 3.0]), w=[0.5, 1.0])
    assert (w.n, w.sx[0], w.sxx[0, 0], w.sy, w.sxy[0]) == pytest.approx((1.5, 2.5, 4.5, 3.5, 6.5))
    # taking the first row out at its weight leaves the second alone
    m = s.minus(np.array([[1.0]]), np.array([1.0]), w=[0.5])
    assert (m.n, m.sx[0], m.sxx[0, 0], m.sy, m.sxy[0]) == pytest.approx((1.0, 2.0, 4.0, 3.0, 6.0))
    # weighted standardization: mean 2.5 / 1.5, variance 4.5 / 1.5 - (2.5 / 1.5)^2
    mean, std, _, _ = s.scaled()
    assert mean[0] == pytest.approx(2.5 / 1.5) and std[0] == pytest.approx(np.sqrt(3.0 - (2.5 / 1.5) ** 2))


def settled(agent):
    """Two lived days of 3 rows each, settled together, as in test_track_a's target test."""
    d1, d2 = pd.Timestamp("2016-05-02"), pd.Timestamp("2016-05-03")
    days = sessions("2016-05-02", "2016-05-05")
    keys = pd.DataFrame({"entity_id": ["A", "B", "C"], "share_class": ""})
    agent.pending = [(d1, keys, {"none": np.ones((3, 2))}), (d2, keys, {"none": 2 * np.ones((3, 2))})]
    labels = pd.concat([pd.DataFrame({"entity_id": ["A", "B", "C"], "share_class": "", "date": d,
                                      "label": [0.1, -0.05, 0.02], "visible_at": nine("2016-05-04")})
                        for d in (d1, d2)], ignore_index=True)
    v = View(nine("2016-05-05"), days, frozenset(), frozenset(), labels.iloc[:0], labels, labels.iloc[:0],
             labels.iloc[:0], Embeddings.empty(0))
    agent.settle(v)
    return agent


def test_recency_weighting_halves_a_day_every_half_life_by_hand():
    a = settled(TrackA(news=False, half_life_days=1))
    # with a half-life of 1 lived day, day 1's rows weigh 0.5 once day 2 is in: n = 3 * 0.5 + 3, sum of x = 3 * 0.5
    # * 1 + 3 * 2 per feature
    assert a.sums["none"].n == pytest.approx(4.5) and a.sums["none"].sx == pytest.approx([7.5, 7.5])
    assert [r[4] for r in a.recent] == [0, 1] and a.lived_days == 2
    assert a._weights(a.recent) == pytest.approx([0.5] * 3 + [1.0] * 3)
    b = settled(TrackA(news=False))
    assert b.sums["none"].n == 6 and b._weights(b.recent) is None


def test_a_very_long_half_life_gives_the_base_agent():
    runs = simulator.run_many(World(**TABLES), {"base": track(), "long": track(half_life_days=1e15)},
                              "2016-04-01", "2017-02-28")
    a, b = runs["base"].decisions, runs["long"].decisions
    assert len(a) == len(b) > 0 and (a.position.to_numpy() == b.position.to_numpy()).all()
    assert np.abs(a.prediction.to_numpy() - b.prediction.to_numpy()).max() < 1e-9


# Averaged coefficients (T02)

def fit(beta):
    return {"pooling": "none", "penalty": 1.0, "mean": np.zeros(2), "std": np.ones(2), "beta": np.array(beta)}


def test_averaged_coefficients_average_the_fits_predictions_by_hand():
    X = {"none": np.array([[2.0, 4.0], [1.0, -1.0]])}
    a = TrackA(news=False, coefficients="averaged")
    a.past, a.fit = [fit([1.0, 0.0]), fit([0.0, 1.0])], fit([0.0, 1.0])
    # fit 1 predicts x1: 2 and 1; fit 2 predicts x2: 4 and -1; their means are 3 and 0
    assert a.score(X) == pytest.approx([3.0, 0.0])
    b = TrackA(news=False)
    b.fit = fit([0.0, 1.0])
    assert b.score(X) == pytest.approx([4.0, -1.0])  # the base scores with its latest fit only
    with pytest.raises(ValueError):
        TrackA(coefficients="mean")


def test_averaged_coefficients_keep_every_fit_and_the_twin_copies_them():
    agent = track(coefficients="averaged")
    simulator.run_many(World(**TABLES), {"avg": agent}, "2016-04-01", "2017-02-28")
    assert len(agent.past) == len(agent.fits) >= 3
    assert agent.past[-1] is agent.fit
    twin = agent.freeze()
    assert len(twin.past) == len(agent.past) and twin.past[0]["beta"] is not agent.past[0]["beta"]
    twin.past[0]["beta"][:] = 0.0
    assert agent.past[0]["beta"].any()  # nothing shared


# Baselines that hold (matched to the chosen trial's hold)

def test_a_baseline_with_hold_3_trades_every_third_session():
    runs = simulator.run_many(World(**BASE), {"h1": Reversal(trade_from="2016-05-02"),
                                              "h3": Reversal(trade_from="2016-05-02", hold=3)},
                              "2016-04-01", "2016-06-30")
    d1, d3 = runs["h1"].decisions, runs["h3"].decisions
    assert (d1.prediction.to_numpy() == d3.prediction.to_numpy()).all()  # it still scores every day
    pos = d3[d3.date >= "2016-05-02"].pivot(index="date", columns="entity_id", values="position").fillna(0.0)
    p1 = d1[d1.date >= "2016-05-02"].pivot(index="date", columns="entity_id", values="position").fillna(0.0)
    days = list(pos.index)
    for i, d in enumerate(days):
        start = days[i - i % 3]  # trades on sessions 0, 3, 6, ... from the first trading day
        assert (pos.loc[d].to_numpy() == p1.loc[start].to_numpy()).all(), d
    assert (d3[d3.date < "2016-05-02"].position == 0).all()
    with pytest.raises(ValueError):
        Momentum(hold=0)


# Non-interference on the made-up world

MAKERS = {"averaged": lambda: track(coefficients="averaged"), "recency": lambda: track(half_life_days=252),
          "momentum_hold_3": lambda: Momentum(hold=3), "random_hold_5": lambda: RandomRanking(1, hold=5),
          "equal_weight": EqualWeight}


@pytest.mark.parametrize("how", leaks.HOW)
@pytest.mark.parametrize("name", list(MAKERS))
def test_non_interference_for_each_variant(name, how):
    assert leaks.non_interference(TABLES, MAKERS[name], "2016-10-03", "2017-03-15", how, seed=4) == []
