"""The event store (PLAN 9.4): Parquet tables in DATA_DIR/store, built from M0's outputs and the official opens.

Raw data, so the store stays on D: and out of git. The tables keep the raw times (dates, created_at, updated_at) and
world/ applies the availability rules, so the rules live in one place (world/rules.py).

- bars: one row per company, share class and session. A member day's bar comes from the plan row that serves it.
  Other days come from the company's own files: no bar that is another security's member bar
  (audit_prices.foreign), no zero-volume fill, only up to BEFORE days before a row and AFTER days after it, and the
  nearest row in time where two rows' files hold the day.
  `ret` is the close-to-close total return of Alpaca's adjusted bars, stitched where a company changes rows and left
  undefined where the previous bar isn't the company's own (audit_prices.returns). A non-member day's return stands
  only where the day before is the same file's previous bar. Then reference/price_events.csv corrects it: an
  overridden close or bar moves the returns into and out of that day, and a distribution's true total return
  replaces the vendor's on its ex-date. Halts are marked `no_trade`.
- opens: the listing exchange's official opening and closing auction prints (data_pipeline/auctions.py) for each
  company, class and session that has one. The simulator trades a stock-day only at its official open.
- labels: for each company, class and session with an official open, the total return from that open to the next
  official open of the same listing (and `end_open_time`, when that open printed, for the availability rule): (close / open) on the first day, the corrected close-to-close returns between,
  and (open / close) on the end day. The closes cancel, so a wrong close can't move a label. Where no official open
  follows and the company stopped trading before the data ends (an acquisition or a failure), the label ends at its
  last traded close (`at_close`), which is PLAN's exit at the last available price. Where none follows because the
  data ends, there is no label.
- stories: Benzinga's stories, not edited more than 3 days after publishing (world.rules.MAX_EDIT_LAG).
- story_entities: (story, company) pairs of the stories the single-firm filter keeps: 1 or 2 companies, each tag
  mapped by the story's New York date (audit_news.companies).
- membership: reference/memberships.csv. identity: reference/identity.csv with each company's CIKs.

research/audit/store.md gets the counts (no prices).

Usage: python -m data_pipeline.store
"""
import gc
import json

import numpy as np
import pandas as pd

from world import rules
from world.rules import keep_story
from .audit_news import BENZINGA, companies, load as load_news
from .audit_prices import foreign, returns
from .auctions import OFFICIAL
from .prices import load as load_bars
from .settings import DATA_DIR, ROOT

STORE = DATA_DIR / "store"
REFERENCE = ROOT / "reference"
REPORT = ROOT / "research" / "audit" / "store.md"
KEY = ["entity_id", "share_class", "date"]
# A file's bars far from its plan row can be another security's: IHS Markit's INFO file holds a thin NYSE Arca
# security in 2025. So non-member days are kept only where they're needed: the stock picker's year of trading before
# a company joins, with the 60 days of features (BEFORE), and the days to sell a removed stock at its next official
# open (AFTER). Calendar days, from world/rules.py, which also decides when views show them.
BEFORE, AFTER = rules.HISTORY_BEFORE.days, rules.HISTORY_AFTER.days
BAR_COLUMNS = ["entity_id", "share_class", "symbol", "date", "open", "high", "low", "close", "volume", "trades", "vwap",
               "ret", "incomplete", "member", "no_trade"]


def file_rows():
    """Every plan row's bars (prices.load), raw prices with the adjusted total return `ret`, and `foreign`."""
    raw, adj, *_ = returns(load_bars("raw"), load_bars("all"))
    df = raw.drop(columns=["ret", "next_ret"]).merge(
        adj[["row", "date", "ret", "stitched"]].rename(columns={"stitched": "stitched_adj"}), on=["row", "date"],
        how="left")
    df["foreign"] = foreign(df)
    return df


