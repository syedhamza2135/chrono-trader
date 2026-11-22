"""M3 step 3: Track A's agent (agent/track_a.py). Each feature against a hand computation, the learner's algebra,
the label embargo, the same output twice, and non-interference on the made-up world and on the real store with
embeddings. The import boundary is tests/test_boundaries.py, which checks every file in agent/."""
import hashlib
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from agent.track_a import PENALTIES, PRICE, Sums, TrackA, _ic, _solve  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from eval import leaks  # noqa: E402
from world.view import View  # noqa: E402
from world.world import Embeddings, World  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASE = synthetic.make_tables(0)
TABLES = {**BASE, "embeddings": synthetic.make_embeddings(BASE)}
UTC = "UTC"
STORE = DATA_DIR / "store"
needs_store = pytest.mark.skipif(not (STORE / "embeddings.parquet").exists(), reason="no embeddings table yet")


def nine(day):
    return pd.Timestamp(day).tz_localize("America/New_York").tz_convert(UTC) + pd.Timedelta(hours=9)


def sessions(first, last):
    return pd.DatetimeIndex(pd.bdate_range(first, last))


# A hand-made view

def bars_of(entity, days, ret, close, volume, incomplete=None):
    n = len(days)
    return pd.DataFrame({"entity_id": entity, "share_class": "", "symbol": entity, "date": days, "open": close,
                         "high": close, "low": close, "close": close, "volume": volume, "trades": 1, "vwap": close,
                         "ret": ret, "incomplete": incomplete if incomplete is not None else [False] * n,
                         "member": True, "no_trade": False, "visible_at": [nine(d) for d in days]})


def embeddings_of(rows, last, avg):
    r = pd.DataFrame(rows, columns=["story_id", "visible_at"])
    r = r.assign(vintage_year=2016, available_at=r.visible_at)[["story_id", "vintage_year", "available_at",
                                                                  "visible_at"]]
    return Embeddings(r, np.asarray(last, np.float16), np.asarray(avg, np.float16))


def view(today, days, bars, se=None, emb=None, members=("A", "B")):
    t = nine(today)
    se = se if se is not None else pd.DataFrame({"story_id": pd.Series(dtype="int64"), "entity_id": pd.Series(dtype=str),
                                                 "visible_at": pd.Series(dtype="datetime64[ns, UTC]")})
    return View(t, days, frozenset(members), frozenset(members), bars, bars.iloc[:0].assign(label=0.0), bars.iloc[:0],
                se, emb if emb is not None else Embeddings.empty(2))


def test_price_features_match_a_hand_computation():
    days = sessions("2016-01-04", "2016-06-30")
    today = days[-1]
    past = days[days < today]
    n = len(past)
    ret = np.array([0.01 * ((i % 7) - 3) for i in range(n)], dtype=float)
    ret[n - 3] = np.nan  # a missing return is skipped
    close = 10 + np.arange(n, dtype=float)
    volume = 1000 + 10 * np.arange(n, dtype=float)
    incomplete = [False] * n
    incomplete[n - 2] = True  # an incomplete bar counts as missing for volume
    b = bars_of("A", past, ret, close, volume, incomplete)
    b = pd.concat([b, bars_of("A", [today], [0.5], [99.0], [1e9])])  # today's bar must be ignored
    got = TrackA().price_features(view(today, days, b), [("A", ""), ("B", "")])
    # the hand computation, from the inputs above
    r = [math.log(1 + x) for x in ret if not math.isnan(x)]
    want = {"r1": sum(r[-1:]), "r5": sum(r[-5:]), "r20": sum(r[-20:]), "r60": sum(r[-60:]),
            "vol20": float(np.std(r[-20:]))}
    dv = [c * v for c, v, bad in zip(close, volume, incomplete)]
    last5 = [x for x, bad in zip(dv[-5:], incomplete[-5:]) if not bad]
    last60 = [x for x, bad in zip(dv[-60:], incomplete[-60:]) if not bad]
    want["dvol_ratio"] = math.log((sum(last5) / len(last5)) / (sum(last60) / len(last60)))
    assert got.shape == (2, len(PRICE))
    for k, name in enumerate(PRICE):
        assert got[0, k] == pytest.approx(want[name], rel=1e-12, abs=1e-15), name
    assert np.isnan(got[1]).all()  # B has no bars: missing, counted as the mean once scaled


