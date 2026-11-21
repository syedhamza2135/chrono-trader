"""Judge check for M-2 (b): how research/ex_date_opens.py reads each total_return row's formula, without calling
Alpaca. For each row: each term's ratio, and whether it is the parent's open, another security's open, or a fixed
amount (cash). Prints no prices beyond what price_events.csv already holds.
Usage: python research/review_2026-11-21_fixes/judge_scripts/m2_terms.py"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT))
import ex_date_opens as x  # noqa: E402

ev = pd.read_csv(ROOT / "reference" / "price_events.csv", dtype=str, keep_default_na=False)
for i, r in ev[ev.action == "total_return"].iterrows():
    f = x.FORMULA.search(r.evidence)
    if not f or "+" not in f.group(1):
        print(f"{r.symbol} {r.date}: blank ({'no formula' if not f else 'ratio: ' + f.group(0)})")
        continue
    closes = x.ex_date_closes(r.evidence, r.date)
    kinds = []
    for k, (ratio, n) in enumerate(x.terms(f.group(1))):
        sym = closes.get(n)
        if k == 0 and (sym is None or sym == r.symbol):
            kinds.append(f"parent x{ratio:.4g}" + ("" if sym else " (unmatched)"))
        elif sym is None:
            kinds.append(f"FIXED {n} x{ratio:.4g}")
        else:
            kinds.append(f"{sym} open x{ratio:.4g}")
    n_formulas = len(x.FORMULA.findall(r.evidence))
    print(f"{r.symbol} {r.date}: {f.group(0)} -> {'; '.join(kinds)}  [formulas in evidence: {n_formulas}]")
