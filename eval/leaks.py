"""The non-interference check (PLAN 5.1 and 9.11): change every record not yet visible at t, run again, and compare
every decision up to t.

`perturb` takes the store's tables and returns copies in which every record visible only after t (world/world.py:
available after t, or held back until a later join) is scrambled, shifted later, or deleted. Records visible by t
are untouched, and a changed record that would become visible by t is dropped, so the view at t is the same in both.
A leak-free agent makes identical decisions on both, up to and including the decision at t.
- scramble: late values are swapped among the late records, numbers are scaled at random, and the signs of returns
  and labels are flipped at random. A swap alone keeps the mean, spread and signs of the late data, so it would miss
  a scaler fitted on all of it, or a count of later gains.
- shift: late records move 7 days later. It catches a leak through dates; their values stay.
- delete: late records go, and joins after t never happen. It catches a leak through counts.
A planted leak must be caught by at least one of the three.

`compare` lists any difference: a missing or extra decision row, a different position, or a prediction more than
1e-12 apart.
"""
import numpy as np
import pandas as pd

from world import rules
from world.clock import Clock
from world.world import World, spells, visible_at

HOW = ("scramble", "shift", "delete")
SHIFT = pd.Timedelta(days=7)
SIGNED = ("ret", "label")


def late_rows(tables, t):
    """Per table, a boolean mask of the records not visible at t."""
    ns = pd.Timestamp(t).as_unit("ns").value
    sp = spells(tables["membership"])
    m = tables["membership"]
    far = pd.Timestamp("2262-01-01")
    return {
        "bars": visible_at("bars", tables["bars"], sp) > ns,
        "labels": visible_at("labels", tables["labels"], sp) > ns,
        "opens": (rules.official_open(tables["opens"].date) > pd.Timestamp(t)).to_numpy(),
        "stories": visible_at("stories", tables["stories"], sp) > ns,
        "story_entities": visible_at("story_entities", tables["story_entities"], sp, tables["stories"]) > ns,
        "joins": (rules.membership(m.member_from) > pd.Timestamp(t)).to_numpy(),
        "leaves": (m.member_to.notna() & (rules.membership(m.member_to.fillna(far)) > pd.Timestamp(t))).to_numpy(),
    }


def perturb(tables, t, how, seed=0):
    """Copies of `tables` (bars, labels, opens, stories, story_entities, membership) with every record not visible
    at t scrambled, shifted later or deleted."""
    if how not in HOW:
        raise ValueError(how)
    rng = np.random.default_rng(seed)
    late = late_rows(tables, t)
    out = {k: v.copy() for k, v in tables.items()}

    def scramble(df, mask, cols):
        idx = np.flatnonzero(mask)
        if len(idx) > 1:
            for c in cols:
                values = df[c].to_numpy(copy=True)
                values[idx] = values[rng.permutation(idx)]
                if np.issubdtype(values.dtype, np.number) and values.dtype != bool:
                    values = values.astype(float)
                    values[idx] *= rng.uniform(0.5, 1.5, len(idx))
                    if c in SIGNED:
                        values[idx] *= rng.choice([-1.0, 1.0], len(idx))
                df[c] = values
        return df

    m = out["membership"]
    if how == "delete":
        for k in ("bars", "labels", "opens", "stories", "story_entities"):
            out[k] = out[k][~late[k]].reset_index(drop=True)
        m.loc[late["leaves"], "member_to"] = pd.NaT
        out["membership"] = m[~late["joins"]].reset_index(drop=True)
    elif how == "shift":
        out["bars"].loc[late["bars"], "date"] += SHIFT
        out["labels"].loc[late["labels"], ["date", "end"]] += SHIFT
        out["opens"].loc[late["opens"], "date"] += SHIFT
        out["stories"].loc[late["stories"], ["created_at", "updated_at"]] += SHIFT
        m.loc[late["joins"], "member_from"] += SHIFT
        m.loc[late["leaves"], "member_to"] += SHIFT
    else:
        numeric = [c for c in ("open", "high", "low", "close", "volume", "trades", "vwap", "ret") if c in out["bars"]]
        scramble(out["bars"], late["bars"], numeric)
        scramble(out["labels"], late["labels"], ["label"])
        scramble(out["opens"], late["opens"], ["open"])
        scramble(out["stories"], late["stories"], ["headline", "symbols"])
        scramble(out["story_entities"], late["story_entities"], ["entity_id"])
        m.loc[late["joins"], "member_from"] += SHIFT
        m.loc[late["leaves"], "member_to"] += SHIFT
    if how != "delete":
        # A changed record must stay hidden at t. A swapped company id, or a date moved into a membership window, can
        # bring a record that was hidden (its company hadn't joined, or it lay outside every window) into view.
        ns = pd.Timestamp(t).as_unit("ns").value
        sp = spells(out["membership"])
        for k in ("bars", "labels", "story_entities"):
            shown = visible_at(k, out[k], sp, out["stories"]) <= ns
            out[k] = out[k][~(late[k] & shown)].reset_index(drop=True)
    return out


def decisions_until(tables, make_agent, first, last, clock=None, give_world=False):
    """Every decision from `first` to `last` of a fresh agent, from a World built on `tables`. The agent gets no
    World unless `give_world` (only a planted leak asks for it). Views refuse the sealed years."""
    world = World(**tables, clock=clock)
    agent = make_agent(world) if give_world else make_agent()
    rows = []
    for day in world.clock.between(first, last):
        d = agent.decide(world.view(world.clock.decision_time(day)))
        if d is not None and len(d):
            rows.append(d.assign(date=day))
    cols = ["date", "entity_id", "share_class", "prediction", "position"]
    out = pd.concat(rows, ignore_index=True)[cols] if rows else pd.DataFrame(columns=cols)
    return out.astype({"entity_id": str, "share_class": str}).sort_values(cols[:3], ignore_index=True)


def compare(a, b, tol=1e-12):
    """Differences between two runs' decisions: rows in one only, positions that differ, predictions beyond tol."""
    key = ["date", "entity_id", "share_class"]
    m = a.merge(b, on=key, how="outer", suffixes=("_a", "_b"), indicator=True)
    problems = []
    one_side = m[m["_merge"] != "both"]
    if len(one_side):
        problems.append(f"{len(one_side)} decision rows in only one run, first on {one_side.date.min()}")
    both = m[m["_merge"] == "both"]
    pos = both[both.position_a != both.position_b]
    if len(pos):
        problems.append(f"{len(pos)} positions differ, first on {pos.date.min()}")
    gap = (both.prediction_a - both.prediction_b).abs()
    far = both[(gap > tol) | (both.prediction_a.isna() != both.prediction_b.isna())]  # NaN against a number too
    if len(far):
        problems.append(f"{len(far)} predictions differ by more than {tol}, first on {far.date.min()}")
    return problems


def non_interference(tables, make_agent, first, last, how, seed=0, clock=None, give_world=False):
    """Run to the decision on session `last`, perturb every record not visible then, run again, compare."""
    t = (clock or Clock()).decision_time(last)
    a = decisions_until(tables, make_agent, first, last, clock, give_world)
    b = decisions_until(perturb(tables, t, how, seed), make_agent, first, last, clock, give_world)
    return compare(a, b)
