"""Judge check for M-2 (b) and (c). Read-only: changes no file.

For each total_return row with an open_return: recompute it from the store (parent's official open and the previous
close in the same entity and class) and Alpaca's official opens for the other securities, using the functions of
research/ex_date_opens.py, and compare with the csv. Also report:
- how many store bars share the row's (symbol, date), and whether apply_events and ex_date_opens pick the same one;
- when each other security's official open printed, against the parent's open_time (the label's end_open_time).
Prints differences, counts and minutes only, no prices.
Usage (calls Alpaca's auctions endpoint): set CHRONO_ENV_FILE, then
  python research/review_2026-11-21_fixes/judge_scripts/m2_recompute.py"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT))
import ex_date_opens as x  # noqa: E402
from data_pipeline import auctions  # noqa: E402

ev = pd.read_csv(x.EVENTS, dtype=str, keep_default_na=False)
bars = pd.read_parquet(x.STORE / "bars.parquet", columns=["entity_id", "share_class", "symbol", "date", "close", "member"])
opens = pd.read_parquet(x.STORE / "opens.parquet", columns=["entity_id", "share_class", "date", "open", "open_time"])
b = bars.merge(opens, on=["entity_id", "share_class", "date"], how="left").sort_values(
    ["entity_id", "share_class", "date"], kind="stable", ignore_index=True)
b["prev_close"] = b.groupby(["entity_id", "share_class"], sort=False).close.shift(1)
later, worst, n, maxdiff = 0, [], 0, 0.0
for i, r in ev[(ev.action == "total_return") & (ev.open_return != "")].iterrows():
    d = pd.Timestamp(r.date)
    same = b[(b.symbol == r.symbol) & (b.date == d)]
    if len(same) != 1:
        print(f"{r.symbol} {r.date}: {len(same)} bars share the symbol and date, members {same.member.tolist()}")
    p = same.sort_values("member", kind="stable").iloc[-1]  # apply_events: member wins, else the last in order
    f = x.FORMULA.search(r.evidence)
    closes = x.ex_date_closes(r.evidence, r.date)
    value = 0.0
    for k, (ratio, num) in enumerate(x.terms(f.group(1))):
        sym = closes.get(num)
        if k == 0 and (sym is None or sym == r.symbol):
            value += ratio * p.open
        elif sym is None:
            value += ratio * float(num)
        else:
            off = auctions.official(pd.DataFrame(auctions.fetch(sym, r.date, r.date, r.date), columns=auctions.PRINT_COLUMNS))
            off = off[off.date == r.date].iloc[0]
            value += ratio * float(off.open)
            mins = (pd.Timestamp(off.open_time) - pd.Timestamp(p.open_time)).total_seconds() / 60
            if mins > 0:
                later += 1
                worst.append((round(mins, 1), sym, r.date, int(off.open_size)))
    ret = value / p.prev_close - 1
    diff = abs(round(ret, 4) - float(r.open_return))
    maxdiff = max(maxdiff, diff)
    n += 1
    if diff > 1e-9:
        print(f"{r.symbol} {r.date}: recomputed open_return differs from the csv by {diff:.4f}")
print(f"rows recomputed: {n}; largest difference from the csv: {maxdiff:.4f}")
print(f"other securities whose official open printed after the parent's: {later}")
for m in sorted(worst, reverse=True):
    print(f"  {m[1]} on {m[2]}: {m[0]} minutes after the parent's open (open print of {m[3]} shares)")
