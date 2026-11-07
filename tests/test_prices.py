"""The price audit's rules on small made-up bars: incomplete bars, returns on a first member day, why a company stops
trading, company member days, corrections without prices, the print-check counts, and the pick preview on each
company's own bars. No data files and no network.

Run with: python -m pytest tests
"""
import exchange_calendars as xcals
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from data_pipeline import audit_prices as ap
from data_pipeline import prices

CALENDAR = xcals.get_calendar("XNYS")
DAYS = CALENDAR.sessions_in_range("2020-10-01", "2021-03-31")
CUT = pd.Timestamp("2021-01-19")  # the first member day of the companies that join (2021-01-15 is the session before)


def plan_row(entity, symbol, use_from, use_to, close, volume, trades=10_000, start="2020-10-01", end="2021-03-31",
             share_class="", asof="2021-06-30"):
    """One plan row as prices.load returns it: the file's bars from start to end, member from use_from to use_to.
    close, volume and trades are one number for every bar, or a function of the bar's date."""
    dates = DAYS[(DAYS >= start) & (DAYS <= end)]
    value = lambda v: [v(d) for d in dates] if callable(v) else v
    df = pd.DataFrame({"date": dates, "close": value(close), "volume": value(volume), "trades": value(trades)})
    df["incomplete"] = prices.incomplete(df)
    df = df.assign(entity_id=entity, symbol=symbol, share_class=share_class, asof=asof, use_from=use_from, use_to=use_to,
                   member=(df.date >= pd.Timestamp(use_from)) & (df.date <= pd.Timestamp(use_to)))
    df["row"] = df["symbol"] + "__" + df["asof"] + "__" + df["use_from"]
    return df


def frame(*rows):
    return pd.concat(rows, ignore_index=True).sort_values(["row", "date"]).reset_index(drop=True)


def spliced(row, source):
    """Alpaca's history follows a symbol: the row's file holds the source row's bars before CUT."""
    row = row.copy()
    row.loc[row.date < CUT, ["close", "volume"]] = source.loc[source.date < CUT, ["close", "volume"]].to_numpy()
    return row


def ret_on(df, symbol, day):
    return df.loc[(df.symbol == symbol) & (df.date == pd.Timestamp(day)) & df.member, "ret"].item()


# Incomplete bars

def test_incomplete_is_a_trade_count_far_below_its_median():
    bars = pd.DataFrame({"volume": [1_000_000] * 20 + [100_000, 400_000, 300_000, 1_100_000, 0, 1_000_000],
                         "trades": [10_000] * 20 + [20, 3_500, 5_000, 40, 0, 10_000]})
    # a handful of trades; a half-day; a quiet day; a few large prints; a zero-volume halt; a normal day
    assert prices.incomplete(bars).tolist()[20:] == [True, False, False, True, False, False]


def test_incomplete_waits_for_ten_previous_bars():
    few = pd.DataFrame({"volume": [1_000_000] * 9 + [1_000], "trades": [10_000] * 9 + [1]})
    enough = pd.DataFrame({"volume": [1_000_000] * 10 + [1_000], "trades": [10_000] * 10 + [1]})
    assert not prices.incomplete(few).any()
    assert prices.incomplete(enough).tolist() == [False] * 10 + [True]


def test_load_marks_incomplete_bars(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "BARS", tmp_path)
    monkeypatch.setattr(prices, "PLAN", tmp_path / "plan.csv")
    pd.DataFrame({"entity_id": ["E1"], "symbol": ["TEST"], "share_class": [""], "asof": ["2021-02-01"],
                  "use_from": ["2020-10-15"], "use_to": ["2021-03-31"], "reused": [True]}).to_csv(tmp_path / "plan.csv", index=False)
    (tmp_path / "raw").mkdir()
    days = DAYS[:25]
    volume, trades = [1_000_000] * 24 + [5_000], [10_000] * 24 + [3]
    pq.write_table(pa.table({"t": [f"{d.date()}T05:00:00Z" for d in days], "open": [10.0] * 25, "high": [10.0] * 25,
                             "low": [10.0] * 25, "close": [10.0] * 25, "volume": volume, "trades": trades, "vwap": [10.0] * 25}),
                   tmp_path / "raw" / "TEST__2021-02-01.parquet")
    df = prices.load("raw")
    assert df.incomplete.tolist() == [False] * 24 + [True]
    assert df.member.tolist() == [False] * 10 + [True] * 15
    slim = prices.load("raw", columns=["t", "close"])
    assert "volume" not in slim and "trades" not in slim and slim.incomplete.tolist() == df.incomplete.tolist()


