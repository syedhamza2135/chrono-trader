"""The simulator (PLAN 9.5 and 9.8) and the daily loop.

Each session k, at 9:00 New York time, the loop gives the agent `world.view(9:00 on k)` and nothing else. The agent
returns target positions as weights of equity. Then the simulator:
1. Marks each holding whose label ends at this session's open: its value grows by the label, the total return from
   its last official open to this one (data_pipeline/store.py). A holding without an official open today (a halt,
   or the NYSE's failed openings on 2023-01-24) keeps its value until its next one.
2. Sells, at its last traded close, a holding whose company stopped trading after an acquisition: PLAN's exit at
   the last available price. After a failure the label is -1 (data_pipeline/store.py), so the holding is worth
   nothing. Either way the label ends at that close, and the sale happens at the next session.
3. Trades every stock that has an official open today to its target, and charges costs on the traded value
   (5 bps per side, PLAN 9.8). A stock without an official open isn't traded: the simulator trades only at the
   listing exchange's opening auction print. A stock with an official open but no label from it (the next open is
   across a day without a return, such as a rejoining company's gap) can't be valued after today, so it is sold
   at today's open and not bought; `forced_sales` counts these. On the data's last day nothing is forced.

Equity is cash plus the holdings' values. Weights are values over equity, after trading.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import seal

COST_BPS = 5.0
LISTING = ["entity_id", "share_class"]


@dataclass
class Run:
    decisions: pd.DataFrame  # date, entity_id, share_class, prediction, position (the agent's target weight)
    equity: pd.DataFrame  # date, equity (after costs), cost, gross (sum of absolute weights), traded
    stats: dict  # forced_sales, unmarked


class Simulator:
    def __init__(self, world, cost_bps=COST_BPS):
        self.cost = cost_bps / 1e4
        o = world.opens.dropna(subset=["open"])
        self.opens = {d: set(zip(g.entity_id.astype(str), g.share_class.astype(str)))
                      for d, g in o.groupby("date", observed=True)}
        lab = world.labels.df
        self.labels = {k: g.sort_values("date") for k, g in lab.groupby([lab.entity_id.astype(str),
                                                                          lab.share_class.astype(str)], observed=True)}
        self.cash, self.values, self.pending = 1.0, {}, {}
        self.unmarked = 0  # holdings marked at an official open with no label to carry them there
        self.forced_sales = 0  # holdings sold because no label runs from today's open
        self.data_end = pd.Timestamp(lab.end.max()) if len(lab) else None
        self.rows = []

    def _label_from(self, key, day):
        g = self.labels.get(key)
        if g is None:
            return None
        i = g.date.searchsorted(day)
        if i < len(g) and g.date.iat[i] == day:
            return g.end.iat[i], float(g.label.iat[i]), bool(g.at_close.iat[i])
        return None

    def step(self, day, targets):
        day = pd.Timestamp(day)
        tradable = self.opens.get(day, set())
        cost = 0.0
        # 1 and 2: labels that end by today.
        for key in list(self.values):
            p = self.pending.get(key)
            if p is None:
                if key in tradable:
                    self.unmarked += 1
                continue
            end, growth, at_close = p
            if (end == day and not at_close) or (at_close and end < day):
                self.values[key] *= 1 + growth
                del self.pending[key]
                if at_close:
                    v = self.values.pop(key)
                    cost += abs(v) * self.cost
                    self.cash += v
        equity = self.cash + sum(self.values.values())
        # 3: trade to the targets where there is an official open today.
        want = {} if targets is None or targets.empty else {
            (str(e), str(c)): float(w) for e, c, w in zip(targets.entity_id, targets.share_class, targets.position)}
        if self.data_end is None or day < self.data_end:
            for key in sorted((set(want) | set(self.values)) & tradable):
                if self._label_from(key, day) is None and (want.get(key, 0.0) or key in self.values):
                    self.forced_sales += key in self.values
                    want[key] = 0.0
        traded = 0.0
        for key in sorted(set(want) | set(self.values)):
            if key not in tradable:
                continue
            target = want.get(key, 0.0) * equity
            change = target - self.values.get(key, 0.0)
            if abs(change) > 0:
                traded += abs(change)
                cost += abs(change) * self.cost
                self.cash -= change
                if target == 0.0:
                    self.values.pop(key, None)
                    self.pending.pop(key, None)
                else:
                    self.values[key] = target
        self.cash -= cost
        for key in self.values:
            if key in tradable:
                p = self._label_from(key, day)
                if p is None:
                    self.pending.pop(key, None)
                else:
                    self.pending[key] = p
        equity = self.cash + sum(self.values.values())
        gross = sum(abs(v) for v in self.values.values()) / equity if equity else np.nan
        self.rows.append({"date": day, "equity": equity, "cost": cost, "gross": gross, "traded": traded})


def run(world, agent, first, last, cost_bps=COST_BPS, settings=None):
    """The daily loop from the session `first` to the session `last`: decide at 9:00, fill at the open. Dates in the
    sealed years need a matching seal (sim/seal.py) on the run's whole settings: the caller's, the costs, and the
    agent's class and parameters."""
    full = {**(settings or {}), "cost_bps": cost_bps, "agent": type(agent).__name__,
            "agent_params": getattr(agent, "params", None)}
    seal.check(first, last, full if settings is not None else None)
    if pd.Timestamp(last) >= seal.sealed_start():
        world.allow_sealed = True  # the seal holds; views may now open the sealed years
    sim = Simulator(world, cost_bps)
    decisions = []
    for day in world.clock.between(first, last):
        targets = agent.decide(world.view(world.clock.decision_time(day)))
        sim.step(day, targets)
        if targets is not None and len(targets):
            decisions.append(targets.assign(date=day))
    cols = ["date", "entity_id", "share_class", "prediction", "position"]
    d = pd.concat(decisions, ignore_index=True)[cols] if decisions else pd.DataFrame(columns=cols)
    return Run(d, pd.DataFrame(sim.rows), {"forced_sales": sim.forced_sales, "unmarked": sim.unmarked})
