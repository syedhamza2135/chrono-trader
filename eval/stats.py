"""The statistics the dev report needs (PLAN 3 "Statistics", 5.5 and 9.10; M3 step 5), in plain numpy, since the venv
has no SciPy or statsmodels.

- Newey-West standard errors for a least-squares fit (Newey and West 1987), with the Bartlett kernel and the lag
  rule floor(4 (T / 100) ^ (2 / 9)) of Newey and West (1994), the usual default. A mean is the fit on a constant.
- The normal distribution's cdf (from math.erfc) and its inverse (by bisection on the cdf).
- A book's statistics from its daily returns: total and annual return, annual volatility, Sharpe over zero (the
  store has no cash rate) and the maximum drawdown, with 252 sessions a year.
- The probabilistic and deflated Sharpe ratios (Bailey and Lopez de Prado 2012 and 2014), on daily, not annual,
  Sharpe ratios, with the expected maximum of N trials' Sharpe ratios from their spread.
"""
import math

import numpy as np

YEAR = 252
EULER = 0.5772156649015329


def nw_lag(n):
    """Newey and West (1994): floor(4 (n / 100) ^ (2 / 9)), at least 0."""
    return max(int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))), 0) if n > 0 else 0


def nw_ols(y, X, lag=None):
    """Least squares of y on the columns of X, with Newey-West (Bartlett) standard errors. Rows in time order.
    Returns (coefficients, standard errors, lag)."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float).reshape(len(y), -1)
    n = len(y)
    lag = nw_lag(n) if lag is None else int(lag)
    xx_inv = np.linalg.inv(X.T @ X)
    b = xx_inv @ X.T @ y
    g = X * (y - X @ b)[:, None]
    s = g.T @ g
    for k in range(1, min(lag, n - 1) + 1):
        gamma = g[k:].T @ g[:-k]
        s += (1.0 - k / (lag + 1.0)) * (gamma + gamma.T)
    v = xx_inv @ s @ xx_inv
    return b, np.sqrt(np.maximum(np.diag(v), 0.0)), lag


def norm_cdf(z):
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def norm_ppf(p):
    """The inverse of norm_cdf, by bisection, to about 1e-12."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be strictly between 0 and 1")
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def nw_mean(x, lag=None):
    """{n, mean, se, t, p}: the mean of a series in time order, its Newey-West standard error, the t-statistic and
    the one-sided p-value for a mean above zero. NaNs are dropped. Fewer than 2 values give NaNs."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return {"n": len(x), "mean": float(x.mean()) if len(x) else math.nan, "se": math.nan, "t": math.nan,
                "p": math.nan, "lag": 0}
    b, se, lag = nw_ols(x, np.ones((len(x), 1)), lag)
    t = b[0] / se[0] if se[0] > 0 else math.nan
    return {"n": len(x), "mean": float(b[0]), "se": float(se[0]), "t": float(t),
            "p": 1.0 - norm_cdf(t) if not math.isnan(t) else math.nan, "lag": lag}


def max_drawdown(r):
    """The largest fall of the wealth path from a previous peak, as a negative fraction (0 if it never falls). The
    path starts at 1 before the first return."""
    w = np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(r, dtype=float))])
    return float((w / np.maximum.accumulate(w) - 1.0).min())


def book_stats(r):
    """{days, total, annual_return, annual_vol, sharpe, max_drawdown} from daily returns (NaNs dropped)."""
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n == 0:
        return {"days": 0, "total": math.nan, "annual_return": math.nan, "annual_vol": math.nan,
                "sharpe": math.nan, "max_drawdown": math.nan}
    total = float(np.prod(1.0 + r) - 1.0)
    sd = float(r.std(ddof=1)) if n > 1 else math.nan
    return {"days": n, "total": total, "annual_return": (1.0 + total) ** (YEAR / n) - 1.0,
            "annual_vol": sd * math.sqrt(YEAR) if n > 1 else math.nan,
            "sharpe": float(r.mean()) / sd * math.sqrt(YEAR) if n > 1 and sd > 0 else math.nan,
            "max_drawdown": max_drawdown(r)}


def moments(r):
    """(daily Sharpe, skewness, kurtosis) with population moments; the kurtosis is not excess (a normal gives 3)."""
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    m = r.mean()
    d = r - m
    m2, m3, m4 = (d ** 2).mean(), (d ** 3).mean(), (d ** 4).mean()
    sd = r.std(ddof=1)
    return float(m / sd), float(m3 / m2 ** 1.5), float(m4 / m2 ** 2)


def psr(sr, n, skew, kurt, benchmark=0.0):
    """The probabilistic Sharpe ratio (Bailey and Lopez de Prado 2012): the probability that the true daily Sharpe is
    above `benchmark`, given an observed daily Sharpe `sr` over n returns with that skewness and kurtosis."""
    den = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2
    return norm_cdf((sr - benchmark) * math.sqrt(n - 1) / math.sqrt(den))


def expected_max_sharpe(n_trials, var_trials):
    """The expected largest of n_trials daily Sharpe ratios when all are noise around zero with variance var_trials
    (Bailey and Lopez de Prado 2014): sqrt(V) ((1 - g) Z(1 - 1/N) + g Z(1 - 1/(N e))), g Euler's constant. One trial
    gives 0."""
    if n_trials <= 1:
        return 0.0
    z1, z2 = norm_ppf(1.0 - 1.0 / n_trials), norm_ppf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_trials) * ((1.0 - EULER) * z1 + EULER * z2)


def deflated_sharpe(r, n_trials, trial_srs):
    """{sr, sr_annual, skew, kurt, n, n_trials, var_trials, sr0, dsr} for the chosen version's daily returns `r`.
    n_trials is the ledger's count; trial_srs are the daily Sharpe ratios of the trials run (their spread gives V).
    The DSR is the PSR against the expected maximum of n_trials noise trials."""
    sr, skew, kurt = moments(r)
    n = int(np.sum(~np.isnan(np.asarray(r, dtype=float))))
    srs = np.asarray(trial_srs, dtype=float)
    var = float(srs.var(ddof=1)) if len(srs) > 1 else 0.0
    sr0 = expected_max_sharpe(n_trials, var)
    return {"sr": sr, "sr_annual": sr * math.sqrt(YEAR), "skew": skew, "kurt": kurt, "n": n, "n_trials": n_trials,
            "var_trials": var, "sr0": sr0, "dsr": psr(sr, n, skew, kurt, sr0)}
