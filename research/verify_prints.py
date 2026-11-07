"""Check daily bars against the exchanges' official opening and closing auction prints.

A daily bar's open and close should match the listing exchange's official open (trade condition O or Q) and official
close (6 or M) to within a cent, or 0.2% of the official price when that is more. Nordstrom on 26 Mar 2018 failed
this: its bar opened and closed about 36% above the official prints, because another security's trades were mixed
into its history. A few trades requests per stock-day, so this runs on a list of days, not on all bars.

Every exchange reports its own opening and closing prints, and on a chaotic day they disagree. The official one is
the listing exchange's auction, so each side is judged on the listing exchange's largest print only, and a side whose
print isn't found is not judged (open_checked and close_checked say which sides were). Verdicts: matches (both sides
checked, both match); MISMATCH open, close, or open and close (judged on the sides checked); open only or close only
(that side matches, and the other side's print wasn't found); no auction prints found; no trades under this symbol
that day.

Usage: python research/verify_prints.py <in.csv> <out.csv>
  in.csv columns: symbol, date (YYYY-MM-DD), bar_open, bar_close; optional asof (defaults to date)
"""
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import exchange_calendars as xcals

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline import alpaca

NY = ZoneInfo("America/New_York")
XNYS = xcals.get_calendar("XNYS")
OPEN_CONDITIONS = {"O", "Q"}
CLOSE_CONDITIONS = {"6", "M"}
EXCHANGES = {"N": "NYSE", "A": "NYSE American", "P": "NYSE Arca", "Z": "Cboe BZX",
             "Q": "Nasdaq", "S": "Nasdaq", "T": "Nasdaq"}  # Alpaca's codes; Nasdaq's auctions print under Q, T or both
HEADER = ["symbol", "date", "bar_open", "official_open", "bar_close", "official_close", "open_gap", "close_gap",
          "trades_seen", "verdict", "all_open_prints", "all_close_prints", "open_print", "close_print", "open_spread",
          "close_spread", "listing_exchange", "open_checked", "close_checked"]


def _trades(symbol, asof, start, end):
    out = []
    for body in alpaca.pages("/v2/stocks/trades", symbols=symbol, start=start.isoformat(), end=end.isoformat(),
                             limit=10000, feed="sip", asof=asof):
        out += body.get("trades", {}).get(symbol, [])
    return out


def on_exchange(prints, exchange):
    return [p for p in prints if EXCHANGES.get(p[1], p[1]) == exchange]


def listing_exchange(prints):
    """The exchange of the largest auction print: the listing exchange's auctions dwarf the other exchanges'."""
    if not prints:
        return None
    code = max(prints, key=lambda p: p[2])[1]
    return EXCHANGES.get(code, code)


def official_prints(symbol, day, asof):
    """(opening prints, closing prints, n trades seen, listing exchange). Each print is (price, exchange, size, New
    York time), from every exchange; the listing exchange is the one with the day's largest auction print.

    The closing window runs from 5 seconds before the session's close on the NYSE calendar (13:00 on an early close)
    to 30 minutes after it, because the NYSE's closing auction can print minutes late (16:06:42 for LYB on
    2020-03-16). The opening auction prints within seconds of the open, so a narrow window comes first, and a wider
    one is tried when the listing exchange has no opening print in it: a delayed opening on news or an imbalance (the
    NYSE opened MS at 09:37:36 on 2023-01-24, after other exchanges had printed a few shares at 9:30)."""
    if not XNYS.is_session(day):
        raise RuntimeError(f"{day} is not an NYSE session")
    opens_at = XNYS.session_open(day).tz_convert(NY).to_pydatetime()
    closes_at = XNYS.session_close(day).tz_convert(NY).to_pydatetime()
    stamp = lambda t: datetime.fromisoformat(t["t"].replace("Z", "+00:00")).astimezone(NY).strftime("%H:%M:%S")
    seen = 0

    def prints(conditions, start, end):
        nonlocal seen
        trades = _trades(symbol, asof, start, end)
        seen += len(trades)
        return [(t["p"], t["x"], t["s"], stamp(t)) for t in trades if conditions & set(t.get("c", []))]

    opens = prints(OPEN_CONDITIONS, opens_at - timedelta(seconds=10), opens_at + timedelta(minutes=5))
    closes = prints(CLOSE_CONDITIONS, closes_at - timedelta(seconds=5), closes_at + timedelta(minutes=30))
    if not on_exchange(opens, listing_exchange(opens + closes)):
        opens += prints(OPEN_CONDITIONS, opens_at + timedelta(minutes=5), opens_at + timedelta(hours=1))
    return opens, closes, seen, listing_exchange(opens + closes)


def matches(bar, official):
    """Within a cent, or 0.2% of the official price when that is more. The 1e-9 absorbs float error on a cent."""
    return abs(bar - official) <= max(0.01, 0.002 * official) + 1e-9


def _spread(prints):
    prices = [p[0] for p in prints]
    return max(prices) / min(prices) - 1 if prices else 0.0


def check(r):
    """The output row (HEADER's columns) for one input row."""
    try:
        opens, closes, n, listing = official_prints(r["symbol"], r["date"], r.get("asof") or r["date"])
    except RuntimeError as exc:
        return [r["symbol"], r["date"], r["bar_open"], "", r["bar_close"], "", "", "", 0, f"error: {str(exc)[:80]}",
                "", "", "", "", "", "", "", False, False]
    bo, bc = float(r["bar_open"]), float(r["bar_close"])
    top_open = max(on_exchange(opens, listing), key=lambda p: p[2], default=None)  # the listing exchange's auction
    top_close = max(on_exchange(closes, listing), key=lambda p: p[2], default=None)
    o = top_open[0] if top_open else None
    c = top_close[0] if top_close else None
    gap = lambda bar, ref: "" if ref is None else round(bar / ref - 1, 4)
    off = [side for side, bar, ref in (("open", bo, o), ("close", bc, c)) if ref is not None and not matches(bar, ref)]
    if n == 0:
        verdict = "no trades under this symbol that day"
    elif o is None and c is None:
        verdict = "no auction prints found"
    elif off:
        verdict = "MISMATCH " + " and ".join(off)
    elif o is None or c is None:
        verdict = "open only" if c is None else "close only"
    else:
        verdict = "matches"
    fmt = lambda ps: " ".join(f"{p}@{x}x{s}" for p, x, s, _ in sorted(ps, key=lambda p: -p[2])[:6])
    show = lambda p: f"{p[0]} on {p[1]}, {p[2]} shares at {p[3]}" if p else ""
    return [r["symbol"], r["date"], bo, o, bc, c, gap(bo, o), gap(bc, c), n, verdict, fmt(opens), fmt(closes),
            show(top_open), show(top_close), round(_spread(opens), 4), round(_spread(closes), 4),
            listing or "", top_open is not None, top_close is not None]


def main(src, dst):
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    done = set()
    if Path(dst).exists():  # resume: keep finished rows, skip them
        old = csv.DictReader(open(dst, encoding="utf-8"))
        if old.fieldnames and old.fieldnames != HEADER:
            sys.exit(f"{dst} has other columns (an older version of this check); write to a new file")
        done = {(r["symbol"], r["date"]) for r in old}
    with open(dst, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not done:
            w.writerow(HEADER)
        for r in rows:
            if (r["symbol"], r["date"]) not in done:
                w.writerow(check(r))
                f.flush()


if __name__ == "__main__":
    main(*sys.argv[1:3])
