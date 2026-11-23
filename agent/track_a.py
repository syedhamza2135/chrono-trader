"""Track A's agent (PLAN 5.3 and 9.5 to 9.8; M3 step 3). It sees only the views the loop hands it, and keeps what it
saw in its own memory.

- Picking (PLAN 9.5): the toy agent's rule, which reproduces M0's list (tests/test_leaks.py): on the year's first
  decision, the 50 members with the highest median daily dollar volume over the year before; in 2016 on the first
  trading day of April, from January to March. A pick that leaves the index drops out until the next pick.
- Features per stock and day (PLAN 9.6), from the view at 9:00:
  - r1, r5, r20, r60: sums of log(1 + ret) over the stock's last 1, 5, 20 and 60 bars (bars dated before today,
    within 200 calendar days); vol20: the standard deviation (ddof 0) of the last 20 of those; dvol_ratio: the log of
    the mean dollar volume (raw close times volume) of the last 5 bars over that of the last 60, without incomplete
    bars.
  - news_count and news_none: how many of the stock's filtered stories became available since the last decision, and
    a flag when none did. A story becomes available to a stock when both its embedding and its link to that stock
    are in the view. news_new: the mean of those stories' embeddings (zeros when none).
  - news_memory: the mean of every past story embedding of the stock, each weighted by 0.5 ** (age / 5), its age
    counted in sessions (half-life 5 trading days); zeros before the first story. Kept as running sums for every
    company in the view, started on the first decision from the stories the view holds.
  Each embedding feature comes in both poolings (last layer, mean of all layers); validation picks one.
- Target (PLAN 9.6): log(1 + label), the open-to-open return, minus that day's mean over the stocks with a label.
- Learning (PLAN 9.5 and 9.7): rows enter the learner once their labels are in the view. At each monthly refit, a
  day's rows enter together if every row has its label or 10 sessions have passed (rows still without one are
  dropped); the others wait for the next refit. The ridge
  is kept as running sums (count, sum of x, x'x, sum of y, x'y) per pooling, in float64, so it only ever adds lived
  days. On the first decision of each month, once fit_after_months have been lived, it chooses the penalty and the
  pooling on a validation part, then refits the scaler and the ridge on every row in the sums.
  - The validation part is the most recent 20% of the labelled lived days, at least the last 3 months, until 5 years
    have been lived; then the last 12 months. Left out of both parts (the k-2 gap): the lived day just before it, and
    any earlier day with a label that showed at or after the first validation decision (a label whose end open came
    late; judge S1). So every training label was in the view before the first validation decision. Training sums
    are the full sums minus the rows held out, which the agent keeps (at most about 13 months of rows).
  - The score is the mean daily rank IC of the validation predictions. Ties go to the last-layer pooling, then to the
    larger penalty. With fewer than 20 training days there is no fit.
  - Features are standardized with the training rows' means and standard deviations (1 where a deviation is 0). A
    missing value is 0 before scaling, in the sums and in scoring alike (judge S2).
- Policy (PLAN 9.8): rank by prediction. long_short: plus 1 / n_side for the top n_side and minus 1 / n_side for the
  bottom n_side; long_only: the top n_side at 1 / n_side. With hold > 1 it trades every hold sessions and keeps its
  positions between; with a band it keeps a holding while it stays in the top (or bottom) band ranks. Before
  trade_from (2016 is watch-only, PLAN 5.5) every position is 0 and no book is kept, so the first trading day starts
  fresh (judge N3). Before the first fit it makes no decision.
- news=False gives the price-only twin (PLAN 9.9): no news features at all.
- The dev variants (PLAN 5.3 and 9.7; M3 step 6, trials T02 and T03):
  - coefficients="averaged": each day's prediction is the mean of the predictions of every monthly fit made so far,
    each with its own scaler, penalty and pooling. The validation that picks each fit is unchanged.
  - half_life_days=h: recency weighting. Before each lived day's rows enter the sums, the sums are multiplied by
    0.5 ** (1 / h), so a lived day's weight halves every h lived days. The rows held out for validation are taken
    out at their current weights. Validation scores the predictions as before, unweighted.
- freeze() gives a frozen twin (PLAN 5.3, 9.9; M3 step 4): a copy of the agent's state with learning off. It keeps
  picking each year, updating its news memory and trading, but never refits, so it decides with the fit it had.

`fits` records each refit's decision time and the latest visible_at of its training labels, for the embargo test.
"""
import math

