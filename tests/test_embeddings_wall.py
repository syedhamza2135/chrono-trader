"""The time wall for embeddings (review finding M-3, before M2 writes the table): every embedding row carries its
availability time, a view shows a row only once its story is visible, the World refuses rows it can't trust, and the
leak checks (non-interference and a planted leak) cover news features. On the made-up world of tests/synthetic.py.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from agent.reversal import ReversalAgent  # noqa: E402
from eval import leaks  # noqa: E402
from world import rules  # noqa: E402
from world.clock import Clock  # noqa: E402
from world.world import World  # noqa: E402

BASE = synthetic.make_tables(0)
TABLES = {**BASE, "embeddings": synthetic.make_embeddings(BASE)}
FIRST, T = "2017-01-03", pd.Timestamp("2017-03-15")
DAYS = ["2016-06-15", "2016-12-30", "2017-01-03", "2017-03-15", "2017-06-29"]


def world(**changes):
    return World(**{**TABLES, **changes})


# The rows and the rule

def test_every_row_carries_its_storys_availability_time():
    emb, st = TABLES["embeddings"], TABLES["stories"].set_index("story_id")
    want = rules.story(st.loc[emb.story_id, "updated_at"].reset_index(drop=True))
    assert (pd.to_datetime(emb.available_at, utc=True).reset_index(drop=True) == want).all()


@pytest.mark.parametrize("day", DAYS)
def test_a_view_shows_exactly_the_embeddings_of_the_linked_stories_it_shows(day):
    """An embedding shows once its story and one of its company links do (judge J-1), not with the story alone."""
    v = world().view(Clock().decision_time(day))
    assert len(v.embeddings) > 0
    assert set(v.embeddings.rows.story_id) == set(v.story_entities.story_id)
    assert set(v.embeddings.rows.story_id) <= set(v.stories.story_id)
    assert (v.embeddings.rows.visible_at <= v.t).all()
    assert v.embeddings.last.shape == (len(v.embeddings), 8) and v.embeddings.avg.shape == (len(v.embeddings), 8)


def test_an_embedding_shows_15_minutes_after_its_storys_update_to_the_nanosecond():
    w = world()
    sid = int(TABLES["stories"].story_id.iloc[100])
    assert TABLES["story_entities"].entity_id.iloc[100] not in {"E43"} | {f"E{i}" for i in range(50, 58)}
    at = rules.story(TABLES["stories"].updated_at.iloc[[100]]).iloc[0]
    before, after = w.view(at - pd.Timedelta(nanoseconds=1)), w.view(at)
    assert sid not in set(before.embeddings.rows.story_id)
    assert sid in set(after.embeddings.rows.story_id)


def test_the_vectors_follow_their_rows():
    w = world()
    v = w.view(Clock().decision_time("2017-03-15"))
    src = TABLES["embeddings"].set_index("story_id")
    for i in [0, len(v.embeddings) // 2, len(v.embeddings) - 1]:
        sid = v.embeddings.rows.story_id.iloc[i]
        assert np.array_equal(v.embeddings.last[i], src.loc[sid, "emb_last"])
        assert np.array_equal(v.embeddings.avg[i], src.loc[sid, "emb_avg"])


def test_a_view_shares_no_memory_with_the_world():
    w = world()
    v = w.view(Clock().decision_time("2017-03-15"))
    for mine, theirs in ((v.embeddings.last, w.embeddings._last), (v.embeddings.avg, w.embeddings._avg)):
        assert mine.base is None and not np.shares_memory(mine, theirs)
        assert len(mine) < len(theirs)  # the later rows exist, but nothing in the view reaches them


def test_a_world_without_embeddings_gives_empty_ones():
    v = World(**BASE).view(Clock().decision_time("2017-03-15"))
    assert len(v.embeddings) == 0


# The World refuses rows it can't trust

def _changed(i, **cols):
    e = TABLES["embeddings"].copy()
    for c, val in cols.items():
        e.loc[i, c] = val
    return e


def test_a_row_timed_before_its_story_is_refused():
    e = TABLES["embeddings"].copy()
    e.loc[5, "available_at"] = e.loc[5, "available_at"] - pd.Timedelta(hours=1)
    with pytest.raises(ValueError, match="available_at"):
        world(embeddings=e)


def test_a_stale_row_from_before_its_story_was_edited_is_refused():
    st = TABLES["stories"].copy()
    st.loc[7, "updated_at"] = st.loc[7, "updated_at"] + pd.Timedelta(hours=2)  # the story changed after reading
    with pytest.raises(ValueError, match="available_at"):
        world(stories=st)


def test_a_row_read_by_the_wrong_vintage_is_refused():
    e = TABLES["embeddings"].copy()
    e.loc[9, "vintage_year"] = e.loc[9, "vintage_year"] + 1  # a model from the story's own year
    with pytest.raises(ValueError, match="vintage"):
        world(embeddings=e)


def test_a_row_with_no_kept_story_is_refused():
    st = TABLES["stories"].copy()
    st.loc[11, "updated_at"] = st.loc[11, "created_at"] + pd.Timedelta(days=4)  # dropped: edited after 3 days
    e = TABLES["embeddings"].copy()
    e.loc[11, "available_at"] = rules.embedding(st.updated_at.iloc[[11]]).iloc[0]
    with pytest.raises(ValueError, match="no kept story"):
        world(stories=st, embeddings=e)
    e2 = pd.concat([TABLES["embeddings"], TABLES["embeddings"].iloc[[0]].assign(story_id=10**9)], ignore_index=True)
    with pytest.raises(ValueError, match="no kept story"):
        world(embeddings=e2)


def test_a_repeated_story_is_refused():
    e = pd.concat([TABLES["embeddings"], TABLES["embeddings"].iloc[[3]]], ignore_index=True)
    with pytest.raises(ValueError, match="repeat"):
        world(embeddings=e)


# The leak checks cover news features

class NewsAgent(ReversalAgent):
    """An honest agent that reads embeddings: it tilts each stock's score by the mean first value of the last-layer
    embeddings of its stories visible in the past three days, all from the view."""

    def score(self, f, v):
        rows = v.embeddings.rows.assign(x=v.embeddings.last[:, 0].astype(float))
        rows = rows[rows.visible_at > v.t - pd.Timedelta(days=3)]
        x = rows.merge(v.story_entities[["story_id", "entity_id"]], on="story_id")
        tilt = x.groupby(x.entity_id.astype(str)).x.mean()
        return super().score(f, v) + 0.5 * f.entity_id.astype(str).map(tilt).fillna(0).to_numpy(dtype=float)


class FutureEmbedding(ReversalAgent):
    """The planted leak: the same tilt from the embeddings of stories that become visible in the next day, read from
    the World."""

    def __init__(self, world):
        super().__init__(warmup=15)
        e = world.embeddings
        rows = e.rows.assign(x=e._last[e.order, 0].astype(float))  # rows are sorted by visible_at; _last isn't
        self.news = rows.merge(world.story_entities.df[["story_id", "entity_id"]], on="story_id")

    def score(self, f, v):
        soon = self.news[(self.news.visible_at > v.t) & (self.news.visible_at <= v.t + pd.Timedelta(days=1))]
        tilt = soon.groupby(soon.entity_id.astype(str)).x.mean()
        return super().score(f, v) + 5.0 * f.entity_id.astype(str).map(tilt).fillna(0).to_numpy(dtype=float)


news = lambda: NewsAgent(warmup=15)


def test_the_news_agent_reads_the_embeddings():
    """Without its tilt the honest agent decides differently, so the checks below test a reader of embeddings."""
    a = leaks.decisions_until(TABLES, news, FIRST, T)
    b = leaks.decisions_until(TABLES, lambda: ReversalAgent(warmup=15), FIRST, T)
    assert leaks.compare(a, b)


@pytest.mark.parametrize("how", leaks.HOW)
def test_changing_every_later_record_and_embedding_changes_no_decision(how):
    assert leaks.non_interference(TABLES, news, FIRST, T, how, seed=1) == []


@pytest.mark.parametrize("how", leaks.HOW)
@pytest.mark.parametrize("day", ["2016-12-30", "2017-03-15"])
def test_the_perturbed_embeddings_at_t_are_the_original_ones(how, day):
    t = Clock().decision_time(day)
    a, b = World(**TABLES).view(t), World(**leaks.perturb(TABLES, t, how, seed=5)).view(t)
    oa, ob = np.argsort(a.embeddings.rows.story_id.to_numpy()), np.argsort(b.embeddings.rows.story_id.to_numpy())
    pd.testing.assert_frame_equal(a.embeddings.rows.iloc[oa].reset_index(drop=True),
                                  b.embeddings.rows.iloc[ob].reset_index(drop=True))
    assert np.array_equal(a.embeddings.last[oa], b.embeddings.last[ob])
    assert np.array_equal(a.embeddings.avg[oa], b.embeddings.avg[ob])


def test_the_perturbation_changes_the_later_embeddings():
    """Shift moves a late embedding with its story; one late only through its links (a company that joins later)
    keeps its story's time, and the later membership hides it."""
    t = Clock().decision_time("2017-03-15")
    rows = leaks.late_rows(TABLES, t)
    late = rows["embeddings"]
    assert 0 < late.sum() < len(late)
    story_late = TABLES["embeddings"].story_id.isin(set(TABLES["stories"].story_id[rows["stories"]])).to_numpy()
    assert story_late[late].mean() > 0.5 and not story_late[~late].any()
    for how in leaks.HOW:
        out = leaks.perturb(TABLES, t, how, seed=5)["embeddings"]
        if how == "delete":
            assert len(out) == (~late).sum()
        else:
            moved = out.loc[late, "available_at"].to_numpy() != TABLES["embeddings"].loc[late, "available_at"].to_numpy()
            changed = [not np.array_equal(a, b) for a, b in zip(out.loc[late, "emb_last"],
                                                                 TABLES["embeddings"].loc[late, "emb_last"])]
            if how == "shift":
                assert (moved == story_late[late]).all()
                v = World(**leaks.perturb(TABLES, t, how, seed=5)).view(t)
                assert not set(v.embeddings.rows.story_id) & set(TABLES["embeddings"].story_id[late])
            else:
                assert np.mean(changed) > 0.9