# Returns on a first member day, or after a gap

@pytest.fixture
def first_days():
    """Each company's own made-up bars, distinct across companies, and the splices Alpaca's histories make."""
    bars = lambda base: dict(close=lambda d: base + d.day_of_year / 1000, volume=lambda d: int(base * 1000) + d.day_of_year)
    old = plan_row("E-OLD", "OLD", "2020-10-01", "2021-01-15", **bars(50))  # 21st Century Fox
    new = spliced(plan_row("E-NEW", "OLD", "2021-01-19", "2021-03-31", asof="2021-03-01", **bars(40)), old)  # Fox Corp
    pre = plan_row("E-PRE", "PRE", "2021-01-19", "2021-03-31", **bars(30))  # its own trading before it joins
    ren = [plan_row("E-REN", "AAA", "2021-01-19", "2021-02-12", asof="2021-02-01", **bars(20)),
           plan_row("E-REN", "BBB", "2021-02-16", "2021-03-31", asof="2021-03-15", **bars(20))]  # a rename: one history
    chem = plan_row("E-CHEM", "CHM", "2020-10-01", "2021-01-15", **bars(60))  # Dow Chemical
    dd = [spliced(plan_row("E-DD", "DDA", "2021-01-19", "2021-02-12", asof="2021-02-01", **bars(70)), chem),
          spliced(plan_row("E-DD", "DDB", "2021-02-16", "2021-03-31", asof="2021-03-15", **bars(70)), chem)]  # DowDuPont
    dow = plan_row("E-DOW", "DOW", "2021-01-19", "2021-03-31", close=lambda d: 66.0 if d < CUT else 56 + d.day / 100,
                   volume=lambda d: 0 if d < CUT else 5_000 + d.day)  # Dow Inc: zero-volume fills before it trades
    rejoin = [plan_row("E-REJ", "REJ", "2020-10-01", "2020-12-31", **bars(80)),
              plan_row("E-REJ", "REJ", "2021-02-01", "2021-03-31", **bars(80))]  # leaves and rejoins, one file
    raw = frame(old, new, pre, *ren, chem, *dd, dow, *rejoin)
    adj = raw.assign(close=raw.close * 0.9)
    return ap.returns(raw, adj)


def test_first_member_day_after_another_security_has_no_return(first_days):
    raw, adj, _, _, starts, undefined = first_days
    for symbol, day in (("OLD", "2021-01-19"), ("DDA", "2021-01-19"), ("DOW", "2021-01-19"), ("PRE", "2021-01-19")):
        assert pd.isna(ret_on(raw, symbol, day)) and pd.isna(ret_on(adj, symbol, day)), symbol
    assert (starts, undefined) == (6, 4)


def test_first_member_day_keeps_its_return_where_the_previous_bar_is_shown_to_be_its_own(first_days):
    raw, adj, boundaries, stitched, _, _ = first_days
    a = raw[raw.symbol == "AAA"].set_index("date").close
    assert ret_on(raw, "AAA", "2021-01-19") == pytest.approx(a[CUT] / a[pd.Timestamp("2021-01-15")] - 1)  # BBB's file holds it
    r = raw[(raw.symbol == "REJ") & (raw.use_from == "2021-02-01")].set_index("date").close
    assert ret_on(raw, "REJ", "2021-02-01") == pytest.approx(r[pd.Timestamp("2021-02-01")] / r[pd.Timestamp("2021-01-29")] - 1)
    assert pd.notna(ret_on(adj, "REJ", "2021-02-01"))
    assert (boundaries, stitched) == (2, 0)  # AAA to BBB and DDA to DDB, each new file holding the old row's bar


