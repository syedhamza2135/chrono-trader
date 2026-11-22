"""The dev report's metrics (PLAN 9.10; M3 step 5), computed after a run from its decisions, its equity rows and the
realized labels. Nothing here is seen by an agent.

- daily_rank_ic, ic_by_quarter, paired_gaps, twin_gaps: the skill metric and the frozen-twin gaps.
- book_returns, turnover, book_table, cost_table: each book's statistics, before and after costs. A run's equity
  rows come from the simulator at one cost; sim.simulator.replay gives them at any other.
- beta, sector_tilt: the exposures.
- seed_spread, regimes, regime_table, coefficient_life: reported, not tested.
"""
import math

import numpy as np
import pandas as pd

from . import stats

KEY = ["entity_id", "share_class", "date"]


def daily_rank_ic(decisions, labels, min_stocks=10):
    """The Spearman correlation, each day, between the predictions and the realized labels (open-to-open total
    returns) across the stocks predicted that day (PLAN 9.10). Days with fewer than `min_stocks` stocks with both
    are left out. Returns a Series by date."""
    lab = labels[KEY + ["label"]].astype({"entity_id": str, "share_class": str})
    d = decisions[KEY + ["prediction"]].astype({"entity_id": str, "share_class": str})
    d["date"], lab["date"] = pd.to_datetime(d.date), pd.to_datetime(lab.date)
    x = d.merge(lab, on=KEY).dropna(subset=["prediction", "label"])
    out = {}
    for day, g in x.groupby("date"):
        if len(g) >= min_stocks:
            out[day] = g.prediction.rank().corr(g.label.rank())
    return pd.Series(out, name="rank_ic", dtype=float).sort_index()


def within(s, first=None, last=None):
    s = s.sort_index()
    if first is not None:
        s = s[s.index >= pd.Timestamp(first)]
    if last is not None:
        s = s[s.index <= pd.Timestamp(last)]
    return s


def _row(x):
    m = stats.nw_mean(np.asarray(x, dtype=float))
    return {"days": m["n"], "mean": m["mean"], "se": m["se"], "t": m["t"], "p": m["p"]}


def ic_by_quarter(ic, first=None, last=None):
    """One row per calendar quarter ("2017Q1"), then "all": days, mean IC, its Newey-West standard error, t and the
    one-sided p for a mean above zero. Each quarter's lag follows its own length."""
    ic = within(ic.dropna(), first, last)
    rows = {str(q): _row(g.to_numpy()) for q, g in ic.groupby(ic.index.to_period("Q"))}
    rows["all"] = _row(ic.to_numpy())
    return pd.DataFrame(rows).T[["days", "mean", "se", "t", "p"]].astype({"days": int})


def paired_gaps(a, b, first=None, last=None, by="year"):
    """The daily differences a - b on the days both have, by year (or "all" only, with by=None), with Newey-West
    statistics."""
    d = within((a - b).dropna(), first, last)
    rows = {}
    if by == "year":
        rows = {str(y): _row(g.to_numpy()) for y, g in d.groupby(d.index.year)}
    rows["all"] = _row(d.to_numpy())
    return pd.DataFrame(rows).T[["days", "mean", "se", "t", "p"]].astype({"days": int})


def twin_gaps(live_ic, twin_ics, last=None):
    """PLAN 9.10's frozen-twin gaps: for each twin frozen at the end of year Y ({Y: its daily IC}), the paired daily
    IC difference live minus twin in each year after Y, and over all of them. Rows (twin, year)."""
    out = []
    for y, tw in sorted(twin_ics.items()):
        g = paired_gaps(live_ic, tw, first=pd.Timestamp(y + 1, 1, 1), last=last)
        g.insert(0, "twin", f"end of {y}")
        out.append(g.rename_axis("year").reset_index())
    cols = ["twin", "year", "days", "mean", "se", "t", "p"]
    return pd.concat(out, ignore_index=True)[cols] if out else pd.DataFrame(columns=cols)


# The books

def book_returns(equity, first=None, last=None):
    """A book's daily returns, by date, from its equity rows (the simulator's, after costs at the cost it ran at;
    sim.simulator.replay gives the rows at another cost). The run starts with 1.0 in cash."""
    e = equity.sort_values("date")
    eq = e.equity.to_numpy(dtype=float)
    r = eq / np.concatenate([[1.0], eq[:-1]]) - 1.0
    return within(pd.Series(r, index=pd.DatetimeIndex(e.date), name="ret"), first, last)


def turnover(equity, first=None, last=None):
    """The mean daily traded value (buys plus sells) over the pre-trade equity."""
    e = equity.sort_values("date")
    pre = (e.equity + e.cost).to_numpy(dtype=float)
    share = pd.Series(e.traded.to_numpy(dtype=float) / pre, index=pd.DatetimeIndex(e.date))
    return float(within(share, first, last).mean())


