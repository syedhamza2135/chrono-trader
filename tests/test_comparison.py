"""M3 step 4: the comparison harness. The frozen twins, the price-only twin, the shuffled-news placebo, the baselines,
the one-pass loop (sim.simulator.run_many), SPY buy-and-hold and the trial ledger. Every agent here passes
non-interference."""
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from agent.baselines import EqualWeight, Momentum, RandomRanking, Reversal  # noqa: E402
from agent.placebo import Placebo, shuffled_links  # noqa: E402
from agent.track_a import TrackA  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from eval import leaks, trials  # noqa: E402
from eval.benchmarks import spy_buy_and_hold  # noqa: E402
from sim import simulator  # noqa: E402
from test_track_a import bars_of, nine, sessions, view  # noqa: E402
from world.clock import Clock  # noqa: E402
from world.world import World  # noqa: E402

BASE = synthetic.make_tables(0)
TABLES = {**BASE, "embeddings": synthetic.make_embeddings(BASE)}
FIRST, LAST = "2016-04-01", "2017-03-15"
STORE = DATA_DIR / "store"
needs_store = pytest.mark.skipif(not (STORE / "embeddings.parquet").exists(), reason="no embeddings table yet")


def track(**kw):
    return TrackA(fit_after_months=2, min_val_months=1, **kw)


def agents():
    return {"live": track(), "price_only": track(news=False), "placebo_1": Placebo(track(), 1),
            "random_1": RandomRanking(1), "momentum": Momentum(), "reversal": Reversal(), "equal": EqualWeight()}


@pytest.fixture(scope="module")
def together():
    calls = []
    world = World(**TABLES)
    real = world.view
    world.view = lambda t: (calls.append(t), real(t))[1]
    runs = simulator.run_many(world, agents(), FIRST, LAST, freeze=("live",))
    return runs, calls


# One pass

def test_one_pass_builds_each_view_once(together):
    runs, calls = together
    n = len(Clock().between(FIRST, LAST))
    assert len(calls) == n == len(set(calls))
    assert set(runs) == set(agents()) | {"live_frozen_2016"}


@pytest.mark.parametrize("name", list(agents()))
def test_one_pass_gives_each_agent_the_run_it_gets_alone(together, name):
    runs, _ = together
    alone = simulator.run(World(**TABLES), agents()[name], FIRST, LAST)
    pd.testing.assert_frame_equal(runs[name].decisions, alone.decisions)
    pd.testing.assert_frame_equal(runs[name].equity, alone.equity)
    assert len(alone.decisions) > 0


class Mutator:
    """An agent that tries to change the view it is handed."""
    params = None

    def __init__(self):
        self.refused = 0

    def decide(self, v):
        v.bars["ret"] = 0.0
        v.story_entities["entity_id"] = "E00"
        try:
            v.embeddings.last[:] = 0
        except ValueError:
            self.refused += 1
        return None


def test_an_agent_that_changes_its_view_changes_no_other_agents_run():
    m = Mutator()
    runs = simulator.run_many(World(**TABLES), {"mutator": m, "live": track()}, "2016-10-03", "2017-01-31")
    alone = simulator.run(World(**TABLES), track(), "2016-10-03", "2017-01-31")
    pd.testing.assert_frame_equal(runs["live"].decisions, alone.decisions)
    assert m.refused == len(Clock().between("2016-10-03", "2017-01-31"))


# The frozen twins

def test_the_frozen_twin_is_the_live_agent_at_the_year_end_with_learning_off(together):
    runs, _ = together
    live = track()
    world = World(**TABLES)
    for day in world.clock.between(FIRST, "2016-12-30"):
        live.decide(world.view(world.clock.decision_time(day)))
    twin = live.freeze()
    assert twin.learning is False and twin.pending == [] and twin.recent == [] and twin.sums is None
    assert twin.fit is not live.fit and np.array_equal(twin.fit["beta"], live.fit["beta"])
    n_fits = len(twin.fits)
    alone = simulator.run(world, twin, "2017-01-03", LAST)
    assert len(twin.fits) == n_fits  # it never refit
    assert np.array_equal(twin.fit["beta"], live.fit["beta"])  # the live agent's December fit, unchanged
    pd.testing.assert_frame_equal(runs["live_frozen_2016"].decisions, alone.decisions)
    assert runs["live_frozen_2016"].decisions.date.min() == pd.Timestamp("2017-01-03")
    assert leaks.compare(runs["live_frozen_2016"].decisions,
                         runs["live"].decisions[runs["live"].decisions.date >= "2017-01-03"])  # the live one learned


class TwinAfter:
    """For the leak check: the live agent until `at`, then its frozen twin."""

    def __init__(self, at):
        self.live, self.at, self.twin = track(), pd.Timestamp(at), None
        self.params = None

    def decide(self, v):
        if self.twin is None and v.today >= self.at:
            self.twin = self.live.freeze()
        return (self.twin or self.live).decide(v)


