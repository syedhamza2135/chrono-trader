"""The pilot for the stronger probes' margin (research/audit/cutoff.md section 8.4). Applies the flag rule of
reader.cutoff.probe2_cell, with a margin of 2, 3 or 4, to the first probe set's saved scores (n2000/probes.parquet).
Prints counts and probe ids only. Usage: python research/probe_margin_pilot.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reader import cutoff as C  # noqa: E402


def main():
    sc = pd.read_parquet(C.OUT / "n2000" / "probes.parquet")
    years = {p["probe_id"]: p["event_year"] for p in C.load_probes()}
    keep = C.MARGIN
    try:
        for margin in (2.0, 3.0, 4.0):
            C.MARGIN = margin
            nxt = flg = 0
            flagged = []
            for pid, g in sc.groupby("probe_id", sort=True):
                s, E = dict(zip(g.vintage, g.score)), years[pid]
                if not 2016 <= E <= 2024:
                    continue
                inf, fl, _, _ = C.probe2_cell(s, E, E - 1)
                nxt += inf
                flg += fl
                flagged += [f"{pid} on {E - 1}"] if fl else []
            print(f"margin {margin:.0f}: informative for the vintage just before the event {nxt}, flagged {flg}"
                  f" ({', '.join(flagged) or 'none'})")
    finally:
        C.MARGIN = keep
    # the 2024 rule (probe2_last), tried on every earlier year: V = E-1, lo from V's three predecessors
    usable = flg = 0
    flagged = []
    for pid, g in sc.groupby("probe_id", sort=True):
        s, E = dict(zip(g.vintage, g.score)), years[pid]
        if not 2016 <= E <= 2024:
            continue
        lo = C.probe2_lo(s, E - 1)
        if lo <= -C.MARGIN:
            usable += 1
            if s[E - 1] >= lo + C.MARGIN / 2:
                flg += 1
                flagged.append(f"{pid} on {E - 1}")
    print(f"the 2024 rule on the vintage just before each event: usable {usable}, flagged {flg}"
          f" ({', '.join(flagged) or 'none'})")


if __name__ == "__main__":
    main()
