"""Daily bars per company, stitched from the download plan (DATA_DIR/bars/plan.csv, written by bars.py).

Each plan row names a file (ticker, asof) and the member days it serves for one company. `load` returns every
row's full file history, with `member` marking the days the plan assigns to the company. A company listed with two
share classes has one plan row per class, and the rows of one class never overlap in time.

Only member days are certain to be the company's. Alpaca's histories follow a symbol, so a file's bars outside its
row can belong to another security: the UAA file is class C before 2016-12-07, the FOXA file is 21st Century Fox
before 2019-03-19, and the DWDP file is Dow Chemical before 2017-09-01. A reader that looks outside a row, like the
stock picker's year of trading before a company joins, must keep only the company's own bars
(audit_prices.universe_preview shows how). Returns across a change of row need the previous row's close
(audit_prices.returns).

`incomplete` marks bars that hold only part of the day's trades (see `incomplete`).
"""
import pandas as pd
import pyarrow.parquet as pq

from .settings import DATA_DIR

BARS = DATA_DIR / "bars"
PLAN = BARS / "plan.csv"
COLUMNS = ["t", "open", "high", "low", "close", "volume", "trades", "vwap"]

# Incomplete bars. On 2021-04-19, 2021-10-25 and 2022-03-08 Alpaca's bars for most NYSE-listed stocks hold a handful
# of trades: at most 1.7% of the file's usual count. On every other day no member bar with trades falls below 12% (a
# half-day), except Kellogg's on 2018-03-26 (6 trades; Nordstrom's bar that day ends at Kellogg's close). So the trade
# count alone decides. Volume can't: a few large prints can bring a partial bar near its usual volume (PSX on
# 2022-03-08 has more than its usual volume from 0.4% of its usual trades).
TRAILING, MIN_BARS = 20, 10  # medians over the file's previous 20 bars, judged once there are 10
INCOMPLETE_TRADES = 0.05


def plan():
    return pd.read_csv(PLAN, dtype=str)


def trailing_ratios(bars):
    """Volume and trade count of each bar of one file (sorted by date) over their medians across the previous bars."""
    prev = bars[["volume", "trades"]].shift(1).rolling(TRAILING, min_periods=MIN_BARS).median()
    return bars.volume / prev.volume, bars.trades / prev.trades


def incomplete(bars):
    """True where a bar holds only part of the day's trades: its trade count below 5% of the median of the file's
    previous 20 bars. Its volume, high, low and vwap aren't the day's, and its open may not be either (on 2022-03-08
    many such bars hold a single price). Zero-volume bars (halts, and Alpaca's fills after a last trade) are not
    incomplete."""
    _, trades = trailing_ratios(bars)
    return (bars.volume > 0) & (trades < INCOMPLETE_TRADES)


def load(adjustment="raw", columns=COLUMNS):
    """One frame: entity_id, symbol, share_class, asof, use_from, use_to, date, member, incomplete, and the bar
    columns."""
    frames = []
    for (symbol, asof), rows in plan().fillna({"share_class": ""}).groupby(["symbol", "asof"]):
        path = BARS / adjustment / f"{symbol.replace('/', '_')}__{asof}.parquet"
        if not path.exists():
            continue
        t = pq.read_table(path, columns=list(dict.fromkeys(["t", *columns, "volume", "trades"]))).to_pandas()
        t["date"] = pd.to_datetime(t["t"].str[:10])
        t = t.drop(columns="t").sort_values("date", ignore_index=True)
        t["incomplete"] = incomplete(t)
        t = t.drop(columns=[c for c in ("volume", "trades") if c not in columns])
        for r in rows.itertuples():
            member = (t["date"] >= pd.Timestamp(r.use_from)) & (t["date"] <= pd.Timestamp(r.use_to))
            frames.append(t.assign(entity_id=r.entity_id, symbol=symbol, share_class=r.share_class, asof=asof,
                                   use_from=r.use_from, use_to=r.use_to, member=member))
    df = pd.concat(frames, ignore_index=True)
    df["row"] = df["symbol"] + "__" + df["asof"] + "__" + df["use_from"]
    return df.sort_values(["row", "date"]).reset_index(drop=True)
