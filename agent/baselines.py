"""The matched baselines (PLAN 5.3 and 9.9; M3 step 4). Each trades the same 50 picks as Track A (the toy agent's
rule, agent/reversal.py), through the same loop, from the same first pick, with every position 0 before trade_from
(2016 is watch-only, PLAN 5.5). They learn nothing.

- RandomRanking: long-short on a random score per stock and day, drawn from a generator seeded by (seed, the day's
  date), in pick order, so a seed always gives the same ranking.
- Momentum (12-1): long-short on the log return from 252 bars ago to 21 bars ago: the sum of log(1 + ret) over the
  stock's bars [-252:-21] before today, within 400 calendar days. Fewer bars give the sum of those there are.
- Reversal (5-day): long-short on minus r5, the sum of log(1 + ret) over the last 5 bars.
- EqualWeight: long-only, every live pick at 1 / n, every day.
SPY buy-and-hold is not an agent, since SPY is never in a view: eval.benchmarks.spy_buy_and_hold computes it.

A missing score counts as 0. Long-short books hold the top n_side at plus 1 / n_side and the bottom n_side at minus
1 / n_side, ties broken by company id.

With hold > 1 a baseline trades every hold sessions and keeps its positions between, as Track A does, so it trades
on the same days as a Track A trial that holds as long (the owner, 23 Nov). It still scores every day. Its turnover
is not matched: the band is Track A's alone, so a banded trial trades less (on the dev years T09 turns over 0.39 of
equity a day, reversal and the random seeds 0.64 to 0.67, momentum 0.12). Compare the books before costs (M3 review
S3-1, 23 Nov). Equal weight is
run with hold 1, rebalanced daily (the owner, 23 Nov, step 4).
"""
import numpy as np
import pandas as pd

from world.view import View  # noqa: F401 (the one import an agent may make from this project)

from .reversal import ReversalAgent

LOOKBACK = pd.Timedelta(days=400)


class Baseline:
    rule = ""

    def __init__(self, n_picks=50, n_side=10, first_pick="2016-04-01", trade_from="2017-01-01", hold=1):
        if not (isinstance(hold, int) and hold >= 1):
            raise ValueError("hold is a whole number of sessions, at least 1")
        self.n_picks, self.n_side, self.hold = n_picks, n_side, hold
        self.first_pick, self.trade_from = pd.Timestamp(first_pick), pd.Timestamp(trade_from)
        self.params = {"rule": self.rule, "n_picks": n_picks, "n_side": n_side, "first_pick": first_pick,
                       "trade_from": trade_from, "hold": hold}
        self.held, self.since_trade = {}, None
        self.picks, self.pick_year = [], None
        self.fits = []  # it never fits; the embargo check finds nothing to check

    def pick(self, v):
        return ReversalAgent.pick(self, v)

    def returns(self, v, picks):
        """{(entity, class): log returns of its bars before today, oldest first}."""
        b = v.bars
        b = b[(b.date < v.today) & (b.date >= v.today - LOOKBACK)]
        keys = pd.Series(list(zip(b.entity_id.astype(str), b.share_class.astype(str))), index=b.index)
        b = b[keys.isin(set(picks))]
        out = {}
        for (e, c), g in b.groupby([b.entity_id.astype(str), b.share_class.astype(str)], sort=True):
            r = np.log1p(g.sort_values("date").ret.to_numpy(dtype=float))
            out[(e, c)] = r[~np.isnan(r)]
        return out

    def scores(self, v, picks):
        raise NotImplementedError

    def positions(self, picks, score):
        order = sorted(range(len(picks)), key=lambda i: (-score[i], picks[i]))
        n = min(self.n_side, len(picks) // 2)
        pos = np.zeros(len(picks))
        pos[order[:n]] = 1.0 / self.n_side
        pos[order[len(order) - n:]] = -1.0 / self.n_side
        return pos

    def decide(self, v):
        if v.today < self.first_pick:
            return None
        if self.pick_year != v.today.year:
            self.picks, self.pick_year = self.pick(v), v.today.year
        live = [p for p in self.picks if p[0] in v.members]
        if not live:
            return None
        score = np.nan_to_num(np.asarray(self.scores(v, live), dtype=float))
        if v.today < self.trade_from:
            pos, self.held, self.since_trade = np.zeros(len(live)), {}, None
        elif self.since_trade is None or self.since_trade + 1 >= self.hold:
            pos, self.since_trade = self.positions(live, score), 0
            self.held = dict(zip(live, pos))
        else:
            pos, self.since_trade = np.array([self.held.get(k, 0.0) for k in live]), self.since_trade + 1
        out = pd.DataFrame({"entity_id": [k[0] for k in live], "share_class": [k[1] for k in live],
                            "prediction": score, "position": pos})
        return out.sort_values(["prediction", "entity_id", "share_class"], ascending=[False, True, True],
                               ignore_index=True)


class RandomRanking(Baseline):
    rule = "random"

    def __init__(self, seed, **kw):
        super().__init__(**kw)
        self.seed = seed
        self.params["seed"] = seed

    def scores(self, v, picks):
        return np.random.default_rng([self.seed, v.today.toordinal()]).random(len(picks))


class Momentum(Baseline):
    rule = "momentum_12_1"

    def scores(self, v, picks):
        r = self.returns(v, picks)
        return [r[p][-252:-21].sum() if p in r and len(r[p]) > 21 else np.nan for p in picks]


class Reversal(Baseline):
    rule = "reversal_5"

    def scores(self, v, picks):
        r = self.returns(v, picks)
        return [-r[p][-5:].sum() if p in r and len(r[p]) else np.nan for p in picks]


class EqualWeight(Baseline):
    rule = "equal_weight"

    def scores(self, v, picks):
        return np.zeros(len(picks))

    def positions(self, picks, score):
        return np.full(len(picks), 1.0 / len(picks))