def company_series(df):
    """One bar per company, class and date: the member bar where there is one, else the company's own bar from the
    nearest row in time, within BEFORE days before a row or AFTER days after it. A non-member day's return stands
    only where the series' previous bar is the same file's previous bar."""
    member = df[df.member]
    other = df[~df.member & ~df["foreign"] & (df.volume > 0)]
    other = other[~pd.MultiIndex.from_frame(other[KEY]).isin(pd.MultiIndex.from_frame(member[KEY]))]
    use_from, use_to = pd.to_datetime(other.use_from), pd.to_datetime(other.use_to)
    before = other.date < use_from
    dist = np.where(before, (use_from - other.date).dt.days, (other.date - use_to).dt.days)
    keep = ((before & (dist <= BEFORE)) | (~before & (dist <= AFTER))).to_numpy()
    other = other[keep].assign(dist=dist[keep])
    other = other.sort_values(KEY + ["dist", "use_from"], ascending=[True, True, True, True, False])
    other = other.drop_duplicates(KEY).drop(columns="dist")
    s = pd.concat([member, other], ignore_index=True).sort_values(KEY, ignore_index=True)
    s["date"] = s.date.astype("datetime64[ns]")
    s["file_prev_date"] = s.file_prev_date.astype("datetime64[ns]")
    g = s.groupby(["entity_id", "share_class"], sort=False)
    same_file = (g.row.shift(1) == s.row) & (g.date.shift(1) == s.file_prev_date)
    s.loc[~s.member & ~same_file, "ret"] = np.nan
    return s


def apply_events(s, events):
    """Apply reference/price_events.csv to the company series; return the series and what was applied."""
    s = s.copy()
    s["no_trade"] = False
    applied = []
    # Every bar the series keeps, member day or not: a member day's label can end on the first day after a removal
    # (EQT spun off Equitrans the day it left the index). Member bars win a clash.
    days = s.date.dt.strftime("%Y-%m-%d")
    pos = {(sym, d): i for i, (sym, d, m) in enumerate(zip(s.symbol, days, s.member)) if not m}
    pos.update({(sym, d): i for i, (sym, d, m) in enumerate(zip(s.symbol, days, s.member)) if m})
    nxt = s.groupby(["entity_id", "share_class"], sort=False).cumcount(ascending=False) > 0  # has a later bar

    def move_close(i, new_close):
        ratio = new_close / s.at[i, "close"]
        s.at[i, "ret"] = (1 + s.at[i, "ret"]) * ratio - 1
        if nxt.iat[i]:
            s.at[i + 1, "ret"] = (1 + s.at[i + 1, "ret"]) / ratio - 1
        s.at[i, "close"] = new_close

    order = {"override_bar": 0, "override_close": 1, "total_return": 2, "no_trade": 3}
    for e in sorted(events.itertuples(), key=lambda e: order.get(e.action, 9)):
        i = pos.get((e.symbol, e.date))
        if e.action in ("override_open", "stopped_trading"):
            applied.append((e.action, "checked against the opens" if e.action == "override_open" else "no bar to fix"))
            continue
        if i is None:
            applied.append((e.action, "no bar in the store"))
            continue
        if e.action == "override_bar":
            move_close(i, float(e.close))
            for c in ("open", "high", "low", "vwap"):
                s.at[i, c] = float(getattr(e, c))
            s.at[i, "volume"] = int(round(float(e.volume)))
        elif e.action == "override_close":
            move_close(i, float(e.close))
        elif e.action == "total_return":
            s.at[i, "ret"] = float(e.total_return)
        elif e.action == "no_trade":
            s.at[i, "no_trade"] = True
        applied.append((e.action, "applied"))
    return s, pd.DataFrame(applied, columns=["action", "result"])


def official_opens(s):
    """The official prints of each company-series bar, from the file that served it."""
    off = pd.read_parquet(OFFICIAL)
    off["date"] = pd.to_datetime(off.date).astype("datetime64[ns]")
    keys = s[["entity_id", "share_class", "symbol", "asof", "date"]]
    o = keys.merge(off.drop(columns=[c for c in ("n_open_prints", "n_close_prints") if c in off]),
                   on=["symbol", "asof", "date"], how="inner")
    return o.rename(columns={"close": "official_close"})


