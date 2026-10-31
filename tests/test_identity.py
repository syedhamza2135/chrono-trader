"""Invariants of the identity tables (reference/*.csv), and the cases that went wrong before they existed.

Run with: python -m pytest tests
"""
from datetime import date, timedelta

import pandas as pd
import pytest

from data_pipeline.bars import spell_class
from data_pipeline.identity import OUT, REFERENCE, SymbolIndex, overlaps

ENTITIES = pd.read_csv(REFERENCE / "entities.csv", dtype=str).fillna("")
ROWS = pd.read_csv(OUT, dtype=str).fillna("")
MEMBERS = pd.read_csv(REFERENCE / "memberships.csv", dtype=str).fillna("")
INDEX = SymbolIndex()


def _d(s):
    return date.fromisoformat(s) if s else None


def members_on(day):
    return {r.entity_id for r in MEMBERS.itertuples() if _d(r.member_from) <= day and (not r.member_to or day < _d(r.member_to))}


def test_every_member_company_is_described():
    assert set(MEMBERS.entity_id) <= set(ENTITIES.entity_id)
    assert (ENTITIES.name != "").all()
    assert ENTITIES.ciks.str.fullmatch(r"\d{10}( \d{10})*").all()


def test_no_ticker_means_two_companies_on_one_day():
    rows = ROWS.assign(valid_from=pd.to_datetime(ROWS.valid_from).dt.date,
                       valid_to=pd.to_datetime(ROWS.valid_to.replace("", None)).dt.date)
    assert overlaps(rows).empty


def test_rows_of_one_class_follow_each_other():
    # A class is one listing: its tickers follow each other in time (UA, then UAA for Under Armour's class A).
    for (e, k), g in ROWS.groupby(["entity_id", "share_class"]):
        spans = sorted((_d(r.valid_from), _d(r.valid_to) or date.max) for r in g.itertuples())
        for a, b in spans:
            assert a <= b, f"{e} class {k!r}: row runs backwards, {a}..{b}"
        for (a, b), (c, d) in zip(spans, spans[1:]):
            assert b < c, f"{e} class {k!r}: {a}..{b} overlaps {c}..{d}"


@pytest.mark.parametrize("ticker,company,expected", [
    ("UAA", "Under Armour", "A"), ("UA", "Under Armour", "C"),  # UA meant class A until 2016-12-06, class C after
    ("DISCA", "Discovery", "A"), ("DISCK", "Discovery", "C"), ("GOOGL", "Alphabet", "A"), ("GOOG", "Alphabet", "C"),
    ("FOXA", "Fox Corporation", "A"), ("FOX", "Fox Corporation", "B"), ("NWSA", "News Corp", "A"), ("NWS", "News Corp", "B"),
])
def test_each_class_period_uses_its_own_class(ticker, company, expected):
    ents = set(ENTITIES[ENTITIES.name.str.contains(company)].entity_id)
    periods = MEMBERS[MEMBERS.entity_id.isin(ents) & (MEMBERS.source_ticker == ticker)]
    assert len(periods) == 1
    m = periods.iloc[0]
    assert spell_class(ROWS[ROWS.entity_id == m.entity_id], ticker, _d(m.member_from), _d(m.member_to) or date.max) == expected


def test_membership_periods_of_one_listing_do_not_overlap():
    # Two share classes of one company (DISCA and DISCK) are both members at once; one listing never is twice,
    # whatever ticker the membership file used (it listed Michael Kors as both KORS and CPRI for 2016-2018).
    spans = {}
    for r in MEMBERS.itertuples():
        mine = ROWS[ROWS.entity_id == r.entity_id]
        k = spell_class(mine, r.source_ticker, _d(r.member_from), _d(r.member_to) or date.max) if mine.share_class.nunique() > 1 else ""
        spans.setdefault((r.entity_id, k), []).append((_d(r.member_from), _d(r.member_to) or date.max))
    for (e, k), s in spans.items():
        s.sort()
        for (a, b), (c, d) in zip(s, s[1:]):
            assert b <= c, f"{e} class {k!r}: {a}..{b} overlaps {c}..{d}"


def test_every_member_day_has_a_ticker():
    for r in MEMBERS.itertuples():
        start = max(_d(r.member_from), date(2016, 1, 1))
        end = (_d(r.member_to) - timedelta(days=1)) if r.member_to else date(2026, 10, 1)
        if end < start:
            continue
        mine = ROWS[ROWS.entity_id == r.entity_id]
        for day in (start, start + (end - start) / 2, end):
            ok = any(_d(x.valid_from) <= day and (not x.valid_to or day <= _d(x.valid_to)) for x in mine.itertuples())
            assert ok, f"{r.entity_id} has no ticker on {day}"


@pytest.mark.parametrize("day", [date(y, m, 15) for y in range(2015, 2027) for m in (1, 7) if date(y, m, 15) < date(2026, 10, 1)])
def test_about_500_member_companies(day):
    # 503-505 listed securities; Alphabet, Fox, News Corp and others list two classes, so slightly fewer companies
    assert 490 <= len(members_on(day)) <= 506


@pytest.mark.parametrize("tag,day,expected", [
    ("FB", date(2020, 1, 2), "Meta"), ("META", date(2023, 1, 3), "Meta"),
    ("META", date(2021, 7, 1), None),  # Roundhill's Metaverse ETF held the ticker then
    ("DOC", date(2023, 1, 3), None),  # Physicians Realty, not a member
    ("DOC", date(2025, 1, 3), "Healthpeak"),
    ("PCLN", date(2016, 6, 1), "Booking"), ("BRK/B", date(2019, 5, 1), "Berkshire"), ("BRK", date(2019, 5, 1), "Berkshire"),
    ("YHOO", date(2016, 6, 1), "Yahoo"), ("IR", date(2019, 6, 3), "Trane"), ("IR", date(2021, 6, 1), "Ingersoll"),
    ("CB", date(2015, 6, 1), "Chubb Corp"), ("ACE", date(2015, 6, 1), "Chubb Limited"),
])
def test_tags_map_to_the_right_company(tag, day, expected):
    names = {ENTITIES.set_index("entity_id").name.get(e, "") for e in INDEX.lookup(tag, day)}
    if expected is None:
        assert not names
    else:
        assert len(names) == 1 and expected.lower() in next(iter(names)).lower(), names


def test_both_chubbs_were_members_in_2015():
    on = members_on(date(2015, 6, 1))
    chubbs = ENTITIES[ENTITIES.name.str.contains("Chubb")].entity_id
    assert len(set(chubbs) & on) == 2
