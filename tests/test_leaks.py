"""The leak tests (PLAN 5.1 and 9.11): non-interference, the planted leaks, and the label embargo.

They run the whole loop with the toy agent (agent/reversal.py) on a made-up world (tests/synthetic.py), and, where
the store exists on D:, on the real one. Each planted leak is a copy of the toy agent, or of the rules, with one
leak put in on purpose; the test passes only if a check catches it. Planted leaks get the World on purpose
(`give_world`); honest agents never do.

Run with: python -m pytest tests
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from agent.reversal import ReversalAgent  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from eval import leaks  # noqa: E402
from world import rules  # noqa: E402
from world.clock import Clock  # noqa: E402
from world.world import World  # noqa: E402

TABLES = synthetic.make_tables(0)
FIRST = "2017-01-03"  # the year's pick, from 2016's bars; a short warm-up lets the ridge fit by February
_s = Clock().between("2017-01-03", "2017-06-30")
_month_first = [d for i, d in enumerate(_s) if i == 0 or d.month != _s[i - 1].month]
# The pick day, every refit day and the session after each, and the days around the March joins and the April rejoin
CHECK_DAYS = sorted(set(_month_first) | {_s[_s.get_loc(d) + 1] for d in _month_first} |
                    {pd.Timestamp("2017-02-28"), pd.Timestamp("2017-03-31"), pd.Timestamp("2017-04-04")})
T = pd.Timestamp("2017-03-15")
toy = lambda: ReversalAgent(warmup=15)


# Non-interference

@pytest.mark.parametrize("how", leaks.HOW)
def test_changing_every_later_record_changes_no_decision(how):
    assert leaks.non_interference(TABLES, toy, FIRST, T, how, seed=1) == []


@pytest.mark.parametrize("how", leaks.HOW)
def test_on_the_pick_day_too(how):
    assert leaks.non_interference(TABLES, toy, FIRST, FIRST, how, seed=2) == []


@pytest.mark.parametrize("day, how", [(d, leaks.HOW[i % 3]) for i, d in enumerate(CHECK_DAYS)])
def test_non_interference_on_every_check_day(day, how):
    """Every check day, each with one of the three modes in turn (T and the pick day run all three above)."""
    assert leaks.non_interference(TABLES, toy, FIRST, day, how, seed=day.day) == []


@settings(max_examples=3, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(i=st.integers(0, len(_s) - 1), how=st.sampled_from(leaks.HOW), seed=st.integers(0, 10**6))
def test_non_interference_on_random_days(i, how, seed):
    assert leaks.non_interference(TABLES, toy, FIRST, _s[i], how, seed) == []


KEYS = {"bars": ["entity_id", "share_class", "date"], "labels": ["entity_id", "share_class", "date"],
        "stories": ["story_id"], "story_entities": ["story_id", "entity_id"]}


@pytest.mark.parametrize("how", leaks.HOW)
@pytest.mark.parametrize("day", ["2016-11-15", "2017-02-15", "2017-03-15", "2017-05-01"])
def test_the_perturbed_view_at_t_is_the_original_view(how, day):
    """Only records not visible at t change, and none of them comes into view by t: a swapped company id or a moved
    date once let hidden records show, which would flag an honest agent."""
    t = Clock().decision_time(day)
    a, b = World(**TABLES).view(t), World(**leaks.perturb(TABLES, t, how, seed=5)).view(t)
    for name, key in KEYS.items():
        x = getattr(a, name).sort_values(key, ignore_index=True)
        y = getattr(b, name).sort_values(key, ignore_index=True)
        pd.testing.assert_frame_equal(x, y, check_dtype=False, obj=f"{name} on {day} ({how})")


def test_compare_flags_a_prediction_missing_in_one_run():
    a = pd.DataFrame({"date": [T], "entity_id": ["E01"], "share_class": [""], "prediction": [float("nan")],
                      "position": [0.0]})
    assert leaks.compare(a, a.assign(prediction=[0.7])) and leaks.compare(a, a) == []


def test_the_perturbation_touches_only_records_not_yet_visible():
    t = Clock().decision_time(T)
    bars = TABLES["bars"].assign(row_id=np.arange(len(TABLES["bars"])))  # follows each row through the perturbation
    tables = {**TABLES, "bars": bars}
    early = bars[~leaks.late_rows(tables, t)["bars"]].reset_index(drop=True)
    for how in leaks.HOW:
        p = leaks.perturb(tables, t, how, seed=3)["bars"]  # late rows that would show by t are dropped, so count may fall
        kept = p[p.row_id.isin(early.row_id)].reset_index(drop=True)
        pd.testing.assert_frame_equal(early, kept, check_dtype=False, obj=how)
    # Before March's joins, the joiners' earlier bars count as late: they show only at the join (or never)
    before_join = leaks.late_rows(TABLES, Clock().decision_time("2017-02-15"))
    hidden = TABLES["bars"].entity_id.isin(["E55", "E56", "E57"]) & (TABLES["bars"].date < pd.Timestamp("2017-02-15"))
    assert before_join["bars"][hidden.to_numpy()].all()


def test_a_view_holds_nothing_of_a_company_before_it_joins():
    w = World(**TABLES)
    v = w.view(Clock().decision_time("2017-02-15"))
    for name in ("bars", "labels", "story_entities"):
        assert not set(getattr(v, name).entity_id) & {"E55", "E56", "E57"}, name
    gap = v.bars[(v.bars.entity_id == "E43") & (v.bars.date > pd.Timestamp("2016-06-15"))]
    assert gap.empty  # E43's gap shows only at its rejoin in April


# The planted leaks: each one must make a check fail

class FutureReturn(ReversalAgent):
    """Adds the return from today's open to tomorrow's, read from the World rather than the view."""

    def __init__(self, world):
        super().__init__(warmup=15)
        lab = world.labels.df
        self.future = dict(zip(zip(lab.entity_id.astype(str), lab.share_class.astype(str), lab.date), lab.label))

    def score(self, f, v):
        ahead = np.array([self.future.get((e, c, v.today), 0.0) for e, c in zip(f.entity_id, f.share_class)])
        return super().score(f, v) + 100 * ahead


class FutureHeadline(ReversalAgent):
    """Counts the stories about each stock in the next 24 hours, from the World's stories."""

    def __init__(self, world):
        super().__init__(warmup=15)
        st_, se = world.stories.df, world.story_entities.df
        self.news = se.merge(st_[["story_id", "headline", "updated_at"]], on="story_id")

    def score(self, f, v):
        soon = self.news[(self.news.updated_at > v.t) & (self.news.updated_at <= v.t + pd.Timedelta(days=1))]
        n = soon.groupby(soon.entity_id.astype(str)).headline.apply(lambda h: sum(len(x) for x in h))
        return super().score(f, v) + f.entity_id.map(n).fillna(0).to_numpy(dtype=float)