def labels(s, opens, data_end):
    """The open-to-open total return of each company, class and session with an official open (see the module)."""
    o = opens.reindex(columns=["entity_id", "share_class", "date", "open", "open_time"]).dropna(subset=["open"])
    x = s[KEY + ["close", "ret", "volume"]].merge(o.rename(columns={"open": "official_open"}), on=KEY, how="left")
    out = []
    for (ent, cls), g in x.groupby(["entity_id", "share_class"], sort=False):
        dates, close = g.date.to_numpy(), g.close.to_numpy(dtype=float)
        oo, ret = g.official_open.to_numpy(dtype=float), g.ret.to_numpy(dtype=float)
        printed = pd.to_datetime(g.open_time, utc=True).to_numpy()  # when each official open printed
        undefined = np.cumsum(np.isnan(ret))  # a label can't cross a day without a return
        growth = np.cumsum(np.log1p(np.nan_to_num(ret)))  # log total return up to each close
        opened = np.flatnonzero(~np.isnan(oo))
        traded = np.flatnonzero(g.volume.to_numpy(dtype=float) > 0)
        last_traded = traded[-1] if len(traded) else -1
        stopped = len(traded) > 0 and dates[last_traded] < np.datetime64(data_end)
        for k, i in enumerate(opened):
            if k + 1 < len(opened):
                j, at_close = opened[k + 1], False
            elif stopped and last_traded >= i:
                j, at_close = last_traded, True
            else:
                continue
            if undefined[j] != undefined[i]:
                continue
            value = close[i] / oo[i] * np.exp(growth[j] - growth[i]) * (1.0 if at_close else oo[j] / close[j]) - 1
            out.append((ent, cls, dates[i], dates[j], value, at_close, pd.NaT if at_close else printed[j]))
    lab = pd.DataFrame(out, columns=["entity_id", "share_class", "date", "end", "label", "at_close", "end_open_time"])
    lab["end_open_time"] = pd.to_datetime(lab.end_open_time, utc=True)
    return lab


def stories():
    """Benzinga stories kept by the 3-day rule, and the single-firm filter's (story, company) pairs."""
    df = load_news()
    df = df[df.source.isin(BENZINGA)]
    df = df[keep_story(df.created_at, df.updated_at).to_numpy()]
    df = companies(df)
    single = df[(df.n_companies >= 1) & (df.n_companies <= 2)]
    pairs = single[["id", "entities"]].explode("entities").dropna(subset=["entities"])
    st = pd.DataFrame({"story_id": df.id.to_numpy(), "created_at": df.created.to_numpy(),
                       "updated_at": df.updated.to_numpy(), "headline": df.headline.to_numpy(),
                       "symbols": df.symbols.to_numpy(), "n_companies": df.n_companies.to_numpy()})
    se = pd.DataFrame({"story_id": pairs.id.to_numpy(), "entity_id": pairs.entities.to_numpy()})
    return st, se


def reference_tables():
    members = pd.read_csv(REFERENCE / "memberships.csv", dtype=str)
    m = pd.DataFrame({"entity_id": members.entity_id, "member_from": pd.to_datetime(members.member_from),
                      "member_to": pd.to_datetime(members.member_to)})
    ident = pd.read_csv(REFERENCE / "identity.csv", dtype=str).fillna("")
    ciks = pd.read_csv(REFERENCE / "entities.csv", dtype=str).set_index("entity_id").ciks
    ident = ident[["entity_id", "symbol", "share_class", "valid_from", "valid_to"]].assign(cik=ident.entity_id.map(ciks))
    return m, ident


