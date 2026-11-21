"""Checks of the membership and identity tables in D:/chrono-data/store. Prints counts, ids, symbols and dates only.
Run from the repo root:
  D:\\venvs\\chrono-trader\\Scripts\\python.exe -W ignore research\\review_2026-11-21\\scripts\\check_identity\\check_identity.py
"""
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

S = "D:/chrono-data/store/"
mem = pq.read_table(S + "membership.parquet").to_pandas()
ide = pq.read_table(S + "identity.parquet").to_pandas()
bars = pq.read_table(S + "bars.parquet", columns=["entity_id", "share_class", "symbol", "date", "member"]).to_pandas()
opens = pq.read_table(S + "opens.parquet", columns=["entity_id", "share_class", "date", "open"]).to_pandas()
counts = json.load(open(S + "counts.json"))
DATA_END = pd.Timestamp(counts["data_end"])
FAR = pd.Timestamp("2262-01-01")
sessions = pd.DatetimeIndex(sorted(bars.date.unique()))
sessions = sessions[sessions <= DATA_END]
sess_ns = sessions.to_numpy().astype("datetime64[ns]")
print("rows: membership", len(mem), "identity", len(ide), "bars", len(bars), "opens", len(opens))
print("data_end", DATA_END.date(), "| sessions in bars", len(sessions), sessions.min().date(), sessions.max().date())


def head(title):
    print("\n==== " + title)


def day(x):
    return None if pd.isna(x) else pd.Timestamp(x).date().isoformat()


# ------------------------------------------------------------------ check 1
head("CHECK 1: membership dates and null member_to")
has_to = mem.member_to.notna()
bad = mem[has_to & (mem.member_from > mem.member_to)]
eq = mem[has_to & (mem.member_from == mem.member_to)]
print("rows with member_to present:", int(has_to.sum()), "| member_from > member_to:", len(bad),
      "| member_from == member_to (empty span, member_to is exclusive):", len(eq))
null = mem[~has_to]
print("null member_to rows:", len(null), "| distinct entities:", null.entity_id.nunique(),
      "| member_from of those rows:", day(null.member_from.min()), "to", day(null.member_from.max()))
nf = null[["entity_id", "member_from"]].rename(columns={"member_from": "null_from"})
later = mem.merge(nf, on="entity_id")
print("rows that start after a null-member_to row of the same entity:", int((later.member_from > later.null_from).sum()),
      "| entities with two null rows:", int(null.entity_id.duplicated().sum()))
active = mem[(mem.member_from <= DATA_END) & (mem.member_to.isna() | (mem.member_to > DATA_END))]
print("rows active on data_end (member_from <= data_end, member_to null or later):", len(active),
      "| entities:", active.entity_id.nunique(), "| of which member_to present:", int(active.member_to.notna().sum()))
print("member_to max:", day(mem.member_to.max()), "| rows with member_to after data_end:", int((has_to & (mem.member_to > DATA_END)).sum()))
snap = pd.read_csv("D:/chrono-data/membership/components_extended.csv")
last = snap.iloc[-1]
tick = last.tickers.split(",")
print("index file components_extended.csv, last snapshot", last.date, ":", len(tick), "tickers (distinct", len(set(tick)), ")")
print("PLAN L476 says the membership ends with 503 members")
ends_snap = mem[has_to & (mem.member_to == pd.Timestamp(last.date))]
print("rows whose member_to equals the last snapshot date:", len(ends_snap))

# ------------------------------------------------------------------ check 2
head("CHECK 2: membership overlaps and daily member counts")
m = mem.assign(end=mem.member_to.fillna(FAR))
over = []
for e, g in m.groupby("entity_id"):
    r = list(g.sort_values("member_from").itertuples())
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            if r[j].member_from < r[i].end and r[i].member_from < r[j].end:  # member_to is exclusive
                over.append((e, day(r[i].member_from), day(r[i].member_to), day(r[j].member_from), day(r[j].member_to)))
