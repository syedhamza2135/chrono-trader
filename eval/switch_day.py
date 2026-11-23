"""The switch-day check (research/audit/cutoff.md, section 10.2, frozen on 21 Nov; M3 decision 2), as written there:

- What. Each year's stories switch to a new vintage on 1 January (New York). A vintage that leaked into the start of
  the year it reads would read early-year headlines better than later ones, so the news effect would be larger
  right after each switch.
- How. For each year, split its sessions into the first 20 and the rest. Compute the news effect for each day.
  Then take the mean over all years' first-20 days minus the mean over all years' other days, with Newey-West
  standard errors over the pooled days.
- Warning. Either of these: (a) the pooled difference is above zero, one-sided at 5%; (b) in at least half of the
  years, the first-20 mean is above the rest of that year's mean by more than two of its standard errors.

The news effect on a day is the live agent's daily rank IC minus the price-only twin's (cutoff.md 10.2, "Limits",
and M3 decision 2). How the rules are read here, where cutoff.md leaves a detail open:
- "Its sessions" are the year's trading sessions from the calendar, so the first 20 are the year's first 20
  sessions whether or not the agent had a prediction on them. Days without both ICs are left out.
- A difference of means with Newey-West standard errors is the least-squares slope of the effect on a first-20
  dummy, with an intercept, over the days in date order. The lag is Newey and West's (1994) rule for that many
  days.
- "Its standard errors" in (b) are that year's difference's Newey-West standard error, from the same fit on that
  year's days alone.
- The years counted in (b) are those of the check that have days in both parts; "at least half" means at least
  that many over 2.
"""
import math

import numpy as np
import pandas as pd

from . import stats

FIRST = 20
ALPHA = 0.05


def _diff(effect, first20):
    """(difference, Newey-West se, t, one-sided p, days in first 20, other days) of a fit on [1, dummy]."""
    n1, n0 = int(first20.sum()), int((~first20).sum())
    if n1 == 0 or n0 == 0 or len(effect) < 3:
        return math.nan, math.nan, math.nan, math.nan, n1, n0
    X = np.column_stack([np.ones(len(effect)), first20.astype(float)])
    b, se, _ = stats.nw_ols(effect, X)
    t = b[1] / se[1] if se[1] > 0 else math.nan
    return float(b[1]), float(se[1]), float(t), 1.0 - stats.norm_cdf(t) if not math.isnan(t) else math.nan, n1, n0


def switch_day(live_ic, price_only_ic, sessions, years):
    """Runs the check on `years` (for the dev report, 2017 to 2019). `sessions` are the trading sessions (the
    clock's), so the first 20 of each year come from the calendar. Returns {"years": a table per year, "pooled":
    {...}, "warning_a", "warning_b", "warning"}."""
    effect = (live_ic - price_only_ic).dropna().sort_index()
    sessions = pd.DatetimeIndex(sessions).sort_values()
    first20 = set()
    for y in years:
        first20 |= set(sessions[sessions.year == y][:FIRST])
    effect = effect[effect.index.year.isin(list(years))]
    dummy = effect.index.isin(list(first20))
    rows = []
    for y in years:
        m = effect.index.year == y
        d, se, t, p, n1, n0 = _diff(effect[m].to_numpy(), dummy[m])
        above = bool(not math.isnan(d) and d > 2.0 * se)
        rows.append({"year": y, "first20_days": n1, "other_days": n0,
                     "first20_mean": float(effect[m][dummy[m]].mean()) if n1 else math.nan,
                     "other_mean": float(effect[m][~dummy[m]].mean()) if n0 else math.nan,
                     "difference": d, "se": se, "above_by_two_se": above})
    table = pd.DataFrame(rows)
    d, se, t, p, n1, n0 = _diff(effect.to_numpy(), dummy)
    pooled = {"difference": d, "se": se, "t": t, "p": p, "first20_days": n1, "other_days": n0}
    counted = table[(table.first20_days > 0) & (table.other_days > 0)]
    warning_a = bool(not math.isnan(p) and p < ALPHA)
    warning_b = bool(len(counted) > 0 and 2 * int(counted.above_by_two_se.sum()) >= len(counted))
    return {"years": table, "pooled": pooled, "years_counted": len(counted), "warning_a": warning_a,
            "warning_b": warning_b, "warning": warning_a or warning_b}