import numpy as np
import pandas as pd

from world.view import View  # noqa: F401 (the one import an agent may make from this project)

from .reversal import ReversalAgent

NY = "America/New_York"
PRICE = ["r1", "r5", "r20", "r60", "vol20", "dvol_ratio"]
POOLINGS = ("last", "avg")
PENALTIES = tuple(10.0 ** k for k in range(-2, 5))
HALF_LIFE = 5
LOOKBACK = pd.Timedelta(days=200)
SETTLE = 10  # sessions a day's rows wait for their labels
MIN_TRAIN_DAYS = 20
KEY = ["entity_id", "share_class"]


def _ic(pred, y, day_index):
    """Mean over days of the Spearman correlation of pred and y (days with at least 3 rows and some spread)."""
    df = pd.DataFrame({"d": day_index, "p": pred, "y": y})
    out = []
    for _, g in df.groupby("d", sort=True):
        if len(g) < 3:
            continue
        a, b = g.p.rank().to_numpy(), g.y.rank().to_numpy()
        if a.std() == 0 or b.std() == 0:
            continue
        out.append(float(np.corrcoef(a, b)[0, 1]))
    return float(np.mean(out)) if out else -np.inf


class Sums:
    """Running sums of one pooling's rows: n, sum of x, x'x, sum of y, x'y (float64)."""

    def __init__(self, k):
        self.n, self.sx, self.sxx = 0, np.zeros(k), np.zeros((k, k))
        self.sy, self.sxy = 0.0, np.zeros(k)

    def add(self, X, y, sign=1.0, w=None):
        """Adds the rows (or takes them out, with sign -1), each with weight w (1 when w is None)."""
        if w is None:
            self.n += sign * len(y)
            self.sx += sign * X.sum(axis=0)
            self.sxx += sign * (X.T @ X)
            self.sy += sign * y.sum()
            self.sxy += sign * (X.T @ y)
            return
        w = np.asarray(w, dtype=np.float64)
        self.n += sign * float(w.sum())
        self.sx += sign * (w @ X)
        self.sxx += sign * (X.T @ (X * w[:, None]))
        self.sy += sign * float(w @ y)
        self.sxy += sign * (X.T @ (w * y))

    def decay(self, f):
        """Multiplies every row's weight by f."""
        self.n, self.sy = self.n * f, self.sy * f
        self.sx, self.sxx, self.sxy = self.sx * f, self.sxx * f, self.sxy * f

    def minus(self, X, y, w=None):
        out = Sums(len(self.sx))
        out.n, out.sx, out.sxx, out.sy, out.sxy = self.n, self.sx.copy(), self.sxx.copy(), self.sy, self.sxy.copy()
        out.add(X, y, -1.0, w)
        return out

    def scaled(self):
        """(mean, std, Z'Z, Z'(y - mean y)) of the standardized features, from the sums alone."""
        n = self.n
        mean = self.sx / n
        var = np.diag(self.sxx) / n - mean ** 2
        std = np.sqrt(np.clip(var, 0.0, None))
        std[std < 1e-12] = 1.0
        cxx = self.sxx - n * np.outer(mean, mean)
        cxy = self.sxy - mean * self.sy
        return mean, std, cxx / np.outer(std, std), cxy / std