class ScalerOnAllData(ReversalAgent):
    """Scales its features with means and spreads taken from every bar in the World, past and future."""

    def __init__(self, world):
        super().__init__(warmup=15)
        r = np.log1p(world.bars.df.ret.to_numpy(dtype=float))
        self.all_mean, self.all_std = np.nanmean(r), np.nanstd(r)

    def refit(self, v):
        super().refit(v)
        if self.beta is not None:
            self.mean = np.full(4, self.all_mean)
            self.std = np.full(4, self.all_std)


class FutureBreadth(ReversalAgent):
    """Tilts every score by the share of the World's later labels that are gains: future market breadth."""

    def __init__(self, world):
        super().__init__(warmup=15)
        self.labels = world.labels.df

    def score(self, f, v):
        later = self.labels[self.labels.date >= v.today]
        return super().score(f, v) + 1e-3 * float((later.label > 0).mean()) * np.arange(len(f))


class FutureStockList(ReversalAgent):
    """Picks the year's stocks by their dollar volume over the coming year, from the World's bars."""
    horizon = pd.DateOffset(years=1)

    def __init__(self, world):
        super().__init__(warmup=15)
        self.bars = world.bars.df

    def pick(self, v):
        b = self.bars[(self.bars.date >= v.today) & (self.bars.date < v.today + self.horizon)]
        b = b[b.entity_id.astype(str).isin(v.members)]
        dv = (b.close * b.volume).groupby([b.entity_id.astype(str), b.share_class.astype(str)]).median()
        dv = dv.rename("dv").reset_index().sort_values(["dv", "entity_id"], ascending=[False, True])
        best = dv.drop_duplicates("entity_id").head(self.n_picks)
        return list(zip(best.entity_id, best.share_class))


class ShortPeekStockList(FutureStockList):
    """The same, peeking only 28 days ahead."""
    horizon = pd.Timedelta(days=28)


class NotYetJoined(ReversalAgent):
    """Leans away from the stocks of companies that will join soon, read from the World's bars."""

    def __init__(self, world):
        super().__init__(warmup=15)
        self.bars = world.bars.df

    def score(self, f, v):
        soon = self.bars[~self.bars.entity_id.astype(str).isin(v.joined) & (self.bars.date < v.today)]
        return super().score(f, v) - 1e-3 * soon.close.sum() * np.arange(len(f))


class UnrealizedLabels(ReversalAgent):
    """Trains on every label in the World, including those not realized yet (it breaks the label embargo)."""

    def __init__(self, world):
        super().__init__(warmup=15)
        self.all_labels = world.labels.df

    def refit(self, v):
        class Wider:
            pass
        w = Wider()
        w.__dict__.update(v.__dict__)
        w.labels = self.all_labels
        super().refit(w)


