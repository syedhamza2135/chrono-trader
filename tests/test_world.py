"""The time wall (world/): the clock, the availability rules and World.view(t), on made-up records.

Run with: python -m pytest tests
"""
import pandas as pd
import pytest

from world import rules
from world.clock import Clock, at
from world.world import World

UTC = lambda s: pd.Timestamp(s, tz="UTC")
NYT = lambda s: pd.Timestamp(s, tz="America/New_York").tz_convert("UTC")


# The clock

def test_nine_in_new_york_is_14_utc_in_winter_and_13_in_summer():
    c = Clock()
    assert c.decision_time("2021-03-12") == UTC("2021-03-12 14:00")  # Friday, still EST
    assert c.decision_time("2021-03-15") == UTC("2021-03-15 13:00")  # Monday after the change to EDT
    assert c.decision_time("2021-11-05") == UTC("2021-11-05 13:00")  # Friday, still EDT
    assert c.decision_time("2021-11-08") == UTC("2021-11-08 14:00")  # Monday after the change back


def test_early_closes_and_holidays_come_from_the_nyse_calendar():
    c = Clock()
    assert c.close_time("2019-11-29") == NYT("2019-11-29 13:00")  # the day after Thanksgiving
    assert c.close_time("2019-11-27") == NYT("2019-11-27 16:00")
    assert not c.is_session("2019-11-28") and not c.is_session("2019-11-30")
    assert c.next_session("2019-11-27") == pd.Timestamp("2019-11-29")
    assert c.previous_session("2019-12-02") == pd.Timestamp("2019-11-29")


# The rules

def test_a_story_is_available_15_minutes_after_its_last_update():
    got = rules.story(pd.Series(["2020-01-06T13:59:00Z"]))
    assert got.iloc[0] == UTC("2020-01-06 14:14")


def test_a_story_edited_more_than_3_days_after_publishing_is_dropped():
    created = pd.Series(["2020-01-06T10:00:00Z"] * 2)
    keep = rules.keep_story(created, pd.Series(["2020-01-09T10:00:00Z", "2020-01-09T10:00:01Z"]))
    assert list(keep) == [True, False]


def test_a_bar_is_available_at_16_new_york_time_also_on_an_early_close_and_across_daylight_saving():
    got = rules.bar(pd.Series(pd.to_datetime(["2021-03-12", "2021-03-15", "2019-11-29"])))
    assert list(got) == [UTC("2021-03-12 21:00"), UTC("2021-03-15 20:00"), UTC("2019-11-29 21:00")]


def test_the_vendors_bar_timestamp_is_not_the_close_time():
    """Alpaca stamps a daily bar at midnight UTC, which is the evening before in New York."""
    vendor = UTC("2021-03-15 00:00")
    assert rules.bar(pd.Series([pd.Timestamp("2021-03-15")])).iloc[0] > Clock().decision_time("2021-03-15") > vendor


def test_a_label_is_available_at_the_open_that_ends_it():
    got = rules.label(pd.Series(pd.to_datetime(["2021-03-15", "2019-11-27", "2019-11-29"])), [False, True, True])
    assert got.iloc[0] == NYT("2021-03-15 09:30")
    assert got.iloc[1] == NYT("2019-11-29 09:30")  # an exit on Wednesday shows at Friday's open, after Thanksgiving
    assert got.iloc[2] == NYT("2019-12-02 09:30")  # an exit on Friday shows on Monday


def test_a_membership_change_is_available_from_midnight_on_its_effective_date():
    assert rules.membership(pd.Series([pd.Timestamp("2020-12-21")])).iloc[0] == NYT("2020-12-21 00:00")


# The view