# The price-only twin and the placebo

def test_the_price_only_twin_reads_no_news(together):
    runs, _ = together
    twin = track(news=False)
    assert twin.poolings == ("none",)
    assert leaks.compare(runs["price_only"].decisions, runs["live"].decisions)


def groups_of(v):
    """For each embedded link (story_entities row), the session it first reaches, found independently: the first
    session whose 9:00 New York is at or after the later of its link's and its embedding's visible_at."""
    emb = v.embeddings.rows.set_index("story_id").visible_at
    out = {}
    for i, r in v.story_entities.reset_index(drop=True).iterrows():
        if r.story_id not in emb.index:
            continue
        avail = max(r.visible_at, emb[r.story_id])
        out[i] = next(s for s in v.sessions if nine(s) >= avail) if nine(v.sessions[-1]) >= avail else v.sessions[-1]
    return out


@pytest.mark.parametrize("day", ["2016-12-30", "2017-03-15"])
def test_the_placebo_swaps_news_only_among_the_same_days_links(day):
    v = World(**TABLES).view(Clock().decision_time(day))
    se = v.story_entities.reset_index(drop=True)
    a, b, c = shuffled_links(v, 1), shuffled_links(v, 1), shuffled_links(v, 2)
    pd.testing.assert_frame_equal(a, b)  # a seed always shuffles the same way
    assert (a.story_id == se.story_id).all() and (a.visible_at == se.visible_at).all()  # stories and times stay
    g = groups_of(v)
    by_day = {}
    for i, s in g.items():
        by_day.setdefault(s, []).append(i)
    for s, rows in by_day.items():
        assert sorted(a.entity_id[rows]) == sorted(se.entity_id[rows]), s  # the same day's companies, permuted
    unembedded = [i for i in range(len(se)) if i not in g]
    assert (a.entity_id[unembedded] == se.entity_id[unembedded]).all()
    # a permutation of k companies leaves about one in place, so count only days with at least 3 different ones
    many = [i for rows in by_day.values() if se.entity_id[rows].nunique() >= 3 for i in rows]
    assert len(many) > 100 and (a.entity_id[many] != se.entity_id[many]).mean() > 0.5
    assert (a.entity_id != c.entity_id).any()


def test_a_pair_is_shuffled_the_same_way_in_every_later_view():
    """So the news memory, kept day by day, sees one consistent placebo."""
    w = World(**TABLES)
    v1, v2 = w.view(Clock().decision_time("2017-02-01")), w.view(Clock().decision_time("2017-02-15"))
    a1, a2 = shuffled_links(v1, 3), shuffled_links(v2, 3)
    n = len(a1)
    assert v1.story_entities.reset_index(drop=True).equals(v2.story_entities.iloc[:n].reset_index(drop=True))
    both = set(v1.embeddings.rows.story_id) & set(v2.embeddings.rows.story_id)  # still in the window in v2
    rows = [i for i in range(n) if a1.story_id[i] in both]
    assert len(rows) > 100
    assert (a1.entity_id[rows].to_numpy() == a2.entity_id[rows].to_numpy()).all()


def test_the_placebo_seeds_give_different_runs():
    runs = simulator.run_many(World(**TABLES), {"live": track(), "p1": Placebo(track(), 1), "p2": Placebo(track(), 2)},
                              "2016-10-03", "2017-02-28")
    assert leaks.compare(runs["p1"].decisions, runs["live"].decisions)
    assert leaks.compare(runs["p1"].decisions, runs["p2"].decisions)


# The baselines

def test_random_ranking_is_fixed_by_its_seed():
    a = simulator.run(World(**TABLES), RandomRanking(4), "2017-01-03", "2017-01-31").decisions
    b = simulator.run(World(**TABLES), RandomRanking(4), "2017-01-03", "2017-01-31").decisions
    c = simulator.run(World(**TABLES), RandomRanking(5), "2017-01-03", "2017-01-31").decisions
    pd.testing.assert_frame_equal(a, b)
    assert leaks.compare(a, c)
    per_day = a.groupby("date").position
    assert (per_day.apply(lambda p: (p > 0).sum()) == 10).all() and (per_day.sum().abs() < 1e-12).all()


