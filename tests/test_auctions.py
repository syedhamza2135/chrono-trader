"""The official auction prints (data_pipeline/auctions.py) on made-up prints, with no network.

Run with: python -m pytest tests
"""
import pandas as pd
import pytest

from data_pipeline import auctions


def prints(*rows):
    """Made-up prints: (date, side, hh:mm:ss UTC, exchange, price, size, condition), in Alpaca's order."""
    return pd.DataFrame(
        [("TEST", "2024-01-02", d, side, pd.Timestamp(f"{d}T{hms}Z"), x, p, s, c) for d, side, hms, x, p, s, c in rows],
        columns=auctions.PRINT_COLUMNS)


def one(df, date):
    return auctions.official(df).set_index("date").loc[date]


def test_an_nyse_day_takes_the_nyse_auctions_and_ignores_small_prints_elsewhere():
    df = prints(("2024-03-14", "o", "13:30:00", "P", 100.5, 40, "Q"),
                ("2024-03-14", "o", "13:30:02", "N", 101.0, 9000, "O"),
                ("2024-03-14", "o", "13:30:02", "N", 101.0, 9000, "Q"),
                ("2024-03-14", "c", "20:00:00", "T", 99.0, 300, "M"),
                ("2024-03-14", "c", "20:00:02", "N", 98.5, 20000, "6"))
    r = one(df, "2024-03-14")
    assert r.listing_exchange == "NYSE"
    assert (r.open, r.open_size, r.close, r.close_size) == (101.0, 9000, 98.5, 20000)
    assert r.open_time == pd.Timestamp("2024-03-14T13:30:02Z")
    assert (r.n_open_prints, r.n_close_prints) == (3, 2)


def test_nasdaq_prints_under_q_t_and_s_count_as_one_exchange():
    df = prints(("2024-03-14", "o", "13:30:00", "Q", 50.0, 70000, "O"),
                ("2024-03-14", "o", "13:30:00", "T", 50.0, 70000, "O"),
                ("2024-03-14", "c", "20:00:00", "S", 51.0, 150000, "M"),
                ("2024-03-14", "c", "20:00:00", "P", 51.2, 100, "M"))
    r = one(df, "2024-03-14")
    assert (r.listing_exchange, r.open, r.close) == ("Nasdaq", 50.0, 51.0)


def test_a_delayed_opening_is_still_the_listing_exchanges_print():
    """The NYSE opened LLY at 09:38:25 on 2023-01-24, after other exchanges had printed a few shares at 9:30."""
    df = prints(("2023-01-24", "o", "14:30:00", "P", 343.28, 2, "Q"),
                ("2023-01-24", "o", "14:30:01", "T", 365.22, 1, "Q"),
                ("2023-01-24", "o", "14:38:25", "N", 340.0, 16693, "Q"),
                ("2023-01-24", "c", "21:00:02", "N", 345.0, 40000, "6"))
    r = one(df, "2023-01-24")
    assert (r.listing_exchange, r.open, r.open_size) == ("NYSE", 340.0, 16693)
    assert len(auctions.late_opens(auctions.official(df))) == 0  # 8 minutes late is inside the hour


def test_a_side_missing_on_the_listing_exchange_stays_empty():
    df = prints(("2024-03-14", "o", "13:30:00", "P", 20.0, 10, "Q"),
                ("2024-03-14", "c", "20:00:00", "N", 21.0, 5000, "6"))
    r = one(df, "2024-03-14")
    assert r.listing_exchange == "NYSE"
    assert pd.isna(r.open) and r.close == 21.0
    assert r.n_open_prints == 1


def test_ties_go_to_the_print_listed_first():
    df = prints(("2024-03-14", "o", "13:30:00", "N", 10.0, 500, "O"),
                ("2024-03-14", "o", "13:30:00", "N", 10.1, 500, "Q"))
    assert one(df, "2024-03-14").open == 10.0


def test_days_are_kept_apart():
    df = prints(("2024-03-14", "o", "13:30:00", "Q", 10.0, 500, "O"),
                ("2024-03-15", "o", "13:30:00", "N", 11.0, 800, "O"))
    off = auctions.official(df).set_index("date")
    assert off.listing_exchange.to_dict() == {"2024-03-14": "Nasdaq", "2024-03-15": "NYSE"}


def test_an_open_more_than_an_hour_late_is_reported():
    df = prints(("2024-03-14", "o", "14:31:00", "N", 10.0, 500, "O"))  # 10:31 in New York, after DST began
    assert len(auctions.late_opens(auctions.official(df))) == 1


def test_fetch_reads_every_page_and_refuses_another_symbol(monkeypatch):
    pages = [{"auctions": {"TEST": [{"d": "2024-03-14", "o": [{"t": "2024-03-14T13:30:00.5Z", "x": "N", "p": 1.0,
                                                                "s": 5, "c": "O"}], "c": []}]}},
             {"auctions": {"TEST": [{"d": "2024-03-15", "c": [{"t": "2024-03-15T20:00:00Z", "x": "N", "p": 2.0,
                                                                "s": 6, "c": "6"}]}]}}]
    monkeypatch.setattr(auctions.alpaca, "pages", lambda *a, **k: iter(pages))
    rows = auctions.fetch("TEST", "2024-03-15", "2024-03-14", "2024-03-15")
    assert [(r[2], r[3], r[6]) for r in rows] == [("2024-03-14", "o", 1.0), ("2024-03-15", "c", 2.0)]
    monkeypatch.setattr(auctions.alpaca, "pages", lambda *a, **k: iter([{"auctions": {"OTHER": []}}]))
    with pytest.raises(RuntimeError):
        auctions.fetch("TEST", "2024-03-15", "2024-03-14", "2024-03-15")


def test_saved_prints_read_back_the_same(tmp_path):
    rows = [("TEST", "2024-03-15", "2024-03-14", "o", "2024-03-14T13:30:00.123456789Z", "N", 1.5, 5, "O")]
    auctions.save(tmp_path / "x.parquet", rows)
    back = pd.read_parquet(tmp_path / "x.parquet")
    assert back.t[0] == pd.Timestamp("2024-03-14T13:30:00.123456789Z")
    assert (back.p[0], back.s[0], back.side[0]) == (1.5, 5, "o")