touch = 0
for e, g in m.groupby("entity_id"):
    r = list(g.sort_values("member_from").itertuples())
    touch += sum(1 for a, b in zip(r, r[1:]) if b.member_from == a.end)
print("entities with more than one row:", int((m.entity_id.value_counts() > 1).sum()),
      "| overlapping row pairs for one entity:", len(over), "| touching spans (not overlap):", touch)
for o in over[:20]:
    print("   (entity, from1, to1, from2, to2)", o)
start = mem.member_from.to_numpy().astype("datetime64[ns]")
endm = m.end.to_numpy().astype("datetime64[ns]")
codes = pd.factorize(mem.entity_id)[0]
ds = sessions[sessions >= pd.Timestamp("2016-01-04")]
d = ds.to_numpy().astype("datetime64[ns]")
ents, rows_ = [], []
for x in d:
    on = (start <= x) & (endm > x)
    rows_.append(int(on.sum()))
    ents.append(len(np.unique(codes[on])))
cnt = pd.DataFrame({"date": ds, "rows": rows_, "entities": ents})
print("sessions counted:", len(cnt), day(cnt.date.min()), "to", day(cnt.date.max()))
print("distinct members per session: min", cnt.entities.min(), "on", day(cnt.date[cnt.entities.idxmin()]),
      "| max", cnt.entities.max(), "on", day(cnt.date[cnt.entities.idxmax()]))
print("membership rows per session: min", cnt.rows.min(), "| max", cnt.rows.max())
outside = cnt[(cnt.entities < 500) | (cnt.entities > 505)]
print("sessions with members outside 500..505:", len(outside))
print("sessions per member count:", {int(k): int(v) for k, v in cnt.entities.value_counts().sort_index().items()})
print("first 10 outside sessions:", [(day(a), int(b)) for a, b in zip(outside.date[:10], outside.entities[:10])])
print("outside sessions by year:", {int(k): int(v) for k, v in outside.date.dt.year.value_counts().sort_index().items()})
mbd = bars[bars.member & (bars.date >= pd.Timestamp("2016-01-04"))].groupby("date").entity_id.nunique()
mbd = mbd.reindex(cnt.date).fillna(0).astype(int).to_numpy()
print("member-flag bars, distinct entities per session: min", mbd.min(), "max", mbd.max(),
      "| sessions where that differs from the membership table:", int((mbd != cnt.entities.to_numpy()).sum()))

# ------------------------------------------------------------------ check 3
head("CHECK 3: identity spans")
print("columns:", list(ide.columns))
print("empty valid_from:", int((ide.valid_from == "").sum()), "| empty valid_to:", int((ide.valid_to == "").sum()),
      "| empty share_class:", int((ide.share_class == "").sum()))
print("share_class values:", ide.share_class.value_counts().to_dict())
ide = ide.copy()
ide["vf"] = pd.to_datetime(ide.valid_from)
ide["vt"] = pd.to_datetime(ide.valid_to.replace("", None))
ide["vte"] = ide.vt.fillna(FAR)  # valid_to is the last day, inclusive (identity.py:376)
bad3 = ide[ide.vt.notna() & (ide.vf > ide.vt)]
print("valid_from > valid_to:", len(bad3), "| valid_from == valid_to (one day):", int((ide.vt.notna() & (ide.vf == ide.vt)).sum()))
for r in bad3.head(20).itertuples():
    print("   ", r.entity_id, r.symbol, r.share_class, r.valid_from, r.valid_to)
print("duplicate rows on (entity, symbol, share_class, valid_from, valid_to):",
      int(ide.duplicated(["entity_id", "symbol", "share_class", "valid_from", "valid_to"]).sum()))


def pairs(df, keys):
    out = []
    for k, g in df.groupby(keys):
        r = list(g.sort_values("vf").itertuples())
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                if r[j].vf <= r[i].vte and r[i].vf <= r[j].vte:
                    out.append((k, r[i], r[j]))
    return out


