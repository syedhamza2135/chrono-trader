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
        cost = traded = 0.0
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
                    traded += abs(v)  # the exit sale at the last close (review of 21 Nov, L-S1)
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
    agent's class and parameters, and the World's embedding window (M3 decision 1). A World with a vintage_offset
    (the older-vintage rerun, M3 step 7) is refused for any sealed date, seal or not."""
    full = {**(settings or {}), "cost_bps": cost_bps, "agent": type(agent).__name__,
            "agent_params": getattr(agent, "params", None),
            "embedding_window_days": getattr(world, "embedding_window_days", None)}
    _offset(world, last, full)
    seal.check(first, last, full if settings is not None else None)
    was_allowed = world.allow_sealed
    if pd.Timestamp(last) >= seal.sealed_start():
        world.allow_sealed = True  # the seal holds; views may now open the sealed years
    sim = Simulator(world, cost_bps)
    decisions = []
    try:
        for day in world.clock.between(first, last):
            targets = agent.decide(world.view(world.clock.decision_time(day)))
            sim.step(day, targets)
            if targets is not None and len(targets):
                decisions.append(targets.assign(date=day))
    finally:
        world.allow_sealed = was_allowed  # the seal covers this run only (review of 21 Nov, L-S4)
    cols = ["date", "entity_id", "share_class", "prediction", "position"]
    d = pd.concat(decisions, ignore_index=True)[cols] if decisions else pd.DataFrame(columns=cols)
    return Run(d, pd.DataFrame(sim.rows), {"forced_sales": sim.forced_sales, "unmarked": sim.unmarked})


def _offset(world, last, full):
    """Refuse a World with a vintage_offset for a run that reaches the sealed years, and record the offset in the
    settings (so in their hash) when it is not 0. With offset 0 the settings stay as they were, so older runs' hashes
    don't change."""
    off = getattr(world, "vintage_offset", 0)
    if off:
        if pd.Timestamp(last) >= seal.sealed_start():
            raise PermissionError("a World with a vintage_offset may not run into the sealed years")
        full["vintage_offset"] = off


def _fresh(base):
    """A simulator with base's read-only lookups (official opens, labels) and a new, empty book."""
    sim = Simulator.__new__(Simulator)
    sim.cost, sim.opens, sim.labels, sim.data_end = base.cost, base.opens, base.labels, base.data_end
    sim.cash, sim.values, sim.pending = 1.0, {}, {}
    sim.unmarked = sim.forced_sales = 0
    sim.rows = []
    return sim


def _own_view(v):
    """A view of the agent's own: shallow copies of the tables (pandas copies on write, so an agent that changes one
    changes only its own) and read-only vectors, so no agent can reach another's decisions through a shared view."""
    from world.view import View
    from world.world import Embeddings
    e = v.embeddings
    last, avg = e.last.view(), e.avg.view()
    last.flags.writeable = avg.flags.writeable = False
    return View(v.t, v.sessions.copy(), v.members, v.joined, v.bars.copy(deep=False), v.labels.copy(deep=False),
                v.stories.copy(deep=False), v.story_entities.copy(deep=False),
                Embeddings(e.rows.copy(deep=False), last, avg))


def run_many(world, agents, first, last, cost_bps=COST_BPS, settings=None, freeze=()):
    """The daily loop for several agents at once (M3 step 4): each session's view is built once and every agent
    decides on its own copy of it, each with its own simulator. `agents` maps names to agents, in a fixed order. For
    each name in `freeze`, at the first session of each new year a frozen twin (the agent's `freeze()`, learning off)
    joins as "<name>_frozen_<year just ended>" and trades from that session on. The seal covers every agent's
    settings. Returns {name: Run}, the twins included, and gives the same decisions as one `run` per agent."""
    agents = dict(agents)
    full = {**(settings or {}), "cost_bps": cost_bps, "embedding_window_days": getattr(world, "embedding_window_days",
                                                                                         None),
            "agents": {n: {"agent": type(a).__name__, "agent_params": getattr(a, "params", None)}
                       for n, a in agents.items()}, "freeze": list(freeze)}
    _offset(world, last, full)
    seal.check(first, last, full if settings is not None else None)
    was_allowed = world.allow_sealed
    if pd.Timestamp(last) >= seal.sealed_start():
        world.allow_sealed = True
    base = Simulator(world, cost_bps)
    sims = {n: _fresh(base) for n in agents}
    decisions = {n: [] for n in agents}
    year = None
    try:
        for day in world.clock.between(first, last):
            if year is not None and day.year != year:
                for n in freeze:
                    twin = f"{n}_frozen_{year}"
                    agents[twin], sims[twin], decisions[twin] = agents[n].freeze(), _fresh(base), []
            year = day.year
            v = world.view(world.clock.decision_time(day))
            for n, agent in agents.items():
                targets = agent.decide(_own_view(v))
                sims[n].step(day, targets)
                if targets is not None and len(targets):
                    decisions[n].append(targets.assign(date=day))
    finally:
        world.allow_sealed = was_allowed
    cols = ["date", "entity_id", "share_class", "prediction", "position"]
    out = {}
    for n in agents:
        d = pd.concat(decisions[n], ignore_index=True)[cols] if decisions[n] else pd.DataFrame(columns=cols)
        out[n] = Run(d, pd.DataFrame(sims[n].rows), {"forced_sales": sims[n].forced_sales,
                                                     "unmarked": sims[n].unmarked})
    return out


def replay(world, run, costs=(0.0, 5.0, 10.0, 20.0), base=None, settings=None):
    """{cost_bps: equity rows}: the run's own targets traded again through a fresh simulator at each cost, on the
    same sessions (PLAN 9.8's cost table, and every book "before costs" at 0). Costs change no decision, so this is
    the run at that cost, exactly; at the run's own cost it gives back its equity rows. No agent or view is used.
    Pass `base` (a Simulator on the same World) to reuse its lookups across runs. Sessions in the sealed years need
    the seal, as in `run`: pass the run's settings (review W3-4)."""
    days = pd.to_datetime(run.equity.date)
    if len(days):
        seal.check(days.min(), days.max(), settings)
    base = base or Simulator(world, 0.0)
    targets = {pd.Timestamp(d): g for d, g in run.decisions.groupby("date")}
    out = {}
    for c in costs:
        sim = _fresh(base)
        sim.cost = c / 1e4
        for day in days:
            sim.step(day, targets.get(pd.Timestamp(day)))
        out[c] = pd.DataFrame(sim.rows)
    return out
