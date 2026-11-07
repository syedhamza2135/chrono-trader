"""World: the store's records, each with the time it becomes visible. Only the loop and the simulator hold a World;
agents get views (world/view.py), and they may not import this module.

A record becomes visible at its available_at (world/rules.py), and never before its company's S&P 500 membership
makes it relevant. The store keeps every company that was a member at any time since 2015, so showing one outside
its memberships would tell the agent it joins, or rejoins, later. So for a record about company c dated day d:
- inside a membership of c, or up to HISTORY_AFTER after one: it shows at its own available_at;
- up to HISTORY_BEFORE before a membership: it shows from that membership's start, like the history of a new member
  (the stock picker ranks a new member on its year of trading before). This holds for a rejoin too: EQT's bars from
  before its 2022 rejoin show at the rejoin, not during its 2018 to 2022 gap;
- otherwise never.

Each table is sorted by visible_at, and a view holds copies of each table's prefix: nothing reachable from a view
holds a later record. Views on or after the sealed start (reference/split.json) need `allow_sealed`, which the
runner sets only after the seal holds (sim/seal.py), or a data audit sets explicitly.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import rules
from .clock import NY, Clock
from .view import View

NEVER = np.iinfo("int64").max
ROOT = Path(__file__).resolve().parents[1]
KEYS = ("entity_id", "share_class", "symbol")


def _ns(times):
    return pd.DatetimeIndex(times).as_unit("ns").asi8


def sealed_start(root=ROOT):
    split = json.loads((root / "reference" / "split.json").read_text(encoding="utf-8"))
    return pd.Timestamp(split["periods"]["sealed"]["start"])


def spells(membership):
    """Each company's memberships, overlapping ones (a company's two classes) merged: entity_id, start, end (the
    first day after, or NaT while a member)."""
    m = membership[["entity_id", "member_from", "member_to"]].copy()
    m["entity_id"] = m.entity_id.astype(str).astype(object)
    m["end"] = pd.to_datetime(m.member_to).fillna(pd.Timestamp.max.normalize())
    m["start"] = pd.to_datetime(m.member_from)
    out = []
    for e, g in m.sort_values(["entity_id", "start"]).groupby("entity_id", sort=False):
        cur_s, cur_e = None, None
        for s, end in zip(g.start, g.end):
            if cur_s is None or s > cur_e:
                if cur_s is not None:
                    out.append((e, cur_s, cur_e))
                cur_s, cur_e = s, end
            else:
                cur_e = max(cur_e, end)
        out.append((e, cur_s, cur_e))
    df = pd.DataFrame(out, columns=["entity_id", "start", "end"])
    df["entity_id"] = df.entity_id.astype(object)
    df["end"] = df.end.where(df.end < pd.Timestamp.max.normalize())
    return df


def known_from(entity_ids, dates, sp):
    """For each (company, date), the earliest time a view may show a record of that company dated that day (int64
    nanoseconds; NEVER where it may not)."""
    left = pd.DataFrame({"entity_id": pd.Series(entity_ids).astype(str).to_numpy(dtype=object),
                         "date": pd.to_datetime(pd.Series(dates)).dt.normalize().astype("datetime64[ns]").to_numpy(),
                         "i": np.arange(len(entity_ids))}).sort_values("date", kind="stable")
    left["entity_id"] = left.entity_id.astype("str")  # one string type on both sides of the merge
    s = sp.assign(start=sp.start.astype("datetime64[ns]"), entity_id=sp.entity_id.astype("str")).sort_values("start")
    prev = pd.merge_asof(left, s.rename(columns={"start": "prev_start", "end": "prev_end"}), left_on="date",
                         right_on="prev_start", by="entity_id", direction="backward")
    nxt = pd.merge_asof(left, s[["entity_id", "start"]].rename(columns={"start": "next_start"}), left_on="date",
                        right_on="next_start", by="entity_id", direction="forward", allow_exact_matches=False)
    prev = prev.set_index("i").sort_index()
    nxt = nxt.set_index("i").sort_index()
    out = np.full(len(left), NEVER, dtype="int64")
    near_prev = prev.prev_start.notna() & (prev.prev_end.isna() | (prev.date < prev.prev_end + rules.HISTORY_AFTER))
    near_next = ~near_prev & nxt.next_start.notna() & (nxt.next_start - nxt.date <= rules.HISTORY_BEFORE)
    if near_prev.any():
        out[near_prev.to_numpy()] = _ns(rules.membership(prev.prev_start[near_prev]))
    if near_next.any():
        out[near_next.to_numpy()] = _ns(rules.membership(nxt.next_start[near_next]))
    return out


def visible_at(table, df, sp, stories=None):
    """The visible_at (int64 nanoseconds) of each row of one of the store's tables, given the companies' spells."""
    if table == "bars":
        return np.maximum(_ns(rules.bar(df.date)), known_from(df.entity_id, df.date, sp))
    if table == "labels":
        end_open = df["end_open_time"] if "end_open_time" in df else None
        return np.maximum(_ns(rules.label(df.end, df.at_close, end_open)), known_from(df.entity_id, df.date, sp))
    if table == "stories":
        return _ns(rules.story(df.updated_at))
    if table == "story_entities":
        st = stories.drop_duplicates("story_id").set_index("story_id")
        available = pd.Series(_ns(rules.story(st.updated_at)), index=st.index)
        day = pd.to_datetime(st.created_at, utc=True).dt.tz_convert(NY).dt.tz_localize(None).dt.normalize()
        return np.maximum(df.story_id.map(available).to_numpy(dtype="int64"),
                          known_from(df.entity_id, df.story_id.map(day), sp))
    raise ValueError(table)


def _plain(df):
    """Key columns as plain Python strings (no category lists, no shared Arrow buffers), and list columns (a story's
    tags) as tuples of their own: Parquet hands each row's list as a view into one array of every row's lists."""
    df = df.copy()
    for c in df.columns:
        first = next((x for x in df[c] if x is not None), None) if df[c].dtype == object else None
        if isinstance(first, (np.ndarray, list, tuple)):
            df[c] = pd.Series([() if x is None else tuple(str(s) for s in x) for x in df[c]], index=df.index,
                              dtype=object)
        elif c in KEYS or c == "headline" or pd.api.types.is_string_dtype(df[c]):
            df[c] = df[c].astype(object)
    return df


class _Sorted:
    """A table sorted by visible_at, with the times as int64 nanoseconds for a binary search."""

    def __init__(self, df, visible_at):
        order = np.argsort(visible_at, kind="stable")
        self.df = _plain(df).iloc[order].reset_index(drop=True)
        self.at = np.asarray(visible_at, dtype="int64")[order]
        self.df["visible_at"] = pd.to_datetime(np.minimum(self.at, np.iinfo("int64").max - 1), utc=True)

    def upto(self, ns):
        """A detached copy of the rows visible at ns."""
        return self.df.iloc[: int(np.searchsorted(self.at, ns, side="right"))].copy(deep=True)


class World:
    def __init__(self, bars, labels, opens, stories, story_entities, membership, clock=None, allow_sealed=False):
        self.clock = clock or Clock()
        self.allow_sealed = allow_sealed
        self._sealed = sealed_start()
        m = membership.copy()
        m["entity_id"] = m.entity_id.astype(str)
        self.membership = m
        self._spells = spells(m)
        joins = pd.DataFrame({"entity_id": m.entity_id, "step": 1, "at": _ns(rules.membership(m.member_from))})
        ended = m[m.member_to.notna()]
        leaves = pd.DataFrame({"entity_id": ended.entity_id, "step": -1, "at": _ns(rules.membership(ended.member_to))})
        self._events = pd.concat([joins, leaves], ignore_index=True).sort_values(["at", "step"], kind="stable",
                                                                                 ignore_index=True)
        self.bars = _Sorted(bars, visible_at("bars", bars, self._spells))
        self.labels = _Sorted(labels, visible_at("labels", labels, self._spells))
        keep = rules.keep_story(stories.created_at, stories.updated_at).to_numpy()
        stories = stories[keep].reset_index(drop=True)
        self.stories = _Sorted(stories, visible_at("stories", stories, self._spells))
        se = story_entities[story_entities.story_id.isin(stories.story_id)].reset_index(drop=True)
        self.story_entities = _Sorted(se, visible_at("story_entities", se, self._spells, stories))
        self.opens = _plain(opens).sort_values(["entity_id", "share_class", "date"]).reset_index(drop=True)
        self.data_end = pd.Timestamp(labels.end.max()) if len(labels) else None

    def members_at(self, ns):
        """(members at t, every company that has joined by t), from the join and leave events available at t."""
        ev = self._events.iloc[: int(np.searchsorted(self._events["at"].to_numpy(), ns, side="right"))]
        count = ev.groupby("entity_id").step.sum()
        return frozenset(count.index[count > 0]), frozenset(count.index)

    def view(self, t):
        t = pd.Timestamp(t)
        if t.tzinfo is None:
            raise ValueError("view(t) needs a time zone; the clock's times are UTC")
        t = t.tz_convert("UTC")
        if not self.allow_sealed and t.tz_convert(NY).tz_localize(None) >= self._sealed:
            raise PermissionError(f"{t} is in the sealed years: run through sim.simulator.run, which checks the seal")
        ns = t.as_unit("ns").value
        members, joined = self.members_at(ns)
        return View(t, self.clock.sessions, members, joined, self.bars.upto(ns), self.labels.upto(ns),
                    self.stories.upto(ns), self.story_entities.upto(ns))

    @classmethod
    def load(cls, store=None, clock=None, allow_sealed=False):
        """The World from the store's Parquet files (DATA_DIR/store by default)."""
        if store is None:
            from data_pipeline.settings import DATA_DIR
            store = DATA_DIR / "store"
        read = lambda name: pd.read_parquet(store / f"{name}.parquet")
        return cls(read("bars"), read("labels"), read("opens"), read("stories"), read("story_entities"),
                   read("membership"), clock, allow_sealed)