def make_world(**changes):
    days = pd.to_datetime(["2021-03-11", "2021-03-12", "2021-03-15", "2021-03-16"]).astype("datetime64[ns]")
    bars = pd.DataFrame({"entity_id": ["A"] * 4 + ["B"] * 4, "share_class": "", "symbol": ["AAA"] * 4 + ["BBB"] * 4,
                         "date": list(days) * 2, "close": [1.0, 2, 3, 4, 10, 20, 30, 40], "ret": 0.0,
                         "member": True})
    labels = pd.DataFrame({"entity_id": ["A"] * 3, "share_class": "", "date": days[:3], "end": days[1:],
                           "label": [0.1, 0.2, 0.3], "at_close": False})
    opens = pd.DataFrame({"entity_id": ["A"], "share_class": "", "date": days[:1], "open": [1.0]})
    stories = pd.DataFrame({"story_id": [1, 2], "created_at": [UTC("2021-03-15 12:00"), UTC("2021-03-15 12:50")],
                            "updated_at": [UTC("2021-03-15 12:00"), UTC("2021-03-15 12:50")],
                            "headline": ["early", "late"], "symbols": [["AAA"], ["BBB"]]})
    story_entities = pd.DataFrame({"story_id": [1, 2], "entity_id": ["A", "B"]})
    membership = pd.DataFrame({"entity_id": ["A", "B"], "member_from": pd.to_datetime(["2010-01-04", "2021-03-15"]),
                               "member_to": pd.to_datetime(["2021-03-16", None])})
    tables = dict(bars=bars, labels=labels, opens=opens, stories=stories, story_entities=story_entities,
                  membership=membership)
    tables.update(changes)
    return World(**tables, allow_sealed=True)  # made-up records; 2021 is in the sealed years


def test_yesterdays_close_is_in_the_view_and_todays_is_not():
    v = make_world().view(Clock().decision_time("2021-03-15"))
    assert v.bars[v.bars.entity_id == "A"].date.max() == pd.Timestamp("2021-03-12")


def test_at_nine_on_day_k_the_newest_label_is_day_k_minus_2s():
    v = make_world().view(Clock().decision_time("2021-03-16"))
    assert v.labels.date.max() == pd.Timestamp("2021-03-12")  # day k-2; day k-1's label ends at day k's open


def test_a_story_shows_15_minutes_after_its_update_to_the_nanosecond():
    w = make_world()
    assert list(w.view(UTC("2021-03-15 12:14:59.999999999")).stories.story_id) == []
    assert list(w.view(UTC("2021-03-15 12:15")).stories.story_id) == [1]


def test_a_company_shows_only_once_it_has_joined_and_then_with_its_history():
    w = make_world()
    before = w.view(UTC("2021-03-15 03:59"))  # B joins at 0:00 New York time on 2021-03-15 (04:00 UTC)
    assert "B" not in set(before.bars.entity_id) and before.members == {"A"}
    after = w.view(UTC("2021-03-15 04:00"))
    assert set(after.bars[after.bars.entity_id == "B"].date) == {pd.Timestamp("2021-03-11"), pd.Timestamp("2021-03-12")}
    assert after.members == {"A", "B"}


def test_a_story_about_a_company_that_has_not_joined_yet_is_hidden():
    membership = pd.DataFrame({"entity_id": ["A", "B"], "member_from": pd.to_datetime(["2010-01-04", "2021-03-16"]),
                               "member_to": pd.to_datetime([None, None])})
    v = make_world(membership=membership).view(UTC("2021-03-15 20:00"))
    assert list(v.stories.story_id) == [1, 2]  # the news itself is public
    assert list(v.story_entities.entity_id) == ["A"]  # but B's link to it would say B joins later


def test_a_removal_shows_on_its_effective_date_and_the_company_stays_known():
    w = make_world()
    assert "A" in w.view(UTC("2021-03-16 03:59")).members
    v = w.view(UTC("2021-03-16 04:00"))
    assert "A" not in v.members and "A" in v.joined


def test_a_view_needs_a_time_zone():
    with pytest.raises(ValueError):
        make_world().view(pd.Timestamp("2021-03-15 09:00"))


def test_the_world_leaves_the_frames_it_is_given_unchanged():
    frame = pd.DataFrame({"entity_id": ["A"], "share_class": "", "symbol": "AAA", "date": [pd.Timestamp("2021-03-11")],
                          "close": [1.0], "ret": [0.0], "member": [True]})
    before = frame.copy()
    make_world(bars=frame)
    pd.testing.assert_frame_equal(frame, before)


