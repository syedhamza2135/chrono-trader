"""Binary-search the ticker-sorted part of FNSPID All_external.csv for given tickers, via range requests.

Usage: python -I news_ticker_search.py <url> <lo_byte> <hi_byte> TICKER [TICKER ...]
Prints, for each ticker, whether rows exist and the years they cover in a 2 MB window.
"""
import collections
import csv
import io
import re
import sys
import urllib.request

csv.field_size_limit(10**9)
COLS = ["Date", "Article_title", "Stock_symbol", "Url", "Publisher", "Author",
        "Article", "Lsa_summary", "Luhn_summary", "Textrank_summary", "Lexrank_summary"]
ROW_START = re.compile(r"\n(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC,)")


def fetch(url, off, n):
    req = urllib.request.Request(url, headers={"Range": f"bytes={off}-{off + n - 1}"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8", errors="replace")


def rows_at(url, off, n=262144):
    raw = fetch(url, off, n)
    m = ROW_START.search(raw)
    if not m:
        return []
    out = []
    try:
        for rec in csv.reader(io.StringIO(raw[m.end():])):
            if len(rec) == len(COLS):
                out.append(dict(zip(COLS, rec)))
    except csv.Error:
        pass
    return out[:-1]


def first_ticker(url, off):
    for r in rows_at(url, off):
        if r["Stock_symbol"]:
            return r["Stock_symbol"]
    return None


def main():
    url, lo0, hi0 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as resp:
        url = resp.geturl()
    for target in sys.argv[4:]:
        lo, hi = lo0, hi0
        while hi - lo > 1_000_000:
            mid = (lo + hi) // 2
            t = first_ticker(url, mid)
            if t is None or t >= target:
                hi = mid
            else:
                lo = mid
        window = rows_at(url, lo, 2_097_152)
        hits = [r for r in window if r["Stock_symbol"] == target]
        years = collections.Counter(r["Date"][:4] for r in hits)
        nearby = sorted({r["Stock_symbol"] for r in window})
        print(f"{target}: {len(hits)} rows in window; years {sorted(years.items())}; tickers nearby {nearby[:6]}...")
        for r in hits[:2]:
            print(f"      {r['Date']} | {r['Article_title'][:80]}")


if __name__ == "__main__":
    main()