def test_an_adjustment_still_shows_on_a_day_without_a_return():
    """Ingersoll Rand's first member day: its file holds Gardner Denver's history, which the adjusted file scales."""
    raw = frame(plan_row("E-IR", "IRX", "2021-01-19", "2021-03-31", close=lambda d: 30 + d.day_of_year / 1000, volume=9_000))
    adj = raw.assign(close=raw.close.where(raw.date >= CUT, raw.close * 1.13))
    raw, adj, _, _, _, undefined = ap.returns(raw, adj)
    assert undefined == 1 and pd.isna(ret_on(raw, "IRX", "2021-01-19"))
    events = ap.adjustment_events(raw, adj, pd.DataFrame(columns=["symbol", "date", "kind", "status"]))
    assert events[["symbol", "date"]].values.tolist() == [["IRX", "2021-01-19"]]


# Member days without a bar, and company member days

def test_days_after_a_last_trade_are_put_down_to_a_failure_or_an_acquisition():
    sessions = CALENDAR.sessions_in_range("2021-03-01", "2021-03-12")
    rows = frame(plan_row("E-BANK", "BANK", "2021-03-01", "2021-03-12", 10.0, 1_000, end="2021-03-05"),
                 plan_row("E-TGT", "TGT", "2021-03-01", "2021-03-12", 20.0, 2_000, end="2021-03-10"),
                 plan_row("E-LATE", "LATE", "2021-03-01", "2021-03-12", 30.0, 3_000, start="2021-03-03"))
    events = pd.DataFrame({"symbol": ["BANK", "TGT", "BANK"], "date": ["2021-03-08", "2021-03-02", "2021-03-03"],
                           "kind": ["failure", "failure", "halt"], "status": ["ok", "ok", "ok"]})
    gaps = ap.coverage(rows, sessions, events)
    assert gaps.groupby(["symbol", "where", "why"]).size().to_dict() == {
        ("BANK", "after", "failure"): 5, ("LATE", "before", ""): 2, ("TGT", "after", "acquisition"): 2}  # TGT's failure row is too early


def test_company_member_days_count_a_two_class_company_once():
    sessions = CALENDAR.sessions_in_range("2021-03-01", "2021-03-05")  # the check ends on 2021-03-05
    without = lambda df, day: df[df.date != pd.Timestamp(day)]
    raw = frame(plan_row("E-TWO", "TWOA", "2021-03-01", "2021-03-31", 10.0, 1_000, share_class="A"),
                without(plan_row("E-TWO", "TWOC", "2021-03-01", "2021-03-31", 9.0, 900, share_class="C"), "2021-03-03"),
                without(plan_row("E-GAP", "GAP", "2021-03-01", "2021-03-31", 20.0, 2_000), "2021-03-04"))
    assert ap.company_member_days(raw, sessions) == (10, 1)


# Corrections and the print check

def test_correction_names_the_kind_and_row_without_prices():
    events = pd.DataFrame({"symbol": ["AAA", "BBB", "CCC", "DDD"], "date": ["2021-01-04"] * 4,
                           "kind": ["open_print", "spin_off", "halt", "failure"], "status": ["wrong", "missing", "ok", "ok"],
                           "action": ["override_open", "total_return", "no_trade", "stopped_trading"],
                           "open": ["12.5", None, None, None], "close": [None] * 4, "total_return": [None, "0.0243", None, None]})
    assert [ap.correction(r) for r in events.itertuples()] == [
        "override_open (price_events row 1)", "spin_off: total return +2.4% (price_events row 2)",
        "halt: no_trade (price_events row 3)", "failure: stopped_trading (price_events row 4)"]


