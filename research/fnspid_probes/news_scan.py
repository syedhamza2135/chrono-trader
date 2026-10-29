"""Print the first rows' ticker, date and domain at a list of byte offsets of FNSPID All_external.csv.

Usage: python -I news_scan.py <url> <offset> [<offset> ...]
"""
import re
import sys
import urllib.request

sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0].rsplit("\\", 1)[0])
from news_ticker_search import rows_at  # noqa: E402


def main():
    url = sys.argv[1]
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as resp:
        url = resp.geturl()
    for off in map(int, sys.argv[2:]):
        rows = rows_at(url, off, 131072)
        if not rows:
            print(f"{off:>13,}: no rows")
            continue
        tick = sorted({r["Stock_symbol"] for r in rows})
        dom = {re.sub(r"^https?://(www\.)?([^/]+).*$", r"\2", r["Url"]).strip() for r in rows}
        print(f"{off:>13,}: {len(rows):4} rows tickers {tick[:3]}..{tick[-1:]} dates {rows[0]['Date'][:10]}..{rows[-1]['Date'][:10]} domains {sorted(dom)[:3]}")


if __name__ == "__main__":
    main()