o1 = pairs(ide, ["entity_id", "share_class"])
print("overlapping spans, same entity and share class (ends inclusive):", len(o1))
for k, a, b in o1[:20]:
    print("   ", k, "|", a.symbol, a.valid_from, a.valid_to, "|", b.symbol, b.valid_from, b.valid_to)
o2 = [p for p in pairs(ide, ["symbol"]) if p[1].entity_id != p[2].entity_id]
print("symbols held by two entities on the same day:", len(o2))
for k, a, b in o2[:20]:
    print("   ", k, "|", a.entity_id, a.valid_from, a.valid_to, "|", b.entity_id, b.valid_from, b.valid_to)
o3 = [p for p in pairs(ide, ["symbol"]) if p[1].entity_id == p[2].entity_id]
print("overlapping spans of one symbol within one entity:", len(o3))
print("entities with two or more share classes listed:",
      int(ide.groupby("entity_id").share_class.apply(lambda s: s[s != ""].nunique() > 1).sum()))

# ------------------------------------------------------------------ check 4
head("CHECK 4: joins")
mem_ents, ide_ents = set(mem.entity_id), set(ide.entity_id)
print("membership entities:", len(mem_ents), "| identity entities:", len(ide_ents),
      "| in membership, not identity:", len(mem_ents - ide_ents), "| in identity, not membership:", len(ide_ents - mem_ents))
print("   ids in membership but not identity (up to 20):", sorted(mem_ents - ide_ents)[:20])
spans = {e: (g.vf.to_numpy().astype("datetime64[D]"), g.vte.to_numpy().astype("datetime64[D]")) for e, g in ide.groupby("entity_id")}
sess_d = sessions.to_numpy().astype("datetime64[D]")
miss_cal = miss_sess = 0
hit_rows = []
for r in mem.itertuples():
    a = np.datetime64(r.member_from.date(), "D")
    b = np.datetime64((r.member_to if pd.notna(r.member_to) else DATA_END + pd.Timedelta(days=1)).date(), "D")
    cal = np.arange(a, b)
    s = sess_d[(sess_d >= a) & (sess_d < b)]
    vf, vt = spans.get(r.entity_id, (np.array([], dtype="datetime64[D]"),) * 2)
    cc = np.zeros(len(cal), dtype=bool)
    sc = np.zeros(len(s), dtype=bool)
    for f, t in zip(vf, vt):
        cc |= (cal >= f) & (cal <= t)
        sc |= (s >= f) & (s <= t)
    miss_cal += int((~cc).sum())
    miss_sess += int((~sc).sum())
    if (~sc).any() or (~cc).any():
        hit_rows.append((r.entity_id, str(a), str(b), int((~cc).sum()), int((~sc).sum())))
print("(4a) membership rows:", len(mem), "| calendar days (to data_end) with no covering identity row:", miss_cal,
      "| store sessions with none:", miss_sess, "| membership rows affected:", len(hit_rows))
for x in hit_rows[:20]:
    print("   (entity, from, to, calendar misses, session misses)", x)

bd = bars[bars.date <= DATA_END].groupby(["entity_id", "date"], as_index=False).member.max()
spans_m = {e: (g.member_from.to_numpy().astype("datetime64[ns]"), g.member_to.fillna(FAR).to_numpy().astype("datetime64[ns]"))
           for e, g in mem.groupby("entity_id")}
cov = np.zeros(len(bd), dtype=bool)
dates_ns = bd.date.to_numpy().astype("datetime64[ns]")
for e, idx in bd.groupby("entity_id").indices.items():
    if e in spans_m:
        f, t = spans_m[e]
        dd = dates_ns[idx]
        ok = np.zeros(len(idx), dtype=bool)
        for a, b in zip(f, t):
            ok |= (dd >= a) & (dd < b)
        cov[idx] = ok
