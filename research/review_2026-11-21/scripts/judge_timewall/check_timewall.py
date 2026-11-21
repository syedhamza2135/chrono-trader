"""Judge checks for the time wall, on the made-up world in tests/synthetic.py. Run from the repo root:
D:\venvs\chrono-trader\Scripts\python.exe <this file>"""
import sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import synthetic, test_boundaries as tb
from agent.reversal import ReversalAgent
from eval import leaks
from world.world import World

TABLES = synthetic.make_tables(0)
FIRST, T = "2017-01-03", pd.Timestamp("2017-03-15")

# 1. An agent that leaks through a channel outside the World it is handed passes non-interference.
OUTSIDE = World(**TABLES).labels.df  # stands in for a file on disk, which perturb() never touches
FUT = dict(zip(zip(OUTSIDE.entity_id.astype(str), OUTSIDE.share_class.astype(str), OUTSIDE.date), OUTSIDE.label))
class OutOfBand(ReversalAgent):
    def score(self, f, v):
        ahead = np.array([FUT.get((e, c, v.today), 0.0) for e, c in zip(f.entity_id, f.share_class)])
        return super().score(f, v) + 100 * ahead
mk = lambda: OutOfBand(warmup=15)
for how in leaks.HOW:
    print("1. out-of-band future labels,", how, "->", leaks.non_interference(TABLES, mk, FIRST, T, how, seed=1) or "PASSES (not caught)")
honest = leaks.decisions_until(TABLES, lambda: ReversalAgent(warmup=15), FIRST, T)
leaky = leaks.decisions_until(TABLES, mk, FIRST, T)
print("   but its positions differ from the honest agent's on", (honest.position != leaky.position).sum(), "rows")

# 2. The AST boundary misses a reader imported under an alias.
with tempfile.TemporaryDirectory() as d:
    (Path(d) / "agent").mkdir()
    p = Path(d) / "agent" / "evil.py"
    p.write_text("from pandas import read_parquet as rp\nfrom numpy import fromregex\n"
                 "x = rp('D:/chrono-data/store/labels.parquet')\ny = fromregex('reference/price_events.csv', 'x', [('a', 'U9')])\n")
    tb.ROOT = Path(d)
    print("2. import problems:", tb.agent_import_problems(p), "| name problems:", tb.agent_name_problems(p))

# 3. A view is detached: mutating it changes neither the World nor the next view.
w = World(**TABLES)
t0 = w.clock.decision_time(pd.Timestamp("2017-03-14")); t1 = w.clock.decision_time(pd.Timestamp("2017-03-15"))
v0 = w.view(t0); n_before = len(w.bars.df); first_close = w.bars.df.close.iloc[0]
v0.bars.loc[:, "close"] = -1.0; v0.labels.loc[:, "label"] = 99.0
v1 = w.view(t1)
print("3. world bars rows same:", len(w.bars.df) == n_before, "| world close untouched:", w.bars.df.close.iloc[0] == first_close,
      "| next view clean:", (v1.bars.close != -1).all() and (v1.labels.label != 99).all())
print("   view attributes:", sorted(vars(v0)))
print("   any attribute is a World:", any(isinstance(x, World) for x in vars(v0).values()))

# 4. Cut-offs at 9:00: no bar dated today or later, no label ending today or later, no story after t.
bad = 0
for day in w.clock.between("2017-01-03", "2017-06-30"):
    v = w.view(w.clock.decision_time(day))
    bad += int((v.bars.date >= v.today).sum()) + int((v.labels.end >= v.today).sum())
    bad += int((pd.to_datetime(v.stories.updated_at, utc=True) + pd.Timedelta(minutes=15) > v.t).sum())
    bad += int((v.sessions > v.today).sum())
print("4. rows past the 9:00 cut over H1 2017:", bad)
