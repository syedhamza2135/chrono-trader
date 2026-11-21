"""I3: what types reach identity.compare's `r.member_to or date.max` (identity.py:460).
Rebuilds the identity inputs offline, pinned to the original run date (today = 2026-10-31, as in
D:/chrono-data/review/scripts/run_identity_pinned.py), with every network call blocked. Writes nothing.
Run from the repo root:
  D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore research\\review_2026-11-21\\scripts\\skeptic_checks\\i3_member_to_types.py
"""
import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import data_pipeline.alpaca as alpaca  # noqa: E402
import data_pipeline.identity as identity  # noqa: E402
import data_pipeline.wikipedia as wp  # noqa: E402


def blocked(*a, **k):
    raise RuntimeError("network blocked in this check")


wp._get = blocked
alpaca.pages = blocked
identity.write_tables = blocked  # never write

today = date(2026, 10, 31)
b = identity.build_all(today)
members = b["members"]
resolved = members[members.entity != ""]
print("members rows", len(members), "resolved rows", len(resolved), "member_to dtype", resolved.member_to.dtype)
kinds = Counter()
for r in resolved.itertuples():
    v = r.member_to
    if v is None:
        kinds["None"] += 1
    elif isinstance(v, float) and math.isnan(v):
        kinds["float NaN"] += 1
    else:
        kinds[type(v).__name__] += 1
print("member_to types reaching compare:", dict(kinds))
print("member_from types:", dict(Counter(type(v).__name__ for v in resolved.member_from)))
missing, extra = identity.compare(b["wiki"], b["find"], resolved)
print("compare ran: missing entities", len(missing), "extra entities", len(extra))
# Same check on what memberships.csv holds (written by write_tables from the same frame)
import pandas as pd  # noqa: E402
csv = pd.read_csv("reference/memberships.csv", dtype=str)
print("reference/memberships.csv rows", len(csv), "empty member_to", int(csv.member_to.isna().sum()),
      "| resolved rows with None member_to", kinds["None"])