bd["covered"] = cov
flag = bd.member.astype(bool)
print("(4b) bars entity-days:", len(bd), "| flagged member:", int(flag.sum()), "| covered by a membership row:", int(bd.covered.sum()))
a_ = bd[flag & ~bd.covered]
b_ = bd[~flag & bd.covered]
print("     member-flag entity-days with no membership row:", len(a_), "| entities:", a_.entity_id.nunique())
print("     bars entities not in membership at all:", bars.entity_id[~bars.entity_id.isin(mem_ents)].nunique())
print("     covered by membership but member flag false:", len(b_), "| entities:", b_.entity_id.nunique())
for e, x in list(zip(a_.entity_id, a_.date.dt.date))[:20]:
    print("     member bar, no membership row:", e, x)
for e, x in list(zip(b_.entity_id, b_.date.dt.date))[:20]:
    print("     covered by membership, flag false:", e, x)

# ------------------------------------------------------------------ check 5
head("CHECK 5: membership days with no bar or no open")
parts = []
for r in mem.itertuples():
    a = np.datetime64(r.member_from, "ns")
    b = np.datetime64(r.member_to if pd.notna(r.member_to) else DATA_END + pd.Timedelta(days=1), "ns")
    parts.append(pd.DataFrame({"entity_id": r.entity_id, "date": sess_ns[(sess_ns >= a) & (sess_ns < b)]}))
md = pd.concat(parts).drop_duplicates()
print("membership entity-days (store sessions to data_end):", len(md), "| first", day(md.date.min()))
nb_ = bars.groupby(["entity_id", "date"]).size().rename("nbars").reset_index()
nm_ = bars[bars.member].groupby(["entity_id", "date"]).size().rename("nmem").reset_index()
no_ = opens[opens.open.notna()].groupby(["entity_id", "date"]).size().rename("nop").reset_index()
na_ = opens.groupby(["entity_id", "date"]).size().rename("nany").reset_index()
x = md
for t in (nb_, nm_, no_, na_):
    x = x.merge(t, how="left", on=["entity_id", "date"])
nobar = x[x.nbars.isna()].sort_values(["entity_id", "date"])
nomem = x[x.nmem.isna()]
noop = x[x.nop.isna() & x.nbars.notna()].sort_values(["entity_id", "date"])
print("(5a) entity-days with no bar of any kind:", len(nobar), "| entities:", nobar.entity_id.nunique())
print("(5b) entity-days with no member-flag bar:", len(nomem))
print("(5c) entity-days with a bar but no official open:", len(noop), "| row missing in opens:", int(noop.nany.isna().sum()),
      "| row present with null open:", int(noop.nany.notna().sum()))
print("     entity-days with no open at all (bar or not):", int(x.nop.isna().sum()))
mbar = bars[bars.member][["entity_id", "share_class", "date"]]
oc = opens[opens.open.notna()][["entity_id", "share_class", "date"]].assign(_o=1)
mm = mbar.merge(oc, how="left", on=["entity_id", "share_class", "date"])
print("     class level: member bars", len(mbar), "| with no non-null open:", int(mm._o.isna().sum()),
      "| counts.json member_bars_with_official_open:", counts["member_bars_with_official_open"])
print("no bar, first 20 by (entity, date):")
for e, dte in list(zip(nobar.entity_id, nobar.date.dt.date))[:20]:
    print("   ", e, dte)
print("bar but no open, first 20 by (entity, date):")
for e, dte in list(zip(noop.entity_id, noop.date.dt.date))[:20]:
    print("   ", e, dte)
print("no-bar entity-days by year:", {int(k): int(v) for k, v in nobar.date.dt.year.value_counts().sort_index().items()})
print("no-open entity-days, top 8 dates:", noop.date.dt.date.astype(str).value_counts().head(8).to_dict())
print("no-open entity-days by year:", {int(k): int(v) for k, v in noop.date.dt.year.value_counts().sort_index().items()})
