"""Probe partial FNSPID news CSV chunks: structure, timestamps, sources.

Usage: python -I fnspid_probe.py <kind: all|nasdaq> <chunk> [<chunk> ...]
A chunk that starts mid-file is realigned to the first full row.
"""
import collections
import csv
import io
import re
import sys
from datetime import datetime

csv.field_size_limit(10**9)

ALL_COLS = ["Date", "Article_title", "Stock_symbol", "Url", "Publisher", "Author",
            "Article", "Lsa_summary", "Luhn_summary", "Textrank_summary", "Lexrank_summary"]
NASDAQ_COLS = ["Unnamed: 0"] + ALL_COLS
DATE_RE = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC"

BUCKETS = {
    "pre-market": re.compile(r"pre-?market", re.I),
    "mid-day": re.compile(r"mid-?day", re.I),
    "mid-morning": re.compile(r"mid-?morning", re.I),
    "after-hours": re.compile(r"after-?hours", re.I),
    "52-week highs/lows": re.compile(r"52-week (highs|lows)", re.I),
    "movers from <day>": re.compile(r"movers from", re.I),
    "earnings scheduled": re.compile(r"earnings scheduled", re.I),
}


def rows_from(path, kind):
    raw = open(path, "rb").read().decode("utf-8", errors="replace")
    cols = ALL_COLS if kind == "all" else NASDAQ_COLS
    if raw.startswith(cols[0]):
        raw = raw[raw.index("\n") + 1:]
    else:
        start = (r"\n(?=" + DATE_RE + ",)") if kind == "all" else (r"\n(?=\d+\.0," + DATE_RE + ",)")
        m = re.search(start, raw)
        if not m:
            return []
        raw = raw[m.end():]
    out = []
    reader = csv.reader(io.StringIO(raw))
    try:
        for rec in reader:
            if len(rec) != len(cols):
                continue
            out.append(dict(zip(cols, rec)))
    except csv.Error:
        pass
    return out[:-1]  # the last row may be cut off


def main():
    kind, paths = sys.argv[1], sys.argv[2:]
    rows = []
    for p in paths:
        got = rows_from(p, kind)
        tick = collections.Counter(r["Stock_symbol"] for r in got)
        years = collections.Counter(r["Date"][:4] for r in got)
        print(f"{p.split('/')[-1]}: {len(got)} rows; tickers {tick.most_common(4)}; years {sorted(years.items())}")
        rows += got
    print(f"\nTOTAL rows {len(rows)}")
    parsed = []
    for r in rows:
        try:
            parsed.append((datetime.strptime(r["Date"], "%Y-%m-%d %H:%M:%S UTC"), r))
        except ValueError:
            pass
    print("unparseable dates:", len(rows) - len(parsed))
    hours = collections.Counter(d.hour for d, _ in parsed)
    print("hour-of-day histogram (as stored):", [hours.get(h, 0) for h in range(24)])
    zero_ms = [d for d, _ in parsed if d.minute == 0 and d.second == 0]
    print(f"rows at HH:00:00: {len(zero_ms)} ({len(zero_ms) / max(1, len(parsed)):.1%}); their hours:",
          sorted(collections.Counter(d.hour for d in zero_ms).items()))
    pubs = collections.Counter(r["Publisher"] for _, r in parsed)
    print("publishers:", pubs.most_common(8))
    doms = collections.Counter(re.sub(r"^https?://(www\.)?([^/]+).*$", r"\2", r["Url"]) for _, r in parsed)
    print("url domains:", doms.most_common(8))
    print("article text present:", sum(1 for _, r in parsed if r["Article"].strip()), "of", len(parsed))
    print("\nheadline buckets -> stored hour (weekday) samples:")
    for name, pat in BUCKETS.items():
        hits = [(d, r) for d, r in parsed if pat.search(r["Article_title"])]
        if not hits:
            continue
        hc = collections.Counter(d.hour for d, _ in hits)
        print(f"  {name}: n={len(hits)} hours={sorted(hc.items())}")
        for d, r in hits[:3]:
            print(f"      {d:%Y-%m-%d %a %H:%M} | {r['Article_title'][:90]}")
    per_url = collections.Counter(r["Url"] for _, r in parsed)
    multi = sum(1 for u, c in per_url.items() if c > 1)
    print(f"\nURLs appearing under >1 ticker row: {multi} of {len(per_url)} distinct URLs")


if __name__ == "__main__":
    main()
