"""The event store's rules (data_pipeline/store.py) on made-up bars, with no data files.

Run with: python -m pytest tests
"""
import numpy as np
import pandas as pd
import pytest

from data_pipeline import store

D = pd.to_datetime(["2024-03-11", "2024-03-12", "2024-03-13", "2024-03-14", "2024-03-15"]).astype("datetime64[ns]")


def series(close, ret, volume=None, entity="E1", share_class=""):
    n = len(close)
    return pd.DataFrame({"entity_id": entity, "share_class": share_class, "date": D[:n], "close": close, "ret": ret,
                         "volume": volume if volume is not None else [1000] * n})


def opens(values, entity="E1", share_class=""):
    o = pd.DataFrame({"entity_id": entity, "share_class": share_class, "date": D[: len(values)], "open": values})
    return o.dropna(subset=["open"])


def test_a_label_runs_from_one_official_open_to_the_next_through_the_closes():
    s = series([10.0, 11.0, 12.0], [np.nan, 0.10, 12 / 11 - 1])
    lab = store.labels(s, opens([9.5, 10.5, 12.5]), data_end=D[2])
    first = lab.iloc[0]
    assert (first.date, first.end, bool(first.at_close)) == (D[0], D[1], False)
    assert first.label == pytest.approx(10.5 / 9.5 - 1, abs=1e-12)  # no dividend: just the two opens
    assert len(lab) == 2  # the last open has no next open before the data ends, so no label


def test_the_closes_cancel_so_a_wrong_close_cannot_move_a_label():
    good = series([10.0, 11.0, 12.0], [np.nan, 0.10, 12 / 11 - 1])
    bad = series([10.0, 15.0, 12.0], [np.nan, 0.5, 12 / 15 - 1])  # day 2's close is wrong, and so are its returns
    o = opens([9.5, 10.5, 12.5])
    a, b = store.labels(good, o, D[2]), store.labels(bad, o, D[2])
    assert np.allclose(a.label, b.label, rtol=0, atol=1e-12)


def test_a_dividend_inside_the_label_counts():
    """A 1.0 dividend goes ex on day 2: the close falls 11 to 10, but the total return is (10 + 1) / 11 - 1 = 0."""
    s = series([11.0, 10.0], [np.nan, 0.0])
    lab = store.labels(s, opens([11.0, 10.0]), data_end=D[1])
    assert lab.label.iloc[0] == pytest.approx(11.0 / 11.0 * (1 + 0.0) * (10.0 / 10.0) - 1, abs=1e-12)


def test_a_day_without_an_official_open_is_spanned():
    s = series([10.0, 10.0, 12.0], [np.nan, 0.0, 0.2], volume=[1000, 0, 1000])  # day 2: a halt
    lab = store.labels(s, opens([10.0, np.nan, 11.0]), data_end=D[2])
    assert list(lab.date) == [D[0]] and lab.end.iloc[0] == D[2]
    assert lab.label.iloc[0] == pytest.approx(10 / 10 * 1.0 * 1.2 * 11 / 12 - 1, abs=1e-12)


def test_a_company_that_stops_trading_exits_at_its_last_traded_close():
    """Its last label ends at the last bar with volume, ignoring zero-volume fills after (Signature Bank's). The data
    runs on to D[-1], so the company stopped before the data ends."""
    s = series([10.0, 9.0, 9.0], [np.nan, -0.1, 0.0], volume=[1000, 500, 0])
    lab = store.labels(s, opens([10.0, 9.5, np.nan]), data_end=D[-1])
    last = lab.iloc[-1]
    assert (last.date, last.end, bool(last.at_close)) == (D[1], D[1], True)
    assert last.label == pytest.approx(9.0 / 9.5 - 1, abs=1e-12)


def test_no_label_crosses_a_day_without_a_return():
    s = series([10.0, 11.0, 12.0], [np.nan, np.nan, 12 / 11 - 1])
    lab = store.labels(s, opens([10.0, 11.0, 12.0]), data_end=D[2])
    assert list(lab.date) == [D[1]]


def test_labels_are_per_listing():
    s = pd.concat([series([10.0, 11.0], [np.nan, 0.1], entity="A"), series([20.0, 19.0], [np.nan, -0.05], entity="B")])
    o = pd.concat([opens([10.0, 11.0], entity="A"), opens([20.0, 19.0], entity="B")])
    lab = store.labels(s.reset_index(drop=True), o, D[1]).set_index("entity_id").label
    assert lab["A"] == pytest.approx(0.1) and lab["B"] == pytest.approx(-0.05)


def event_series():
    return pd.DataFrame({"entity_id": "E1", "share_class": "", "symbol": "ABC", "date": D[:3], "member": True,
                         "open": 10.0, "high": 11.0, "low": 9.0, "close": [10.0, 11.0, 12.0], "volume": 100,
                         "vwap": 10.5, "ret": [np.nan, 0.10, 12 / 11 - 1]})