def test_print_checks_count_a_side_only_where_its_print_was_found():
    moves = pd.DataFrame({"verdict": ["matches", "open only", "close only", "MISMATCH close", "no auction prints found",
                                      "no trades under this symbol that day", None, "CONFLICT open"],
                          "open_checked": [True, True, False, True, False, False, None, True],
                          "close_checked": [True, False, True, True, False, False, None, True]})
    assert ap.print_checks(moves) == "5 (opens 4, closes 4; 2 failed)"
    as_read = moves.assign(open_checked=moves.open_checked.astype(str), close_checked=moves.close_checked.astype(str))
    assert ap.print_checks(as_read) == "5 (opens 4, closes 4; 2 failed)"
    assert ap.print_checks(moves.drop(columns=["open_checked", "close_checked"])) == "7 (2 failed)"


def test_large_moves_carry_the_checked_sides_when_the_print_check_has_them():
    adj = pd.DataFrame({"entity_id": ["E1", "E1"], "symbol": ["AAA", "AAA"], "date": pd.to_datetime(["2021-01-04", "2021-01-05"]),
                        "member": [True, True], "ret": [0.30, 0.01], "next_ret": [0.01, None], "stitched": [False, False]})
    events = pd.DataFrame(columns=["symbol", "date", "kind", "status", "action", "total_return"])
    prints = pd.DataFrame({"symbol": ["AAA"], "date": ["2021-01-04"], "verdict": ["open only"], "open_checked": [True], "close_checked": [False]})
    moves = ap.large_moves(adj, prints, events)
    assert moves[["verdict", "open_checked", "close_checked"]].values.tolist() == [["open only", True, False]]
    assert "open_checked" not in ap.large_moves(adj, prints.drop(columns=["open_checked", "close_checked"]), events)


# The pick preview

def test_pick_preview_ranks_each_company_on_its_own_bars():
    day = pd.Timestamp("2021-03-01")
    big = plan_row("E-BIG", "BIG", "2020-10-01", "2021-03-31", 100.0, 10_000)  # 1.0M a day
    oldco = plan_row("E-OLDCO", "OLDCO", "2020-10-01", "2021-01-15", 100.0, 50_000)  # 5.0M a day, leaves
    newco = spliced(plan_row("E-NEWCO", "NEWCO", "2021-01-19", "2021-03-31", 50.0, 10_000), oldco)  # 0.5M of its own
    fill = plan_row("E-FILL", "FILL", "2021-02-01", "2021-03-31", close=lambda d: 66.0 if d < pd.Timestamp("2021-02-01") else 20.0,
                    volume=lambda d: 0 if d < pd.Timestamp("2021-02-01") else 100_000)  # 2.0M after zero-volume fills
    ren = [plan_row("E-REN", "OLDT", "2020-10-01", "2021-01-15", 40.0, 10_000, asof="2020-12-01"),
           plan_row("E-REN", "NEWT", "2021-01-19", "2021-03-31", 40.0, lambda d: 10 if d < CUT else 10_000)]  # 0.4M
    inc = plan_row("E-INC", "INC", "2020-10-01", "2021-03-31", 10.0, lambda d: 30_000 if d.month in (10, 11) else 1_000)
    inc["incomplete"] = inc.volume < 30_000  # made-up flags: most of the window is incomplete
    raw = frame(big, oldco, newco, fill, *ren, inc)
    members = pd.DataFrame({"entity_id": ["E-BIG", "E-OLDCO", "E-NEWCO", "E-FILL", "E-REN", "E-INC"],
                            "member_from": pd.to_datetime(["2020-10-01", "2020-10-01", "2021-01-19", "2021-02-01", "2020-10-01", "2020-10-01"]),
                            "member_to": pd.to_datetime([None, "2021-01-19", None, None, None, None])})
    uni = ap.universe_preview(raw, members, {2021: day}, {})
    assert uni[["symbol", "median_dollar_volume_musd"]].values.tolist() == [
        ["FILL", 2.0], ["BIG", 1.0], ["NEWCO", 0.5], ["NEWT", 0.4], ["INC", 0.3]]


