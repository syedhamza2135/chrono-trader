"""Audit the downloaded daily bars and write research/audit/prices.md plus CSVs.

Everything is per company (the identity table's entity), on the days the download plan assigns to it. Returns
are stitched where a company changes rows (see `returns`).
Checks:
- survivorship: every member company has bars on each picking date
- coverage: member sessions with no bar (after a last trade, before a first trade, or inside)
- identity: no two companies share a price history on their member days
- zero-volume bars on member days (trading halts, and days after a last trade)
- large moves: adjusted one-day moves above 25% on member days, with the official-print check where it ran
  (DATA_DIR/audit/official_prints.csv, from research/verify_prints.py)
- adjustment events: member days whose adjusted and raw moves differ by more than 4% (splits, special dividends,
  spin-offs), joined to the hand-checked corrections in reference/price_events.csv
- trading days: bar dates against the NYSE calendar
It also previews the stock-picking rule (top 50 by median daily dollar volume over the previous year, one share
class per company). The real pick happens inside the agent loop; this preview only checks the data supports it.

Usage: python -m data_pipeline.audit_prices
"""
from collections import defaultdict
from datetime import date

import exchange_calendars as xcals
import pandas as pd

from .prices import load
from .settings import DATA_DIR, ROOT

OUT = ROOT / "research" / "audit"
REFERENCE = ROOT / "reference"
FIRST_YEAR, LAST_YEAR = 2016, 2026


def read_reference():
    entities = pd.read_csv(REFERENCE / "entities.csv", dtype=str)
    members = pd.read_csv(REFERENCE / "memberships.csv", dtype=str)
    members["member_from"] = pd.to_datetime(members.member_from)
    members["member_to"] = pd.to_datetime(members.member_to)
    events_path = REFERENCE / "price_events.csv"
    events = pd.read_csv(events_path, dtype=str) if events_path.exists() else pd.DataFrame(columns=["symbol", "date", "kind", "status"])
    return entities, members, events


def pick_dates(sessions):
    """The first trading day of each year; in 2016 the first trading day of April (prices start in 2016)."""
    out = {}
    for y in range(FIRST_YEAR, LAST_YEAR + 1):
        start = pd.Timestamp(y, 4, 1) if y == FIRST_YEAR else pd.Timestamp(y, 1, 1)
        later = sessions[sessions >= start]
        if len(later):
            out[y] = later[0]
    return out


def members_on(day, members):
    m = members
    return set(m[(m.member_from <= day) & (m.member_to.isna() | (m.member_to > day))].entity_id)


def survivorship(raw, members, picks):
    on_member = raw[raw.member]
    out = []
    for year, day in picks.items():
        ents = members_on(day, members)
        near = on_member[(on_member.date >= day) & (on_member.date <= day + pd.Timedelta(days=10))]
        missing = sorted(ents - set(near.entity_id))
        out.append({"year": year, "date": day.date(), "members": len(ents), "missing": len(missing), "entities": " ".join(missing)})
    return pd.DataFrame(out)


def shared_histories(raw):
    """Different companies with at least 20 identical (date, close, volume) member days."""
    m = raw[raw.member & (raw.volume > 0)]
    key = m.date.dt.strftime("%Y-%m-%d") + "|" + m.close.round(4).astype(str) + "|" + m.volume.astype(str)
    groups = m.assign(key=key).groupby("key").entity_id.unique()
    pairs = defaultdict(int)
    for ents in groups[groups.str.len() > 1]:
        ents = sorted(ents)
        for i in range(len(ents)):
            for j in range(i + 1, len(ents)):
                pairs[(ents[i], ents[j])] += 1
    return pd.DataFrame([{"entity_a": a, "entity_b": b, "identical_rows": n} for (a, b), n in pairs.items() if n >= 20],
                        columns=["entity_a", "entity_b", "identical_rows"])