def book_table(books, first, last, before=None):
    """One row per book ({name: equity rows after costs}): its statistics after costs, before costs where `before`
    has its rows at 0 bps ({name: equity rows}), and its daily turnover."""
    before = before or {}
    rows = {}
    for name, eq in books.items():
        net = stats.book_stats(book_returns(eq, first, last).to_numpy())
        gross = stats.book_stats(book_returns(before[name], first, last).to_numpy()) if name in before else {}
        rows[name] = {"annual_return": net["annual_return"], "annual_vol": net["annual_vol"],
                      "sharpe_after_costs": net["sharpe"], "sharpe_before_costs": gross.get("sharpe", math.nan),
                      "annual_return_before_costs": gross.get("annual_return", math.nan),
                      "max_drawdown": net["max_drawdown"], "daily_turnover": turnover(eq, first, last),
                      "days": net["days"]}
    return pd.DataFrame(rows).T.astype({"days": int})


def cost_table(by_cost, first, last):
    """The book's statistics at each cost ({bps per side: equity rows}, from sim.simulator.replay; PLAN 9.8)."""
    rows = {}
    for c in sorted(by_cost):
        st = stats.book_stats(book_returns(by_cost[c], first, last).to_numpy())
        rows[f"{c:g} bps"] = {k: st[k] for k in ("annual_return", "annual_vol", "sharpe", "max_drawdown", "total")}
    return pd.DataFrame(rows).T


def spy_open_returns(spy):
    """SPY's open-to-open return on each session, from the adjusted opens, so it lines up with the book's marks."""
    s = spy.sort_values("date")
    return pd.Series((s.adj_open / s.adj_open.shift(1) - 1.0).to_numpy(), index=pd.DatetimeIndex(s.date),
                     name="spy").dropna()


def beta(book, market):
    """{beta, se, t, alpha_daily, days}: the least-squares slope of the book's daily returns on the market's, with
    an intercept and Newey-West standard errors, over the days both have."""
    x = pd.concat([book.rename("y"), market.rename("x")], axis=1).dropna()
    if len(x) < 3:
        return {"beta": math.nan, "se": math.nan, "t": math.nan, "alpha_daily": math.nan, "days": len(x)}
    b, se, _ = stats.nw_ols(x.y.to_numpy(), np.column_stack([np.ones(len(x)), x.x.to_numpy()]))
    return {"beta": float(b[1]), "se": float(se[1]), "t": float(b[1] / se[1]) if se[1] > 0 else math.nan,
            "alpha_daily": float(b[0]), "days": len(x)}


def sectors_for(pairs, sectors):
    """Each (entity_id, date) row's sector: the run whose valid_from is the latest on or before the date; a date
    before the first run gets the first run's sector (eval.benchmarks.sector_on's rule); a company never listed gets
    "Unknown"."""
    p = pairs[["entity_id", "date"]].astype({"entity_id": str}).assign(date=lambda d: pd.to_datetime(d.date))
    p = p.reset_index(drop=True).assign(_i=lambda d: np.arange(len(d)))
    s = sectors[["entity_id", "sector", "valid_from"]].astype({"entity_id": str, "sector": str})
    s = s.assign(valid_from=pd.to_datetime(s.valid_from).astype("datetime64[ns]")).sort_values("valid_from")
    m = pd.merge_asof(p.astype({"date": "datetime64[ns]"}).sort_values("date"), s, left_on="date",
                      right_on="valid_from", by="entity_id", direction="backward")
    first = s.groupby("entity_id").sector.first()
    m["sector"] = m.sector.fillna(m.entity_id.map(first)).fillna("Unknown")
    return m.sort_values("_i").sector.to_numpy()


def sector_tilt(decisions, sectors, first=None, last=None):
    """The book's net target weight in each sector, averaged over the days it holds anything, and the mean of its
    absolute value; plus the mean over days of the summed absolute net weights ("all"). From the agent's targets
    (decisions.position), not the filled holdings."""
    d = decisions[decisions.position != 0].copy()
    d["date"] = pd.to_datetime(d.date)
    if first is not None:
        d = d[d.date >= pd.Timestamp(first)]
    if last is not None:
        d = d[d.date <= pd.Timestamp(last)]
    if d.empty:
        return pd.DataFrame(columns=["mean_net", "mean_abs_net"])
    d["sector"] = sectors_for(d, sectors)
    net = d.pivot_table(index="date", columns="sector", values="position", aggfunc="sum", fill_value=0.0)
    out = pd.DataFrame({"mean_net": net.mean(), "mean_abs_net": net.abs().mean()})
    out.loc["all"] = [net.sum(axis=1).mean(), net.abs().sum(axis=1).mean()]
    return out