def test_momentum_and_reversal_match_a_hand_computation():
    days = sessions("2015-01-01", "2016-06-30")
    today = days[-1]
    past = days[days < today]
    n = len(past)
    ra = np.array([0.001 * ((i % 11) - 5) for i in range(n)])
    rb = -ra
    b = pd.concat([bars_of("A", past, ra, np.ones(n), np.ones(n)), bars_of("B", past, rb, np.ones(n), np.ones(n))])
    v = view(today, days, b)
    keep = past >= today - pd.Timedelta(days=400)
    la, lb = np.log1p(ra[keep]), np.log1p(rb[keep])
    mom = Momentum().scores(v, [("A", ""), ("B", "")])
    assert mom == pytest.approx([la[-252:-21].sum(), lb[-252:-21].sum()], rel=1e-12)
    rev = Reversal().scores(v, [("A", ""), ("B", "")])
    assert rev == pytest.approx([-la[-5:].sum(), -lb[-5:].sum()], rel=1e-12)


def test_equal_weight_holds_every_pick_at_one_over_n_and_2016_is_watch_only():
    d = simulator.run(World(**TABLES), EqualWeight(), "2016-12-01", "2017-01-31").decisions
    before, after = d[d.date < "2017-01-01"], d[d.date >= "2017-01-01"]
    assert (before.position == 0).all() and len(before) > 0
    assert (after.groupby("date").position.sum() - 1).abs().max() < 1e-12
    assert (after.groupby("date").position.min() > 0).all()


def test_spy_buy_and_hold_matches_a_hand_computation():
    spy = pd.DataFrame({"date": pd.to_datetime(["2016-12-30", "2017-01-03", "2017-01-04", "2017-01-05"]),
                        "adj_open": [99.0, 100.0, 102.0, 101.0]})
    e = spy_buy_and_hold(spy, "2017-01-03", "2017-01-04")
    assert list(e.equity) == [1.0, 1.02] and list(e.date.dt.day) == [3, 4]


# Non-interference for every agent here

MAKERS = {"placebo": lambda: Placebo(track(), 1), "twin": lambda: TwinAfter("2017-01-03"),
          "random": lambda: RandomRanking(2), "momentum": Momentum, "reversal": Reversal, "equal": EqualWeight}


@pytest.mark.parametrize("how", leaks.HOW)
@pytest.mark.parametrize("name", list(MAKERS))
def test_non_interference_for_each_twin_and_baseline(name, how):
    assert leaks.non_interference(TABLES, MAKERS[name], "2016-10-03", "2017-03-15", how, seed=3) == []


@needs_store
def test_non_interference_for_the_placebo_on_the_real_store():
    from test_embedding_window import real_tables_with_embeddings
    tables = real_tables_with_embeddings("2017-04-01")
    assert leaks.non_interference(tables, lambda: Placebo(track(), 1), "2016-11-01", "2017-02-15", "scramble",
                                  seed=7) == []


# The trial ledger

class FakeGit:
    def head(self):
        return "abc123"

    def dirty(self):
        return True


def test_the_ledger_records_each_run_with_its_settings_hash(tmp_path):
    from sim.seal import settings_hash
    settings = {"agents": {"live": {"n_side": 10}}, "cost_bps": 5.0}
    now = pd.Timestamp("2026-11-22 10:00", tz="America/New_York")
    row = trials.record(settings, "2016-01-04", "2019-12-31", ["live", "equal"], "D:/x", runs=tmp_path, git=FakeGit(),
                        now=now)
    trials.record(settings, "2016-01-04", "2019-12-31", ["live"], "D:/y", runs=tmp_path, git=FakeGit(), now=now)
    assert trials.count(tmp_path) == 0  # neither row names a trial (a comparison pass, say)
    trials.record(settings, "2016-01-04", "2019-12-31", ["live"], "not yet run", runs=tmp_path, git=FakeGit(),
                  now=now, trial="T01", status="planned")
    trials.record(settings, "2016-01-04", "2019-12-31", ["live"], "D:/z", runs=tmp_path, git=FakeGit(), now=now,
                  trial="T01")
    trials.record(settings, "2016-01-04", "2019-12-31", ["live"], "D:/w", runs=tmp_path, git=FakeGit(), now=now,
                  trial="T02")
    assert trials.count(tmp_path) == 2  # T01 planned and run counts once
    trials.record(settings, "2016-01-04", "2019-12-31", ["live"], "dropped", runs=tmp_path, git=FakeGit(), now=now,
                  trial="T02", status="dropped")
    assert trials.count(tmp_path) == 1 and len(trials.rows(tmp_path)) == 6  # dropped, and its rows kept
    assert [r["status"] for r in trials.rows(tmp_path)][:5] == ["run", "run", "planned", "run", "run"]
    with pytest.raises(ValueError):
        trials.record(settings, "x", "y", [], "z", runs=tmp_path, git=FakeGit(), now=now, status="done")
    with open(tmp_path / "trials.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["settings_hash"] == settings_hash(settings) == row["settings_hash"]
    assert rows[0]["commit"] == "abc123" and rows[0]["dirty"] == "True" and rows[0]["agents"] == "live equal"
    assert (tmp_path / "settings" / f"{row['settings_hash']}.json").exists()
