"""Skeptic check for L5: does the World pass extra store columns through to the view? Synthetic world, with
end_open_time added to labels and n_companies added to stories if absent."""
import sys
from pathlib import Path
import pandas as pd
ROOT = Path.cwd(); sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import synthetic
from world.world import World
T = synthetic.make_tables(0)
print("synthetic labels has end_open_time:", "end_open_time" in T["labels"], "| stories has n_companies:", "n_companies" in T["stories"])
if "end_open_time" not in T["labels"]:
    T["labels"] = T["labels"].assign(end_open_time=pd.NaT)
if "n_companies" not in T["stories"]:
    T["stories"] = T["stories"].assign(n_companies=1)
w = World(**T)
v = w.view(w.clock.decision_time(pd.Timestamp("2017-03-15")))
print("view labels columns:", list(v.labels.columns))
print("view stories columns:", list(v.stories.columns))