def test_bars_older_than_200_days_are_left_out():
    days = sessions("2015-01-01", "2016-06-30")
    today = days[-1]
    past = days[days < today]
    ret = np.where(past < today - pd.Timedelta(days=200), 1.0, 0.0)
    b = bars_of("A", past, ret, np.ones(len(past)), np.ones(len(past)))
    got = TrackA().price_features(view(today, days, b), [("A", "")])
    assert got[0, PRICE.index("r60")] == 0.0


def news_world():
    """Decisions on Monday 2 May and Tuesday 3 May 2016. A gets story 1 on Friday before 9:00 (so it is one session
    old on Monday, and not new) and story 2 on Monday, story 3 before Tuesday's decision. Story 4's embedding shows on
    Monday, but its link to B only before Tuesday's decision."""
    days = sessions("2016-04-25", "2016-05-04")
    se = pd.DataFrame({"story_id": [1, 2, 3, 4], "entity_id": ["A", "A", "A", "B"],
                       "visible_at": [nine("2016-04-29") - pd.Timedelta(hours=1), nine("2016-05-02") - pd.Timedelta(hours=1),
                                      nine("2016-05-03") - pd.Timedelta(hours=2), nine("2016-05-03") - pd.Timedelta(hours=3)]})
    emb_rows = [(1, se.visible_at[0]), (2, se.visible_at[1]), (4, nine("2016-05-02") - pd.Timedelta(hours=5)),
                (3, se.visible_at[2])]
    last = [[1.0, 0.0], [3.0, 2.0], [7.0, 7.0], [5.0, -1.0]]
    avg = [[2.0, 2.0], [4.0, 0.0], [1.0, 1.0], [6.0, 6.0]]
    return days, se, emb_rows, last, avg


def views_of_news_world():
    days, se, emb_rows, last, avg = news_world()
    b = pd.concat([bars_of(e, days[:1], [0.0], [1.0], [1.0]) for e in ("A", "B")])
    out = []
    for d in (pd.Timestamp("2016-05-02"), pd.Timestamp("2016-05-03")):
        t = nine(d)
        keep = [i for i, (s, at) in enumerate(emb_rows) if at <= t]
        e = embeddings_of([emb_rows[i] for i in keep], [last[i] for i in keep], [avg[i] for i in keep])
        out.append(view(d, days[days <= d], b, se[se.visible_at <= t].reset_index(drop=True), e))
    return out


