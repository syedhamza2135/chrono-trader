"""The rest of PLAN 9.11 that M1 adds: trading days, survivorship, large moves, shared return series, timestamp
anchors and the vintage rule. The audit files they read are in research/audit/; the store tests skip without it.

Run with: python -m pytest tests
"""
from pathlib import Path

import pandas as pd
import pytest

from data_pipeline.audit_news import recaps
from data_pipeline.settings import DATA_DIR
from reader.vintage import breaches, vintage_for
from world.clock import NY, Clock

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "research" / "audit"
STORE = DATA_DIR / "store"
needs_store = pytest.mark.skipif(not (STORE / "bars.parquet").exists(), reason="the event store isn't built")


def test_the_clock_has_no_sessions_on_holidays_or_days_of_mourning():
    c = Clock()
    for day in ("2016-07-04", "2018-12-05", "2020-12-25", "2025-01-09", "2026-04-03"):
        assert not c.is_session(day), day  # 2018-12-05 and 2025-01-09: national days of mourning


@needs_store
def test_decision_days_are_the_trading_days_in_the_price_data():
    bars = pd.read_parquet(STORE / "bars.parquet", columns=["symbol", "date", "member"])
    aapl = bars[(bars.symbol == "AAPL") & bars.member].date
    days = Clock().between(aapl.min(), aapl.max())
    assert list(days) == sorted(aapl)


@needs_store
def test_the_store_ends_on_the_datas_last_day():
    """A few bar files hold later bars (12, to 2026-10-30); a label ending there made the simulator think the data
    ran on, and sell every holding on the real last day."""
    import json
    end = pd.Timestamp(json.loads((ROOT / "reference" / "split.json").read_text())["data_through"])
    for name, col in (("bars", "date"), ("opens", "date"), ("labels", "end")):
        assert pd.read_parquet(STORE / f"{name}.parquet", columns=[col])[col].max() <= end, name


def test_every_member_on_each_pick_date_has_bars():
    s = pd.read_csv(AUDIT / "survivorship.csv", dtype={"missing": int})
    assert len(s) == 11 and (s.missing == 0).all()


def test_every_large_move_on_a_member_day_was_reviewed():
    m = pd.read_csv(AUDIT / "large_moves.csv", dtype=str)
    unreviewed = m[m.verdict.isna() & m.correction.isna()]
    assert len(m) > 0 and unreviewed.empty


def test_no_two_companies_share_a_return_series():
    assert pd.read_csv(AUDIT / "identity_shared_data.csv").empty


KNOWN_EARLY = {11575469, 12016835, 12509052, 17985961, 19245125}  # research/audit/news.md, 4 of them headline typos


@needs_store
def test_session_recaps_land_in_their_windows():
    """Benzinga's pre-market, mid-day and after-hours recaps, stamped in New York time, fall in or after their
    sessions. Timestamps that ran early (FNSPID's were 8 hours off) would put many before them."""
    st = pd.read_parquet(STORE / "stories.parquet", columns=["story_id", "created_at", "headline"])
    ny = pd.to_datetime(st.created_at, utc=True).dt.tz_convert(NY)
    rec = recaps(pd.DataFrame({"id": st.story_id, "year": ny.dt.year, "ny": ny, "headline": st.headline}))
    early = set(rec.id[rec.status == "early"].astype(int))
    assert len(rec) > 12000 and early <= KNOWN_EARLY


def test_each_story_gets_the_vintage_from_the_year_before_its_new_york_year():
    created = pd.Series(pd.to_datetime(["2019-12-31T23:50:00-05:00", "2020-01-01T05:10:00Z", "2016-06-01T12:00:00Z",
                                        "2025-06-02T12:00:00Z", "2026-03-02T12:00:00Z"], utc=True, format="ISO8601"))
    assert list(vintage_for(created)) == [2018, 2019, 2015, 2024, 2024]  # 2024 is the latest vintage


def test_the_vintage_check_flags_a_model_from_the_same_year():
    stories = pd.DataFrame({"story_id": [1, 2], "created_at": pd.to_datetime(["2020-03-02T15:00Z", "2020-03-02T15:00Z"])})
    emb = pd.DataFrame({"story_id": [1, 2], "vintage_year": [2019, 2020]})
    assert list(breaches(emb, stories).story_id) == [2]
    late = pd.DataFrame({"story_id": [3, 4], "created_at": pd.to_datetime(["2026-03-02T15:00Z", "2020-03-02T15:00Z"])})
    emb = pd.DataFrame({"story_id": [3, 4], "vintage_year": [2025, 2018]})  # no 2025 model; 2018 isn't the rule's
    assert list(breaches(emb, late).story_id) == [3, 4]


@needs_store
def test_every_embedded_story_was_read_by_an_earlier_vintage():
    """Embeddings arrive in M2; until then the table doesn't exist and there is nothing to breach."""
    path = STORE / "embeddings.parquet"
    if not path.exists():
        pytest.skip("no embeddings yet (M2)")
    stories = pd.read_parquet(STORE / "stories.parquet", columns=["story_id", "created_at"])
    assert breaches(pd.read_parquet(path, columns=["story_id", "vintage_year"]), stories).empty