def main():
    STORE.mkdir(parents=True, exist_ok=True)
    print("store: bars", flush=True)
    rows = file_rows()
    data_end = rows.loc[(rows.symbol == "AAPL") & rows.member, "date"].max()  # the data's last session
    s = company_series(rows)
    s = s[s.date <= data_end].reset_index(drop=True)  # a few files hold later bars (12 to 2026-10-30)
    events = pd.read_csv(REFERENCE / "price_events.csv", dtype=str)
    s, applied = apply_events(s, events)
    opens = official_opens(s)
    lab = labels(s, opens, data_end)
    bars = s[BAR_COLUMNS].reset_index(drop=True)
    opens_out = opens[["entity_id", "share_class", "date", "open", "open_time", "listing_exchange", "official_close"]]

    # The 54 opens price_events.csv overrides must equal the auctions' official opens.
    ov = events[events.action == "override_open"].assign(date=lambda e: pd.to_datetime(e.date), open=lambda e: e.open.astype(float))
    ov = ov.merge(s[["symbol", "date", "entity_id", "share_class", "member"]][s.member], on=["symbol", "date"], how="left")
    ov = ov.merge(opens_out[["entity_id", "share_class", "date", "open"]].rename(columns={"open": "auction_open"}),
                  on=["entity_id", "share_class", "date"], how="left")
    override_same = int(((ov.open - ov.auction_open).abs() < 1e-9).sum())
    for name, df in (("bars", bars), ("opens", opens_out), ("labels", lab)):
        df.to_parquet(STORE / f"{name}.parquet", index=False)
    member_days = bars[bars.member]
    with_open = member_days.merge(opens_out.dropna(subset=["open"])[KEY], on=KEY, how="inner")
    # An exit label ends where a company's series ends before the data does: it stopped trading, or the store stops
    # keeping its bars AFTER days after a removal while its file trades on.
    # A series that ends on or before its last member day stopped trading, even when its file trades on under the
    # ticker as another security (DuPont, IHS Markit, WestRock).
    ends = s.groupby(["entity_id", "share_class"], sort=False).agg(last=("date", "max"), row=("row", "last"))
    ends["last_member"] = s[s.member].groupby(["entity_id", "share_class"], sort=False).date.max()
    traded_to = rows[rows.volume > 0].groupby("row").date.max()
    cut = (ends.row.map(traded_to) > ends["last"]) & (ends["last"] > ends["last_member"])
    window_cut = cut.rename("window_cut").reset_index()
    exits = lab[lab.at_close].merge(window_cut, on=["entity_id", "share_class"], how="left")
    counts = {
        "data_end": str(data_end.date()),
        "bars": len(bars), "member_bars": len(member_days), "non_member_bars": int((~bars.member).sum()),
        "member_bars_without_return": int(member_days.ret.isna().sum()),
        "member_bars_with_official_open": len(with_open),
        "labels": len(lab), "labels_at_close": int(lab.at_close.sum()),
        "exits_stopped_trading": int((~exits.window_cut.fillna(False).astype(bool)).sum()),
        "exits_window_cut": int(exits.window_cut.fillna(False).astype(bool).sum()),
        "price_events": applied.value_counts().rename("rows").reset_index().to_dict("records"),
        "override_opens_equal_to_auctions": f"{override_same} of {len(ov)}",
    }
    del rows, s, opens, lab, bars, opens_out, member_days, with_open, exits
    gc.collect()

    print("store: stories", flush=True)
    st, se = stories()
    membership, identity = reference_tables()
    for name, df in (("stories", st), ("story_entities", se), ("membership", membership), ("identity", identity)):
        df.to_parquet(STORE / f"{name}.parquet", index=False)
    counts.update({"stories": len(st), "story_entities": len(se), "stories_with_a_company": int(se.story_id.nunique()),
                   "membership_rows": len(membership), "identity_rows": len(identity)})
    (STORE / "counts.json").write_text(json.dumps(counts, indent=2, default=str), encoding="utf-8")
    report(counts)
    print(REPORT.read_text(encoding="utf-8"), flush=True)


def report(c):
    lines = ["# The event store (M1)", "",
             "Written by `python -m data_pipeline.store`. Counts only: the tables are raw data in `D:\\chrono-data\\store`.",
             "", f"- Data through {c['data_end']}.",
             f"- Bars: {c['bars']:,}, of which {c['member_bars']:,} on member days and {c['non_member_bars']:,} on the "
             "companies' own days outside membership.",
             f"- Member bars without a return (the previous bar isn't the company's own): {c['member_bars_without_return']:,}.",
             f"- Member bars with an official open: {c['member_bars_with_official_open']:,}. The simulator doesn't trade "
             "a stock on a day without one.",
             f"- Labels: {c['labels']:,}. {c['labels_at_close']:,} end at a last traded close: "
             f"{c['exits_stopped_trading']:,} where the company stopped trading (an acquisition or a failure), and "
             f"{c['exits_window_cut']:,} where the store stops keeping a removed company's bars, {AFTER} days after "
             "its removal, while its file trades on.",
             f"- The 54 opens that `reference/price_events.csv` overrides, equal to the auctions' official opens: "
             f"{c['override_opens_equal_to_auctions']}.",
             "- `reference/price_events.csv`, by action and result:"]
    lines += [f"  - {r['action']}: {r['result']}, {r['rows']}" for r in c["price_events"]]
    lines += [f"- Stories (Benzinga, edited at most 3 days after publishing): {c['stories']:,}. Kept by the single-firm "
              f"filter and naming a company in the identity table: {c['stories_with_a_company']:,}, in "
              f"{c['story_entities']:,} (story, company) pairs.",
              f"- Membership rows: {c['membership_rows']}. Identity rows: {c['identity_rows']}."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
