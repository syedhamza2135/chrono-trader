"""Skeptic check for M1. Run from the worktree root.
Part A: each snippet in its own file under a temp agent/ package, through the two AST checks.
Part B: an agent that really reads a parquet file from disk (via an aliased import) passes non-interference."""
import sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path.cwd(); sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import synthetic, test_boundaries as tb
from agent.reversal import ReversalAgent
from eval import leaks
from world.world import World

SNIPPETS = {
    "control_plain_read_parquet": "import pandas as pd\nx = pd.read_parquet('f')\n",
    "control_from_import_no_alias": "from pandas import read_parquet\nx = read_parquet('f')\n",
    "alias_read_parquet": "from pandas import read_parquet as rp\nx = rp('f')\n",
    "alias_read_csv": "from pandas import read_csv as rc\nx = rc('f')\n",
    "np_fromregex": "import numpy as np\ny = np.fromregex('f', 'x', [('a', 'U9')])\n",
    "from_numpy_fromregex": "from numpy import fromregex\ny = fromregex('f', 'x', [('a', 'U9')])\n",
    "alias_np_load": "from numpy import load as ld\ny = ld('f')\n",
}
real_root = tb.ROOT
with tempfile.TemporaryDirectory() as d:
    (Path(d) / "agent").mkdir(); tb.ROOT = Path(d)
    for k, s in SNIPPETS.items():
        p = Path(d) / "agent" / f"{k}.py"; p.write_text(s)
        imp, nam = tb.agent_import_problems(p), tb.agent_name_problems(p)
        print(f"A {k}: import_problems={len(imp)} name_problems={len(nam)} -> {'CAUGHT' if imp or nam else 'MISSED'}")
tb.ROOT = real_root

TABLES = synthetic.make_tables(0)
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / "labels.parquet"
    World(**TABLES).labels.df[["entity_id", "share_class", "date", "label"]].to_parquet(f)  # a file on disk
    from pandas import read_parquet as rp
    class DiskReader(ReversalAgent):
        def score(self, fr, v):
            lab = rp(f); lab = lab[lab.date == v.today]
            fut = dict(zip(zip(lab.entity_id.astype(str), lab.share_class.astype(str)), lab.label))
            return super().score(fr, v) + 100 * np.array([fut.get((e, c), 0.0) for e, c in zip(fr.entity_id, fr.share_class)])
    mk = lambda: DiskReader(warmup=15)
    for how in leaks.HOW:
        r = leaks.non_interference(TABLES, mk, "2017-01-03", "2017-03-15", how, seed=1)
        print(f"B non_interference {how}: problems={len(r)}")
    h = leaks.decisions_until(TABLES, lambda: ReversalAgent(warmup=15), "2017-01-03", "2017-03-15")
    l = leaks.decisions_until(TABLES, mk, "2017-01-03", "2017-03-15")
    m = h.merge(l, on=["date", "entity_id", "share_class"], suffixes=("_h", "_l"))
    print("B rows compared:", len(m), "positions differing from the honest agent:", int((m.position_h != m.position_l).sum()))
