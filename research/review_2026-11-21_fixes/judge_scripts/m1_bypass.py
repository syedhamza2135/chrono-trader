"""Judge check for M-1: snippets an agent file could hold, run through the hardened checks in tests/test_boundaries.py
(agent_import_problems and agent_name_problems) without writing into agent/. Then three that pass are run for
real on a made-up file in a temp folder, to show they read it. Changes no repo file.
Usage: python research/review_2026-11-21_fixes/judge_scripts/m1_bypass.py"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))
import test_boundaries as tb  # noqa: E402


class Probe:
    """Stands in for agent/_probe.py: the checks only read its text and its place in the package."""
    def __init__(self, text):
        self.text = text

    def read_text(self, encoding=None):
        return self.text

    def relative_to(self, root):
        return Path("agent/_probe.py")


SNIPPETS = {
    "review: aliased read_parquet": "from pandas import read_parquet as rp\nx = rp('labels.parquet')\n",
    "review: aliased read_csv": "from pandas import read_csv as rc\nx = rc('a.csv')\n",
    "review: np.fromregex": "import numpy as np\nx = np.fromregex('a', 'b', [('a', 'U9')])\n",
    "review: from numpy import fromregex": "from numpy import fromregex\n",
    "review: from numpy import load as ld": "from numpy import load as ld\n",
    "module __dict__": "import pandas as pd\nx = pd.__dict__['read_' + 'parquet']('labels.parquet')\n",
    "typing.get_type_hints on a string annotation":
        "import typing\n\ndef f(x: \"[l for l in __builtins__['op' 'en']('labels.csv')]\"): pass\n"
        "rows = typing.get_type_hints(f)['x']\n",
    "a query string": "import pandas as pd\np = 'labels.csv'\n"
        "x = pd.DataFrame({'a': [1]}).query('a > @pd.read_csv(@p).label.iloc[0]', engine='python')\n",
    "relative world.view": "from ..world.view import View\n",
    "View's module globals": "from world.view import View\nx = View.__init__.__globals__\n",
    "scipy.sparse.load_npz": "from scipy.sparse import load_npz\nx = load_npz('emb.npz')\n",
}

for name, text in SNIPPETS.items():
    p = Probe(text)
    found = tb.agent_import_problems(p) + tb.agent_name_problems(p)
    print(f"{'CAUGHT' if found else 'PASSES'}  {name}: {found}")

# Run the two that pass, on a made-up file.
d = Path(tempfile.mkdtemp())
(d / "labels.csv").write_text("date,label\n2030-01-02,0.5\n", encoding="utf-8")
import pandas as pd  # noqa: E402
pd.DataFrame({"label": [0.5]}).to_parquet(d / "labels.parquet")
ns = {}
exec(SNIPPETS["module __dict__"].replace("'labels.parquet'", repr(str(d / "labels.parquet"))), ns)
print("pd.__dict__ read:", ns["x"].label.tolist())
ns = {}
exec(SNIPPETS["typing.get_type_hints on a string annotation"].replace("labels.csv", str(d / "labels.csv").replace("\\", "/")), ns)
print("get_type_hints read:", ns["rows"])
ns = {}
exec(SNIPPETS["a query string"].replace("'labels.csv'", repr(str(d / "labels.csv"))), ns)
print("query read the file and returned rows:", len(ns["x"]))
