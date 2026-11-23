"""The shuffled-news placebo (PLAN 5.3 and 9.9; M3 step 4): the same agent, with the news swapped between stocks
within each day.

A (story, company) pair reaches an agent at its availability: the later of the story's embedding and that link
showing in the view (agent/track_a.py). Pairs are grouped by the decision they first reach, that is the first
session whose 9:00 is at or after their availability. Within each group the companies are permuted at random, with a
generator seeded by (seed, that session's date), and the shuffled links are handed to the agent in a fresh View. A
story never moves to another day, its times never change, and only links that carry an embedding are touched.
A permutation reorders the group's companies, so each company keeps exactly as many links that day: the placebo
tests what the news says, not whether there is news (M3 review S3-4). A story with two links can be handed the same
company twice; the agent drops the copy (agent/track_a.py), so it sees slightly less news than the live agent, not
exactly the same amount (M3 review W3-7). The permutation is among every company with news in that group, not only
the agent's 50 picks.

Everything comes from the view at t. Today's group is always whole in today's view, and Track A uses only the pairs
new since its last decision, which form today's group, so it sees each pair shuffled once. A later view does not
always shuffle an older group the same way: when the 90-day window's edge cuts into a group, the shorter group gets
a different permutation (M3 review W3-2). That is not a leak, since every pair still comes from the view at t.
"""
import numpy as np
import pandas as pd

from world.view import View

NY = "America/New_York"


def shuffled_links(v, seed):
    """The view's story_entities with the companies of the embedded links permuted within each decision's group."""
    se = v.story_entities.reset_index(drop=True)
    rows = v.embeddings.rows[["story_id", "visible_at"]]
    p = se.reset_index().merge(rows, on="story_id", suffixes=("", "_e"))
    if p.empty:
        return se
    avail = p[["visible_at", "visible_at_e"]].max(axis=1)
    nine = pd.DatetimeIndex(v.sessions).tz_localize(NY) + pd.Timedelta(hours=9)
    group = np.searchsorted(nine.tz_convert("UTC").asi8, pd.DatetimeIndex(avail).tz_convert("UTC").asi8, side="left")
    group = np.minimum(group, len(nine) - 1)
    p = p.assign(group=group, entity_id=p.entity_id.astype(str)).sort_values(
        ["group", "story_id", "entity_id", "index"], ignore_index=True)
    out = se.copy()
    ent = out.entity_id.astype(str).to_numpy(dtype=object)
    for g, idx in p.groupby("group", sort=True).indices.items():
        day = pd.Timestamp(v.sessions[g]).toordinal()
        rng = np.random.default_rng([seed, day])
        rows_g = p.loc[idx]
        ent[rows_g["index"].to_numpy()] = rng.permutation(rows_g.entity_id.to_numpy(dtype=object))
    out["entity_id"] = ent
    return out


class Placebo:
    """Wraps an agent: every view it gets has its news links shuffled within each day."""

    def __init__(self, inner, seed):
        self.inner, self.seed = inner, seed
        self.params = {"inner": type(inner).__name__, "inner_params": inner.params, "seed": seed}

    @property
    def fits(self):
        return self.inner.fits

    def decide(self, v):
        w = View(v.t, v.sessions, v.members, v.joined, v.bars, v.labels, v.stories, shuffled_links(v, self.seed),
                 v.embeddings)
        return self.inner.decide(w)