def seed_spread(ics, books, first, last):
    """Per seed ({seed: daily IC}, {seed: equity rows}): mean IC, its t and the Sharpe after costs; then the min,
    max, mean and standard deviation across seeds (PLAN 5.5)."""
    rows = {}
    for s in sorted(ics):
        m = stats.nw_mean(within(ics[s].dropna(), first, last).to_numpy())
        sh = stats.book_stats(book_returns(books[s], first, last).to_numpy())["sharpe"] \
            if s in books else math.nan
        rows[str(s)] = {"mean_ic": m["mean"], "t": m["t"], "sharpe_after_costs": sh}
    t = pd.DataFrame(rows).T
    if len(t):
        for name, f in (("min", "min"), ("max", "max"), ("mean", "mean"), ("std", "std")):
            t.loc[name] = getattr(t.iloc[:len(rows)], f)()
    return t


def regimes(spy, sessions, trend_days=200, vol_days=20, fall=0.10, after=20):
    """Each session's market regime, from SPY's adjusted closes before that session only:
    - trend: "up" if the last close is above the mean of the last `trend_days` closes, else "down" (the 200-day
      moving-average rule; Faber 2007 uses the 10-month average);
    - vol: "high" if the standard deviation of the last `vol_days` close-to-close log returns is above its median
      over all of SPY's sessions so far (an expanding median, so a label never uses a later close), else "low";
    - shock: "after shock" on the session a correction starts (the last close first `fall` or more below the highest
      close so far, the usual 10% definition of a correction) and the `after` - 1 sessions that follow, else
      "none". A new shock can start only after a new high. The walk starts at SPY's first close, not at the
      window's, so a window that opens inside a fall still sees the earlier peak.
    Sessions without enough history get NaN for that column."""
    s = spy.sort_values("date").set_index(pd.DatetimeIndex(spy.sort_values("date").date)).adj_close
    days = pd.DatetimeIndex(sessions)
    prior = s.shift(1).reindex(s.index)  # the close before each SPY session
    ma = s.rolling(trend_days).mean().shift(1)
    vol = np.log(s).diff().rolling(vol_days).std().shift(1)
    out = pd.DataFrame(index=days)
    p, m, v = prior.reindex(days), ma.reindex(days), vol.reindex(days)
    out["trend"] = np.where(m.isna() | p.isna(), None, np.where(p > m, "up", "down"))
    med = vol.expanding().median().reindex(days)
    out["vol"] = np.where(v.isna(), None, np.where(v > med, "high", "low"))
    shock = {}
    peak, armed, left = -math.inf, True, 0
    for d in s.index.union(days):
        c = prior.get(d, math.nan)
        if not math.isnan(c):
            if c > peak:
                peak, armed = c, True
            if armed and c <= (1.0 - fall) * peak:
                armed, left = False, after
        shock[d] = "after shock" if left > 0 else "none"
        left = max(left - 1, 0)
    out["shock"] = [shock[d] for d in days]
    return out


def regime_table(ic, book, labels, first=None, last=None):
    """For each regime column and value: days, mean IC with its Newey-West t, and the book's Sharpe after costs."""
    ic, book = within(ic.dropna(), first, last), within(book.dropna(), first, last)
    rows = []
    for col in labels.columns:
        for val, g in labels.groupby(col):
            days = g.index
            m = stats.nw_mean(ic.reindex(days).dropna().to_numpy())
            st = stats.book_stats(book.reindex(days).dropna().to_numpy())
            rows.append({"regime": col, "value": val, "ic_days": m["n"], "mean_ic": m["mean"], "t": m["t"],
                         "book_days": st["days"], "sharpe": st["sharpe"]})
    return pd.DataFrame(rows)


def coefficient_life(twin_ics, last=None):
    """How long learned coefficients keep working (PLAN 9.10): each frozen twin's mean daily IC by quarter since its
    snapshot (1 is the first quarter after the year end), with Newey-West t. Rows (twin, quarter)."""
    rows = []
    for y, tw in sorted(twin_ics.items()):
        x = within(tw.dropna(), pd.Timestamp(y + 1, 1, 1), last)
        q = (x.index.year - (y + 1)) * 4 + (x.index.month - 1) // 3 + 1
        for k, g in x.groupby(q):
            m = stats.nw_mean(g.to_numpy())
            rows.append({"twin": f"end of {y}", "quarter": int(k), "days": m["n"], "mean_ic": m["mean"], "t": m["t"]})
    return pd.DataFrame(rows, columns=["twin", "quarter", "days", "mean_ic", "t"])
