"""Probe: does Alpaca's historical auctions endpoint exist on this plan, and does it give the listing exchange's
official opening auction? Prints counts, exchanges and prices only, never keys. Run from the main checkout so its
data_pipeline loads .env at runtime."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from data_pipeline import alpaca  # noqa: E402

symbols = "LLY,MA,XOM,AAPL,MSFT"
t0 = time.monotonic()
try:
    body = alpaca.get("/v2/stocks/auctions", symbols=symbols, start="2023-01-23", end="2023-01-25", feed="sip")
except RuntimeError as exc:
    print("ERROR:", str(exc)[:300])
    raise SystemExit(1)
print("seconds:", round(time.monotonic() - t0, 2))
print("top-level keys:", sorted(body))
auctions = body.get("auctions") or {}
print("next_page_token:", body.get("next_page_token"))
for sym, days in sorted(auctions.items()):
    for d in days:
        opens = d.get("o") or []
        closes = d.get("c") or []
        big = sorted(opens, key=lambda p: -p.get("s", 0))[:3]
        print(sym, d.get("d"), "n_open", len(opens), "n_close", len(closes),
              "open prints:", [(p.get("x"), p.get("p"), p.get("s"), p.get("c"), p.get("t")) for p in big])
if auctions:
    first = next(iter(auctions.values()))[0]
    print("one raw day record:", json.dumps(first)[:600])
