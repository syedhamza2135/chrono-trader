"""Value each distribution in reference/price_events.csv at the ex-date's official opens (review of 21 Nov, M-2).

A `total_return` row holds the ex-date's close-to-close total return, worked out in its evidence as
(parent close + ratio x other close + cash) / previous close - 1. A label that ends on the ex-date needs the same
return valued at the open, so the ex-date's closes don't enter it. This script takes each row's formula and puts each
security's official open on the ex-date in place of its close. It writes two columns:
- `open_value`: what one share held the evening before is worth at the ex-date's opens (parent open x its ratio +
  ratio x other security's open + cash). `data_pipeline.store.labels` divides it by the series' own previous close,
  so a later correction of that close can't leave it stale (the judge of 21 Nov, J-5).
- `open_value_time`: when the last of those opens printed (UTC). The label that ends there becomes visible no
  earlier (J-3).
The evidence ends with the opens used and the open-based total return over the store's previous close.

- The parent's open, its print time and its previous close come from the store (DATA_DIR/store).
- Another security's open comes from Alpaca's auctions endpoint (data_pipeline.auctions.fetch and official, asof
  the ex-date, so a reused ticker resolves to the new security): the listing exchange's opening print. Where the
  store also has that symbol's open that day, the script reports any difference.
- Cash, and anything the row values at a fixed amount (a warrant priced at a later close), stays as it is.
- Rows whose true return is a plain price ratio (the formula has no sum) keep both columns blank: there the
  close-based end piece already cancels the closes.

Raw prices go only into reference/price_events.csv, which AGENTS.md allows. In a worktree, set CHRONO_ENV_FILE.

Usage: python research/ex_date_opens.py [--write]   (without --write it prints the rows and changes nothing)
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline import auctions  # noqa: E402
from data_pipeline.settings import DATA_DIR, ROOT  # noqa: E402

EVENTS = ROOT / "reference" / "price_events.csv"
STORE = DATA_DIR / "store"
FORMULA = re.compile(r"\(([^()]*)\) / ([\d.]+) - 1")
THIN = 10_000  # an opening print smaller than this is reported
PRICE = re.compile(r"([A-Z][A-Z.]*)(?: \([^)]*\))? (\d+\.\d+)")


def terms(formula):
    """[(ratio, number)] from '39.63 + 26.86/6', '18.56 + 0.8 x 20.89' or '76.10/3 + 24.81/3'."""
    out = []
    for t in formula.split(" + "):
        t = t.strip()
        if " x " in t:
            r, n = t.split(" x ")
            out.append((float(r), n))
        elif "/" in t:
            n, k = t.split("/")
            out.append((1 / float(k), n))
        else:
            out.append((1.0, t))
    return out


def ex_date_closes(evidence, date):
    """{close: symbol} for the prices the evidence gives on the ex-date ('...; WRK 39.63 and NGVT 26.86 on <date>')."""
    m = re.search(r"Alpaca closes[^:]*:(.*?) on " + re.escape(date), evidence)
    if not m:
        return {}
    part = m.group(1).split(";")[-1]
    return {n: sym for sym, n in PRICE.findall(part)}


def store_tables():
    bars = pd.read_parquet(STORE / "bars.parquet", columns=["entity_id", "share_class", "symbol", "date", "close",
                                                            "member"])
    opens = pd.read_parquet(STORE / "opens.parquet", columns=["entity_id", "share_class", "date", "open", "open_time"])
    bars = bars.merge(opens, on=["entity_id", "share_class", "date"], how="left")
    bars = bars.sort_values(["entity_id", "share_class", "date"], ignore_index=True)
    bars["prev_close"] = bars.groupby(["entity_id", "share_class"], sort=False).close.shift(1)
    # Member bars win a clash, as in data_pipeline.store.apply_events.
    return bars.sort_values("member").drop_duplicates(["symbol", "date"], keep="last").set_index(["symbol", "date"])


def alpaca_open(symbol, date):
    off = auctions.official(pd.DataFrame(auctions.fetch(symbol, date, date, date), columns=auctions.PRINT_COLUMNS))
    off = off[off.date == date]
    if not len(off) or pd.isna(off.open.iloc[0]):
        return None
    if off.open_size.iloc[0] < THIN:
        print(f"  note: {symbol}'s official open on {date} is a print of {int(off.open_size.iloc[0])} shares")
    return float(off.open.iloc[0]), pd.Timestamp(off.open_time.iloc[0])


def main(write):
    events = pd.read_csv(EVENTS, dtype=str, keep_default_na=False)
    events = events.drop(columns=[c for c in ("open_return",) if c in events])  # this branch's first version
    for c in ("open_value", "open_value_time"):
        if c not in events:
            events[c] = ""
    bars = store_tables()
    for i, r in events[events.action == "total_return"].iterrows():
        f = FORMULA.search(r.evidence)
        if not f or "+" not in f.group(1):
            print(f"row {i + 2} {r.symbol} {r.date}: a plain ratio, left blank")
            continue
        key = (r.symbol, pd.Timestamp(r.date))
        if key not in bars.index or pd.isna(bars.loc[key, "open"]):
            print(f"row {i + 2} {r.symbol} {r.date}: no store bar with an official open, left blank")
            continue
        parent = bars.loc[key]
        closes = ex_date_closes(r.evidence, r.date)
        value, used, last = 0.0, [], pd.Timestamp(parent.open_time)
        for k, (ratio, n) in enumerate(terms(f.group(1))):
            sym = closes.get(n)
            if k == 0 and (sym is None or sym == r.symbol):  # the parent's own share
                value += ratio * parent.open
                used.append(f"{r.symbol} {parent.open:.4g}")
            elif sym is None:  # cash, or a value the row fixes
                value += ratio * float(n)
            else:
                got = alpaca_open(sym, r.date)
                if got is None:
                    raise SystemExit(f"row {i + 2}: no official open for {sym} on {r.date}")
                o, when = got
                last = max(last, when)
                s = bars.open.get((sym, pd.Timestamp(r.date)))
                if s is not None and pd.notna(s) and abs(s - o) > 1e-9:
                    print(f"row {i + 2}: note, the store's {sym} open differs from Alpaca's ({s} vs {o})")
                value += ratio * o
                used.append(f"{sym} {o:.4g}")
        stated = float(f.group(2))
        if abs(stated - parent.prev_close) > 0.006 * stated and "Per old share" not in r.evidence:
            print(f"row {i + 2} {r.symbol} {r.date}: note, the evidence's previous close {stated} differs from the "
                  f"store's {parent.prev_close:.4f}")
        ret = value / parent.prev_close - 1
        events.at[i, "open_value"] = f"{value:.6f}"
        events.at[i, "open_value_time"] = last.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        note = (f" Valued at the ex-date's official opens ({', '.join(used)}) over the store's previous close, the "
                f"total return is {ret:+.2%} (open_value; research/ex_date_opens.py).")
        events.at[i, "evidence"] = r.evidence.split(" Valued at the ex-date's official opens")[0] + note
        print(f"row {i + 2} {r.symbol} {r.date}: close-based {float(r.total_return):+.4f}, open-based {ret:+.4f}")
    if write:
        events.to_csv(EVENTS, index=False, lineterminator="\n")
        print(f"wrote {EVENTS}")


if __name__ == "__main__":
    main("--write" in sys.argv)
