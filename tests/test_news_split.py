"""The news audit's story counts and the split's sums, on small synthetic frames. Years and dates are New York time.

Run with: python -m pytest tests
"""
from datetime import date

import exchange_calendars as xcals
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from data_pipeline import audit_news, split
from data_pipeline.audit_prices import pick_dates

CALENDAR = xcals.get_calendar("XNYS")
PICKS = pick_dates(CALENDAR.sessions_in_range("2016-01-01", "2017-12-29"))  # 2016-04-01, then 2017-01-03


@pytest.fixture
def members(tmp_path, monkeypatch):
    """Company A is a member throughout. B joins on 2016-06-01 and leaves on 2017-01-03 (member_to is exclusive)."""
    (tmp_path / "reference").mkdir()
    pd.DataFrame({"entity_id": ["A", "B"], "member_from": ["2010-01-04", "2016-06-01"], "member_to": ["", "2017-01-03"]}) \
        .to_csv(tmp_path / "reference" / "memberships.csv", index=False)
    monkeypatch.setattr(audit_news, "ROOT", tmp_path)


def stories(rows):
    """Benzinga stories as load() and companies() leave them, from (id, created_at in UTC, companies named)."""
    df = pd.DataFrame(rows, columns=["id", "created_at", "entities"])
    df["ny"] = pd.to_datetime(df.created_at, utc=True).dt.tz_convert("America/New_York")
    df["year"] = df.ny.dt.year
    df["entities"] = df.entities.apply(tuple)
    return df


def single_firm(df):
    """The frame main() hands to reading_load and by_day: one row per story and company, with the New York date."""
    return df[["id", "year", "entities"]].assign(day=df.ny.dt.date).explode("entities").dropna(subset=["entities"])


def test_years_are_new_york_years(tmp_path, monkeypatch):
    stamps = ["2017-01-01T03:00:00Z", "2017-01-01T06:00:00Z"]  # 22:00 on New Year's Eve in New York, then 01:00
    pq.write_table(pa.table({"id": [1, 2], "created_at": stamps, "updated_at": stamps, "headline": ["", ""],
                             "source": ["", ""], "url": ["", ""], "symbols": [["A"], ["A"]]}), tmp_path / "2017-01.parquet")
    monkeypatch.setattr(audit_news, "NEWS", tmp_path)
    df = audit_news.load().sort_values("id")
    assert list(df.year) == [2016, 2017]
    assert list(df.ny.dt.date) == [date(2016, 12, 31), date(2017, 1, 1)]


def test_picked_stories_count_from_the_pick_date(members):
    df = stories([
        (1, "2016-03-31T15:00:00Z", ["A"]),  # before the first list, picked on 2016-04-01
        (2, "2016-04-01T15:00:00Z", ["A"]),
        (3, "2017-01-02T15:00:00Z", ["A"]),  # a holiday, before the 2017 list is picked on 2017-01-03
        (4, "2017-01-03T15:00:00Z", ["A"]),
    ])
    picked = pd.DataFrame({"year": [2016, 2017], "entity_id": ["A", "A"]})
    assert audit_news.reading_load(single_firm(df), picked, PICKS) == [
        {"year": 2016, "members": 2, "picked": 1}, {"year": 2017, "members": 2, "picked": 1}]


def test_daily_counts_use_new_york_dates_and_member_days(members):
    df = stories([
        (1, "2015-12-31T15:00:00Z", ["A"]),  # before 2016: not counted
        (2, "2016-05-31T15:00:00Z", ["B"]),  # B isn't a member yet
        (3, "2016-06-01T15:00:00Z", ["A", "B"]),  # names two members, counts once
        (4, "2016-06-02T00:30:00Z", ["B"]),  # 20:30 on 2016-06-01 in New York
        (5, "2017-01-03T15:00:00Z", ["B"]),  # B has left
    ])
    assert audit_news.by_day(df, single_firm(df)).to_dict("index") == {
        date(2016, 5, 31): {"stories": 1, "members": 0},
        date(2016, 6, 1): {"stories": 2, "members": 2},
        date(2017, 1, 3): {"stories": 1, "members": 0},
    }


def split_counts():
    """The warm-up and a dev period whose data ends on 2017-01-04, over stories on dates in and between them."""
    sessions = CALENDAR.sessions_in_range("2016-01-01", "2017-01-04")
    members = pd.DataFrame({"entity_id": ["A"], "member_from": pd.to_datetime(["2010-01-04"]), "member_to": pd.to_datetime([None])})
    dates = ["2016-01-03", "2016-01-04", "2016-12-30", "2016-12-31", "2017-01-02", "2017-01-03", "2017-01-05"]
    daily = pd.DataFrame({"date": pd.to_datetime(dates), "stories": [1, 2, 4, 8, 16, 32, 64], "members": [1] * 7})
    return (split.counts("2016-01-01", "2016-12-31", sessions, members, daily),
            split.counts("2017-01-01", str(sessions[-1].date()), sessions, members, daily))


def test_split_counts_stories_from_the_first_session_to_the_last():
    warm_up, dev = split_counts()
    assert (warm_up["start"], warm_up["end"], warm_up["benzinga_stories"]) == ("2016-01-04", "2016-12-30", 2 + 4)
    assert warm_up["single_firm_stories_about_members"] == 2
    assert (warm_up["first_pick"], warm_up["picked_stock_days"]) == ("2016-04-01", 50 * 191)
    # Nothing from the days between the periods, or from 2017-01-05, after the last session
    assert (dev["start"], dev["end"], dev["benzinga_stories"], dev["single_firm_stories_about_members"]) == (
        "2017-01-03", "2017-01-04", 32, 1)


def test_split_counts_nothing_that_rests_on_the_picks():
    # The picks are ranked on price times volume, so stories about them stay out of split.json
    for period in split_counts():
        assert set(period) == {"start", "end", "sessions", "first_pick", "picked_stock_days", "member_company_days",
                               "benzinga_stories", "single_firm_stories_about_members"}
