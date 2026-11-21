"""I1 follow-up: for the first day of each low run, the membership entities that left since the previous session
and those that join on the next session after the run. Also the rows of ACE and CB. Ids, symbols and dates only.
Run from the repo root with D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore <this file>.
"""
import pandas as pd

ref = pd.read_csv("reference/memberships.csv", dtype=str)
ref["f"] = pd.to_datetime(ref.member_from)
ref["t"] = pd.to_datetime(ref.member_to).fillna(pd.Timestamp("2262-01-01"))
bars = pd.read_parquet("D:/chrono-data/store/bars.parquet", columns=["date"])
S = pd.DatetimeIndex(sorted(bars.date.unique()))
S = S[(S >= "2016-01-04") & (S <= "2019-01-31")]


def ents(d):
    a = ref[(ref.f <= d) & (ref.t > d)]
    return set(a.entity_id)


def tick(es, d):
    a = ref[(ref.f <= d + pd.Timedelta(days=30)) & (ref.t > d - pd.Timedelta(days=30)) & ref.entity_id.isin(es)]
    return sorted(set(zip(a.entity_id, a.source_ticker, a.member_from, a.member_to.fillna("open"))))


n = {d: len(ents(d)) for d in S}
i = 0
while i < len(S):
    if n[S[i]] < 500 and (i == 0 or n[S[i - 1]] >= 500):
        j = i
        while j + 1 < len(S) and n[S[j + 1]] < 500:
            j += 1
        before, first, after = S[i - 1], S[i], S[j + 1]
        left = ents(before) - ents(first)
        joined = ents(after) - ents(S[j])
        print(f"run {first.date()}..{S[j].date()} ({j - i + 1} sessions):", "left at start", tick(left, first),
              "| joined after", tick(joined, after))
        i = j + 1
    else:
        i += 1
print()
for t in ["ACE", "CB"]:
    for r in ref[ref.source_ticker == t].itertuples():
        print(t, "row:", r.entity_id, r.member_from, r.member_to if isinstance(r.member_to, str) else None, "|", r.how)
