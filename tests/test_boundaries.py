"""The import boundaries (PLAN 9.1 and 9.11).

- `agent` takes exactly one thing from this project, `from world.view import View`, and from outside only the
  libraries listed here. It names nothing that reads files, runs code or reaches past a view's own rows (`.base`,
  `vars`, `World`, `load`, `read_*`, dunder attributes), whether called or merely referenced.
- `world`, `sim`, `eval` and `data_pipeline` import nothing from `agent`.

An AST check can't be complete. The non-interference and planted-leak tests (tests/test_leaks.py) catch leaks through
what a run is handed, but not reads from disk: the files are the same in both runs. Those are stopped only here, by
name (`read_*`, `read`, `io`, `get_engine` and the rest), so a new way to read files must be added to FORBIDDEN. Every
name counts: an attribute, a variable, each part of an imported module's path, and both the imported name and its
alias in `from x import a as b` (the review of 21 Nov, M-1, got past the check with `from pandas import read_parquet
as rp`). A real guarantee would run decide() in a process that can't see DATA_DIR or reference/, a later option.

Run with: python -m pytest tests
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OURS = {"agent", "world", "sim", "eval", "data_pipeline", "reader", "research", "tests"}
AGENT_LIBRARIES = {"numpy", "pandas", "scipy", "sklearn", "river", "math", "statistics", "dataclasses", "functools",
                   "itertools", "collections", "typing", "heapq", "bisect", "enum", "abc", "__future__"}
FORBIDDEN = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr",
             "delattr", "load", "loads", "loadtxt", "genfromtxt", "fromfile", "memmap", "read_text", "read_bytes",
             "base", "World", "world", "gc", "sys", "os", "importlib", "inspect", "pickle", "pyarrow",
             "io", "get_engine", "read", "HDFStore", "open_memmap", "ParquetFile", "parquet", "feather", "pathlib",
             "Path", "urlopen", "requests", "subprocess", "socket", "shutil", "as_strided", "stride_tricks",
             "fromregex", "npyio", "ctypes", "builtins", "tempfile", "glob", "mmap", "urllib", "zipfile", "lib",
             # Code in a string (the judge of 21 Nov, J-1): a query string and a string annotation both run code.
             "query", "get_type_hints", "ForwardRef", "_evaluate", "singledispatch"}
FORBIDDEN_PREFIXES = ("read_", "load_", "_mgr", "_data", "_pa_array", "_ndarray")


def statements(path):
    """(kind, module, names) for every import in one file, relative imports resolved against its package."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = path.relative_to(ROOT).with_suffix("").parts[:-1]
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [("import", a.name, []) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = ".".join(package[: len(package) - node.level + 1]) if node.level else ""
            module = ".".join(x for x in (base, node.module or "") if x)
            out.append(("from", module, [a.name for a in node.names]))
    return out


def files(package):
    return sorted((ROOT / package).rglob("*.py"))


def agent_import_problems(path):
    bad = []
    for kind, module, names in statements(path):
        top = module.split(".")[0]
        if top == "agent":
            continue
        if top in OURS:
            if not (kind == "from" and module == "world.view" and set(names) <= {"View"}):
                bad.append(f"{kind} {module} {names}")
        elif top not in AGENT_LIBRARIES:
            bad.append(f"{kind} {module}")
    return bad


def forbidden(name):
    dunder = name.startswith("__") and name.endswith("__") and name not in ("__init__", "__name__")
    return name in FORBIDDEN or name.startswith(FORBIDDEN_PREFIXES) or dunder or name == "__builtins__"


def agent_name_problems(path):
    """Every forbidden name: a variable, an attribute, and in an import each part of the module's path, the imported
    name and its alias, so `from pandas import read_parquet as rp` is caught at the import."""
    bad = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Name):
            names = [node.id]
        elif isinstance(node, ast.Attribute):
            names = [node.attr]
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = (node.module or "").split(".") if isinstance(node, ast.ImportFrom) else []
            module = [] if module == ["world", "view"] else module  # the one import allowed, checked above
            names = module + [part for a in node.names for part in a.name.split(".") + [a.asname or ""]]
        else:
            continue
        bad += [f"{name} on line {node.lineno}" for name in names if name and forbidden(name)]
    return bad


