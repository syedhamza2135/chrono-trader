"""How the stronger probes' rules behave on synthetic scores (research/audit/cutoff.md section 8.5). For each of 200
seeds, every probe of reader/probes2.csv gets a score of -5 for a vintage that doesn't know the answer and -0.5 for
one that does, plus normal noise. A share of the events is never learned by any vintage. An honest table has every
vintage from E on know a year-E event; a leaky one also has 2018 know 2019 and 2024 know 2025. Prints rates only; no
model or store is read. Usage: python research/probe_rules_sim.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reader import cutoff as C  # noqa: E402

PROBES = C.load_probes(C.PROBES2)


def table(knows, noise, seed, learned):
    rng = np.random.default_rng(seed)
    out = {}
    for p in PROBES:
        learn = rng.random() < learned
        out[p["probe_id"]] = {v: (-0.5 if knows(v, p["event_year"]) and learn else -5.0) + rng.normal(0, noise)
                              for v in C.VINTAGES}
    return out


def main(runs=200):
    def honest(v, E):
        return v >= E

    def leaky(v, E):
        return v >= E or (v, E) in ((2018, 2019), (2024, 2025))

    for noise in (0.7, 1.0, 1.5):
        for learned in (0.5, 0.8):
            fail = weak = caught = 0
            for s in range(runs):
                res, _, _ = C.probe2_outcomes(table(honest, noise, s, learned), PROBES)
                fail += sum(r["outcome"] == "fail" for r in res.values())
                weak += sum(r["outcome"] == "too weak" for r in res.values())
                res, _, _ = C.probe2_outcomes(table(leaky, noise, s, learned), PROBES)
                caught += (res[2018]["outcome"] == "fail") + (res[2024]["outcome"] == "fail")
            print(f"noise {noise}, share learned {learned}: an honest vintage fails {fail / (10 * runs):.3f} and is"
                  f" too weak {weak / (10 * runs):.3f}; a leaky 2018 or 2024 fails {caught / (2 * runs):.3f}")


if __name__ == "__main__":
    main()
