"""The official print check (research/verify_prints.py) on made-up trade lists, with no network.

Run with: python -m pytest tests
"""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

SPEC = importlib.util.spec_from_file_location("verify_prints", Path(__file__).resolve().parents[1] / "research" / "verify_prints.py")
vp = importlib.util.module_from_spec(SPEC)  # research/ is not a package
SPEC.loader.exec_module(vp)
NY = ZoneInfo("America/New_York")
DAY = "2024-03-14"  # an ordinary session, 9:30 to 16:00


def trade(day, hms, exchange, price, size, *conditions):
    """One trade as Alpaca's trades endpoint returns it, from a New York time."""
    t = datetime.fromisoformat(f"{day}T{hms}").replace(tzinfo=NY).astimezone(timezone.utc)
    return {"t": t.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "x": exchange, "p": price, "s": size, "c": ["@", *conditions]}


@pytest.fixture
def tape(monkeypatch):
    """A made-up list of trades, served window by window in place of Alpaca's. Any real request fails the test."""
    trades = []
    at = lambda t: datetime.fromisoformat(t["t"].replace("Z", "+00:00"))
    monkeypatch.setattr(vp, "_trades", lambda symbol, asof, start, end: [t for t in trades if start <= at(t) < end])
    monkeypatch.setattr(vp.alpaca, "get", lambda *args, **kwargs: pytest.fail("network request"))
    return trades


def run(day, bar_open, bar_close):
    return dict(zip(vp.HEADER, vp.check({"symbol": "TEST", "date": day, "bar_open": str(bar_open), "bar_close": str(bar_close)})))


def test_the_output_keeps_the_old_columns():
    old = ["symbol", "date", "bar_open", "official_open", "bar_close", "official_close", "open_gap", "close_gap",
           "trades_seen", "verdict", "all_open_prints", "all_close_prints", "open_print", "close_print", "open_spread",
           "close_spread"]
    assert vp.HEADER == old + ["listing_exchange", "open_checked", "close_checked"]


def test_a_late_nyse_close_after_a_small_arca_print(tape):
    tape += [trade(DAY, "09:30:16", "N", 50.0, 800_000, "O"), trade(DAY, "09:30:16", "N", 50.0, 800_000, "Q"),
             trade(DAY, "16:00:00", "P", 39.0, 1_000, "6"),  # Arca's own closing print comes first
             trade(DAY, "16:04:46", "N", 40.0, 500_000, "6"), trade(DAY, "16:04:46", "N", 40.0, 500_000, "M")]
    out = run(DAY, 50.0, 40.0)
    assert out["listing_exchange"] == "NYSE"
    assert out["official_close"] == 40.0 and out["close_checked"]
    assert out["close_print"] == "40.0 on N, 500000 shares at 16:04:46"
    assert out["verdict"] == "matches"


def test_a_13_00_early_close(tape):
    day = "2023-07-03"  # the NYSE closed at 13:00
    tape += [trade(day, "09:30:00", "N", 50.0, 5_000, "O"),
             trade(day, "13:00:01", "N", 51.0, 80_000, "6"), trade(day, "13:00:01", "N", 51.0, 80_000, "M")]
    out = run(day, 50.0, 51.0)
    assert out["official_close"] == 51.0 and out["close_checked"]
    assert out["verdict"] == "matches"


def test_a_missing_close_is_not_judged(tape):
    tape += [trade(DAY, "09:30:00", "N", 50.0, 100_000, "O"),
             trade(DAY, "16:00:00", "P", 45.0, 1_000, "6")]  # no NYSE closing print, only Arca's
    out = run(DAY, 50.0, 49.0)
    assert out["listing_exchange"] == "NYSE"
    assert out["official_close"] is None and not out["close_checked"] and out["open_checked"]
    assert out["verdict"] == "open only"


def test_a_0_3_percent_open_gap(tape):
    tape += [trade(DAY, "09:30:00", "N", 100.0, 50_000, "O"), trade(DAY, "16:00:00", "N", 101.0, 400_000, "6")]
    assert run(DAY, 100.3, 101.0)["verdict"] == "MISMATCH open"
    assert run(DAY, 100.2, 101.0)["verdict"] == "matches"


def test_a_one_cent_gap_on_a_cheap_stock(tape):
    tape += [trade(DAY, "09:30:00", "T", 2.0, 30_000, "O"), trade(DAY, "09:30:00", "Q", 2.0, 30_000, "Q"),
             trade(DAY, "16:00:00", "Q", 2.5, 200_000, "6"), trade(DAY, "16:00:00", "Q", 2.5, 200_000, "M")]
    out = run(DAY, 2.01, 2.49)  # half a percent off on both sides, but only a cent
    assert out["listing_exchange"] == "Nasdaq"
    assert out["verdict"] == "matches"
    assert run(DAY, 2.02, 2.5)["verdict"] == "MISMATCH open"


def test_a_delayed_nyse_open_after_small_prints_elsewhere(tape):
    tape += [trade(DAY, "09:30:00", "P", 49.0, 2_000, "O"), trade(DAY, "09:30:00", "T", 49.1, 1_500, "O"),
             trade(DAY, "09:37:36", "N", 50.0, 30_000, "O"), trade(DAY, "16:00:00", "N", 51.0, 600_000, "6")]
    out = run(DAY, 50.0, 51.0)
    assert out["official_open"] == 50.0 and out["open_checked"]
    assert out["verdict"] == "matches"


@pytest.mark.parametrize("trades, verdict", [
    ([], "no trades under this symbol that day"),
    ([trade(DAY, "10:00:00", "N", 50.0, 100)], "no auction prints found"),
    ([trade(DAY, "16:00:00", "N", 51.0, 600_000, "6")], "close only"),
    ([trade(DAY, "09:30:00", "N", 48.0, 9_000, "O"), trade(DAY, "16:00:00", "N", 52.0, 600_000, "6")],
     "MISMATCH open and close"),
])
def test_other_verdicts(tape, trades, verdict):
    tape += trades
    assert run(DAY, 50.0, 51.0)["verdict"] == verdict


def test_a_day_off_is_an_error(tape):
    assert run("2023-07-04", 50.0, 51.0)["verdict"] == "error: 2023-07-04 is not an NYSE session"
