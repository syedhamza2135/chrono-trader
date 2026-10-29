"""Audit the downloaded daily bars and write research/audit/prices.md plus CSVs.

Checks:
- survivorship: every member on each January (April in 2016) has bars around that date
- identity: the same company under several tickers, and different companies under one ticker
- large moves: adjusted one-day moves above 25% while a member, and moves that reverse next day
- trading days: bar dates against the NYSE calendar
It also previews the stock-picking rule (top 50 by median daily dollar volume over the previous
year). The real pick happens inside the agent loop; this preview only checks the data supports it.

Usage: python -m data_pipeline.audit_prices
"""
from collections import defaultdict
from datetime import date

import exchange_calendars as xcals
import pandas as pd
import pyarrow.parquet as pq

from .bars import last_complete_day
from .membership import load_snapshots, members_on, spells
from .settings import DATA_DIR, ROOT

BARS = DATA_DIR / "bars"
OUT = ROOT / "research" / "audit"
FIRST_YEAR, LAST_YEAR = 2016, 2026


def load(adjustment):
    frames = []
    for path in sorted((BARS / adjustment).glob("*.parquet")):
        df = pq.read_table(path, columns=["ticker", "asof", "t", "open", "close", "volume"]).to_pandas()
        if not df.empty:
            frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["t"].str[:10])
    df["spell"] = df["ticker"] + "__" + df["asof"]
    return df.drop(columns="t").sort_values(["spell", "date"]).reset_index(drop=True)


def spell_table(snapshots):
    rows = []
    today = last_complete_day()  # the same date bars.py used to name current members' files
    for ticker, runs in spells(snapshots, since=date(FIRST_YEAR, 1, 1)).items():
        for start, end in runs:
            last = (end - pd.Timedelta(days=1)) if end else today
            rows.append({"ticker": ticker, "start": pd.Timestamp(start), "end": pd.Timestamp(end) if end else pd.NaT,
                         "spell": f"{ticker}__{max(last, start).isoformat()}"})
    return pd.DataFrame(rows)


def pick_dates():
    return {y: pd.Timestamp(y, 4, 1) if y == FIRST_YEAR else pd.Timestamp(y, 1, 1) for y in range(FIRST_YEAR, LAST_YEAR + 1)}


def survivorship(raw, snapshots, table):
    by_spell = raw.groupby("spell")["date"].agg(["min", "max", "count"])
    out = []
    for year, day in pick_dates().items():
        members = members_on(day.date(), snapshots)
        missing = []
        for t in sorted(members):
            cand = table[(table.ticker == t) & (table.start <= day) & ((table.end.isna()) | (table.end > day))]
            sp = cand.spell.iloc[0] if len(cand) else None
            ok = sp in by_spell.index and by_spell.loc[sp, "min"] <= day + pd.Timedelta(days=10) and by_spell.loc[sp, "max"] >= day
            if not ok:
                missing.append(t)
        out.append({"year": year, "date": day.date(), "members": len(members), "missing": len(missing), "tickers": " ".join(missing)})
    return pd.DataFrame(out)


def identity(raw, table):
    # Rows shared exactly (date, close, volume) between spells reveal the same company under two tickers.
    key = raw["date"].dt.strftime("%Y-%m-%d") + "|" + raw["close"].round(4).astype(str) + "|" + raw["volume"].astype(str)
    groups = raw.assign(key=key).groupby("key")["spell"].unique()
    pair_counts = defaultdict(int)
    for spells_ in groups[groups.str.len() > 1]:
        s = sorted(spells_)
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                pair_counts[(s[i], s[j])] += 1
    shared = pd.DataFrame([{"spell_a": a, "spell_b": b, "identical_rows": n} for (a, b), n in pair_counts.items() if n >= 20])
    if not shared.empty:
        shared["ticker_a"] = shared.spell_a.str.split("__").str[0]
        shared["ticker_b"] = shared.spell_b.str.split("__").str[0]
        shared["kind"] = shared.apply(lambda r: "same ticker, same data (re-entered index)" if r.ticker_a == r.ticker_b
                                      else "same company, different tickers", axis=1)
    # One ticker with several spells whose data differ: a reused ticker (different companies).
    reused = []
    for ticker, grp in table.groupby("ticker"):
        if len(grp) < 2:
            continue
        sp = list(grp.spell)
        same = (not shared.empty) and any(((shared.spell_a == a) & (shared.spell_b == b)).any() or
                                          ((shared.spell_a == b) & (shared.spell_b == a)).any()
                                          for a in sp for b in sp if a < b)
        firsts = [raw.loc[raw.spell == s, "date"].min() for s in sp]
        reused.append({"ticker": ticker, "spells": " ".join(sp), "first_bar_each": " ".join(str(f.date()) if pd.notna(f) else "-" for f in firsts),
                       "verdict": "same company" if same else "different data: check if the ticker was reused"})
    return shared, pd.DataFrame(reused)


def large_moves(adj, table):
    adj = adj.copy()
    adj["ret"] = adj.groupby("spell")["close"].pct_change()
    adj["next_ret"] = adj.groupby("spell")["ret"].shift(-1)
    spans = table.set_index("spell")[["start", "end"]]
    adj = adj.join(spans, on="spell")
    member = (adj.date >= adj.start) & (adj.end.isna() | (adj.date < adj.end))
    big = adj[member & (adj.ret.abs() > 0.25)].copy()
    big["reverses_next_day"] = (big.ret * big.next_ret < 0) & (big.next_ret.abs() > 0.2)
    return big[["ticker", "date", "ret", "next_ret", "reverses_next_day"]].sort_values("date")


