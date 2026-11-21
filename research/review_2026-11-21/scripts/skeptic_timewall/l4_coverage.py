"""Skeptic check for L4: which (day, mode) pairs do the non-interference tests run, and on which world?"""
import sys, ast
from pathlib import Path
import pandas as pd
ROOT = Path.cwd(); sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import test_leaks as tl, synthetic
from eval import leaks
pairs = {(d, h) for i, d in enumerate(tl.CHECK_DAYS) for h in [leaks.HOW[i % 3]]}
pairs |= {(tl.T, h) for h in leaks.HOW} | {(pd.Timestamp(tl.FIRST), h) for h in leaks.HOW}
days = sorted({d for d, _ in pairs})
print("synthetic world spans", synthetic.FIRST, "to", synthetic.LAST)
print("fixed synthetic (day, mode) pairs:", len(pairs), "| distinct days:", len(days), "| first", days[0].date(), "last", days[-1].date())
print("  per mode:", {h: sum(1 for _, x in pairs if x == h) for h in leaks.HOW})
print("hypothesis random days: max_examples =", 3, "drawn from", tl._s[0].date(), "to", tl._s[-1].date())
src = (ROOT / "tests" / "test_leaks.py").read_text(encoding="utf-8")
calls = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "non_interference"]
real = [n.lineno for n in calls if any(isinstance(a, ast.Name) and a.id == "real_tables" for a in n.args)]
print("non_interference calls in tests/test_leaks.py:", len(calls), "| on real_tables (lines):", real)
other = [p.name for p in (ROOT / "tests").glob("test_*.py") if "non_interference" in p.read_text(encoding="utf-8") and p.name != "test_leaks.py"]
print("other test files calling non_interference:", other)