def events(*rows):
    cols = ["symbol", "date", "kind", "status", "action", "open", "high", "low", "close", "volume", "vwap",
            "total_return"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


def test_an_overridden_close_moves_the_return_into_and_out_of_its_day():
    s, applied = store.apply_events(event_series(), events(
        ("ABC", "2024-03-12", "close_print", "wrong", "override_close", None, None, None, "11.55", None, None, None)))
    assert s.close.iloc[1] == 11.55
    assert s.ret.iloc[1] == pytest.approx(11.55 / 10 - 1) and s.ret.iloc[2] == pytest.approx(12 / 11.55 - 1)
    assert list(applied.result) == ["applied"]


def test_a_distributions_true_total_return_replaces_the_vendors():
    s, _ = store.apply_events(event_series(), events(
        ("ABC", "2024-03-13", "spin_off", "wrong", "total_return", None, None, None, None, None, None, "0.0363")))
    assert s.ret.iloc[2] == 0.0363 and s.ret.iloc[1] == pytest.approx(0.10)


def test_a_rebuilt_bar_replaces_the_whole_bar():
    s, _ = store.apply_events(event_series(), events(
        ("ABC", "2024-03-12", "bad_print", "wrong", "override_bar", "10.1", "10.6", "9.9", "10.4", "123", "10.3", None)))
    r = s.iloc[1]
    assert (r.open, r.high, r.low, r.close, r.volume, r.vwap) == (10.1, 10.6, 9.9, 10.4, 123, 10.3)
    assert s.ret.iloc[2] == pytest.approx(12 / 10.4 - 1)


def test_a_halt_is_marked_and_events_without_a_member_bar_are_reported():
    s, applied = store.apply_events(event_series(), events(
        ("ABC", "2024-03-13", "halt", "ok", "no_trade", None, None, None, None, None, None, None),
        ("XYZ", "2024-03-13", "halt", "ok", "no_trade", None, None, None, None, None, None, None)))
    assert list(s.no_trade) == [False, False, True]
    assert sorted(applied.result) == ["applied", "no bar in the store"]


def test_a_correction_applies_on_a_day_outside_membership_too():
    """EQT spun off Equitrans on 2018-11-13, the day it left the index: the last member day's label crosses it."""
    s = event_series().assign(member=[True, True, False])
    s, _ = store.apply_events(s, events(
        ("ABC", "2024-03-13", "spin_off", "wrong", "total_return", None, None, None, None, None, None, "0.012")))
    assert s.ret.iloc[2] == 0.012


def file_bars(rows):
    """Plan-row bars as prices.load and audit_prices.returns give them."""
    cols = ["entity_id", "share_class", "symbol", "asof", "row", "use_from", "use_to", "date", "member", "foreign",
            "volume", "ret", "file_prev_date"]
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df.date)
    df["file_prev_date"] = pd.to_datetime(df.file_prev_date)
    return df


def test_member_bars_win_and_other_days_keep_only_the_companys_own_traded_bars():
    df = file_bars([
        ("E1", "", "OLD", "a1", "r1", "2024-03-13", "2024-03-15", "2024-03-11", False, False, 500, 0.01, None),
        ("E1", "", "OLD", "a1", "r1", "2024-03-13", "2024-03-15", "2024-03-12", False, True, 500, 0.02, "2024-03-11"),
        ("E1", "", "OLD", "a1", "r1", "2024-03-13", "2024-03-15", "2024-03-13", True, False, 500, 0.03, "2024-03-12"),
        ("E1", "", "OLD", "a1", "r1", "2024-03-13", "2024-03-15", "2024-03-14", True, False, 500, 0.04, "2024-03-13"),
        ("E1", "", "NEW", "a2", "r2", "2024-03-16", "2024-03-20", "2024-03-14", False, False, 500, 0.05, "2024-03-13"),
        ("E1", "", "NEW", "a2", "r2", "2024-03-16", "2024-03-20", "2024-03-15", False, False, 0, 0.0, "2024-03-14"),
    ])
    s = store.company_series(df).set_index("date")
    assert list(s.index.strftime("%m-%d")) == ["03-11", "03-13", "03-14"]  # 03-12 is foreign, 03-15 a zero-volume fill
    assert s.loc["2024-03-14", "symbol"] == "OLD"  # the member bar, not the other file's
    assert np.isnan(s.loc["2024-03-11", "ret"])  # no previous bar of the same file in the series


def test_non_member_days_are_kept_only_near_a_membership():
    """A year and a bit before joining (the picker's lookback) and two weeks after leaving: later bars under the old
    ticker can be another security's (IHS Markit's INFO in 2025)."""
    def bar(d, use_from="2020-06-01", use_to="2021-06-01"):
        return ("E1", "", "INFO", "a1", "r1", use_from, use_to, d, False, False, 500, 0.0, None)
    df = file_bars([bar("2019-04-27"), bar("2019-05-03"), bar("2021-06-15"), bar("2021-06-16"),
                    ("E1", "", "INFO", "a1", "r1", "2020-06-01", "2021-06-01", "2020-06-02", True, False, 500, 0.0, None)])
    kept = list(store.company_series(df).date.dt.strftime("%Y-%m-%d"))
    assert kept == ["2019-05-03", "2020-06-02", "2021-06-15"]  # 2019-04-27 is 401 days before, 2021-06-16 15 after


def test_a_non_member_return_needs_the_same_files_previous_bar():
    df = file_bars([
        ("E1", "", "A", "a1", "r1", "2024-03-14", "2024-03-15", "2024-03-11", False, False, 500, 0.01, None),
        ("E1", "", "A", "a1", "r1", "2024-03-14", "2024-03-15", "2024-03-12", False, False, 500, 0.02, "2024-03-11"),
        ("E1", "", "A", "a1", "r1", "2024-03-14", "2024-03-15", "2024-03-13", False, True, 500, 0.03, "2024-03-12"),
        ("E1", "", "A", "a1", "r1", "2024-03-14", "2024-03-15", "2024-03-14", True, False, 500, 0.04, "2024-03-13"),
    ])
    s = store.company_series(df).set_index("date").ret
    assert s["2024-03-12"] == 0.02  # 03-11 is this file's previous bar
    assert s["2024-03-14"] == 0.04  # a member day keeps what audit_prices.returns decided
