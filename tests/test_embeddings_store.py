"""The real embeddings table (M2 step 5): store/embeddings.parquet, its arrays and embeddings.json, against the store's
stories and the time wall. Counts, ids and times only; no headline is read. Skips where the table isn't built.
"""
import json

import numpy as np
import pandas as pd
import pytest

from data_pipeline.settings import DATA_DIR
from reader import embed as E
from reader.vintage import vintage_for
from world import rules
from world.world import World

STORE = DATA_DIR / "store"
pytestmark = pytest.mark.skipif(not (STORE / "embeddings.parquet").exists(), reason="no embeddings table yet (M2)")
EQT = "0000033213"  # left the S&P 500 on 2018-11-13, rejoined on 2022-10-03 (tests/test_leaks.py)


@pytest.fixture(scope="module")
def rows():
    return pd.read_parquet(STORE / "embeddings.parquet", columns=["story_id", "vintage_year", "available_at"])


@pytest.fixture(scope="module")
def wanted():
    """The job's selection on the store as it is now: every story to embed, with its vintage and time."""
    st = pd.read_parquet(STORE / "stories.parquet", columns=["story_id", "created_at", "updated_at"])
    se = pd.read_parquet(STORE / "story_entities.parquet", columns=["story_id"])
    return E.select(st, se)


@pytest.fixture(scope="module")
def meta():
    return json.loads((STORE / "embeddings.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def world():
    return World.load(allow_sealed=True, embedding_window_days=None)  # every row; the window's tests set their own


def test_one_row_for_every_selected_story_and_no_other(rows, wanted, meta):
    assert len(rows) == len(wanted) == meta["rows"] == meta["arrays"]["rows"]
    assert rows.story_id.is_unique
    assert set(rows.story_id) == set(wanted.story_id)


def test_the_story_set_is_the_one_that_was_read(wanted, meta):
    """Review finding L-P7: an edit after the run changes updated_at, and so this hash."""
    assert E.set_hash(wanted.story_id, wanted.updated_at) == meta["story_set_sha256"]


def test_every_row_was_read_by_the_year_before_its_stories_year(rows, wanted, meta):
    w = wanted.set_index("story_id").loc[rows.story_id]
    assert (rows.vintage_year.to_numpy() == vintage_for(w.created_at).to_numpy()).all()
    ny_year = pd.to_datetime(w.created_at, utc=True).dt.tz_convert("America/New_York").dt.year.to_numpy()
    assert (rows.vintage_year.to_numpy() == np.minimum(ny_year - 1, 2024)).all()
    assert set(rows.vintage_year) == set(range(2015, 2025))
    assert {str(v) for v in set(rows.vintage_year)} == set(meta["vintages"])  # each vintage's pin is recorded


def test_every_row_is_available_when_its_story_is(rows, wanted):
    w = wanted.set_index("story_id").loc[rows.story_id]
    want = rules.embedding(w.updated_at.reset_index(drop=True))
    assert (pd.to_datetime(rows.available_at, utc=True).reset_index(drop=True) == want).all()


def test_the_world_loads_the_table_and_maps_its_arrays(world, rows):
    assert world.embeddings is not None
    assert len(world.embeddings.rows) == len(rows)
    assert world.embeddings._last.shape == (len(rows), E.DIM) and world.embeddings._last.dtype == np.float16


@pytest.mark.parametrize("day", ["2016-06-30", "2018-03-01", "2019-12-31"])
def test_a_view_shows_the_embeddings_of_its_linked_stories_only(world, day):
    """Judge J-1 on the real store: the embeddings in a view are exactly the embedded stories among its linked ones,
    each visible by t, as fresh copies."""
    v = world.view(world.clock.decision_time(day))
    shown = set(v.embeddings.rows.story_id)
    assert len(shown) > 0
    assert shown == set(v.story_entities.story_id) & set(world.embeddings.rows.story_id)
    assert (v.embeddings.rows.visible_at <= v.t).all() and (v.embeddings.rows.available_at <= v.t).all()
    assert v.embeddings.last.base is None and v.embeddings.avg.base is None
    assert v.embeddings.last.shape == (len(shown), E.DIM)


def test_no_embedding_tells_of_eqts_rejoin_during_its_gap(world):
    """Judge J-1: in January 2022 EQT is out of the index. Its stories from the gap carry no visible link, so their
    embeddings are hidden too, until the rejoin."""
    se = world.story_entities.df
    eqt_ids = set(se.story_id[se.entity_id == EQT])
    only_eqt = eqt_ids - set(se.story_id[se.entity_id != EQT])
    st = world.stories.df.set_index("story_id")
    gap = {s for s in only_eqt if s in st.index and pd.Timestamp("2019-06-01", tz="UTC") <= st.created_at[s]
           < pd.Timestamp("2021-12-01", tz="UTC")}
    embedded = gap & set(world.embeddings.rows.story_id)
    assert len(embedded) > 0, "the check needs EQT stories from its gap that were embedded"
    v = world.view(world.clock.decision_time("2022-01-03"))
    assert not embedded & set(v.embeddings.rows.story_id)
    assert embedded <= set(v.stories.story_id)  # the stories themselves show, as the whole feed does
    after = world.view(world.clock.decision_time("2022-10-03"))
    assert embedded & set(after.embeddings.rows.story_id)


def test_the_vectors_in_a_view_are_the_stored_ones(world):
    """The view's gathered rows equal the table's rows for the same stories."""
    import pyarrow.parquet as pq
    v = world.view(world.clock.decision_time("2017-03-15"))
    f = pq.ParquetFile(STORE / "embeddings.parquet")
    first = f.read_row_group(0, columns=["story_id", "emb_last", "emb_avg"])
    ids = first.column("story_id").to_numpy()
    pos = {s: i for i, s in enumerate(v.embeddings.rows.story_id)}
    pick = [i for i, s in enumerate(ids) if s in pos][:50]
    assert len(pick) == 50
    for c, got in (("emb_last", v.embeddings.last), ("emb_avg", v.embeddings.avg)):
        stored = first.column(c).combine_chunks().flatten().to_numpy(zero_copy_only=False).reshape(-1, E.DIM)
        assert np.array_equal(stored[pick], got[[pos[ids[i]] for i in pick]])