def returns(raw, adj):
    """Daily returns of each plan row's file, stitched where a company changes rows.

    On a row's first member day the file's previous bar can be another security's, since Alpaca's histories
    follow a symbol (the UAA file's bar for 2016-12-06 is class C, and the new JCI file's bar for 2016-09-02 is the
    old Johnson Controls, not Tyco). Where the company and class were members the session before under another
    row, and the file has no bar that day or one with a different close or volume, the return is stitched from the
    previous row's close, raw and adjusted alike, and marked `stitched`. A stitched return assumes no corporate
    action that day, so each one needs a look (Tyco's shares were consolidated as it became JCI).
    `next_ret` is the company and class's next member-day return."""
    raw = raw.assign(ret=raw.groupby("row").close.pct_change())
    raw = raw.assign(file_prev=raw.groupby("row").close.shift(1), file_prev_vol=raw.groupby("row").volume.shift(1),
                     file_prev_date=raw.groupby("row").date.shift(1))
    m = raw[raw.member].sort_values(["entity_id", "share_class", "date"])
    g = m.groupby(["entity_id", "share_class"])
    prev_row, prev_close, prev_vol, prev_date = g.row.shift(1), g.close.shift(1), g.volume.shift(1), g.date.shift(1)
    boundary = prev_row.notna() & (prev_row != m.row) & ((m.date - prev_date).dt.days <= 5)  # no gap in membership
    same_bar = (m.file_prev_date == prev_date) & ((m.file_prev / prev_close - 1).abs() < 1e-6) & (m.file_prev_vol == prev_vol)
    elsewhere = m.file_prev_date > prev_date  # a session between the two rows that is neither's: keep the file's own return
    broken = boundary & ~same_bar & ~elsewhere
    fix = m.loc[broken, ["row", "date"]].assign(stitched_ret=(m.close / prev_close - 1)[broken])

    def stitch(df):
        df = df.drop(columns=["file_prev"], errors="ignore").assign(ret=df.groupby("row").close.pct_change())
        df = df.merge(fix, on=["row", "date"], how="left")
        df["stitched"] = df.stitched_ret.notna()
        df["ret"] = df.stitched_ret.where(df.stitched, df.ret)
        mm = df[df.member].sort_values(["entity_id", "share_class", "date"])
        df["next_ret"] = mm.groupby(["entity_id", "share_class"]).ret.shift(-1)
        return df.drop(columns="stitched_ret")

    return stitch(raw), stitch(adj), int(boundary.sum()), int(broken.sum())


def coverage(raw, sessions):
    """Member sessions without a bar, per plan row: before the row's first traded bar, after its last, or inside."""
    out = []
    for row, g in raw.groupby("row"):
        r = g.iloc[0]
        want = sessions[(sessions >= pd.Timestamp(r.use_from)) & (sessions <= pd.Timestamp(r.use_to))]
        have = g.date[g.member]
        missing = want[~want.isin(have)]
        if len(missing):
            first, last = (have.min(), have.max()) if len(have) else (pd.NaT, pd.NaT)
            where = ["before" if d < first else "after" if d > last else "inside" for d in missing] if len(have) else ["no bars"] * len(missing)
            out += [{"entity_id": r.entity_id, "symbol": r.symbol, "date": d.date(), "where": w} for d, w in zip(missing, where)]
    return pd.DataFrame(out, columns=["entity_id", "symbol", "date", "where"])


def correction(r):
    """A price_events row in a few words: what the corrected day should use."""
    if r.action == "total_return":
        return f"{r.kind}: total return {float(r.total_return):+.1%}"
    if r.action in ("override_open", "override_close", "override_bar"):
        return f"{r.action} " + " ".join(f"{c} {getattr(r, c)}" for c in ("open", "close") if isinstance(getattr(r, c), str) and getattr(r, c))
    return f"{r.kind}: {r.action}"


def large_moves(adj, prints, events):
    big = adj[adj.member & (adj.ret.abs() > 0.25)].copy()
    big["reverses_next_day"] = (big.ret * big.next_ret < 0) & (big.next_ret.abs() > 0.2)
    big["d"] = big.date.dt.strftime("%Y-%m-%d")
    if len(prints):
        big = big.merge(prints[["symbol", "date", "verdict"]].rename(columns={"date": "d"}), on=["symbol", "d"], how="left")
    else:
        big["verdict"] = ""
    fixes = events.assign(correction=[correction(r) for r in events.itertuples()]).groupby(["symbol", "date"]).correction.agg("; ".join)
    big = big.merge(fixes.rename_axis(["symbol", "d"]).reset_index(), on=["symbol", "d"], how="left")
    return big[["entity_id", "symbol", "d", "ret", "next_ret", "reverses_next_day", "stitched", "verdict", "correction"]].rename(
        columns={"d": "date"}).sort_values("date")


def adjustment_events(raw, adj, events):
    a = adj.set_index(["row", "date"])["ret"].rename("r_adj")
    x = raw.join(a, on=["row", "date"])
    x["diff"] = (1 + x.r_adj) / (1 + x.ret) - 1
    ev = x[x.member & x.ret.notna() & (x["diff"].abs() > 0.04)].copy()
    ev["date"] = ev.date.dt.strftime("%Y-%m-%d")
    ev = ev.merge(events[["symbol", "date", "kind", "status"]], on=["symbol", "date"], how="left")
    return ev[["entity_id", "symbol", "date", "ret", "r_adj", "diff", "kind", "status"]].rename(  # returns only, no prices
        columns={"ret": "r_raw"}).sort_values("date")


