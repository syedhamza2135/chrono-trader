"""I1 follow-up: CPRI, KORS, CCE, CCEP, TYC in the index file, reference/memberships.csv and reference/identity.csv;
and, for every session 2016 to 2018, the snapshot-minus-rows and rows-minus-snapshot sets, grouped.
Counts, ids, symbols and dates only.
Run from the repo root with D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore <this file>.
"""
from collections import Counter

import pandas as pd

ref = pd.read_csv("reference/memberships.csv", dtype=str)
ref["f"] = pd.to_datetime(ref.member_from)
ref["t"] = pd.to_datetime(ref.member_to).fillna(pd.Timestamp("2262-01-01"))
snap = pd.read_csv("D:/chrono-data/membership/components_extended.csv", parse_dates=["date"])
snap["set"] = snap.tickers.str.split(",").map(lambda x: {t.strip() for t in x if t.strip()})
ide = pd.read_csv("reference/identity.csv", dtype=str).fillna("")
WATCH = ["CPRI", "KORS", "CCE", "CCEP", "TYC", "JCI"]

for t in WATCH:
    has = snap[snap.set.map(lambda s: t in s)]
    # runs of consecutive snapshots holding t
    idx = list(has.index)
    runs, start, prev = [], None, None
    for i in idx:
        if start is None:
            start = i
        elif i != prev + 1:
            runs.append((start, prev)); start = i
        prev = i
    if start is not None:
        runs.append((start, prev))
    nxt = lambda j: snap.date[j + 1].date() if j + 1 < len(snap) else None
    print(t, "in index file: runs (first snapshot, first snapshot without):",
          [(snap.date[a].date().isoformat(), str(nxt(b))) for a, b in runs if nxt(b) is None or nxt(b) >= pd.Timestamp("2015-01-01").date()])
    for r in ref[ref.source_ticker == t].itertuples():
        print("   membership row:", r.entity_id, r.member_from, r.member_to if isinstance(r.member_to, str) else None, "|", r.how)
    for r in ide[ide.symbol == t].itertuples():
        print("   identity row:", r.entity_id, r.valid_from, r.valid_to or None, r.share_class or "-")

print()
for e in sorted(set(ide[ide.symbol.isin(WATCH)].entity_id)):
    print("entity", e, "membership rows:",
          [(r.member_from, r.member_to if isinstance(r.member_to, str) else None, r.source_ticker) for r in ref[ref.entity_id == e].itertuples()])

bars = pd.read_parquet("D:/chrono-data/store/bars.parquet", columns=["date"])
sessions = pd.DatetimeIndex(sorted(bars.date.unique()))
sessions = sessions[(sessions >= "2016-01-04") & (sessions <= "2018-12-31")]
groups = Counter()
for d in sessions:
    act = ref[(ref.f <= d) & (ref.t > d)]
    s = snap[snap.date <= d].iloc[-1].set
    rt = set(act.source_ticker)
    pairs = act.entity_id.value_counts()
    groups[(act.entity_id.nunique(), len(s), len(act), int((pairs > 1).sum()), tuple(sorted(s - rt)), tuple(sorted(rt - s)))] += 1
print("\nsessions 2016-2018 grouped (entities, snapshot tickers, active rows, entities with 2+ rows, snapshot-only, rows-only): sessions")
for k, v in sorted(groups.items()):
    print(" ", k, v)
