"""For each ticker, find the end of its block in the ticker-sorted nasdaq.com part and print its oldest dates
and a rough per-year count from the block's tail. Usage: python -I nasdaq_oldest.py <url> <hi_byte> TICKER ..."""
import collections, csv, io, re, sys, urllib.request
csv.field_size_limit(10**9)
COLS = ["idx", "Date", "Article_title", "Stock_symbol", "Url", "Publisher", "Author", "Article", "L1", "L2", "L3", "L4"]
START = re.compile(r"\n(?=\d+\.0,\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC,)")
url, hi0 = sys.argv[1], int(sys.argv[2])
with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as r:
    url = r.geturl()

def rows_at(off, n=196608):
    req = urllib.request.Request(url, headers={"Range": f"bytes={off}-{off + n - 1}"})
    raw = urllib.request.urlopen(req).read().decode("utf-8", errors="replace")
    m = START.search(raw)
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

def first_ticker(off):
    rows = rows_at(off)
    return rows[0]["Stock_symbol"] if rows else None

for target in sys.argv[3:]:
    lo, hi = 0, hi0          # find first offset whose first ticker is > target
    while hi - lo > 300_000:
        mid = (lo + hi) // 2
        t = first_ticker(mid)
        if t is not None and t > target:
            hi = mid
        else:
            lo = mid
    tail = []
    for k in range(1, 16):   # walk back from the boundary, 15 x 192KB
        tail = [r for r in rows_at(max(0, lo - k * 196608)) if r["Stock_symbol"] == target] + tail
    years = collections.Counter(r["Date"][:4] for r in tail)
    oldest = min((r["Date"] for r in tail), default=None)
    print(f"{target}: boundary near byte {lo:,}; oldest date seen {oldest}; tail years {sorted(years.items())}")