def test_news_features_match_a_hand_computation():
    v1, v2 = views_of_news_world()
    a = TrackA()
    picks = [("A", ""), ("B", "")]
    f1 = a.news_features(v1, picks, a.update_news(v1))
    a.last_t = v1.t
    f2 = a.news_features(v2, picks, a.update_news(v2))
    d = 0.5 ** (1 / 5)
    # Decision 1: stories 1 (age 1: it became available before Friday's 9:00) and 2 (age 0) for A.
    # Only story 2 is new. B has nothing (story 4's link isn't in the view yet).
    a1 = f1["last"][0]
    assert a1[0] == 1 and a1[1] == 0  # news_count, news_none
    assert a1[2:4] == pytest.approx([3.0, 2.0])  # news_new: story 2 alone
    w1, w2 = d ** 1, 1.0
    assert a1[4:6] == pytest.approx([(w1 * 1 + w2 * 3) / (w1 + w2), (w1 * 0 + w2 * 2) / (w1 + w2)])
    assert list(f1["last"][1]) == [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    # Decision 2: story 3 is new for A; story 4 is new for B (its link arrived), with its embedding from before.
    a2, b2 = f2["avg"][0], f2["avg"][1]
    assert a2[0] == 1 and a2[2:4] == pytest.approx([6.0, 6.0])  # story 3's avg vector
    ws = [d ** 2, d ** 1, 1.0]  # stories 1, 2, 3 at the second decision
    assert a2[4:6] == pytest.approx([(ws[0] * 2 + ws[1] * 4 + ws[2] * 6) / sum(ws),
                                     (ws[0] * 2 + ws[1] * 0 + ws[2] * 6) / sum(ws)])
    assert b2[0] == 1 and b2[2:4] == pytest.approx([1.0, 1.0]) and b2[4:6] == pytest.approx([1.0, 1.0])


def test_the_memory_kept_day_by_day_equals_the_memory_started_from_the_view():
    """The running memory after two decisions equals one started on the second view alone."""
    v1, v2 = views_of_news_world()
    a = TrackA()
    a.update_news(v1)
    a.last_t = v1.t
    a.update_news(v2)
    b = TrackA()
    b.update_news(v2)
    for ent in ("A", "B"):
        for k in range(3):
            assert np.allclose(a.memory[ent][k], b.memory[ent][k], rtol=1e-12)


def test_the_target_is_the_log_label_minus_the_days_mean():
    a = TrackA()
    day = pd.Timestamp("2016-05-02")
    days = sessions("2016-05-02", "2016-05-04")
    keys = pd.DataFrame({"entity_id": ["A", "B", "C"], "share_class": ""})
    X = {"none": np.arange(6, dtype=float).reshape(3, 2)}
    a.pending = [(day, keys, X)]
    labels = pd.DataFrame({"entity_id": ["A", "B", "C"], "share_class": "", "date": day, "label": [0.1, -0.05, 0.02],
                           "visible_at": nine("2016-05-03") + pd.Timedelta(minutes=30)})
    v = View(nine("2016-05-04"), days, frozenset(), frozenset(), labels.iloc[:0], labels, labels.iloc[:0],
             labels.iloc[:0], Embeddings.empty(0))
    a.settle(v)
    y = np.log1p([0.1, -0.05, 0.02])
    assert a.recent[0][1] == pytest.approx(y - y.mean())
    assert a.sums["none"].n == 3 and a.latest_label == labels.visible_at[0]


# The learner's algebra

def test_the_sums_give_the_standardized_ridge():
    rng = np.random.default_rng(1)
    X, y = rng.normal(2, 3, (200, 5)), rng.normal(0, 1, 200)
    X[:, 4] = 7.0  # a constant feature gets a deviation of 1
    s = Sums(5)
    s.add(X[:120], y[:120])
    s.add(X[120:], y[120:])
    mean, std, zz, zy = s.scaled()
    sd = X.std(axis=0)
    sd[4] = 1.0
    Z = (X - X.mean(axis=0)) / sd
    assert mean == pytest.approx(X.mean(axis=0)) and std == pytest.approx(sd)
    for lam, beta in _solve(zz, zy, PENALTIES).items():
        direct = np.linalg.solve(Z.T @ Z + lam * np.eye(5), Z.T @ (y - y.mean()))
        assert beta == pytest.approx(direct, rel=1e-8, abs=1e-10)
    part = s.minus(X[150:], y[150:])
    ref = Sums(5)
    ref.add(X[:150], y[:150])
    for a, b in zip(part.scaled(), ref.scaled()):
        assert np.allclose(a, b, rtol=1e-9, atol=1e-9)


def test_the_validation_score_is_the_mean_daily_rank_ic():
    pred = np.array([1, 2, 3, 3, 2, 1, 5, 5, 5], dtype=float)
    y = np.array([1, 2, 3, 1, 2, 3, 1, 2, 3], dtype=float)
    day = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2])
    assert _ic(pred, y, day) == pytest.approx(0.0)  # +1, -1, and a day with no spread left out


def run_on(tables, agent, first, last, window=90):
    world = World(**tables, embedding_window_days=window)
    for day in world.clock.between(first, last):
        agent.decide(world.view(world.clock.decision_time(day)))
    return agent