def _solve(zz, zy, penalties):
    """Ridge coefficients for each penalty from one eigendecomposition of Z'Z."""
    w, q = np.linalg.eigh(zz)
    qy = q.T @ zy
    return {lam: q @ (qy / (np.clip(w, 0.0, None) + lam)) for lam in penalties}


class TrackA:
    def __init__(self, n_picks=50, n_side=10, book="long_short", hold=1, band=None, news=True,
                 first_pick="2016-04-01", trade_from="2017-01-01", fit_after_months=6, min_val_months=3,
                 val_share=0.2, full_val_years=5, recent_val_months=12, penalties=PENALTIES, poolings=POOLINGS,
                 coefficients="last", half_life_days=None):
        if book not in ("long_short", "long_only"):
            raise ValueError("book is long_short or long_only")
        if coefficients not in ("last", "averaged"):
            raise ValueError("coefficients is last or averaged")
        if half_life_days is not None and not half_life_days > 0:
            raise ValueError("half_life_days is None or above 0")
        self.coefficients, self.half_life_days = coefficients, half_life_days
        self.n_picks, self.n_side, self.book, self.hold, self.band, self.news = n_picks, n_side, book, hold, band, news
        self.first_pick, self.trade_from = pd.Timestamp(first_pick), pd.Timestamp(trade_from)
        self.fit_after_months, self.min_val_months, self.val_share = fit_after_months, min_val_months, val_share
        self.full_val_years, self.recent_val_months = full_val_years, recent_val_months
        self.penalties = tuple(sorted(penalties))
        self.poolings = tuple(poolings) if news else ("none",)
        self.params = {"n_picks": n_picks, "n_side": n_side, "book": book, "hold": hold, "band": band, "news": news,
                       "first_pick": first_pick, "trade_from": trade_from, "fit_after_months": fit_after_months,
                       "min_val_months": min_val_months, "val_share": val_share, "full_val_years": full_val_years,
                       "recent_val_months": recent_val_months, "penalties": list(self.penalties),
                       "poolings": list(self.poolings), "coefficients": coefficients,
                       "half_life_days": half_life_days}
        self.picks, self.pick_year, self.month = [], None, None
        self.first_day, self.last_t, self.dim = None, None, None
        self.memory = {}  # entity_id -> [sum of weighted last vectors, of avg vectors, sum of weights]
        self.pending = []  # day blocks waiting for their labels: (date, keys, {pooling: X})
        self.recent = []  # labelled day blocks kept for validation: (date, y, {pooling: X})
        self.lived_days = 0
        self.sums = None
        self.latest_label = None
        self.trimmed_latest = None  # the latest label among days trimmed from recent; they stay in the sums
        self.fit = None  # {"pooling", "penalty", "mean", "std", "beta"}
        self.past = []  # every fit made so far, for coefficients="averaged"
        self.fits = []
        self.positions, self.since_trade = {}, None
        self.learning = True
        self._today_index = None

    # The stock list (the toy agent's rule)
    def pick(self, v):
        return ReversalAgent.pick(self, v)

    # Price features
    def price_features(self, v, picks):
        b = v.bars
        b = b[(b.date < v.today) & (b.date >= v.today - LOOKBACK)]
        keys = pd.Series(list(zip(b.entity_id.astype(str), b.share_class.astype(str))), index=b.index)
        b = b[keys.isin(set(picks))]
        rows = {}
        for (e, c), g in b.groupby([b.entity_id.astype(str), b.share_class.astype(str)], sort=True):
            g = g.sort_values("date")
            r = np.log1p(g.ret.to_numpy(dtype=float))
            r = r[~np.isnan(r)]
            dv = (g.close * g.volume).to_numpy(dtype=float)
            dv = np.where(g.incomplete.astype(bool).to_numpy(), np.nan, dv)
            f = {f"r{n}": (r[-n:].sum() if len(r) else np.nan) for n in (1, 5, 20, 60)}
            last20 = r[-20:]
            f["vol20"] = last20.std() if len(last20) > 1 else np.nan
            d5, d60 = np.nanmean(dv[-5:]) if np.isfinite(dv[-5:]).any() else np.nan, \
                np.nanmean(dv[-60:]) if np.isfinite(dv[-60:]).any() else np.nan
            f["dvol_ratio"] = math.log(d5 / d60) if d5 > 0 and d60 > 0 else np.nan
            rows[(e, c)] = [f[k] for k in PRICE]
        return np.array([rows.get(p, [np.nan] * len(PRICE)) for p in picks], dtype=float)

    # News: which (story, company) pairs are in the view, and when each became available
    def _pairs(self, v):
        e = v.embeddings
        rows = e.rows[["story_id", "visible_at"]].assign(i=np.arange(len(e.rows)))
        se = v.story_entities[["story_id", "entity_id", "visible_at"]]
        se = se[se.story_id.isin(set(rows.story_id))]
        p = rows.merge(se, on="story_id", suffixes=("_e", "_l"))
        p["avail"] = p[["visible_at_e", "visible_at_l"]].max(axis=1)
        p["entity_id"] = p.entity_id.astype(str)
        p = p.sort_values(["avail", "story_id", "entity_id"], ignore_index=True)
        return p.drop_duplicates(["story_id", "entity_id"], ignore_index=True)  # one pair each (judge N6)

    def _session_index(self, v, times):
        """For each time, the index in v.sessions of the first session whose 9:00 decision is at or after it."""
        nine = pd.DatetimeIndex(v.sessions).tz_localize(NY) + pd.Timedelta(hours=9)
        return np.searchsorted(nine.tz_convert("UTC").asi8, pd.DatetimeIndex(times).tz_convert("UTC").asi8,
                               side="left")

    def update_news(self, v):
        """Move the memory to today, add the pairs new since the last decision, and return them (pairs, last, avg)."""
        e = v.embeddings
        if self.dim is None:
            self.dim = e.last.shape[1] if e.last.ndim == 2 else 0
        decay = 0.5 ** (1.0 / HALF_LIFE)
        today = len(v.sessions) - 1
        p = self._pairs(v)
        if self.last_t is None:
            new = p[p.avail > self._previous_nine(v)]
            old = p  # every pair in the view starts the memory, weighted by its age
        else:
            new = p[p.avail > self.last_t]
            old = new
            steps = today - self._today_index
            for m in self.memory.values():
                m[0] *= decay ** steps
                m[1] *= decay ** steps
                m[2] *= decay ** steps
        if len(old):
            age = np.maximum(today - self._session_index(v, old.avail), 0)  # judge N5
            w = decay ** age.astype(float)
            idx = old.i.to_numpy()
            last = e.last[idx].astype(np.float64) * w[:, None]
            avg = e.avg[idx].astype(np.float64) * w[:, None]
            for ent, pos in old.groupby("entity_id", sort=True).indices.items():
                m = self.memory.setdefault(ent, [np.zeros(self.dim), np.zeros(self.dim), 0.0])
                m[0] += last[pos].sum(axis=0)
                m[1] += avg[pos].sum(axis=0)
                m[2] += float(w[pos].sum())
        self._today_index = today
        return new

    def _previous_nine(self, v):
        """The decision time of the session before today (the first decision's "since the last decision")."""
        if len(v.sessions) < 2:
            return v.t - pd.Timedelta(days=1)
        return (pd.Timestamp(v.sessions[-2]).tz_localize(NY) + pd.Timedelta(hours=9)).tz_convert("UTC")

    def news_features(self, v, picks, new):
        """{pooling: array (picks x (2 + 2 * dim))}: news_count, news_none, news_new, news_memory."""
        e, d = v.embeddings, self.dim
        out = {}
        groups = new.groupby("entity_id", sort=True).indices
        for k, pool in enumerate(POOLINGS):
            vec = e.last if pool == "last" else e.avg
            rows = []
            for ent, _ in picks:
                pos = groups.get(ent)
                if pos is None:
                    count, mean_new = 0, np.zeros(d)
                else:
                    count = len(pos)
                    mean_new = vec[new.i.to_numpy()[pos]].astype(np.float64).mean(axis=0)
                m = self.memory.get(ent)
                mem = m[k] / m[2] if m is not None and m[2] > 0 else np.zeros(d)
                rows.append(np.concatenate([[float(count), float(count == 0)], mean_new, mem]))
            out[pool] = np.array(rows, dtype=float).reshape(len(picks), 2 + 2 * d)
        return out

    def features(self, v, picks, new):
        """{pooling: X} for the picks, each row rounded to float32 once, so stored and summed rows agree."""
        price = self.price_features(v, picks)
        price = np.nan_to_num(price)  # a missing value is 0, in the sums and in scoring (judge S2)
        if not self.news:
            return {"none": price.astype(np.float32).astype(np.float64)}
        news = self.news_features(v, picks, new)
        return {pool: np.hstack([price, news[pool]]).astype(np.float32).astype(np.float64) for pool in POOLINGS}

    # Learning
    def settle(self, v):
        """Move day blocks whose labels are in the view into the sums and the kept rows."""
        lab = v.labels[["entity_id", "share_class", "date", "label", "visible_at"]].astype(
            {"entity_id": str, "share_class": str})
        today = len(v.sessions) - 1
        index = {pd.Timestamp(s): i for i, s in enumerate(v.sessions)}
        still = []
        for date, keys, X in self.pending:
            got = keys.assign(date=date).merge(lab, on=["entity_id", "share_class", "date"], how="left")
            have = got.label.notna().to_numpy()
            if not have.all() and today - index.get(date, today) < SETTLE:
                still.append((date, keys, X))
                continue
            if have.sum() == 0:
                continue
            y = np.log1p(got.label.to_numpy(dtype=float)[have])
            y = y - y.mean()
            Xs = {pool: x[have] for pool, x in X.items()}
            if self.sums is None:
                self.sums = {pool: Sums(x.shape[1]) for pool, x in Xs.items()}
            if self.half_life_days is not None:
                for s in self.sums.values():
                    s.decay(0.5 ** (1.0 / self.half_life_days))  # every earlier lived day is a day older
            for pool, x in Xs.items():
                self.sums[pool].add(x, y)
            latest = got.visible_at[have].max()
            self.latest_label = latest if self.latest_label is None else max(self.latest_label, latest)
            self.recent.append((date, y, {pool: x.astype(np.float32) for pool, x in Xs.items()}, latest,
                                self.lived_days))  # the day's lived index, for its weight; and the rows are exact:
            # the rows were rounded to float32 when they were made, so this halves their memory and changes nothing
            self.lived_days += 1
        self.pending = still
        self.recent.sort(key=lambda r: r[0])

    def _val_days(self, today):
        """How many of the kept labelled days form the validation part."""
        dates = [r[0] for r in self.recent]
        if today < self.first_day + pd.DateOffset(years=self.full_val_years):
            floor = sum(d > dates[-1] - pd.DateOffset(months=self.min_val_months) for d in dates)
            return max(math.ceil(self.val_share * self.lived_days), floor)
        return sum(d > dates[-1] - pd.DateOffset(months=self.recent_val_months) for d in dates)

    def refit(self, v):
        self.settle(v)
        if not self.recent:
            return
        n_val = min(self._val_days(v.today), len(self.recent) - 1)
        gap, val, first_val_t, train_latest = self.split(n_val)
        if self.lived_days - n_val - len(gap) < MIN_TRAIN_DAYS:
            return
        held = gap + val
        best = None
        for pool in self.poolings:
            Xh = np.vstack([r[2][pool] for r in held]).astype(np.float64)
            yh = np.concatenate([r[1] for r in held])
            w = self._weights(held)
            train = self.sums[pool].minus(Xh, yh) if w is None else self.sums[pool].minus(Xh, yh, w)
            mean, std, zz, zy = train.scaled()
            Xv = np.vstack([r[2][pool] for r in val]).astype(np.float64)
            Zv = (Xv - mean) / std
            yv = np.concatenate([r[1] for r in val])
            day = np.concatenate([[i] * len(r[1]) for i, r in enumerate(val)])
            for lam, beta in sorted(_solve(zz, zy, self.penalties).items(), reverse=True):
                score = _ic(Zv @ beta, yv, day)
                if best is None or score > best[0]:
                    best = (score, pool, lam)
        _, pool, lam = best
        mean, std, zz, zy = self.sums[pool].scaled()
        beta = _solve(zz, zy, (lam,))[lam]
        self.fit = {"pooling": pool, "penalty": lam, "mean": mean, "std": std, "beta": beta}
        if self.coefficients == "averaged":
            self.past.append(self.fit)
        self.fits.append({"t": v.t, "latest_label": self.latest_label, "rows": int(self.sums[pool].n),
                          "pooling": pool, "penalty": lam, "val_days": n_val, "gap_days": len(gap),
                          "held_rows": int(sum(len(r[1]) for r in held)), "first_val_t": first_val_t,
                          "train_latest_label": train_latest, "val_ic": best[0]})
        keep = n_val + 64  # next month's validation part, its gap and any late labels need at most this many
        dropped = [r[3] for r in self.recent[:-keep]]
        if dropped:  # the sums keep these days, so a later split must still see their latest label (review W3-3)
            self.trimmed_latest = max(dropped + ([self.trimmed_latest] if self.trimmed_latest is not None else []))
        self.recent = self.recent[-keep:]

    def freeze(self):
        """A frozen twin: the same rules and the state lived so far, with learning off. Built field by field (an agent
        may not import copy), so nothing in it is shared with this agent."""
        twin = TrackA(**{k: v for k, v in self.params.items()})
        twin.picks, twin.fits = list(self.picks), list(self.fits)
        twin.pick_year, twin.month, twin.first_day = self.pick_year, self.month, self.first_day
        twin.last_t, twin.dim, twin._today_index = self.last_t, self.dim, self._today_index
        twin.memory = {e: [m[0].copy(), m[1].copy(), m[2]] for e, m in self.memory.items()}
        twin.lived_days, twin.latest_label = self.lived_days, self.latest_label
        twin.trimmed_latest = self.trimmed_latest
        twin.fit = None if self.fit is None else {k: (x.copy() if isinstance(x, np.ndarray) else x)
                                                  for k, x in self.fit.items()}
        twin.past = [{k: (x.copy() if isinstance(x, np.ndarray) else x) for k, x in f.items()} for f in self.past]
        twin.positions, twin.since_trade = dict(self.positions), self.since_trade
        twin.learning = False
        return twin

    def split(self, n_val):
        """(gap, val, first_val_t, train_latest): the validation part is the last n_val kept days; the gap is the day
        before it and every earlier kept day whose latest label showed at or after the first validation decision
        (9:00 New York on its date). train_latest is the latest label time among every training day: the kept ones,
        and the days already trimmed from recent, which stay in the sums and so cannot be held out. If any of those
        labels showed at or after the first validation decision, the split raises instead of fitting on it (review
        W3-3; in the steady state it cannot happen, since a trimmed day is about 80 lived days before validation)."""
        val, rest = self.recent[-n_val:], self.recent[:-n_val]
        first_val_t = (pd.Timestamp(val[0][0]).tz_localize(NY) + pd.Timedelta(hours=9)).tz_convert("UTC")
        out = [i == len(rest) - 1 or r[3] >= first_val_t for i, r in enumerate(rest)]
        gap = [r for r, o in zip(rest, out) if o]
        train = [r for r, o in zip(rest, out) if not o]
        latest = [r[3] for r in train] + ([self.trimmed_latest] if self.trimmed_latest is not None else [])
        train_latest = max(latest, default=None)
        if train_latest is not None and train_latest >= first_val_t:
            raise RuntimeError(f"label embargo: a training label showed at {train_latest}, not before the first "
                               f"validation decision {first_val_t}")
        return gap, val, first_val_t, train_latest

    def _weights(self, days):
        """Each kept row's current weight in the sums, or None without recency weighting."""
        if self.half_life_days is None:
            return None
        f = 0.5 ** (1.0 / self.half_life_days)
        return np.concatenate([np.full(len(r[1]), f ** (self.lived_days - 1 - r[4])) for r in days])

    def score(self, X):
        fits = self.past if self.coefficients == "averaged" else [self.fit]
        return np.mean([((X[f["pooling"]] - f["mean"]) / f["std"]) @ f["beta"] for f in fits], axis=0)

    # Policy
    def targets(self, keys, pred):
        order = sorted(range(len(keys)), key=lambda i: (-pred[i], keys[i]))
        n = min(self.n_side, len(keys) // 2 if self.book == "long_short" else len(keys))
        rank = {keys[i]: r for r, i in enumerate(order)}
        top = [keys[i] for i in order[:n]]
        bottom = [keys[i] for i in order[len(order) - n:]] if self.book == "long_short" else []
        if self.band and self.positions:
            band = min(self.band, len(keys) // 2 if self.book == "long_short" else len(keys))
            keep_long = [k for k in keys if self.positions.get(k, 0) > 0 and rank[k] < band]
            keep_short = [k for k in keys if self.positions.get(k, 0) < 0 and rank[k] >= len(keys) - band]
            top = sorted(keep_long, key=rank.get)[:n]
            top += [k for k in (keys[i] for i in order) if k not in top and k not in keep_short][: n - len(top)]
            if self.book == "long_short":
                bottom = sorted(keep_short, key=rank.get, reverse=True)[:n]
                bottom += [k for k in (keys[i] for i in reversed(order)) if k not in bottom and k not in top][
                    : n - len(bottom)]
        pos = {k: 0.0 for k in keys}
        for k in top:
            pos[k] = 1.0 / self.n_side
        for k in bottom:
            pos[k] = -1.0 / self.n_side
        return pos

    def decide(self, v):
        if self.news:
            new = self.update_news(v)
        else:
            new = None
        self.last_t = v.t
        if v.today < self.first_pick:
            return None
        if self.first_day is None:
            self.first_day = v.today
        if self.pick_year != v.today.year:
            self.picks, self.pick_year = self.pick(v), v.today.year
        if self.month != (v.today.year, v.today.month):
            self.month = (v.today.year, v.today.month)
            if self.learning and v.today >= self.first_day + pd.DateOffset(months=self.fit_after_months):
                self.refit(v)
        live = [p for p in self.picks if p[0] in v.members]
        if not live:
            return None
        X = self.features(v, live, new)
        if self.learning:
            self.pending.append((v.today, pd.DataFrame(live, columns=KEY), X))
        if self.fit is None:
            return None
        pred = self.score(X)
        trade = self.since_trade is None or self.since_trade + 1 >= self.hold
        if trade:
            pos, self.since_trade = self.targets(live, pred), 0
        else:
            pos, self.since_trade = {k: self.positions.get(k, 0.0) for k in live}, self.since_trade + 1
        self.positions = pos
        if v.today < self.trade_from:  # watch-only: no book carries into the first trading day (judge N3)
            pos, self.positions, self.since_trade = {k: 0.0 for k in live}, {}, None
        out = pd.DataFrame({"entity_id": [k[0] for k in live], "share_class": [k[1] for k in live],
                            "prediction": pred.astype(float), "position": [pos[k] for k in live]})
        return out.sort_values(["prediction", "entity_id", "share_class"], ascending=[False, True, True],
                               ignore_index=True)
