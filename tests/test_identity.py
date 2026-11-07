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
    ("TFCFA", "Twenty-First Century Fox", "A"), ("TFCF", "Twenty-First Century Fox", "B"),  # its last day, 2019-03-19
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
    # Every day since 2015, so a one-day member (Four Corners on 2015-11-10) is checked too.
    for r in MEMBERS.itertuples():
        start = max(_d(r.member_from), date(2015, 1, 1))
        end = (_d(r.member_to) - timedelta(days=1)) if r.member_to else date(2026, 10, 30)
        if end < start:
            continue
        covered = start - timedelta(days=1)  # every member day up to here has a ticker
        for a, b in sorted((_d(x.valid_from), _d(x.valid_to) or date.max) for x in ROWS[ROWS.entity_id == r.entity_id].itertuples()):
            if a <= covered + timedelta(days=1) <= b:
                covered = min(b, end)
        assert covered == end, f"{r.entity_id} has no ticker on {covered + timedelta(days=1)}"


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
    ("FCPT", date(2015, 11, 10), "Four Corners"),  # a one-day member Wikipedia's monthly lists never showed
    ("BMS", date(2019, 6, 7), "Bemis"), ("BMS", date(2019, 6, 10), "Bemis"),  # Amcor took the seat on 2019-06-11
    ("AMCR", date(2019, 6, 10), None), ("AMCR", date(2019, 6, 11), "Amcor"),
    ("TFCFA", date(2019, 3, 19), "Twenty-First Century Fox"), ("TFCF", date(2019, 3, 19), "Twenty-First Century Fox"),
    ("FOXA", date(2019, 3, 18), "Twenty-First Century Fox"), ("FOXA", date(2019, 3, 19), "Fox Corporation"),
    ("MBC", date(2022, 12, 16), "MasterBrand"), ("MBC", date(2022, 12, 19), None),
    # a class tag whose root is a listed ticker of the same company
    ("LEN.B", date(2019, 1, 2), "Lennar"), ("LEN/B", date(2026, 9, 22), "Lennar"), ("CBS.A", date(2018, 6, 1), "Paramount"),
    ("STZ.B", date(2022, 10, 25), "Constellation Brands"), ("BIO.B", date(2020, 7, 30), "Bio-Rad"),
    ("TAP.A", date(2022, 2, 24), "Molson Coors"), ("UA.C", date(2016, 12, 7), "Under Armour"),
    ("D.UN", date(2019, 1, 2), None), ("BA.", date(2019, 1, 2), None),  # other securities, not Dominion or Boeing
    ("CCL.A", date(2026, 10, 20), None), ("PNC.A", date(2026, 10, 22), None),  # TSX classes, not Carnival or PNC
    # a class added to the index in September 2015 names its company before that too
    ("FOX", date(2015, 6, 1), "Twenty-First Century Fox"), ("NWS", date(2015, 6, 1), "News Corp"),
    ("CMCSK", date(2015, 6, 1), "Comcast"),
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


@pytest.mark.parametrize("tags,day,count", [
    (["LEN", "LEN.B"], date(2019, 1, 2), 1), (["BRK.B", "BRK.A"], date(2019, 1, 2), 1), (["CBS", "CBS.A"], date(2018, 6, 1), 1),
    (["FOXA", "FOX"], date(2015, 6, 1), 1), (["NWSA", "NWS"], date(2015, 6, 1), 1), (["CMCSA", "CMCSK"], date(2015, 2, 23), 1),
    (["D", "D.UN"], date(2019, 1, 2), 2),
])
def test_a_company_counts_once_whatever_class_tags_a_story_carries(tags, day, count):
    assert INDEX.entities(tags, day)[1] == count


@pytest.mark.parametrize("company,day,member", [
    ("Four Corners Property Trust", date(2015, 11, 10), True), ("Four Corners Property Trust", date(2015, 11, 11), False),
    ("Twenty-First Century Fox", date(2019, 3, 19), True), ("Twenty-First Century Fox", date(2019, 3, 20), False),
    ("Fox Corporation", date(2019, 3, 18), False), ("Fox Corporation", date(2019, 3, 19), True),
    ("Bemis Company", date(2019, 6, 7), True), ("Bemis Company", date(2019, 6, 10), True), ("Bemis Company", date(2019, 6, 11), False),
    ("Amcor", date(2019, 6, 10), False), ("Amcor", date(2019, 6, 11), True),
    ("MasterBrand", date(2022, 12, 15), True), ("MasterBrand", date(2022, 12, 16), True), ("MasterBrand", date(2022, 12, 19), False),
])
def test_short_memberships_the_membership_file_leaves_out(company, day, member):
    # From the change log: Bemis held the seat for two sessions before Amcor, 21st Century Fox stayed one session
    # after Fox Corporation joined, and MasterBrand was a member for two sessions after its spin-off.
    ents = set(ENTITIES[ENTITIES.name == company].entity_id)
    assert len(ents) == 1
    assert bool(ents & members_on(day)) == member
