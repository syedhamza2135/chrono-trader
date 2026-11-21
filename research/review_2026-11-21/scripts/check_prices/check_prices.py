"""Checks 1-6 on reference/price_events.csv. Prints counts, row numbers (CSV data rows, 1 = first data row; file line = n+1), symbols, dates, kinds. Never prints prices."""
import re, sys, json
import pandas as pd
ROOT = r"C:\Users\syedh\dev\chrono-trader\.claude\worktrees\full-review-1121-0eb11c"
ev = pd.read_csv(ROOT + r"\reference\price_events.csv", dtype=str, keep_default_na=False)
ev.index = ev.index + 1  # row number among data rows
print("columns:", list(ev.columns))
print("== 1 counts ==")
print("rows:", len(ev))
print(ev.groupby(["kind", "action"]).size().to_string())
print("by kind:", ev.kind.value_counts().to_dict())
print("by action:", ev.action.value_counts().to_dict())
print("by status:", ev.status.value_counts().to_dict())
print("== 2 blanks ==")
for c in ["symbol", "date", "kind", "action", "evidence"]:
    print(c, "blank rows:", list(ev.index[ev[c].str.strip() == ""]))
need = {"override_bar": ["open", "high", "low", "close", "volume", "vwap"], "override_close": ["close"],
        "override_open": ["open"], "total_return": ["total_return"]}
for a, cols in need.items():
    for c in cols:
        r = list(ev.index[(ev.action == a) & (ev[c].str.strip() == "")])
        print(f"action {a} missing {c}:", r)
print("unparseable numeric:", [ (i,c) for i,r in ev.iterrows() for c in ["open","high","low","close","volume","vwap","total_return"] if r[c] and not re.fullmatch(r"-?\d+(\.\d+)?([eE]-?\d+)?", r[c])])
print("== 3 dates ==")
d = pd.to_datetime(ev.date, errors="coerce", format="%Y-%m-%d")
print("unparseable dates:", list(ev.index[d.isna()]))
print("min/max date:", d.min().date(), d.max().date())
print("weekend rows:", list(ev.index[d.dt.dayofweek >= 5]))
bars = pd.read_parquet(r"D:\chrono-data\store\bars.parquet", columns=["symbol", "date", "member", "volume"])
ops = pd.read_parquet(r"D:\chrono-data\store\opens.parquet", columns=["entity_id", "date"])
cnt = json.load(open(r"D:\chrono-data\store\counts.json"))
print("store data_end:", cnt["data_end"], "bars min date:", bars.date.min().date())
inb = set(zip(bars.symbol, bars.date.dt.strftime("%Y-%m-%d")))
tr = set(zip(bars.symbol[bars.volume > 0], bars.date[bars.volume > 0].dt.strftime("%Y-%m-%d")))
bad_range = list(ev.index[(d < "2016-01-01") | (d > cnt["data_end"])])
print("outside 2016-01-01..data_end:", bad_range)
nb = [(i, r.symbol, r.date, r.kind) for i, r in ev.iterrows() if (r.symbol, r.date) not in inb]
print("no bar for symbol/date in store bars:", len(nb))
for x in nb: print("  ", x)
nz = [(i, r.symbol, r.date, r.kind) for i, r in ev.iterrows() if (r.symbol, r.date) in inb and (r.symbol, r.date) not in tr]
print("bar exists but zero volume:", len(nz))
for x in nz: print("  ", x)
alld = set(bars.date.dt.strftime("%Y-%m-%d"))
print("dates not a trading day for any symbol:", [i for i, r in ev.iterrows() if r.date not in alld])
print("== 4 duplicates ==")
dup = ev[ev.duplicated(["symbol", "date", "kind"], keep=False)]
print("dup (symbol,date,kind):", [(i, r.symbol, r.date, r.kind) for i, r in dup.iterrows()])
dup2 = ev[ev.duplicated(["symbol", "date", "action"], keep=False)]
print("dup (symbol,date,action):", [(i, r.symbol, r.date, r.action) for i, r in dup2.iterrows()])
print("== 5 used by store.py ==")
read_actions = {"override_bar", "override_close", "total_return", "no_trade", "override_open", "stopped_trading"}
read_kinds = {"failure"}
print("actions in file not read by store.py:", sorted(set(ev.action) - read_actions))
print("rows with unread action:", list(ev.index[~ev.action.isin(read_actions)]))
print("action counts:", ev.action.value_counts().to_dict())
print("failure kind rows:", [(i, r.symbol, r.date, r.action) for i, r in ev[ev.kind == "failure"].iterrows()])
print("kinds only informational (action read, kind not read):", sorted(set(ev.kind) - read_kinds))
print("== 6 evidence quotes ==")
# a headline quote is text in single quotes that opens after ': ' or '(' and closes before a space or punctuation (apostrophes inside words do not close it), or in double quotes
pat = re.compile(r"""(?:(?<=[:(,] )|(?<=^))'(.+?)'(?=[\s.;,)]|$)|"([^"]+)\"""")
rows_q = {}
nq = 0
for i, r in ev.iterrows():
    ws = [len((a or b).split()) for a, b in pat.findall(r.evidence)]
    nq += len(ws)
    if ws: rows_q[i] = ws
print("rows with at least one quote:", len(rows_q), "quotes:", nq)
print("longest quote words:", max(max(v) for v in rows_q.values()))
over = {i: max(v) for i, v in rows_q.items() if max(v) > 15}
print("rows with a quote over 15 words:", len(over), "row numbers (max words):", over)
print("word-length histogram of quotes:", pd.Series([w for v in rows_q.values() for w in v]).value_counts().sort_index().to_dict())
print("rows with evidence over 100 words (whole note, not a quote):", list(ev.index[ev.evidence.str.split().str.len() > 100]))
