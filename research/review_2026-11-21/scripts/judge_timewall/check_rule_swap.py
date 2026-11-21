# Non-interference trusts the wall's own rules: with bars made visible at the vendor's midnight stamp (a planted
# leak in the wall itself), an honest agent still passes, because perturb() classifies "late" with the same rule.
import sys
from pathlib import Path
import pandas as pd
ROOT = Path.cwd(); sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import synthetic
from agent.reversal import ReversalAgent
from eval import leaks
from world import rules
from world.world import World
rules.bar = lambda dates: pd.to_datetime(pd.Series(dates)).dt.tz_localize("UTC")
TABLES = synthetic.make_tables(0)
w = World(**TABLES)
v = w.view(w.clock.decision_time(pd.Timestamp("2017-03-15")))
print("bars dated today in the 9:00 view under the swapped rule:", int((v.bars.date >= v.today).sum()))
print("non_interference, scramble:", leaks.non_interference(TABLES, lambda: ReversalAgent(warmup=15), "2017-01-03", "2017-03-15", "scramble", seed=1) or "PASSES")