def test_the_validation_part_and_the_gap_are_left_out_of_training(monkeypatch):
    """Each refit's training sums are the full sums minus exactly the gap day and the validation days."""
    seen = []
    real = Sums.minus

    def spy(self, X, y):
        seen.append(len(y))
        return real(self, X, y)

    monkeypatch.setattr(Sums, "minus", spy)
    a = run_on(TABLES, TrackA(fit_after_months=3), "2016-04-01", "2017-03-15")
    assert a.fits
    per_fit = len(a.poolings)
    for k, f in enumerate(a.fits):
        assert seen[k * per_fit:(k + 1) * per_fit] == [f["held_rows"]] * per_fit  # judge S4: exactly those rows
        assert f["gap_days"] >= 1
    assert all(f["val_days"] >= 55 for f in a.fits)  # at least 3 months of sessions


def block(day, label_at):
    return (pd.Timestamp(day), np.zeros(2), {"none": np.zeros((2, 1))}, pd.Timestamp(label_at, tz=UTC))


def test_the_split_holds_out_the_day_before_validation_and_any_late_label():
    """Judge S1: a training day whose label showed at or after the first validation decision is held out too."""
    a = TrackA()
    a.recent = [block("2016-05-02", "2016-05-03 13:31"), block("2016-05-03", "2016-05-04 13:31"),
                block("2016-05-04", "2016-05-09 13:31"),  # its end open came late: shows after 9:00 on 5 May
                block("2016-05-05", "2016-05-06 13:31"), block("2016-05-06", "2016-05-09 13:31"),
                block("2016-05-09", "2016-05-10 13:31")]
    gap, val, first, latest = a.split(2)
    assert [r[0].day for r in val] == [6, 9] and first == nine("2016-05-06")
    assert [r[0].day for r in gap] == [4, 5]  # the late label, and the day just before validation
    assert latest == pd.Timestamp("2016-05-04 13:31", tz=UTC) and latest < first


# The label embargo

def test_every_training_label_was_realized_before_the_refit_that_used_it():
    a = run_on(TABLES, TrackA(fit_after_months=3), "2016-04-01", "2017-06-29")
    assert len(a.fits) >= 8
    assert all(f["latest_label"] is not None and f["latest_label"] <= f["t"] for f in a.fits)
    # and at the validation boundary (judge S3): every training label showed before the first validation decision
    assert all(f["train_latest_label"] is not None and f["train_latest_label"] < f["first_val_t"] for f in a.fits)


def test_nothing_is_fitted_before_six_lived_months_and_2016_is_watch_only():
    world = World(**TABLES)
    a = TrackA()
    out = {}
    for day in world.clock.between("2016-04-01", "2017-01-31"):
        out[day] = a.decide(world.view(world.clock.decision_time(day)))
    assert a.fits[0]["t"] >= nine("2016-10-01")
    fitted = [d for d, x in out.items() if x is not None]
    assert min(fitted) >= pd.Timestamp("2016-10-03")
    assert all((out[d].position == 0).all() for d in fitted if d < pd.Timestamp("2017-01-01"))
    jan = [out[d] for d in fitted if d >= pd.Timestamp("2017-01-01")]
    assert jan and all((x.position > 0).sum() == 10 and (x.position < 0).sum() == 10 for x in jan)
    assert all(x.position.sum() == pytest.approx(0.0, abs=1e-12) for x in jan)


# The policy

def test_the_policy_ranks_holds_and_bands():
    keys = [(f"E{i}", "") for i in range(30)]
    pred = np.arange(30, dtype=float)[::-1]  # E0 best
    a = TrackA(n_side=3, band=5)
    pos = a.targets(keys, pred)
    assert [k for k in keys if pos[k] > 0] == keys[:3] and [k for k in keys if pos[k] < 0] == keys[-3:]
    a.positions = pos
    pred2 = pred.copy()
    pred2[0] = 25.5  # E0 falls to rank 3 (from 0): inside the band of 5, so it stays long and E3 waits
    pred2[3] = 100.0
    pos2 = a.targets(keys, pred2)
    assert [k for k in keys if pos2[k] > 0] == keys[:3]
    pred3 = pred2.copy()
    pred3[0] = 23.5  # now rank 5: outside the band, so E3 takes its place
    pos3 = a.targets(keys, pred3)
    assert [k for k in keys if pos3[k] > 0] == [keys[1], keys[2], keys[3]]
    lo = TrackA(n_side=3, book="long_only").targets(keys, pred)
    assert sum(v > 0 for v in lo.values()) == 3 and not any(v < 0 for v in lo.values())


