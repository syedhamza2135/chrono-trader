"""Probe: how many requests one year of auctions for the 50 picks of 2023 takes. Prints counts only, never keys.
Run from the main checkout so its data_pipeline loads .env at runtime."""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from data_pipeline import alpaca  # noqa: E402

wt = Path(sys.argv[1])
syms = [r["symbol"] for r in csv.DictReader(open(wt / "research/audit/universe_preview.csv", encoding="utf-8"))
        if r["year"] == "2023"]
t0 = time.monotonic()
pages = days = prints = 0
per_symbol = {}
for body in alpaca.pages("/v2/stocks/auctions", symbols=",".join(syms), start="2023-01-01", end="2023-12-31",
                         feed="sip", limit=10000):
    pages += 1
    for sym, recs in (body.get("auctions") or {}).items():
        per_symbol[sym] = per_symbol.get(sym, 0) + len(recs)
        days += len(recs)
        prints += sum(len(r.get("o") or []) + len(r.get("c") or []) for r in recs)
print("symbols asked:", len(syms), "symbols returned:", len(per_symbol))
print("pages:", pages, "day records:", days, "prints:", prints, "seconds:", round(time.monotonic() - t0, 1))
short = {s: n for s, n in per_symbol.items() if n != 250}
print("symbols without 250 days (2023 had 250 sessions):", short)
print("missing symbols:", sorted(set(syms) - set(per_symbol)))