def caught_by(leaky, last):
    """The first perturbation that catches a planted leak, or None."""
    for how in leaks.HOW:
        if leaks.non_interference(TABLES, leaky, FIRST, last, how, seed=1, give_world=True):
            return how
    return None


@pytest.mark.parametrize("leaky, last", [
    (FutureReturn, T), (FutureHeadline, T), (ScalerOnAllData, T), (FutureBreadth, T), (NotYetJoined, T),
    (FutureStockList, pd.Timestamp(FIRST)), (ShortPeekStockList, pd.Timestamp(FIRST)),
    # It refits on a month's first session, with the label that completes at 9:30 that morning.
    (UnrealizedLabels, pd.Timestamp("2017-03-01"))])
def test_non_interference_catches_each_planted_leak(leaky, last):
    assert caught_by(leaky, last), f"{leaky.__name__} was not caught"


def same_day_bars(world, days):
    """Days on which a bar dated that day is in the 9:00 view: the close would be known before it happens."""
    hits = []
    for d in days:
        v = world.view(world.clock.decision_time(d))
        if (v.bars.date >= d).any():
            hits.append(d)
    return hits


def test_bars_are_never_in_the_view_on_their_own_morning():
    assert same_day_bars(World(**TABLES), CHECK_DAYS[:10]) == []


def test_the_vendors_bar_timestamp_as_close_time_is_caught(monkeypatch):
    """Alpaca stamps a daily bar at midnight UTC: the evening before in New York. Used as the close time, it puts
    each day's close in that morning's view."""
    monkeypatch.setattr(rules, "bar", lambda dates: pd.to_datetime(pd.Series(dates)).dt.tz_localize("UTC"))
    assert same_day_bars(World(**TABLES), CHECK_DAYS[:10]) == list(CHECK_DAYS[:10])


# The label embargo

def embargo_breaches(agent):
    return [f for f in agent.fits if f["latest_label"] > f["t"]]


def run_agent(agent, last=T):
    world = World(**TABLES)
    for day in world.clock.between(FIRST, last):
        agent.decide(world.view(world.clock.decision_time(day)))
    return agent


def test_every_training_label_was_realized_before_the_decision_that_used_it():
    agent = run_agent(ReversalAgent(warmup=15))
    assert agent.fits, "the toy agent never refit"
    assert embargo_breaches(agent) == []


def test_the_embargo_check_catches_unrealized_labels():
    assert embargo_breaches(run_agent(UnrealizedLabels(World(**TABLES))))


# On the real store, where it exists

STORE = DATA_DIR / "store"
needs_store = pytest.mark.skipif(not (STORE / "bars.parquet").exists(), reason="the event store isn't built")


@pytest.fixture(scope="module")
def real_tables():
    read = lambda n: pd.read_parquet(STORE / f"{n}.parquet")
    return {n: read(n) for n in ("bars", "labels", "opens", "stories", "story_entities", "membership")}


@needs_store
def test_the_time_wall_reproduces_the_audits_stock_picks(real_tables):
    """Picking through World.view gives research/audit/universe_preview.csv exactly: same companies, same order. It
    reads dollar volumes in the sealed years, as M0's preview did, so it opens them as a data audit."""
    world = World(**real_tables, allow_sealed=True)
    preview = pd.read_csv(Path(__file__).resolve().parents[1] / "research" / "audit" / "universe_preview.csv", dtype=str)
    days = [pd.Timestamp("2016-04-01")] + [world.clock.between(f"{y}-01-01", f"{y}-01-10")[0] for y in range(2017, 2027)]
    agent = ReversalAgent()
    for d in days:
        mine = [e for e, _ in agent.pick(world.view(world.clock.decision_time(d)))]
        assert mine == list(preview[preview.year == str(d.year)].entity_id), d


@needs_store
def test_non_interference_on_the_real_store(real_tables):
    """A short run in the dev years: every record not visible at the decision on 2017-03-15 scrambled."""
    agent = lambda: ReversalAgent(warmup=10)
    assert leaks.non_interference(real_tables, agent, "2017-02-01", "2017-03-15", "scramble", seed=7) == []


@needs_store
def test_a_rejoining_company_is_hidden_during_its_gap(real_tables):
    """EQT left the index on 2018-11-13 and rejoined on 2022-10-03. In January 2022 it isn't a member, and its bars
    from the year before its rejoin show only at the rejoin."""
    world = World(**real_tables, allow_sealed=True)
    eqt = "0000033213"
    v = world.view(world.clock.decision_time("2022-01-03"))
    assert eqt not in v.members
    assert v.bars[(v.bars.entity_id == eqt) & (v.bars.date > pd.Timestamp("2018-11-30"))].empty
    after = world.view(world.clock.decision_time("2022-10-03"))
    assert not after.bars[(after.bars.entity_id == eqt) & (after.bars.date > pd.Timestamp("2021-12-01"))].empty