def test_non_interference_catches_the_planted_embedding_leak():
    caught = [how for how in leaks.HOW
              if leaks.non_interference(TABLES, FutureEmbedding, FIRST, T, how, seed=1, give_world=True)]
    assert caught, "FutureEmbedding was not caught"


def early_embeddings(w, days):
    """Days on which a view holds an embedding whose story it doesn't show: the rule's own check, independent of
    non-interference (which uses the wall's rules, so a wrong rule would pass it)."""
    out = []
    for d in days:
        v = w.view(Clock().decision_time(d))
        if set(v.embeddings.rows.story_id) - set(v.story_entities.story_id):
            out.append(d)
    return out


def test_no_embedding_is_ever_in_a_view_before_its_story():
    assert early_embeddings(world(), DAYS) == []


def test_an_embedding_rule_earlier_than_the_storys_is_caught(monkeypatch):
    """A planted wrong wall: embeddings timed by their story alone, an hour early, with no link gate. The
    independent check catches it."""
    import world.world as ww
    real = ww.visible_at

    def wrong(table, df, sp, stories=None, story_entities=None):
        if table == "embeddings":
            st = stories.drop_duplicates("story_id").set_index("story_id")
            early = pd.Series(ww._ns(rules.story(st.updated_at) - pd.Timedelta(hours=1)), index=st.index)
            return df.story_id.map(early).to_numpy(dtype="int64")
        return real(table, df, sp, stories, story_entities)

    monkeypatch.setattr(ww, "visible_at", wrong)
    assert early_embeddings(world(), list(Clock().between("2016-03-01", "2016-06-30")))


