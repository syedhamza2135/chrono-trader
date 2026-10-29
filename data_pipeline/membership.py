"""S&P 500 membership history from fja05680/sp500: snapshots by date, and each ticker's membership spells.

Tickers are the ones in use at the time (FB until 2022-06-09, then META).
"""
import csv
from datetime import date

from .settings import DATA_DIR

SOURCE = DATA_DIR / "membership" / "components_updated.csv"


def load_snapshots():
    """[(date, frozenset of tickers)], oldest first. Each snapshot holds until the next one."""
    rows = []
    with open(SOURCE, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            tickers = frozenset(t.strip() for t in rec["tickers"].split(",") if t.strip())
            rows.append((date.fromisoformat(rec["date"]), tickers))
    rows.sort()
    return rows


def members_on(day, snapshots):
    current = frozenset()
    for d, tickers in snapshots:
        if d > day:
            break
        current = tickers
    return current


def spells(snapshots, since):
    """{ticker: [(start, end)]} for spells still running on or after `since`.

    `end` is the first snapshot date without the ticker, or None if it's still a member.
    """
    out, opened, previous = {}, {}, frozenset()
    for d, tickers in snapshots:
        for t in tickers - previous:
            opened[t] = d
        for t in previous - tickers:
            out.setdefault(t, []).append((opened.pop(t), d))
        previous = tickers
    for t, start in opened.items():
        out.setdefault(t, []).append((start, None))
    kept = {}
    for t, runs in out.items():
        runs = [(s, e) for s, e in runs if e is None or e >= since]
        if runs:
            kept[t] = sorted(runs)
    return kept
