"""M3 step 2: the embedding window (research/m3_kickoff.md, decision 1). A view at t holds only the embeddings whose
visible_at falls in the 90 days up to t. These tests show that the windowed view is exactly the full view cut by
visible_at, that a row shown late (judge J-1's rejoin) still shows when it becomes visible, that the runner records
the window, and that non-interference holds with the window on the made-up world and on the real store, embeddings
included, in all three modes.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from agent.reversal import ReversalAgent  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from eval import leaks  # noqa: E402
from sim import simulator  # noqa: E402
from world.clock import Clock  # noqa: E402
from world.world import EMBEDDING_WINDOW_DAYS, World  # noqa: E402

BASE = synthetic.make_tables(0)
TABLES = {**BASE, "embeddings": synthetic.make_embeddings(BASE)}
DAYS = ["2016-06-15", "2016-12-30", "2017-01-03", "2017-03-15", "2017-04-03", "2017-06-29"]
WINDOW = pd.Timedelta(days=EMBEDDING_WINDOW_DAYS)
STORE = DATA_DIR / "store"
needs_store = pytest.mark.skipif(not (STORE / "embeddings.parquet").exists(), reason="no embeddings table yet")


def assert_window_cuts_the_full_view(full, windowed, t):
    """The windowed view's embeddings are the full view's last rows, those with visible_at in (t - window, t], in the
    same order with a fresh 0-based index, and their vectors (judge W-2)."""
    keep = (full.rows.visible_at > t - WINDOW).to_numpy()
    n = int(keep.sum())
    assert keep[len(keep) - n:].all()  # the full view is in visible_at order, so the window is its tail
    pd.testing.assert_frame_equal(full.rows.iloc[len(keep) - n:].reset_index(drop=True), windowed.rows)
    assert isinstance(windowed.rows.index, pd.RangeIndex) and windowed.rows.index.start == 0
    assert np.array_equal(full.last[keep], windowed.last) and np.array_equal(full.avg[keep], windowed.avg)
    assert windowed.last.base is None and windowed.avg.base is None  # fresh copies, as before


# The rule

def test_the_default_window_is_90_days_and_fixed_once_built():
    w = World(**TABLES)
    assert EMBEDDING_WINDOW_DAYS == 90 and w.embedding_window_days == 90
    with pytest.raises(AttributeError):
        w.embedding_window_days = None  # judge W-3: a run records the window once


@pytest.mark.parametrize("bad", [0, -5, 1.5, "90", True])
def test_the_world_refuses_a_window_that_is_not_a_positive_whole_number(bad):
    with pytest.raises(ValueError):
        World(**TABLES, embedding_window_days=bad)


@pytest.mark.parametrize("day", DAYS)
def test_the_windowed_view_is_the_full_view_cut_by_visible_at(day):
    t = Clock().decision_time(day)
    full = World(**TABLES, embedding_window_days=None).view(t).embeddings
    windowed = World(**TABLES).view(t)
    assert 0 < len(windowed.embeddings) < len(full) or day == "2016-06-15"
    assert_window_cuts_the_full_view(full, windowed.embeddings, t)
    # the other tables are untouched by the window
    other = World(**TABLES, embedding_window_days=None).view(t)
    for name in ("bars", "labels", "stories", "story_entities"):
        pd.testing.assert_frame_equal(getattr(other, name), getattr(windowed, name))


def test_a_row_leaves_the_window_exactly_90_days_after_it_became_visible():
    w = World(**TABLES)
    rows = w.embeddings.rows
    r = rows.iloc[len(rows) // 3]
    edge = r.visible_at + WINDOW
    inside = w.view(edge - pd.Timedelta(nanoseconds=1)).embeddings.rows.story_id
    outside = w.view(edge).embeddings.rows.story_id
    assert r.story_id in set(inside) and r.story_id not in set(outside)


def test_a_story_shown_late_by_a_rejoin_shows_when_it_becomes_visible():
    """Judge J-1 under the window: E43's stories from its gap show with the rejoin, long after their own time. The
    window is measured on visible_at, so they are in the view from the rejoin on, though their stories are old."""
    w = World(**TABLES)
    rows = w.embeddings.rows
    late = rows[(rows.visible_at - rows.available_at) > WINDOW]
    assert len(late) > 0, "the check needs rows shown more than a window after their story"
    at = late.visible_at.min()
    first = late[late.visible_at == at].story_id
    before, after = w.view(at - pd.Timedelta(nanoseconds=1)), w.view(at)
    assert not set(first) & set(before.embeddings.rows.story_id)
    assert set(first) <= set(after.embeddings.rows.story_id)


def test_the_runner_records_the_window_in_the_runs_settings(monkeypatch):
    seen = []
    monkeypatch.setattr(simulator.seal, "check", lambda first, last, settings: seen.append(settings))
    for window in (90, 30, None):
        simulator.run(World(**TABLES, embedding_window_days=window), ReversalAgent(warmup=15), "2016-04-01",
                      "2016-04-05", settings={"x": 1})
    assert [s["embedding_window_days"] for s in seen] == [90, 30, None]


# Non-interference with the window

class NewsAgent(ReversalAgent):
    """An honest agent that reads embeddings: it tilts each stock's score by the mean first value of the last-layer
    embeddings of its stories visible in the past three days, all from the view."""

    def score(self, f, v):
        rows = v.embeddings.rows.assign(x=v.embeddings.last[:, 0].astype(float))
        rows = rows[rows.visible_at > v.t - pd.Timedelta(days=3)]
        x = rows.merge(v.story_entities[["story_id", "entity_id"]], on="story_id")
        tilt = x.groupby(x.entity_id.astype(str)).x.mean()
        return super().score(f, v) + 0.5 * f.entity_id.astype(str).map(tilt).fillna(0).to_numpy(dtype=float)


class WindowCount(ReversalAgent):
    """Reads only the view: a tiny tilt by how many embeddings the view holds, so a row entering or leaving the
    window moves its predictions."""

    def score(self, f, v):
        return super().score(f, v) + 1e-6 * len(v.embeddings)


@pytest.mark.parametrize("window", [EMBEDDING_WINDOW_DAYS, 30, None])
@pytest.mark.parametrize("how", leaks.HOW)
def test_non_interference_holds_with_any_window(how, window):
    for make in (lambda: NewsAgent(warmup=15), lambda: WindowCount(warmup=15)):
        assert leaks.non_interference(TABLES, make, "2017-01-03", "2017-03-15", how, seed=4,
                                      embedding_window_days=window) == []


def test_non_interference_catches_a_window_anchored_after_t(monkeypatch):
    """Judge W-1, a planted leak: a window anchored on the table's last visible time instead of on t. Which rows it
    drops depends on records after t, and the check must catch it."""
    import world.world as ww
    real = ww._SortedEmbeddings.upto

    def wrong(self, ns, since=None):
        if since is not None:
            since = int(self.at[self.at < ww.NEVER].max()) - 400 * ww.DAY_NS
        return real(self, ns, since)

    monkeypatch.setattr(ww._SortedEmbeddings, "upto", wrong)
    caught = [h for h in leaks.HOW if leaks.non_interference(TABLES, lambda: WindowCount(warmup=15), "2017-01-03",
                                                             "2017-03-15", h, seed=4)]
    assert caught, "the window anchored after t was not caught"


def test_the_window_changes_what_an_agent_sees():
    """So the checks above test something: the count agent decides differently with and without the window."""
    mk = lambda: WindowCount(warmup=15)  # noqa: E731
    a = leaks.decisions_until(TABLES, mk, "2017-01-03", "2017-03-15")
    b = leaks.decisions_until(TABLES, mk, "2017-01-03", "2017-03-15", embedding_window_days=None)
    assert leaks.compare(a, b)


# The real store

@pytest.fixture(scope="module")
def full_world():
    return World.load(embedding_window_days=None)  # dev dates only: the sealed years stay shut (review W3-1)


@needs_store
@pytest.mark.parametrize("day", ["2016-12-30", "2018-06-29", "2019-12-31"])
def test_on_the_real_store_the_windowed_view_is_the_full_view_cut(full_world, day):
    t = full_world.clock.decision_time(day)
    full = full_world.view(t).embeddings
    full_world._window = EMBEDDING_WINDOW_DAYS  # one World on the laptop, not two (judge W-3's note)
    try:
        windowed = full_world.view(t).embeddings
    finally:
        full_world._window = None
    assert 0 < len(windowed) < len(full)
    assert_window_cuts_the_full_view(full, windowed, t)


def real_tables_with_embeddings(cut):
    """The six store tables and the embeddings of the stories available before `cut`: a subset the World accepts
    (it checks each row, not that every story has one), small enough to perturb in memory."""
    tables = {n: pd.read_parquet(STORE / f"{n}.parquet")
              for n in ("bars", "labels", "opens", "stories", "story_entities", "membership")}
    emb = pq.read_table(STORE / "embeddings.parquet",
                        filters=[("available_at", "<", pd.Timestamp(cut, tz="UTC"))]).to_pandas()
    emb["vintage_year"] = emb.vintage_year.astype("int64")
    return {**tables, "embeddings": emb}


@pytest.fixture(scope="module")
def real_news_tables():
    return real_tables_with_embeddings("2017-05-01")


@needs_store
def test_on_the_real_store_the_news_agent_reads_the_embeddings(real_news_tables):
    a = leaks.decisions_until(real_news_tables, lambda: NewsAgent(warmup=10), "2017-02-01", "2017-03-15")
    b = leaks.decisions_until(real_news_tables, lambda: ReversalAgent(warmup=10), "2017-02-01", "2017-03-15")
    assert leaks.compare(a, b)


@needs_store
@pytest.mark.parametrize("how", leaks.HOW)
def test_non_interference_on_the_real_store_with_embeddings(real_news_tables, how):
    """Every record and embedding not visible at the decision on 2017-03-15 scrambled, shifted or deleted, under the
    default window: the news agent decides the same."""
    late = leaks.late_rows(real_news_tables, Clock().decision_time("2017-03-15"))["embeddings"]
    assert late.sum() > 1000, "the check needs late embeddings to perturb"
    assert leaks.non_interference(real_news_tables, lambda: NewsAgent(warmup=10), "2017-02-01", "2017-03-15", how,
                                  seed=7) == []
