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
holds a later record.

Embeddings (review finding M-3): one row per story, with story_id, vintage_year, available_at and the two vectors.
A row becomes visible with its story (rules.embedding). The World refuses the whole table, with an error, if any row
has no kept story, has a vintage other than the rule's (reader/vintage.py), repeats a story, or stores an
available_at other than its story's: a row left over from before its story was edited (review finding L-P7), or
timed by mistake. The one exception is vintage_offset=1, for the older-vintage rerun only (research/audit/cutoff.md
section 10.1, M3 step 7): then every row must carry the vintage a year older than the rule's, and a row with the
rule's own vintage is refused instead. A World with the offset never opens the sealed years: it refuses
allow_sealed, its views refuse sealed dates, and sim.simulator.run refuses it for any sealed date. The runner records
the offset in the run's settings, so it goes into the settings hash. A row shows when its story's first company link does (judge J-1), so an embedding never tells of a
company the view hides. The World keeps the vectors in their stored order (World.load maps the store's .npy files
read-only from D:, since they don't fit in memory twice; judge J-3) with an order by visible_at, and a view gets
fresh copies of the visible rows only.

The embedding window (M3, decision 1 in research/m3_kickoff.md, approved 22 Nov 2026): a view at t holds only the
embeddings whose visible_at falls in the EMBEDDING_WINDOW_DAYS days (of 24 hours) up to t, so a late view stays
small. It is measured on visible_at, so a story whose embedding shows late (a rejoin, judge J-1) still shows on the
day it becomes visible. A window only removes rows a view would otherwise hold. None serves every visible row. The
runner records the window in the run's settings (sim/simulator.py). Views on or after the sealed start (reference/split.json) need `allow_sealed`, which the
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
EMBEDDING_WINDOW_DAYS = 90  # M3 decision 1; PLAN 9.6's news memory has a half-life of 5 sessions
DAY_NS = 86_400 * 10**9


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


def visible_at(table, df, sp, stories=None, story_entities=None):
    """The visible_at (int64 nanoseconds) of each row of one of the store's tables, given the companies' spells.
    An embedding shows when its story's first company link does (judge J-1): the job reads only stories that name a
    store company, so an embedding seen before any link would tell the agent a hidden company is named, which in a
    gap before a rejoin says the company rejoins. A story with no link gives NEVER."""
    if table == "bars":
        return np.maximum(_ns(rules.bar(df.date)), known_from(df.entity_id, df.date, sp))
    if table == "labels":
        end_open = df["end_open_time"] if "end_open_time" in df else None
        return np.maximum(_ns(rules.label(df.end, df.at_close, end_open)), known_from(df.entity_id, df.date, sp))
    if table == "stories":
        return _ns(rules.story(df.updated_at))
    if table == "embeddings":
        st = stories.drop_duplicates("story_id").set_index("story_id")
        available = pd.Series(_ns(rules.embedding(st.updated_at)), index=st.index)
        se = story_entities[story_entities.story_id.isin(st.index)]
        links = pd.Series(visible_at("story_entities", se, sp, stories), index=se.story_id.to_numpy())
        first = links.groupby(level=0).min()
        at = np.maximum(first.to_numpy(dtype="int64"), available.reindex(first.index).to_numpy(dtype="int64"))
        pos = pd.Index(first.index).get_indexer(df.story_id.to_numpy())
        if len(at) == 0:
            return np.full(len(df), NEVER, dtype="int64")
        return np.where(pos >= 0, at[np.maximum(pos, 0)], NEVER).astype("int64")
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


class Embeddings:
    """The embeddings a view holds (View.embeddings): rows (a DataFrame), and last and avg (arrays of their own,
    aligned with rows). Nothing here shares memory with the World's arrays. Defined here, not in world/view.py, so
    the module agents may import still defines View only (tests/test_boundaries.py)."""

    def __init__(self, rows, last, avg):
        if not (len(rows) == len(last) == len(avg)):
            raise ValueError("rows, last and avg must have one entry per embedding")
        self.rows, self.last, self.avg = rows, last, avg

    def __len__(self):
        return len(self.rows)

    @classmethod
    def empty(cls, dim=0):
        rows = pd.DataFrame({"story_id": pd.Series(dtype="int64"), "vintage_year": pd.Series(dtype="int64"),
                             "available_at": pd.Series(dtype="datetime64[ns, UTC]"),
                             "visible_at": pd.Series(dtype="datetime64[ns, UTC]")})
        return cls(rows, np.zeros((0, dim), np.float16), np.zeros((0, dim), np.float16))


def _vectors(col):
    """A column of vectors (lists or arrays, one per row) as one new 2-D array: no row stays a view into a shared
    buffer that holds other rows."""
    if len(col) == 0:
        return np.zeros((0, 0), np.float16)
    return np.stack([np.asarray(x) for x in col]).copy()


def embedding_problems(embeddings, stories, vintage_offset=0):
    """Why the World must refuse an embeddings table built for these (kept) stories: an empty list if none. With
    vintage_offset 1, the vintage each row must carry is a year older than the rule's."""
    from reader.vintage import breaches
    out = []
    st = stories.drop_duplicates("story_id").set_index("story_id")
    known = embeddings.story_id.isin(st.index)
    if not known.all():
        out.append(f"{int((~known).sum())} rows have no kept story")
    if embeddings.story_id.duplicated().any():
        out.append(f"{int(embeddings.story_id.duplicated().sum())} rows repeat a story")
    k = embeddings[known]
    bad = breaches(k[["story_id", "vintage_year"]], stories, vintage_offset)
    if len(bad):
        named = "the vintage the rule names" if vintage_offset == 0 else f"the vintage {vintage_offset} year older"
        out.append(f"{len(bad)} rows were not read by {named}")
    want = _ns(rules.embedding(k.story_id.map(st.updated_at)))
    have = _ns(pd.to_datetime(k.available_at, utc=True))
    if (want != have).any():
        out.append(f"{int((want != have).sum())} rows store an available_at other than their story's")
    return out


def _rows(embeddings):
    """The rows of an embeddings table given as a DataFrame (vectors in columns) or as an Embeddings."""
    return embeddings.rows if isinstance(embeddings, Embeddings) else embeddings


class _SortedEmbeddings:
    """The embeddings in visible_at order: the rows sorted, and the two vectors kept in their given order (arrays in
    memory, or read-only maps of the store's files) with the order that sorts them. Views get gathered copies."""

    def __init__(self, emb, visible_at):
        if isinstance(emb, Embeddings):
            rows, self._last, self._avg = emb.rows, emb.last, emb.avg
        else:
            rows, self._last, self._avg = emb, _vectors(emb.emb_last), _vectors(emb.emb_avg)
        self.order = np.argsort(visible_at, kind="stable")
        rows = rows.iloc[self.order].reset_index(drop=True)
        self.at = np.asarray(visible_at, dtype="int64")[self.order]
        self.rows = pd.DataFrame({"story_id": rows.story_id.astype("int64"),
                                  "vintage_year": rows.vintage_year.astype("int64"),
                                  "available_at": pd.to_datetime(rows.available_at, utc=True),
                                  "visible_at": pd.to_datetime(self.at, utc=True)})

    @staticmethod
    def _gather(vectors, idx):
        out = np.empty((len(idx),) + vectors.shape[1:], dtype=vectors.dtype)
        np.take(vectors, idx, axis=0, out=out)
        return out

    def upto(self, ns, since=None):
        """Fresh copies of the rows visible at ns, and only those visible after `since` if given (the window):
        nothing in them is a view of the World's arrays."""
        k = int(np.searchsorted(self.at, ns, side="right"))
        j = 0 if since is None else min(int(np.searchsorted(self.at, since, side="right")), k)
        idx = self.order[j:k]
        return Embeddings(self.rows.iloc[j:k].reset_index(drop=True).copy(deep=True), self._gather(self._last, idx),
                          self._gather(self._avg, idx))


def _parquet_footer(path):
    """A Parquet file's size and the SHA-256 of its footer, as reader/embed.py's parquet_footer records them."""
    import hashlib
    size = path.stat().st_size
    with path.open("rb") as fh:
        fh.seek(size - 8)
        n = int.from_bytes(fh.read(4), "little")
        fh.seek(size - 8 - n)
        footer = fh.read(n)
    return {"bytes": size, "footer_sha256": hashlib.sha256(footer).hexdigest()}


def load_embeddings(store):
    """The store's embeddings (reader/embed.py) as an Embeddings: the rows from embeddings.parquet, and the vectors
    as read-only maps of embeddings_last.npy and embeddings_avg.npy, in the same order. Stops if the arrays were
    written for other rows (embeddings.json records their story ids' hash)."""
    import hashlib
    meta = json.loads((store / "embeddings.json").read_text(encoding="utf-8"))
    rows = pd.read_parquet(store / "embeddings.parquet", columns=["story_id", "vintage_year", "available_at"])
    arrays = meta.get("arrays")
    if not arrays or not all((store / f).exists() for f in arrays["files"].values()):
        raise ValueError("the embeddings' arrays are missing: run python -m reader.embed arrays")
    ids = hashlib.sha256(np.ascontiguousarray(rows.story_id.to_numpy(dtype="int64")).tobytes()).hexdigest()
    last = np.load(store / arrays["files"]["emb_last"], mmap_mode="r")
    avg = np.load(store / arrays["files"]["emb_avg"], mmap_mode="r")
    if ids != arrays["ids_sha256"] or not (len(rows) == len(last) == len(avg) == arrays["rows"]):
        raise ValueError("the embeddings' arrays were written for other rows: run python -m reader.embed arrays")
    if _parquet_footer(store / "embeddings.parquet") != arrays.get("parquet"):
        raise ValueError("the embeddings' arrays were written for another embeddings.parquet: run python -m "
                         "reader.embed arrays")
    for a in (last, avg):
        if a.dtype != np.float16 or a.ndim != 2 or a.shape[1] != arrays.get("dim"):
            raise ValueError("the embeddings' arrays have the wrong type or width: run python -m reader.embed arrays")
    return Embeddings(rows, last, avg)


class World:
    def __init__(self, bars, labels, opens, stories, story_entities, membership, clock=None, allow_sealed=False,
                 embeddings=None, embedding_window_days=EMBEDDING_WINDOW_DAYS, vintage_offset=0):
        from reader.vintage import check_offset
        self.clock = clock or Clock()
        self._offset = check_offset(vintage_offset)  # read-only after this: a run records it once
        if vintage_offset and allow_sealed:
            raise PermissionError("a World with a vintage_offset never opens the sealed years")
        self.allow_sealed = allow_sealed
        w = embedding_window_days
        if w is not None and (isinstance(w, bool) or not isinstance(w, int) or w <= 0):
            raise ValueError("embedding_window_days must be a positive whole number of days, or None")
        self._window = embedding_window_days  # read-only after this (judge W-3): a run records it once
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
        self.embeddings = None
        if embeddings is not None:
            found = embedding_problems(_rows(embeddings), stories, vintage_offset)
            if found:
                raise ValueError("the embeddings table is refused: " + "; ".join(found))
            self.embeddings = _SortedEmbeddings(embeddings, visible_at("embeddings", _rows(embeddings), self._spells,
                                                                       stories, se))
        self.opens = _plain(opens).sort_values(["entity_id", "share_class", "date"]).reset_index(drop=True)
        self.data_end = pd.Timestamp(labels.end.max()) if len(labels) else None

    @property
    def embedding_window_days(self):
        """The embedding window in days (None: every visible row). Fixed when the World is built."""
        return self._window

    @property
    def vintage_offset(self):
        """0 for the rule's vintages; 1 for the older-vintage rerun only. Fixed when the World is built."""
        return self._offset

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
        sealed = t.tz_convert(NY).tz_localize(None) >= self._sealed
        if sealed and self._offset:
            raise PermissionError(f"{t} is in the sealed years, and a World with a vintage_offset never opens them")
        if not self.allow_sealed and sealed:
            raise PermissionError(f"{t} is in the sealed years: run through sim.simulator.run, which checks the seal")
        ns = t.as_unit("ns").value
        members, joined = self.members_at(ns)
        since = None if self._window is None else ns - self._window * DAY_NS
        return View(t, self.clock.sessions, members, joined, self.bars.upto(ns), self.labels.upto(ns),
                    self.stories.upto(ns), self.story_entities.upto(ns),
                    self.embeddings.upto(ns, since) if self.embeddings is not None else Embeddings.empty())

    @classmethod
    def load(cls, store=None, clock=None, allow_sealed=False, embeddings=True,
             embedding_window_days=EMBEDDING_WINDOW_DAYS, embeddings_store=None, vintage_offset=0):
        """The World from the store's Parquet files (DATA_DIR/store by default), with the embeddings if the store has
        them (judge J-3; embeddings=False leaves them out), served through the window (None for every row). For the
        older-vintage rerun, embeddings_store names the folder of the older table (DATA_DIR/reader_older) and
        vintage_offset is 1; the other tables still come from the store."""
        if store is None:
            from data_pipeline.settings import DATA_DIR
            store = DATA_DIR / "store"
        read = lambda name: pd.read_parquet(store / f"{name}.parquet")
        es = store if embeddings_store is None else Path(embeddings_store)
        if embeddings_store is not None and not (es / "embeddings.parquet").exists():
            raise ValueError(f"{es} has no embeddings.parquet")
        emb = load_embeddings(es) if embeddings and (es / "embeddings.parquet").exists() else None
        return cls(read("bars"), read("labels"), read("opens"), read("stories"), read("story_entities"),
                   read("membership"), clock, allow_sealed, embeddings=emb,
                   embedding_window_days=embedding_window_days, vintage_offset=vintage_offset)
