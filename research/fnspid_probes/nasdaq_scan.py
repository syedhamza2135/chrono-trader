"""Map nasdaq_exteral_data.csv: first rows' ticker/date/domain at byte offsets (handles both row shapes)."""
import csv, io, re, sys, urllib.request
csv.field_size_limit(10**9)
COLS = ["idx", "Date", "Article_title", "Stock_symbol", "Url", "Publisher", "Author", "Article", "L1", "L2", "L3", "L4"]
START = re.compile(r"\n(?=(\d+\.0)?,\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC,)")
url = sys.argv[1]
with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as r:
    url = r.geturl()
for off in map(int, sys.argv[2:]):
    req = urllib.request.Request(url, headers={"Range": f"bytes={off}-{off + 393215}"})
    raw = urllib.request.urlopen(req).read().decode("utf-8", errors="replace")
    m = START.search(raw)
    if not m:
        print(f"{off:>14,}: no row start found"); continue
    rows = []
    try:
        for rec in csv.reader(io.StringIO(raw[m.end():])):
            if len(rec) == len(COLS):
                rows.append(dict(zip(COLS, rec)))
    except csv.Error:
        pass
    rows = rows[:-1]
    if not rows:
        print(f"{off:>14,}: no complete rows"); continue
    tick = sorted({r["Stock_symbol"] for r in rows})
    dom = sorted({re.sub(r"^https?://(www\.)?([^/]+).*$", r"\2", r["Url"]).strip() for r in rows})
    idx = "indexed" if rows[0]["idx"] else "no-index"
    print(f"{off:>14,}: {len(rows):3} rows {idx:8} tickers {tick[:2]}..{tick[-1:]} dates {rows[0]['Date'][:10]}..{rows[-1]['Date'][:10]} {dom[:2]}")
