"""Check daily bars against the exchanges' official opening and closing auction prints.

A daily bar's open and close should sit within a cent or two of the listing exchange's official open (trade
condition O on NYSE tape, Q on Nasdaq) and official close (6 or M). Nordstrom on 26 Mar 2018 failed this: its bar
opened and closed near $64 while the official prints were $46.95 and $47.13, because another security's trades
were mixed into its history. One small trades request per auction, so this runs on a list of days, not on all
bars.

Every exchange reports its own opening and closing prints, and on a chaotic day they disagree. The official one
is the listing exchange's auction, which is by far the largest, so the largest print of each kind is taken.

Usage: python research/verify_prints.py <in.csv> <out.csv>
  in.csv columns: symbol, date (YYYY-MM-DD), bar_open, bar_close; optional asof (defaults to date)
"""
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline import alpaca

NY = ZoneInfo("America/New_York")
OPEN_CONDITIONS = {"O", "Q"}
CLOSE_CONDITIONS = {"6", "M"}
MIN_AUCTION = 1000  # shares; an auction print smaller than this sends the search to the wider window


def _trades(symbol, asof, start, end):
    out = []
    for body in alpaca.pages("/v2/stocks/trades", symbols=symbol, start=start.isoformat(), end=end.isoformat(),
                             limit=10000, feed="sip", asof=asof):
        out += body.get("trades", {}).get(symbol, [])
    return out


def official_prints(symbol, day, asof):
    """(opening prints, closing prints, n trades seen). Each print is (price, exchange, size, New York time).

    The auctions print within seconds of 9:30 and 16:00, so narrow windows come first. A wider one is tried when
    no auction-sized print turns up: a delayed opening on news or an imbalance (the NYSE opened MS at 09:37:36 on
    2023-01-24, after other exchanges had printed a few shares at 9:30), or a late closing print."""
    d = datetime.strptime(day, "%Y-%m-%d")
    at = lambda h, m, s=0: datetime(d.year, d.month, d.day, h, m, s, tzinfo=NY)
    seen = 0
    stamp = lambda t: datetime.fromisoformat(t["t"].replace("Z", "+00:00")).astimezone(NY).strftime("%H:%M:%S")
    found = {}
    for kind, conditions, windows in (("open", OPEN_CONDITIONS, ((at(9, 29, 50), at(9, 35)), (at(9, 35), at(10, 30)))),
                                      ("close", CLOSE_CONDITIONS, ((at(15, 59, 55), at(16, 1)), (at(16, 1), at(16, 30))))):
        prints = []
        for start, end in windows:
            trades = _trades(symbol, asof, start, end)
            seen += len(trades)
            prints += [(t["p"], t["x"], t["s"], stamp(t)) for t in trades if conditions & set(t.get("c", []))]
            if any(p[2] >= MIN_AUCTION for p in prints):
                break
        found[kind] = prints
    return found["open"], found["close"], seen


def _spread(prints):
    prices = [p[0] for p in prints]
    return max(prices) / min(prices) - 1 if prices else 0.0


def main(src, dst):
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    done = set()
    if Path(dst).exists():  # resume: keep finished rows, skip them
        done = {(r["symbol"], r["date"]) for r in csv.DictReader(open(dst, encoding="utf-8"))}
    with open(dst, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not done:
            w.writerow(["symbol", "date", "bar_open", "official_open", "bar_close", "official_close", "open_gap", "close_gap",
                        "trades_seen", "verdict", "all_open_prints", "all_close_prints", "open_print", "close_print",
                        "open_spread", "close_spread"])
        for r in rows:
            if (r["symbol"], r["date"]) in done:
                continue
            try:
                opens, closes, n = official_prints(r["symbol"], r["date"], r.get("asof") or r["date"])
            except RuntimeError as exc:
                w.writerow([r["symbol"], r["date"], r["bar_open"], "", r["bar_close"], "", "", "", 0, f"error: {str(exc)[:80]}",
                            "", "", "", "", "", ""])
                continue
            bo, bc = float(r["bar_open"]), float(r["bar_close"])
            top_open = max(opens, key=lambda p: p[2]) if opens else None  # the listing exchange's auction
            top_close = max(closes, key=lambda p: p[2]) if closes else None
            o = top_open[0] if top_open else None
            c = top_close[0] if top_close else None
            gap = lambda bar, ref: "" if ref is None else round(bar / ref - 1, 4)
            off = [side for side, bar, ref in (("open", bo, o), ("close", bc, c)) if ref and abs(bar / ref - 1) > 0.02]
            if n == 0:
                verdict = "no trades under this symbol that day"
            elif not opens and not closes:
                verdict = "no auction prints found"
            elif off:
                verdict = "MISMATCH " + " and ".join(off)
            else:
                verdict = "matches"
            fmt = lambda ps: " ".join(f"{p}@{x}x{s}" for p, x, s, _ in sorted(ps, key=lambda p: -p[2])[:6])
            show = lambda p: f"{p[0]} on {p[1]}, {p[2]} shares at {p[3]}" if p else ""
            w.writerow([r["symbol"], r["date"], bo, o, bc, c, gap(bo, o), gap(bc, c), n, verdict, fmt(opens), fmt(closes),
                        show(top_open), show(top_close), round(_spread(opens), 4), round(_spread(closes), 4)])
            f.flush()


if __name__ == "__main__":
    main(*sys.argv[1:3])