# The rejoin (judge J-1): the job reads only stories that name a store company, so an embedding seen before any of
# its links would say a hidden company is named. In E43's gap (June 2016 to April 2017) that says E43 rejoins.

def with_feed(t, n=400, seed=3):
    """t plus n feed stories that name no store company: in stories, not in story_entities, never embedded."""
    st = t["stories"]
    extra = st.sample(n, random_state=seed).assign(story_id=np.arange(10**6, 10**6 + n), symbols=[["ZZZ"]] * n)
    return {**t, "stories": pd.concat([st, extra], ignore_index=True)}


def embedded(t):
    linked = t["stories"][t["stories"].story_id.isin(set(t["story_entities"].story_id))]
    return synthetic.make_embeddings({"stories": linked.reset_index(drop=True)})


def rejoin_pair():
    """World A as built (E43 rejoins on 2017-04-03) and World B where E43 never rejoins: B has no second membership
    and none of E43's stories from its gap on."""
    a = with_feed(BASE)
    a["embeddings"] = embedded(a)
    b = {k: v.copy() for k, v in a.items()}
    m = b["membership"]
    b["membership"] = m[~((m.entity_id == "E43") & (m.member_from == pd.Timestamp("2017-04-03")))].reset_index(drop=True)
    day = pd.to_datetime(b["stories"].created_at, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    gap = set(b["stories"].story_id[(day >= pd.Timestamp("2016-06-15")).to_numpy()])
    se = b["story_entities"]
    b["story_entities"] = se[~((se.entity_id == "E43") & se.story_id.isin(gap))].reset_index(drop=True)
    b["embeddings"] = embedded(b)
    return a, b


def test_an_embedding_shows_nothing_of_a_later_rejoin():
    a, b = rejoin_pair()
    t = Clock().decision_time("2016-12-30")
    va, vb = World(**a).view(t), World(**b).view(t)
    assert va.story_entities.reset_index(drop=True).equals(vb.story_entities.reset_index(drop=True))
    assert va.embeddings.rows.reset_index(drop=True).equals(vb.embeddings.rows.reset_index(drop=True))


class UnlinkedCount(ReversalAgent):
    """Reads only the view: a tiny tilt by how many visible embeddings have no visible link (the judge's agent)."""

    def score(self, f, v):
        n = len(set(v.embeddings.rows.story_id) - set(v.story_entities.story_id))
        return super().score(f, v) + 1e-6 * n


def test_an_agent_that_counts_unlinked_embeddings_decides_the_same_with_or_without_the_rejoin():
    a, b = rejoin_pair()
    mk = lambda: UnlinkedCount(warmup=15)  # noqa: E731
    assert leaks.compare(leaks.decisions_until(a, mk, "2016-10-03", "2016-12-30"),
                         leaks.decisions_until(b, mk, "2016-10-03", "2016-12-30")) == []


def test_an_embedding_whose_links_are_all_hidden_is_never_shown():
    """A story linked only to E43 from deep in its gap: the story shows, its embedding doesn't until the link does."""
    a, _ = rejoin_pair()
    w = World(**a)
    se, st = a["story_entities"], a["stories"].set_index("story_id")
    day = pd.to_datetime(st.created_at, utc=True).dt.tz_convert("America/New_York")
    sid = next(int(s) for s in se.story_id[se.entity_id == "E43"]
               if pd.Timestamp("2016-09-01", tz="America/New_York") <= day[s] < pd.Timestamp("2016-12-01", tz="America/New_York"))
    v = w.view(Clock().decision_time("2016-12-30"))
    assert sid in set(v.stories.story_id) and sid not in set(v.embeddings.rows.story_id)
