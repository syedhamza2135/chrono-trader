"""Print check (M0) against the auctions' official prints: how many opens and closes agree. Counts and symbols only."""
import pandas as pd
D = "D:/chrono-data/"
off = pd.read_parquet(D + "auctions/official.parquet")
pc = pd.read_csv(D + "audit/official_prints.csv")
sp = pd.read_csv(D + "audit/official_prints_input_v2.csv", dtype=str)[["symbol", "date", "spell_ticker"]].drop_duplicates(["symbol", "date"])
pc = pc.merge(sp, on=["symbol", "date"], how="left")
plan = pd.read_csv(D + "bars/plan.csv", dtype=str)
def served(sym, d):
    p = plan[(plan.symbol == sym) & (plan.use_from <= d) & (plan.use_to >= d)]
    return p["asof"].tolist()
res = {"open": [0, 0, []], "close": [0, 0, []]}
for r in pc.itertuples():
    for side, col, flag in (("open", "official_open", r.open_checked), ("close", "official_close", r.close_checked)):
        if str(flag) != "True":
            continue
        asofs = served(r.symbol, r.date) or (served(r.spell_ticker, r.date) if isinstance(r.spell_ticker, str) else [])
        sym = r.symbol if served(r.symbol, r.date) else r.spell_ticker
        if not asofs:
            res[side][2].append(f"{r.symbol} {r.date} not a plan stock-day")
            continue
        o = off[(off.symbol == sym) & (off.date == r.date) & (off["asof"].isin(asofs))]
        res[side][0] += 1
        if len(o) and (abs(o[side].iloc[0] - getattr(r, col)) < 1e-9):
            res[side][1] += 1
for side, (n, agree, notplan) in res.items():
    print(side, "plan stock-days judged", n, "agree", agree, "not served by a plan row:", notplan)