def test_agent_takes_only_view_from_this_project_and_only_listed_libraries():
    bad = {p.name: agent_import_problems(p) for p in files("agent")}
    assert {k: v for k, v in bad.items() if v} == {}


def test_agent_names_nothing_that_reads_files_runs_code_or_reaches_past_a_view():
    bad = {p.name: agent_name_problems(p) for p in files("agent")}
    assert {k: v for k, v in bad.items() if v} == {}


def test_the_environment_imports_nothing_from_agent():
    bad = [(str(p.relative_to(ROOT)), m) for pkg in ("world", "sim", "eval", "data_pipeline", "reader") for p in files(pkg)
           for _, m, _ in statements(p) if m.split(".")[0] == "agent"]
    assert bad == []


def test_world_view_holds_nothing_an_agent_could_load_the_store_with():
    """The module agents may import defines View only; World lives in world/world.py."""
    tree = ast.parse((ROOT / "world" / "view.py").read_text(encoding="utf-8"))
    defined = {n.name for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))}
    assert defined == {"View"}
    imported = [m for _, m, _ in statements(ROOT / "world" / "view.py")]
    assert imported == ["world.clock"]


def test_the_checks_catch_the_ways_round_them():
    """The review's sneaky agent: World from world.view, an aliased World.load, vars(pd), and .base."""
    probe = ROOT / "agent" / "_probe_for_test.py"
    probe.write_text("import pandas as pd\nfrom world.view import View, World\nfrom world import rules\n"
                     "from .reversal import FEATURES\nimport os\n"
                     "loader = World.load\nw = loader()\nx = vars(pd)['read_parquet']\n"
                     "y = pd.io.parquet.get_engine('pyarrow').read('store.parquet')\n"
                     "def f(v):\n    return v.bars.close.to_numpy().base\n", encoding="utf-8")
    try:
        imports, names = agent_import_problems(probe), agent_name_problems(probe)
    finally:
        probe.unlink()
    assert imports == ["from world.view ['View', 'World']", "from world ['rules']", "import os"]
    assert {n.split(" ")[0] for n in names} >= {"World", "load", "vars", "base", "io", "get_engine", "read"}


LEAKY_AGENT = """import numpy as np
from pandas import read_parquet as rp
from numpy import load as ld
from numpy import fromregex
from scipy.sparse import load_npz
import typing
import pandas as pd
from world.view import View
from .reversal import ReversalAgent


class DiskReader(ReversalAgent):
    def score(self, frame, view):
        lab = rp("D:/chrono-data/store/labels.parquet")
        future = lab[lab.date == view.today].set_index("entity_id").label
        extra = ld("x.npy") + np.fromregex("y.txt", "z", [("a", "U9")]) + fromregex("y.txt", "z", [("a", "U9")])
        sneaky = pd.__dict__["read_" + "csv"]("labels.csv")  # module globals, by a built string
        rows = frame.query("entity_id == @pd.read_csv('labels.csv').entity_id[0]", engine="python")
        hints = typing.get_type_hints(self.score)  # a string annotation runs as code
        return super().score(frame, view) + 100 * frame.entity_id.map(future).fillna(0).to_numpy() + extra
"""


def test_the_checks_catch_an_agent_that_reads_future_labels_from_a_file():
    """The review of 21 Nov, M-1: this agent passes non-interference under all three perturbations, since the file
    is the same in both runs, so the name check is what stops it. Each way it reads a file is caught at the import or
    the call: an aliased read_parquet, an aliased numpy load, numpy's fromregex by attribute and by import, and the
    judge's J-1 and J-2: scipy's load_npz, a module's __dict__, a query string and typing.get_type_hints."""
    probe = ROOT / "agent" / "_probe_leaky_for_test.py"
    probe.write_text(LEAKY_AGENT, encoding="utf-8")
    try:
        names = agent_name_problems(probe)
    finally:
        probe.unlink()
    caught = {n.split(" ")[0] for n in names}
    assert {"read_parquet", "load", "fromregex", "load_npz", "__dict__", "query", "get_type_hints"} <= caught
    lines = {int(n.split(" ")[-1]) for n in names}
    assert {2, 3, 4, 5} <= lines  # each import is caught where it is made, before any call
