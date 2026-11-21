"""Doc numbers about the store (m1_kickoff Session 2 to 4, README). Counts, dates and symbols only; returns as booleans."""
import json
import numpy as np, pandas as pd, pyarrow.parquet as pq

D = "D:/chrono-data/"
S = D + "store/"
bars = pd.read_parquet(S + "bars.parquet")
lab = pd.read_parquet(S + "labels.parquet")
opens = pd.read_parquet(S + "opens.parquet")
mem = pd.read_parquet(S + "membership.parquet")
ident = pd.read_parquet(S + "identity.parquet")
cj = json.load(open(S + "counts.json"))
print("bars", len(bars), "member", int(bars.member.sum()), "non-member", int((~bars.member).sum()))
print("bars date min/max", bars.date.min().date(), bars.date.max().date())
print("labels", len(lab), "at_close", int(lab.at_close.sum()), "label == -1:", int((lab.label == -1).sum()))
print("counts.json agrees: bars", cj["bars"] == len(bars), "labels", cj["labels"] == len(lab))
sym = ident.drop_duplicates("entity_id").set_index("entity_id").symbol
sym_all = ident.groupby("entity_id").symbol.apply(lambda s: sorted(set(s)))
m1 = lab[lab.label == -1]
for r in m1.itertuples():
    print("  -1 label:", sym_all.get(r.entity_id), "from", str(r.date.date()), "to", str(r.end.date()), "at_close", r.at_close)

# labels that start on a member day and end on a non-member day
key = ["entity_id", "share_class", "date"]
mb = bars[key + ["member"]]
x = lab.merge(mb.rename(columns={"member": "start_member"}), on=key, how="left")
x = x.merge(mb.rename(columns={"date": "end", "member": "end_member"}), on=["entity_id", "share_class", "end"], how="left")
sel = x[(x.start_member == True) & (x.end_member == False)]
print("labels start member / end non-member", len(sel), "of which at_close", int(sel.at_close.sum()))
print("labels start member / end non-member, end bar missing:", int(((x.start_member == True) & x.end_member.isna()).sum()))

# exits: stopped trading vs window cut, recomputed from the raw bar files
plan = pd.read_csv(D + "bars/plan.csv", dtype=str)
data_end = pd.Timestamp(cj["data_end"])
ac = lab[lab.at_close]
exits = ac[["entity_id", "share_class"]].drop_duplicates()
print("at_close labels", len(ac), "distinct company series", len(exits))
last_all = bars[bars.volume > 0].groupby(["entity_id", "share_class"]).date.max()
last_mem = bars[bars.member].groupby(["entity_id", "share_class"]).date.max()
last_sym = bars[bars.volume > 0].sort_values("date").groupby(["entity_id", "share_class"]).symbol.last()
def raw_last(ent, symbol):
    best = None
    for r in plan[(plan.entity_id == ent) & (plan.symbol == symbol)].itertuples():
        t = pq.read_table(D + f"bars/raw/{r.symbol.replace('/', '_')}__{r.asof}.parquet", columns=["t", "volume"]).to_pandas()
        t = t[t.volume > 0]
        if len(t):
            m = pd.to_datetime(t.t).dt.tz_localize(None).dt.normalize().max() if t.t.dtype.kind != "O" else pd.to_datetime(t.t.astype(str).str[:10]).max()
            best = m if best is None else max(best, m)
    return best
cut = 0; stopped = 0; unknown = 0
for e in exits.itertuples():
    k = (e.entity_id, e.share_class)
    L, LM = last_all.get(k), last_mem.get(k)
    rl = raw_last(e.entity_id, last_sym.get(k))
    if rl is None:
        unknown += 1
        continue
    if rl > L and L > LM:
        cut += 1
    else:
        stopped += 1
print("exit series: stopped", stopped, "window cut", cut, "unknown", unknown)
failed_series = {(r.entity_id, r.share_class) for r in m1.itertuples()}
print("failed exit labels", len(failed_series))

# companies that leave and rejoin (gaps between membership rows)
m = mem.sort_values(["entity_id", "member_from"])
rej = []
for e, g in m.groupby("entity_id"):
    if len(g) > 1:
        tos, froms = g.member_to.tolist(), g.member_from.tolist()
        for a, b in zip(tos[:-1], froms[1:]):
            if pd.notna(a) and b > a + pd.Timedelta(days=1):
                rej.append(e); break
print("companies with a gap between membership rows", len(rej), sorted(sum((sym_all.get(e, []) for e in rej), [])))
print("rejoin set contains EQT PCG FSLR KDP ILMN CHK:", {s: any(s in sym_all.get(e, []) for e in rej) for s in ["EQT", "PCG", "FSLR", "KDP", "ILMN", "CHK"]})

# non-member bars, data end
print("non-member bars", int((~bars.member).sum()))
print("membership rows", len(mem), "identity rows", len(ident))
