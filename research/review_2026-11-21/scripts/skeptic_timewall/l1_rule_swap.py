"""Skeptic check for L1. Run from the worktree root. Swap rules.bar for the vendor's midnight stamp (a leak in the
wall), then (a) count same-day bars in 9:00 views, (b) run non_interference for all three modes with an honest agent
and with an agent that uses today's close, (c) run the separate availability check from tests/test_leaks.py."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path.cwd(); sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import synthetic
from agent.reversal import ReversalAgent
from eval import leaks
from world import rules
from world.world import World

orig = rules.bar
TABLES = synthetic.make_tables(0)

class SameDayClose(ReversalAgent):
    """Adds today's ret where the view holds a bar dated today (only possible if the wall leaks)."""
    def score(self, f, v):
        b = v.bars[v.bars.date == v.today]
        r = dict(zip(zip(b.entity_id.astype(str), b.share_class.astype(str)), b.ret))
        return super().score(f, v) + 100 * np.array([r.get((e, c), 0.0) for e, c in zip(f.entity_id, f.share_class)])

for name, rule in (("original rule", orig), ("midnight stamp", lambda d: pd.to_datetime(pd.Series(d)).dt.tz_localize("UTC"))):
    rules.bar = rule
    w = World(**TABLES)
    v = w.view(w.clock.decision_time(pd.Timestamp("2017-03-15")))
    print(f"[{name}] bars dated 2017-03-15 or later in the 9:00 view on 2017-03-15:", int((v.bars.date >= v.today).sum()))
    for label, mk in (("honest", lambda: ReversalAgent(warmup=15)), ("same-day-close", lambda: SameDayClose(warmup=15))):
        for how in leaks.HOW:
            r = leaks.non_interference(TABLES, mk, "2017-01-03", "2017-03-15", how, seed=1)
            print(f"[{name}] {label} {how}: problems={len(r)}")
rules.bar = lambda d: pd.to_datetime(pd.Series(d)).dt.tz_localize("UTC")
import test_leaks as tl
days = tl.CHECK_DAYS[:10]
print("[midnight stamp] tests/test_leaks.same_day_bars hits:", len(tl.same_day_bars(World(**TABLES), days)), "of", len(days))
rules.bar = orig
