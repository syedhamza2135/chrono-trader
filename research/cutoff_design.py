"""Size the redesign of the cutoff check from the first run's saved cells (research/audit/cutoff.md section 7).
Reads only the per-headline losses in DATA_DIR/reader/cutoff/n2000 (story ids and numbers, no text) and the run log
for speeds. Prints numbers only.

1. Each check's bootstrap standard error at N = 2,000, and its expected 95% half-width at other N (it scales as one
   over the square root of N, since every check is a difference of means over independent headlines).
2. The year-specific effect, pooled over vintages: the mean of the check values, with a paired bootstrap interval.
3. The N each check needs for an expected half-width of at most half an effect E, and the laptop hours for that.

Usage: python research/cutoff_design.py
"""
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reader import cutoff as C  # noqa: E402

N0 = 2000


def needed_cells(checks):
    out = set()
    for kind, V in checks:
        if kind == "A":
            out |= {(V, V + 1), (V + 1, V + 1), (V, V), (V + 1, V)}
        else:
            out |= {(V - 1, V), (V, V), (V - 1, V + 1), (V, V + 1)}
    return out


def main():
    losses = C.read_cells(C.cells(), N0, C.OUT / f"n{N0}")
    point, means = C.boot_means(C.gains(losses))
    rows = {}
    for V in C.CHECK_A:
        a, b = (V + 1, V + 1), (V + 1, V)
        rows[("A", V)] = (point[a] - point[b], means[a] - means[b])
    for V in C.CHECK_B:
        a, b = (V, V), (V, V + 1)
        rows[("B", V)] = (point[a] - point[b], means[a] - means[b])
    se = {k: float(np.std(m, ddof=1)) for k, (_, m) in rows.items()}

    print("1. Standard error at N = 2,000, and the expected 95% half-width (1.96 se) at larger N")
    print("| Check | value | se | hw 2,000 | hw 8,000 | hw 12,000 | hw 20,000 |\n|---|---|---|---|---|---|---|")
    for k, (v, _) in rows.items():
        hw = [1.96 * se[k] * np.sqrt(N0 / n) for n in (2000, 8000, 12000, 20000)]
        print(f"| {k[0]} {k[1]} | {v:+.4f} | {se[k]:.4f} | " + " | ".join(f"{h:.4f}" for h in hw) + " |")
    for kind in "AB":
        s = [se[k] for k in rows if k[0] == kind]
        print(f"check {kind}: se at 2,000 from {min(s):.4f} to {max(s):.4f}, median {np.median(s):.4f}")

    print("\n2. The year-specific effect pooled over vintages (mean of the check values), paired bootstrap")
    pooled = {}
    for kind in "AB":
        ks = [k for k in rows if k[0] == kind]
        v = float(np.mean([rows[k][0] for k in ks]))
        m = np.mean([rows[k][1] for k in ks], axis=0)
        lo, hi = C.interval(m)
        pooled[kind] = (v, lo, hi)
        print(f"check {kind}, {len(ks)} vintages: {v:+.4f} [{lo:+.4f}, {hi:+.4f}]")

    log = (C.OUT / "run_n2000.log").read_text(encoding="utf-8", errors="replace")
    speeds = [float(x) for x in re.findall(r"headlines, ([0-9.]+) a second", log)]
    sp = float(np.median(speeds))
    print(f"\n3. Speed in the first run: median {sp:.1f} headlines a second (range {min(speeds)} to {max(speeds)},"
          f" {len(speeds)} cells)")
    pools = C.load_sample()  # noqa: F841 (the sample is capped at N_MAX; eligible counts are in sample.json)
    import json
    elig = json.loads((C.OUT / "sample.json").read_text(encoding="utf-8"))["eligible_by_year"]
    print("smallest eligible year:", min(elig.items(), key=lambda kv: kv[1]))
    for kind, checks in (("A", [k for k in rows if k[0] == "A"]), ("B", [k for k in rows if k[0] == "B"]),
                         ("A and B", list(rows))):
        cells = needed_cells(checks)
        print(f"cells for {kind}: {len(cells)}")
        for E in (0.01, 0.02, 0.03, 0.05):
            # half-width at most E / 2: N = N0 * (1.96 se / (E / 2))^2, for the median and the largest se
            need = [N0 * (1.96 * se[k] / (E / 2)) ** 2 for k in checks]
            nmed, nmax = float(np.median(need)), float(max(need))
            hours = len(cells) * nmed / sp / 3600
            print(f"  E {E:.2f}: N for the median check {nmed:,.0f}, for every check {nmax:,.0f}; at the median N,"
                  f" {len(cells) * nmed:,.0f} passes, {hours:.1f} hours at {sp:.1f} a second")


if __name__ == "__main__":
    main()
