"""I1: on the 41 low sessions, compare the index file's snapshot to reference/memberships.csv.
For each low date: snapshot tickers, active membership rows, distinct entities, tickers in the snapshot with no
active row under that source_ticker, rows active whose source_ticker is not in the snapshot, and entities that
hold two or more active rows. Counts, ids, symbols and dates only.
Run from the repo root:
  D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore research\\review_2026-11-21\\scripts\\skeptic_checks\\i1_low_sessions.py
"""
from collections import Counter

import pandas as pd

ref = pd.read_csv("reference/memberships.csv", dtype=str)
ref["f"] = pd.to_datetime(ref.member_from)
ref["t"] = pd.to_datetime(ref.member_to).fillna(pd.Timestamp("2262-01-01"))
snap = pd.read_csv("D:/chrono-data/membership/components_extended.csv", parse_dates=["date"])
snap["set"] = snap.tickers.str.split(",").map(lambda x: {t.strip() for t in x if t.strip()})
ide = pd.read_csv("reference/identity.csv", dtype=str).fillna("")
bars = pd.read_parquet("D:/chrono-data/store/bars.parquet", columns=["date"])
sessions = pd.DatetimeIndex(sorted(bars.date.unique()))
sessions = sessions[(sessions >= "2016-01-04") & (sessions <= "2018-12-31")]


def sym_entities(sym, d):
    ds = d.date().isoformat()
    hit = ide[(ide.symbol == sym) & (ide.valid_from <= ds) & ((ide.valid_to == "") | (ide.valid_to >= ds))]
    return sorted(set(hit.entity_id))


low = []
allc = Counter()
miss_counter = Counter()
for d in sessions:
    act = ref[(ref.f <= d) & (ref.t > d)]
    n_ent = act.entity_id.nunique()
    allc[n_ent] += 1
    if n_ent >= 500:
        continue
    s = snap[snap.date <= d].iloc[-1]
    tick = s.set
    rows_t = set(act.source_ticker)
    only_snap = sorted(tick - rows_t)
    only_rows = sorted(rows_t - tick)
    multi = act.entity_id.value_counts()
    multi = sorted(multi[multi > 1].index)
    low.append(d)
    for t in only_snap:
        miss_counter[t] += 1
    print(d.date(), "snap", s.date.date(), "tickers", len(tick), "rows", len(act), "entities", n_ent,
          "| in snapshot, no active row:", only_snap, "| active row, not in snapshot:", only_rows,
          "| entities with 2+ rows:", len(multi))
print("\nlow sessions:", len(low), "distinct-entity counts 2016-2018:", dict(sorted(allc.items())))
print("tickers in snapshot with no active row, by number of low sessions:", miss_counter.most_common())

# For each such ticker: the identity entity on the date, and that entity's membership rows.
print("\nwhere the missing tickers go:")
for t in sorted(miss_counter):
    first = next(d for d in low if t in snap[snap.date <= d].iloc[-1].set and t not in set(ref[(ref.f <= d) & (ref.t > d)].source_ticker))
    ents = sym_entities(t, first)
    print(" ", t, "first low day", first.date(), "identity entity on that day:", ents)
    for e in ents:
        for r in ref[ref.entity_id == e].itertuples():
            print("     row", e, r.member_from, r.member_to if isinstance(r.member_to, str) else None, r.source_ticker, "|", r.how)
    for r in ref[ref.source_ticker == t].itertuples():
        print("     rows with source_ticker", t, ":", r.entity_id, r.member_from, r.member_to if isinstance(r.member_to, str) else None, "|", r.how)
