"""M3 step 1: SPY's bars and the sector table, for the evaluation only (research/m3_kickoff.md, decision 4)."""
import pandas as pd
import pytest

from data_pipeline import benchmarks as b
from data_pipeline.settings import DATA_DIR, ROOT
from eval.benchmarks import sector_on
from world.clock import Clock

STORE = DATA_DIR / "store"
needs_tables = pytest.mark.skipif(not (STORE / "spy.parquet").exists() or not (STORE / "sectors.parquet").exists(),
                                  reason="run python -m data_pipeline.benchmarks first")

WIKI = """{| class="wikitable sortable" id="constituents"
! Symbol !! Security !! [[Global Industry Classification Standard|GICS Sector]] !! GICS Sub-Industry !! CIK
|-
| {{NyseSymbol|AAA}} || [[Alpha Inc.]] || [[Information Technology]] || Software || 0000000001
|-
| {{NyseSymbol|BBB}} || Beta Corp || Health Care<ref>note</ref> || Drugs || 2
|-
| {{NyseSymbol|CCC}} || Gamma || || Banks || 0000000003
|}"""


def test_sectors_are_read_from_a_revision_with_links_and_notes_removed():
    assert b.sectors_in(WIKI) == [("0000000001", "Information Technology"), ("0000000002", "Health Care")]


def _monthly(rows):
    return pd.DataFrame([{"stamp": pd.Timestamp(s), "cik": c, "sector": x} for s, c, x in rows])


def test_sector_runs_follow_changes_merge_spellings_and_skip_a_revision_with_two_sectors():
    m = _monthly([("2016-01-01", "1", "Telecommunications Services"), ("2016-02-01", "1", "Telecommunication Services"),
                  ("2016-03-01", "1", "Communication Services"), ("2016-04-01", "1", "Communications Services"),
                  ("2016-01-01", "2", "Energy"), ("2016-02-01", "2", "Energy"), ("2016-02-01", "2", "Materials"),
                  ("2016-03-01", "2", "Energy"), ("2016-01-01", "9", "Utilities")])
    spells, dropped = b.sector_spells(m, {"1": "E1", "2": "E2"})
    assert dropped == 1
    got = [(r.entity_id, r.sector, str(r.valid_from.date()), str(r.valid_to.date())) for r in spells.itertuples()]
    assert got == [("E1", "Telecommunication Services", "2016-01-01", "2016-02-01"),
                   ("E1", "Communication Services", "2016-03-01", "2016-04-01"),
                   ("E2", "Energy", "2016-01-01", "2016-03-01")]


def test_a_cik_of_two_entities_stops_the_build():
    with pytest.raises(ValueError):
        b.entity_of_cik(pd.DataFrame({"entity_id": ["E1", "E2"], "ciks": ["1 2", "2"]}))


def test_sector_on_takes_the_latest_run_and_falls_back_to_the_first():
    s = pd.DataFrame({"entity_id": ["E1", "E1"], "sector": ["Telecommunication Services", "Communication Services"],
                      "valid_from": pd.to_datetime(["2016-01-01", "2018-10-01"]),
                      "valid_to": pd.to_datetime(["2018-09-01", "2019-12-01"])})
    assert sector_on(s, ["E1", "E9"], "2015-06-01") == {"E1": "Telecommunication Services", "E9": None}
    assert sector_on(s, ["E1"], "2018-09-30") == {"E1": "Telecommunication Services"}
    assert sector_on(s, ["E1"], "2018-10-01") == {"E1": "Communication Services"}


def test_spy_table_dates_bars_in_new_york_and_returns_from_adjusted_closes():
    t = ["2016-01-04T05:00:00Z", "2016-01-05T05:00:00Z", "2016-01-06T05:00:00Z"]
    raw = pd.DataFrame({"t": t, "open": [200.0, 201, 202], "close": [201.0, 202, 200], "volume": [10, 20, 30]})
    adj = pd.DataFrame({"t": t, "open": [180.0, 181, 182], "close": [180.0, 189, 180]})
    out = b.spy_table(raw, adj)
    assert list(out.date.dt.strftime("%Y-%m-%d")) == ["2016-01-04", "2016-01-05", "2016-01-06"]
    assert out.ret.isna().tolist() == [True, False, False]
    assert out.ret.iloc[1] == pytest.approx(0.05) and out.ret.iloc[2] == pytest.approx(180 / 189 - 1)
    with pytest.raises(ValueError):
        b.spy_table(raw, adj.iloc[:2])


def test_the_world_never_loads_the_evaluation_tables():
    """World.load reads a fixed list of tables; neither of these is in it, so no View holds them."""
    src = (ROOT / "world" / "world.py").read_text(encoding="utf-8")
    assert "spy" not in src.lower() and "sectors" not in src.lower()
    assert "spy" not in (ROOT / "world" / "view.py").read_text(encoding="utf-8").lower()


@needs_tables
def test_spy_has_a_bar_on_every_session_of_the_store():
    spy = pd.read_parquet(STORE / "spy.parquet")
    sessions = Clock().between("2016-01-04", b.data_through().isoformat())
    assert list(spy.date) == list(sessions)
    assert spy.ret.iloc[1:].notna().all() and (spy[["open", "close", "adj_open", "adj_close"]] > 0).all().all()


@needs_tables
def test_every_member_in_the_warm_up_and_dev_years_has_a_sector_but_a_few_day_stub():
    """Bemis (member 2019-06-07 to 2019-06-11) is the only member from 2016 to 2019 with no sector; it can't be picked,
    since a pick ranks a year of dollar volume."""
    sectors = pd.read_parquet(STORE / "sectors.parquet")
    m = pd.read_parquet(STORE / "membership.parquet")
    lived = m[(m.member_from <= "2019-12-31") & (m.member_to.isna() | (m.member_to >= "2016-01-01"))]
    missing = set(lived.entity_id) - set(sectors.entity_id)
    assert missing == {"0000011199"}