def test_a_longer_hold_trades_every_hold_sessions():
    a = run_on(TABLES, TrackA(fit_after_months=3, min_val_months=1, hold=3, trade_from="2016-01-01"), "2016-04-01",
               "2016-08-31")
    world = World(**TABLES)
    b = TrackA(fit_after_months=3, min_val_months=1, hold=3, trade_from="2016-01-01")
    held = []
    for day in world.clock.between("2016-04-01", "2016-09-30"):
        d = b.decide(world.view(world.clock.decision_time(day)))
        if d is not None:
            held.append(dict(zip(d.entity_id, d.position)))
    assert a.fits and len(held) > 9
    changes = [i for i in range(1, len(held)) if held[i] != {k: held[i - 1].get(k, 0.0) for k in held[i]}]
    assert changes and all(c % 3 == 0 for c in changes)


# The same output twice

SCRIPT = """
import sys, hashlib
sys.path.insert(0, r"{root}"); sys.path.insert(0, r"{tests}")
import synthetic
from agent.track_a import TrackA
from eval import leaks
T = synthetic.make_tables(0); T = {{**T, "embeddings": synthetic.make_embeddings(T)}}
d = leaks.decisions_until(T, lambda: TrackA(fit_after_months=3), "2016-04-01", "2017-02-28")
print(len(d), hashlib.sha256(d.to_csv(float_format="%.17g").encode()).hexdigest())
"""


def test_the_same_output_twice_with_one_blas_thread_and_a_fixed_hash_seed():
    """PLAN 9.7's settings, twice; and once with another hash seed, which shows no set or dict order matters
    (judge S5)."""
    code = SCRIPT.format(root=ROOT, tests=ROOT / "tests")
    outs = []
    for seed in ("0", "0", "1"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
               "MKL_NUM_THREADS": "1"}
        outs.append(subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                                   check=True).stdout)
    assert outs[0] == outs[1] == outs[2] and int(outs[0].split()[0]) > 1000


# Non-interference

def track(**kw):
    return lambda: TrackA(fit_after_months=2, min_val_months=1, **kw)


@pytest.mark.parametrize("how", leaks.HOW)
def test_non_interference_on_the_made_up_world(how):
    for make in (track(), track(news=False), track(hold=3, band=15)):
        assert leaks.non_interference(TABLES, make, "2016-10-03", "2017-03-15", how, seed=2) == []


def test_the_made_up_run_reads_the_news_and_fits():
    a = leaks.decisions_until(TABLES, track(), "2016-10-03", "2017-03-15")
    b = leaks.decisions_until(TABLES, track(news=False), "2016-10-03", "2017-03-15")
    assert len(a) > 500 and leaks.compare(a, b)


@pytest.fixture(scope="module")
def real_news_tables():
    from test_embedding_window import real_tables_with_embeddings
    return real_tables_with_embeddings("2017-04-01")


@needs_store
def test_on_the_real_store_track_a_reads_the_news_and_fits(real_news_tables):
    a = leaks.decisions_until(real_news_tables, track(), "2016-11-01", "2017-02-15")
    b = leaks.decisions_until(real_news_tables, track(news=False), "2016-11-01", "2017-02-15")
    assert len(a) > 200 and leaks.compare(a, b)


@needs_store
@pytest.mark.parametrize("how", leaks.HOW)
def test_non_interference_on_the_real_store_with_embeddings(real_news_tables, how):
    assert leaks.non_interference(real_news_tables, track(), "2016-11-01", "2017-02-15", how, seed=7) == []