def test_a_view_is_a_copy_that_reaches_no_later_row():
    """Nothing reachable from a view's columns (following .base) is longer than the view, and no column carries a
    category list naming companies or tickers the view doesn't hold."""
    v = make_world().view(Clock().decision_time("2021-03-15"))
    for name in ("bars", "labels", "stories", "story_entities"):
        df = getattr(v, name)
        for c in df.columns:
            assert not isinstance(df[c].dtype, pd.CategoricalDtype), (name, c)
            a = df[c].to_numpy()
            while a is not None:
                assert max(getattr(a, "shape", (0,)) or (0,)) <= max(len(df), len(df.columns)), (name, c)
                a = getattr(a, "base", None)
    assert set(v.bars.entity_id.value_counts().index) == set(v.bars.entity_id)


def test_a_views_list_columns_reach_no_other_rows(tmp_path):
    """Parquet hands each story's tags as a view into one array of every story's tags; a view's must be its own."""
    stories = make_world().stories.df.drop(columns="visible_at")
    stories.to_parquet(tmp_path / "s.parquet")
    back = pd.read_parquet(tmp_path / "s.parquet")
    assert back.symbols.iloc[0].base is not None  # the trap is real
    v = make_world(stories=back).view(UTC("2021-03-15 12:15"))
    assert len(v.stories) == 1 and all(getattr(x, "base", None) is None for x in v.stories.symbols)


def test_a_company_with_no_membership_never_shows():
    """A missing join time once wrapped to the smallest int64 and let every such row through."""
    bars = pd.DataFrame({"entity_id": ["A", "Z"], "share_class": "", "symbol": ["AAA", "ZZZ"],
                         "date": pd.to_datetime(["2021-03-11", "2021-03-11"]), "close": 1.0, "ret": 0.0,
                         "member": [True, False]})
    v = make_world(bars=bars).view(Clock().decision_time("2021-03-16"))
    assert list(v.bars.entity_id) == ["A"]


def test_a_rejoining_company_is_hidden_during_its_gap_and_shown_at_its_rejoin():
    days = pd.to_datetime(["2019-12-31", "2020-01-10", "2020-06-01", "2021-03-15"])
    bars = pd.DataFrame({"entity_id": "R", "share_class": "", "symbol": "RRR", "date": days, "close": 1.0,
                         "ret": 0.0, "member": [True, False, False, True]})
    membership = pd.DataFrame({"entity_id": ["R", "R"], "member_from": pd.to_datetime(["2010-01-04", "2021-03-15"]),
                               "member_to": pd.to_datetime(["2020-01-02", None])})
    w = make_world(bars=bars, membership=membership, story_entities=pd.DataFrame(columns=["story_id", "entity_id"]))
    gap = w.view(Clock().decision_time("2020-07-01")).bars
    assert list(gap.date.dt.strftime("%Y-%m-%d")) == ["2019-12-31", "2020-01-10"]  # the gap bar would say R rejoins
    back = w.view(NYT("2021-03-15 00:00"))
    assert "2020-06-01" in set(back.bars.date.dt.strftime("%Y-%m-%d"))


def test_the_sealed_years_need_the_seal():
    w = make_world()
    w.allow_sealed = False
    with pytest.raises(PermissionError):
        w.view(Clock().decision_time("2021-03-15"))
    assert make_world().view(Clock().decision_time("2021-03-15")) is not None


def test_a_label_ending_at_a_delayed_open_shows_when_that_open_printed():
    got = rules.label(pd.Series(pd.to_datetime(["2023-01-24", "2023-01-24"])), [False, False],
                      pd.Series([NYT("2023-01-24 09:38:25"), NYT("2023-01-24 09:30:01")]))
    assert list(got) == [NYT("2023-01-24 09:38:25"), NYT("2023-01-24 09:30:01")]  # when each open printed


def test_today_and_sessions_follow_new_york():
    v = make_world().view(Clock().decision_time("2021-03-15"))
    assert v.today == pd.Timestamp("2021-03-15") and v.sessions[-1] == pd.Timestamp("2021-03-15")
    assert at("2021-03-15", pd.Timestamp("09:00").time()) == v.t