def trading_days(raw):
    cal = xcals.get_calendar("XNYS")
    sessions = cal.sessions_in_range(raw.date.min(), raw.date.max())
    bar_days = pd.DatetimeIndex(sorted(raw.loc[raw.ticker == "AAPL", "date"].unique()))
    return sorted(set(sessions.date) - set(bar_days.date)), sorted(set(bar_days.date) - set(sessions.date))


def universe_preview(raw, snapshots, table):
    raw = raw.assign(dollar_volume=raw.close * raw.volume)
    rows = []
    for year, day in pick_dates().items():
        lo = pd.Timestamp(year, 1, 1) if year == FIRST_YEAR else pd.Timestamp(year - 1, 1, 1)
        members = members_on(day.date(), snapshots)
        live = table[(table.start <= day) & (table.end.isna() | (table.end > day)) & table.ticker.isin(members)]
        window = raw[(raw.date >= lo) & (raw.date < day) & raw.spell.isin(live.spell)]
        med = window.groupby("ticker")["dollar_volume"].median().sort_values(ascending=False)
        for rank, (ticker, dv) in enumerate(med.head(50).items(), 1):
            end = live.loc[live.ticker == ticker, "end"].iloc[0]
            rows.append({"year": year, "rank": rank, "ticker": ticker, "median_dollar_volume_musd": round(dv / 1e6, 1),
                         "left_index": "" if pd.isna(end) else str(end.date())})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    snapshots = load_snapshots()
    table = spell_table(snapshots)
    raw, adj = load("raw"), load("all")
    surv = survivorship(raw, snapshots, table)
    shared, reused = identity(raw, table)
    moves = large_moves(adj, table)
    missing_days, extra_days = trading_days(raw)
    uni = universe_preview(raw, snapshots, table)

    surv.to_csv(OUT / "survivorship.csv", index=False)
    shared.to_csv(OUT / "identity_shared_data.csv", index=False)
    reused.to_csv(OUT / "identity_multi_spell.csv", index=False)
    moves.to_csv(OUT / "large_moves.csv", index=False)
    uni.to_csv(OUT / "universe_preview.csv", index=False)

    churn = uni.groupby("year")["ticker"].apply(set)
    years = sorted(churn.index)
    lines = [
        "# Price audit",
        "",
        f"Generated by `python -m data_pipeline.audit_prices` on {date.today()}. Source: Alpaca daily bars (SIP), raw and fully adjusted,",
        f"for {table.ticker.nunique()} tickers across {len(table)} S&P 500 membership spells since {FIRST_YEAR}.",
        f"{raw.spell.nunique()} spells returned bars; {len(table) - raw.spell.nunique()} returned none.",
        "",
        "## Survivorship: members without bars on each picking date",
        "",
        "| Year | Date | Members | Missing | Tickers |",
        "|---|---|---|---|---|",
        *[f"| {r.year} | {r.date} | {r.members} | {r.missing} | {r.tickers} |" for r in surv.itertuples()],
        "",
        "## Identity",
        "",
        f"Spell pairs sharing at least 20 identical rows (same company): {len(shared)}. See `identity_shared_data.csv`.",
        "",
        "| Ticker A | Ticker B | Identical rows | Kind |",
        "|---|---|---|---|",
        *([f"| {r.ticker_a} | {r.ticker_b} | {r.identical_rows} | {r.kind} |" for r in shared.sort_values('identical_rows', ascending=False).itertuples()] if not shared.empty else []),
        "",
        "Tickers with more than one membership spell:",
        "",
        "| Ticker | First bar of each spell | Verdict |",
        "|---|---|---|",
        *[f"| {r.ticker} | {r.first_bar_each} | {r.verdict} |" for r in reused.itertuples()],
        "",
        "## Large moves",
        "",
        f"Adjusted one-day moves above 25% while a member: {len(moves)}; of those, reversed by more than 20% the next day: {int(moves.reverses_next_day.sum())}.",
        "Reversals are the likeliest data errors. Full list in `large_moves.csv`.",
        "",
        "| Ticker | Date | Move | Next day |",
        "|---|---|---|---|",
        *[f"| {r.ticker} | {r.date.date()} | {r.ret:+.1%} | {r.next_ret:+.1%} |" for r in moves[moves.reverses_next_day].itertuples()],
        "",
        "## Trading days (AAPL bars against the NYSE calendar)",
        "",
        f"NYSE sessions without an AAPL bar: {len(missing_days)} {[str(d) for d in missing_days[:10]]}",
        f"AAPL bars on non-sessions: {len(extra_days)} {[str(d) for d in extra_days[:10]]}",
        "",
        "## Stock-picking preview (top 50 by median daily dollar volume, previous year)",
        "",
        "| Year | Changed from previous year | Later left the index | Top 5 |",
        "|---|---|---|---|",
        *[f"| {y} | {'-' if i == 0 else len(churn[y] - churn[years[i - 1]])} | {int((uni[uni.year == y].left_index != '').sum())} | "
          f"{', '.join(uni[uni.year == y].sort_values('rank').ticker.head(5))} |" for i, y in enumerate(years)],
        "",
        "Full lists in `universe_preview.csv`.",
    ]
    (OUT / "prices.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