def universe_preview(raw, members, picks, names):
    raw = raw.assign(dollar_volume=raw.close * raw.volume)
    rows = []
    for year, day in picks.items():
        lo = pd.Timestamp(year, 1, 1) if year == FIRST_YEAR else day - pd.DateOffset(years=1)
        ents = members_on(day, members)
        live = raw[raw.entity_id.isin(ents) & (pd.to_datetime(raw.use_from) <= day) & (pd.to_datetime(raw.use_to) >= day)]
        window = live[(live.date >= lo) & (live.date < day)]
        per_row = window.groupby(["entity_id", "symbol", "row"]).dollar_volume.median().reset_index()
        best = per_row.sort_values("dollar_volume", ascending=False).drop_duplicates("entity_id")  # one class per company
        for rank, r in enumerate(best.head(50).itertuples(), 1):
            rows.append({"year": year, "rank": rank, "entity_id": r.entity_id, "symbol": r.symbol, "name": names.get(r.entity_id, ""),
                         "median_dollar_volume_musd": round(r.dollar_volume / 1e6, 1)})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    entities, members, events = read_reference()
    names = dict(zip(entities.entity_id, entities.name))
    raw, adj, boundaries, stitched = returns(load("raw"), load("all"))
    cal = xcals.get_calendar("XNYS")
    aapl = raw[(raw.symbol == "AAPL") & raw.member]
    data_end = aapl.date.max()  # files reused from an earlier download stop here; later sessions aren't checked
    sessions = cal.sessions_in_range(raw.date.min(), data_end)
    picks = pick_dates(sessions)
    prints_path = DATA_DIR / "audit" / "official_prints.csv"  # raw prices, so kept out of git
    prints = pd.read_csv(prints_path, dtype={"date": str}) if prints_path.exists() else pd.DataFrame()

    surv = survivorship(raw, members, picks)
    shared = shared_histories(raw)
    zero = raw[raw.member & (raw.volume == 0)][["entity_id", "symbol", "date"]]
    moves = large_moves(adj, prints, events)
    adj_events = adjustment_events(raw, adj, events)
    missing_days = sorted(set(sessions.date) - set(aapl.date.dt.date))
    extra_days = sorted(set(aapl.date.dt.date) - set(sessions.date))
    gaps = coverage(raw, sessions)
    uni = universe_preview(raw, members, picks, names)

    surv.to_csv(OUT / "survivorship.csv", index=False)
    gaps.to_csv(OUT / "member_days_without_bars.csv", index=False)
    shared.to_csv(OUT / "identity_shared_data.csv", index=False)
    zero.to_csv(OUT / "zero_volume.csv", index=False)
    moves.to_csv(OUT / "large_moves.csv", index=False)
    adj_events.to_csv(OUT / "adjustment_events.csv", index=False)
    uni.to_csv(OUT / "universe_preview.csv", index=False)

    member_days = int(raw.member.sum())
    churn = uni.groupby("year").entity_id.apply(set)
    years = sorted(churn.index)
    verdicts = moves.verdict.fillna("")
    failed = verdicts.str.startswith(("MISMATCH", "CONFLICT"))
    flagged_events = adj_events[adj_events.status.isin(["wrong", "missing", "stitched"])]
    lines = [
        "# Price audit",
        "",
        f"Generated by `python -m data_pipeline.audit_prices` on {date.today()}. Source: Alpaca daily bars (SIP), raw and "
        f"fully adjusted, fetched per company and ticker by `python -m data_pipeline.bars` from the identity table: "
        f"{raw.row.nunique()} plan rows for {raw.entity_id.nunique()} companies, {member_days:,} company member days. "
        f"Checks run to {data_end.date()}, the last bar of the files reused from the first download.",
        "",
        f"A company changes rows {boundaries} times while a member (a new ticker, or a new listing). At {stitched} of "
        "them the new file has no bar for the previous session, or another security's (Alpaca's histories follow a "
        "symbol), so that day's return is stitched from the previous row's close. A stitched return assumes no "
        "corporate action that day; `reference/price_events.csv` corrects the ones that had one.",
        "",
        "## Survivorship: member companies without bars on each picking date",
        "",
        "| Year | Date | Members | Missing | Companies |",
        "|---|---|---|---|---|",
        *[f"| {r.year} | {r.date} | {r.members} | {r.missing} | {' '.join(names.get(e, e) for e in r.entities.split()) if r.entities else '-'} |"
          for r in surv.itertuples()],
        "",
        "## Member days without a bar",
        "",
        f"Member sessions with no bar: {len(gaps)} in {gaps.groupby(['entity_id', 'symbol']).ngroups if len(gaps) else 0} rows. "
        f"After a company's last trade: {int((gaps['where'] == 'after').sum())} (an acquisition closes a few days before "
        f"the index removal takes effect). Before its first trade: {int((gaps['where'] == 'before').sum())}. Inside its "
        f"trading: {int((gaps['where'] == 'inside').sum())}. Rows with no bars at all: {int((gaps['where'] == 'no bars').sum())}. "
        "Full list in `member_days_without_bars.csv`.",
        *[f"- {names.get(e, e)} ({s}): {len(g)} sessions, {g.date.min()} to {g.date.max()}, {g['where'].iloc[0]}"
          for (e, s), g in gaps.groupby(["entity_id", "symbol"]) if (g["where"] != "after").any()],
        "",
        "## Identity",
        "",
        f"Pairs of different companies sharing at least 20 identical member-day bars: {len(shared)}.",
        *[f"- {names.get(r.entity_a, r.entity_a)} and {names.get(r.entity_b, r.entity_b)}: {r.identical_rows} rows" for r in shared.itertuples()],
        "",
        "## Zero-volume bars on member days",
        "",
        f"{len(zero)} bars. Alpaca fills a day with no trades with the previous close; the simulator must not trade on them.",
        *[f"- {r.symbol} {r.date.date()}" for r in zero.itertuples()],
        "",
        "## Large moves",
        "",
        f"Adjusted one-day moves above 25% on member days: {len(moves)} ({int(moves.stitched.sum())} stitched across a change "
        f"of row); reversed by more than 20% the next day: "
        f"{int(moves.reverses_next_day.sum())}. Checked against the official auction prints: {int((verdicts != '').sum())} "
        f"({int(failed.sum())} failed). Corrected in `reference/price_events.csv`: {int(moves.correction.notna().sum())}. "
        "Full list in `large_moves.csv`. The table shows the moves that reverse, fail the print check, or have a correction.",
        "",
        "| Company | Ticker | Date | Move | Next day | Official prints | Correction |",
        "|---|---|---|---|---|---|---|",
        *[f"| {names.get(r.entity_id, r.entity_id)} | {r.symbol} | {r.date} | {r.ret:+.1%} | {r.next_ret:+.1%} | "
          f"{r.verdict if isinstance(r.verdict, str) and r.verdict else '-'} | {r.correction if isinstance(r.correction, str) else '-'} |"
          for r in moves[moves.reverses_next_day | failed | moves.correction.notna()].itertuples()],
        "",
        "## Adjustment events",
        "",
        f"Member days whose adjusted and raw moves differ by more than 4%: {len(adj_events)} (splits, special dividends, "
        f"spin-offs). Marked wrong or missing in `reference/price_events.csv`: {len(flagged_events)}. Full list in `adjustment_events.csv`.",
        "",
        "| Company | Ticker | Date | Raw move | Adjusted move | Status |",
        "|---|---|---|---|---|---|",
        *[f"| {names.get(r.entity_id, r.entity_id)} | {r.symbol} | {r.date} | {r.r_raw:+.1%} | {r.r_adj:+.1%} | {r.kind}: {r.status} |"
          for r in flagged_events.itertuples()],
        "",
        f"## Trading days (Apple's member bars against the NYSE calendar, to {data_end.date()})",
        "",
        f"NYSE sessions without an Apple bar: {len(missing_days)} {[str(d) for d in missing_days[:10]]}",
        f"Apple bars on non-sessions: {len(extra_days)} {[str(d) for d in extra_days[:10]]}",
        "",
        "## Stock-picking preview (top 50 companies by median daily dollar volume over the previous year)",
        "",
        "| Year | Picking date | Changed from previous year | Top 5 |",
        "|---|---|---|---|",
        *[f"| {y} | {picks[y].date()} | {'-' if i == 0 else len(churn[y] - churn[years[i - 1]])} | "
          f"{', '.join(uni[uni.year == y].sort_values('rank').symbol.head(5))} |" for i, y in enumerate(years)],
        "",
        "Full lists in `universe_preview.csv`.",
    ]
    (OUT / "prices.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:30]))


if __name__ == "__main__":
    main()