# The whole audit on made-up bars, written to a temporary folder

def test_main_writes_the_new_counts_without_prices(tmp_path, monkeypatch):
    first = DAYS[0]
    aapl = plan_row("E-AAPL", "AAPL", "2020-10-01", "2021-03-31", close=lambda d: 100 + (d - first).days / 100,
                    volume=lambda d: 900 if d == pd.Timestamp("2021-02-10") else 1_000_000 + (d - first).days,
                    trades=lambda d: 2 if d == pd.Timestamp("2021-02-10") else 10_000)
    bank = plan_row("E-BANK", "BANK", "2020-10-01", "2021-03-31", close=lambda d: 40 + (d - first).days / 100,
                    volume=lambda d: 500_000 + (d - first).days, end="2021-03-10")
    jump = plan_row("E-JUMP", "JUMP", "2020-10-01", "2021-03-31", close=lambda d: 13.0 if d >= pd.Timestamp("2021-02-01") else 10.0,
                    volume=lambda d: 700_000 + (d - first).days)
    raw = frame(aapl, bank, jump)
    entities = pd.DataFrame({"entity_id": ["E-AAPL", "E-BANK", "E-JUMP"], "name": ["Apple Co", "Bank Co", "Jump Co"]})
    members = pd.DataFrame({"entity_id": ["E-AAPL", "E-BANK", "E-JUMP"], "member_from": pd.to_datetime(["2020-10-01"] * 3),
                            "member_to": pd.to_datetime([None, None, None])})
    events = pd.DataFrame({"symbol": ["BANK", "JUMP"], "date": ["2021-03-11", "2021-02-01"], "kind": ["failure", "open_print"],
                           "status": ["ok", "wrong"], "action": ["stopped_trading", "override_open"], "open": [None, "12.5"],
                           "close": [None, None], "total_return": [None, None]})
    (tmp_path / "audit").mkdir()
    pd.DataFrame({"symbol": ["JUMP"], "date": ["2021-02-01"], "verdict": ["open only"], "open_checked": [True],
                  "close_checked": [False]}).to_csv(tmp_path / "audit" / "official_prints.csv", index=False)
    monkeypatch.setattr(ap, "read_reference", lambda: (entities, members, events))
    monkeypatch.setattr(ap, "load", lambda adjustment="raw": raw.copy())
    monkeypatch.setattr(ap, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ap, "OUT", tmp_path / "out")
    ap.main()
    md = (tmp_path / "out" / "prices.md").read_text(encoding="utf-8")
    after = len(DAYS[DAYS > pd.Timestamp("2021-03-10")])
    assert f"Company member days to then: {3 * len(DAYS):,} (a company listed with two classes counts once a day), {after} of them" in md
    assert f"After a company's last trade: {after}, 0 where an acquisition" in md and f"{after} where a failed company's shares stop trading (Bank Co;" in md
    assert "1 member bars hold only part of the day's trades" in md and "By date: 2021-02-10 (1)." in md
    assert "Checked against the official auction prints: 1 (opens 1, closes 0; 0 failed)." in md
    assert "override_open (price_events row 2)" in md
    moves = (tmp_path / "out" / "large_moves.csv").read_text(encoding="utf-8")
    assert "override_open (price_events row 2)" in moves and "12.5" not in moves and "12.5" not in md
    incomplete = pd.read_csv(tmp_path / "out" / "incomplete_bars.csv")
    assert list(incomplete.columns) == ["entity_id", "symbol", "date", "volume_ratio", "trades_ratio"]
    assert incomplete[["symbol", "date"]].values.tolist() == [["AAPL", "2021-02-10"]]
    gaps = pd.read_csv(tmp_path / "out" / "member_days_without_bars.csv")
    assert set(gaps.why) == {"failure"} and len(gaps) == after
