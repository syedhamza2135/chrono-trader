"""The import boundaries (PLAN 9.1 and 9.11).

- `agent` takes exactly one thing from this project, `from world.view import View`, and from outside only the
  libraries listed here. It names nothing that reads files, runs code or reaches past a view's own rows (`.base`,
  `vars`, `World`, `load`, `read_*`, dunder attributes), whether called or merely referenced.
- `world`, `sim`, `eval` and `data_pipeline` import nothing from `agent`.

An AST check can't be complete. It stops the paths an agent could take by accident or habit; the non-interference
and planted-leak tests (tests/test_leaks.py) stop leaks it misses.

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
             "base", "World", "world", "gc", "sys", "os", "importlib", "inspect", "pickle", "pyarrow"}
FORBIDDEN_PREFIXES = ("read_", "_mgr", "_data", "_pa_array", "_ndarray")


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


def agent_name_problems(path):
    bad = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
        if name is None:
            continue
        dunder = name.startswith("__") and name.endswith("__") and name not in ("__init__", "__name__", "__dict__")
        if name in FORBIDDEN or name.startswith(FORBIDDEN_PREFIXES) or dunder or name == "__builtins__":
            bad.append(f"{name} on line {node.lineno}")
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
                     "def f(v):\n    return v.bars.close.to_numpy().base\n", encoding="utf-8")
    try:
        imports, names = agent_import_problems(probe), agent_name_problems(probe)
    finally:
        probe.unlink()
    assert imports == ["from world.view ['View', 'World']", "from world ['rules']", "import os"]
    assert {n.split(" ")[0] for n in names} >= {"World", "load", "vars", "base"}
