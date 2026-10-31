"""The identity table: every company that has been an S&P 500 member since 2015, under a permanent entity ID,
with the tickers it traded under, when, and its SEC CIKs.

`python -m data_pipeline.identity` drafts the table from the sources, applies the hand-checked corrections in
reference/identity_fixes.csv, and writes reference/entities.csv, reference/identity.csv (tickers by date, with
share classes), reference/memberships.csv and the report research/audit/identity.md, whose open items are
everything that still needs a check.

Where each fact comes from:
- Tickers and CIKs by month: Wikipedia's S&P 500 list, one revision per month since 2015. Editors showed the
  ticker in use, so the list is a point-in-time record. (SEC EDGAR wants a contact email, so it isn't used.)
- Membership dates: membership.py (fja05680, extended to today). That file sometimes labels an early period with
  a later ticker (AABA for Yahoo in 2016), joins two companies that shared a ticker into one spell (IR before and
  after March 2020), and leaves out members whose ticker another company later took (ACE, Tyco). Each spell is
  therefore resolved to a CIK revision by revision, and Wikipedia's members are compared company by company.
- Rename dates: hand-checked fixes, then the membership file's own switch dates, then Alpaca's name changes
  (since 2020; processing dates, sometimes late).

An entity is a chain of CIKs that kept the same shares. A CIK change on an unchanged ticker is a reorganisation
(Google to Alphabet) only if the old CIK never shows up again and the new one never showed up before. Otherwise
the ticker passed to another company (ACE took CB from Chubb Corp; Gardner Denver took IR when Ingersoll-Rand
became Trane), and the two are separate entities.
"""
import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

import pandas as pd

from . import alpaca
from . import wikipedia as wp
from .bars import last_complete_day
from .membership import load_snapshots, members_on, spells
from .settings import DATA_DIR, ROOT

SINCE = date(2015, 1, 1)
REFERENCE = ROOT / "reference"
FIXES = REFERENCE / "identity_fixes.csv"
OUT = REFERENCE / "identity.csv"
CASES = REFERENCE / "identity_cases.csv"
REPORT = ROOT / "research" / "audit" / "identity.md"
NAME_CHANGES = DATA_DIR / "corporate_actions" / "name_changes.json"
LAG_DAYS = 12  # Wikipedia editors can be this late; differences closer than this to a change are lag


def normalize(symbol):
    """BRK-B, BRK/B and BRK.B are one ticker; Wikipedia used all three at times."""
    return symbol.upper().replace("-", ".").replace("/", ".")


def wiki_months(today):
    """One row per (revision, listed company): the revision in force on the 1st of each month, plus today's list."""
    rows, month = [], SINCE
    while month <= today:
        stamp, text = wp.revision(wp.LIST, month.isoformat())
        stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00")).date()
        rows += [{"stamp": stamp, **r} for r in wp.constituents(text)]
        month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    rows += [{"stamp": today, **r} for r in wp.constituents(wp.current(wp.LIST, today.isoformat()))]
    w = pd.DataFrame(rows)
    w = w[w.cik != ""].drop(columns="date_added")
    w["symbol"] = w.symbol.map(normalize)
    return w.drop_duplicates(["stamp", "symbol", "cik"]).sort_values(["stamp", "symbol"]).reset_index(drop=True)


def name_changes(today):
    """Alpaca's name changes since 2020: [{old_symbol, new_symbol, process_date, old_cusip, new_cusip}]."""
    if not NAME_CHANGES.exists():
        items = []
        for body in alpaca.pages("/v1/corporate-actions", types="name_change", start="2020-01-01",
                                 end=today.isoformat(), limit=1000):
            items += body.get("corporate_actions", {}).get("name_changes", [])
        NAME_CHANGES.parent.mkdir(parents=True, exist_ok=True)
        NAME_CHANGES.write_text(json.dumps(items), encoding="utf-8")
    return json.loads(NAME_CHANGES.read_text(encoding="utf-8"))


class Wiki:
    """Lookups over the monthly revisions."""

    def __init__(self, w):
        self.w = w
        self.stamps = sorted(w.stamp.unique())
        self.cik_of = {(r.stamp, r.symbol): r.cik for r in w.itertuples()}
        self.symbols_of = defaultdict(set)
        for r in w.itertuples():
            self.symbols_of[(r.stamp, r.cik)].add(r.symbol)
        self.ciks_at = w.groupby("stamp").cik.apply(set).to_dict()
        self.ciks_for_symbol = w.groupby("symbol").cik.apply(set).to_dict()
        self.first_seen = w.groupby("cik").stamp.min().to_dict()
        self.last_seen = w.groupby("cik").stamp.max().to_dict()
        last_names = w.sort_values("stamp").groupby("cik").security.last()
        self.name = last_names.str.replace(r"\s*(?:Class [A-Z]|-[A-Z])$", "", regex=True).to_dict()  # one name per company

    def resolve(self, symbol, stamp):
        """(cik, how) for a membership ticker at one revision."""
        if (stamp, symbol) in self.cik_of:
            return self.cik_of[(stamp, symbol)], "same ticker"
        present = [c for c in self.ciks_for_symbol.get(symbol, ()) if c in self.ciks_at[stamp]]
        if len(present) == 1:
            shown = "/".join(sorted(self.symbols_of[(stamp, present[0])]))
            return present[0], f"shown as {shown}"
        if len(present) > 1:
            return "", f"ambiguous: {sorted(present)}"
        return "", "not on Wikipedia then"


def resolve_spells(spell_map, wiki):
    """Split each membership spell into segments that Wikipedia ties to one CIK."""
    out = []
    for ticker, runs in sorted(spell_map.items()):
        for start, end in runs:
            stop = end or date.max
            stamps = [s for s in wiki.stamps if start <= s < stop]
            if not stamps:  # a spell shorter than a month: use the next revision
                stamps = [s for s in wiki.stamps if s >= start][:1]
            seg = None
            for s in stamps:
                cik, how = wiki.resolve(ticker, s)
                if seg and seg["cik"] == cik:
                    seg["last"] = s
                    seg["hows"][how] += 1
                else:
                    seg = {"ticker": ticker, "spell_start": start, "spell_end": end, "cik": cik, "first": s, "last": s,
                           "hows": Counter({how: 1})}
                    out.append(seg)
    segs = pd.DataFrame(out)
    segs["how"] = segs.hows.map(lambda h: "; ".join(f"{k} ({v})" for k, v in h.most_common()))
    return segs.drop(columns="hows")


def chains(wiki, fixes):
    """Union-find over CIKs: join a reorganisation, keep ticker transfers apart. Returns (find, links)."""
    parent = {}

    def find(c):
        parent.setdefault(c, c)
        while parent[c] != c:
            c = parent[c]
        return c

    links = []
    for symbol, g in wiki.w.groupby("symbol"):
        rows = g.sort_values("stamp")[["stamp", "cik"]].values.tolist()
        for (s1, c1), (s2, c2) in zip(rows, rows[1:]):
            if c1 == c2 or (s2 - s1).days > 62:
                continue
            old_lives_on = wiki.last_seen[c1] >= s2
            new_was_there = wiki.first_seen[c2] <= s1
            kind = ("transfer: the old CIK carries on" if old_lives_on else
                    "takeover: the new CIK was listed before" if new_was_there else "reorganisation")
            links.append({"symbol": symbol, "cik_from": c1, "cik_to": c2, "last_old": s1, "first_new": s2, "kind": kind,
                          "name_from": wiki.name[c1], "name_to": wiki.name[c2]})
    forced = {(r["cik_from"], r["cik_to"]): r["action"] for r in fixes if r.get("action") in ("join", "split")}
    for l in links:
        action = forced.get((l["cik_from"], l["cik_to"]))
        if action == "join" or (action is None and l["kind"] == "reorganisation"):
            parent[find(l["cik_from"])] = find(l["cik_to"])
            l["joined"] = True
        else:
            l["joined"] = False
    for c in wiki.w.cik.unique():
        find(c)
    return find, pd.DataFrame(links)


def read_fixes():
    if not FIXES.exists():
        return []
    return [r for r in csv.DictReader(open(FIXES, encoding="utf-8")) if r.get("action")]


def absorb_lag(segs):
    """A one-revision unresolved segment at either end of a spell is Wikipedia lagging an addition or removal:
    give it the neighbouring segment's CIK."""
    segs = segs.copy()
    for (ticker, start), g in segs.groupby(["ticker", "spell_start"]):
        idx = list(g.sort_values("first").index)
        for pos, i in enumerate(idx):
            if segs.at[i, "cik"] or segs.at[i, "first"] != segs.at[i, "last"] or len(idx) == 1:
                continue
            neighbour = idx[pos + 1] if pos == 0 else idx[pos - 1] if pos == len(idx) - 1 else None
            if neighbour is not None and segs.at[neighbour, "cik"]:
                segs.at[i, "cik"] = segs.at[neighbour, "cik"]
                segs.at[i, "how"] = "Wikipedia lagging the change by days"
    return segs


def apply_wiki_fixes(w, fixes):
    """Correct CIKs Wikipedia showed wrongly or stale (HBI with Avery Dennison's CIK, ViacomCBS with Viacom's)."""
    w = w.copy()
    for r in fixes:
        if r["action"] == "wiki_cik":
            hit = ((w.symbol == r["symbol"]) & (w.cik == r["cik_from"]) & (w.stamp >= date.fromisoformat(r["date_from"]))
                   & (w.stamp <= date.fromisoformat(r["date"])))
            w.loc[hit, "cik"] = r["cik"]
    return w


def merge_same_entity(segs):
    """Neighbouring segments of one spell that belong to one company become one."""
    out = []
    for _, g in segs.sort_values(["ticker", "spell_start", "first"]).groupby(["ticker", "spell_start"], sort=False):
        for r in g.to_dict("records"):
            if out and out[-1]["ticker"] == r["ticker"] and out[-1]["spell_start"] == r["spell_start"] and out[-1]["entity"] == r["entity"]:
                out[-1]["last"] = r["last"]
            else:
                out.append(r)
    return pd.DataFrame(out)


def apply_segment_fixes(segs, fixes):
    """Hand-checked CIKs for segments (keyed by ticker and the segment's first revision date, or its spell start),
    spells to drop, and spell starts and ends to correct."""
    segs = segs.copy()
    for r in fixes:
        hit = (segs.ticker == r["ticker"]) & ((segs["first"].astype(str) == r["date_from"]) |
                                             (segs.spell_start.astype(str) == r["date_from"]))
        if r["action"] == "cik":
            segs.loc[hit, "cik"] = r["cik"]
            segs.loc[hit, "how"] = "hand-checked"
        elif r["action"] == "drop":
            segs = segs[~hit]
        elif r["action"] == "spell_end":
            segs.loc[hit, "spell_end"] = date.fromisoformat(r["date"])
        elif r["action"] == "spell_start":
            segs.loc[hit, "spell_start"] = date.fromisoformat(r["date"])
    # Neighbouring segments of one spell that now share a CIK become one.
    out = []
    for _, g in segs.sort_values(["ticker", "spell_start", "first"]).groupby(["ticker", "spell_start"], sort=False):
        for r in g.to_dict("records"):
            if out and out[-1]["ticker"] == r["ticker"] and out[-1]["spell_start"] == r["spell_start"] and out[-1]["cik"] == r["cik"]:
                out[-1]["last"] = r["last"]
            else:
                out.append(r)
    return pd.DataFrame(out)


def periods(segs, fixes):
    """Each segment's membership period. Spell ends are exact; a boundary inside a spell (the ticker passing to
    another company) is placed at a hand-checked date if there is one, else midway between the two revisions."""
    boundary = {(r["ticker"], r["cik_from"], r["cik_to"]): date.fromisoformat(r["date"]) for r in fixes if r["action"] == "boundary"}
    rows = []
    for (ticker, start), g in segs.groupby(["ticker", "spell_start"]):
        g = g.sort_values("first").to_dict("records")
        for pos, r in enumerate(g):
            r["member_from"] = r["spell_start"] if pos == 0 else rows[-1]["member_to"]
            r["to_exact"] = True
            if pos == len(g) - 1:
                r["member_to"] = r["spell_end"]
            else:
                key = (ticker, r["cik"], g[pos + 1]["cik"])
                r["member_to"] = boundary.get(key, r["last"] + (g[pos + 1]["first"] - r["last"]) / 2)
                r["to_exact"] = key in boundary
            rows.append(r)
    for r in fixes:  # members the membership file leaves out
        if r["action"] == "member":
            rows.append({"ticker": r["symbol"], "spell_start": date.fromisoformat(r["date_from"]), "spell_end": date.fromisoformat(r["date"]),
                         "cik": r["cik"], "first": None, "last": None, "how": "added: missing from the membership file",
                         "member_from": date.fromisoformat(r["date_from"]), "member_to": date.fromisoformat(r["date"]), "to_exact": True})
    return pd.DataFrame(rows)


def timelines(wiki, find, members, fixes, renames, today):  # noqa: C901 (one pass over each company's runs)
    """Rows of (entity, symbol, share_class, valid_from, valid_to, dated_by) covering each entity's membership.

    Each run of consecutive revisions showing a symbol becomes a row. A row starts on the hand-checked rename date
    if there is one, else on Alpaca's name-change date (2020 on, within two months), else on its first revision
    (approximate). The entity's first rows reach back to its first membership day, its last rows forward to its
    last; share classes listed together get one row each, and a class added to the index later starts on the day
    it was added.

    Rows form class chains: a run continues the run that ended last before it, and a run with nothing before it
    (a company's first ticker, or a class listed alongside another) starts a chain. A company with one chain has
    share_class ''. A company with several takes each chain's label from the hand-checked `class` fixes (GOOGL is
    class A, GOOG class C), else from the chain's first ticker. Under Armour swapped tickers between its classes
    (UA was class A until 2016-12-06 and class C after), which no chain rule can see, so its rows are written out
    by hand (`rows` fixes, each with its share_class)."""
    exact = {}
    for r in fixes:
        if r["action"] == "rename":
            exact[(r["old"], r["new"])] = date.fromisoformat(r["date"])
    for r in renames:
        exact.setdefault((r["old_symbol"], r["new_symbol"]), date.fromisoformat(r["process_date"]))
    class_of = {(find(r["cik"]), r["symbol"]): r["share_class"] for r in fixes if r["action"] == "class"}
    class_added = members.groupby(["entity", "ticker"]).member_from.apply(list).to_dict()
    class_left = members.dropna(subset=["member_to"]).groupby(["entity", "ticker"]).member_to.apply(list).to_dict()
    stamps = wiki.stamps
    w = wiki.w.assign(entity=wiki.w.cik.map(find))
    cover = members.groupby("entity").agg(start=("member_from", "min"), end=("member_to", lambda s: None if s.isna().any() else s.max()))
    rows = []
    for e, g in w.groupby("entity"):
        if e not in cover.index:
            continue
        start, end = cover.loc[e, "start"], cover.loc[e, "end"]
        present = g.groupby("symbol").stamp.apply(set)
        runs = []
        for symbol, seen in present.items():
            run = None
            for s in stamps:
                if s in seen:
                    run = run or {"symbol": symbol, "first": s}
                    run["last"] = s
                elif run:
                    runs.append(run)
                    run = None
            if run:
                runs.append(run)
        runs.sort(key=lambda r: r["first"])
        merged = []  # a ticker that comes back with nothing else in between is one run (a company re-added)
        for r in runs:
            same = [m for m in merged if m["symbol"] == r["symbol"]]
            if same and not any(o["symbol"] != r["symbol"] and same[-1]["last"] < o["first"] < r["first"] for o in runs):
                same[-1]["last"] = r["last"]
            else:
                merged.append(dict(r))
        runs = sorted(merged, key=lambda r: r["first"])
        for r in runs:  # sorted by first, so a run's predecessor already has its chain
            before = [p for p in runs if p["last"] < r["first"]]
            r["chain"] = max(before, key=lambda p: p["last"])["chain"] if before else r["symbol"]
        labels = {}
        for r in runs:
            if (e, r["symbol"]) in class_of:
                labels.setdefault(r["chain"], class_of[(e, r["symbol"])])
        several = len({r["chain"] for r in runs}) > 1
        earliest = runs[0]["first"]
        latest = max(r["last"] for r in runs)
        next_stamp = lambda s: next((x for x in stamps if x > s), s)
        # A rename date counts if it falls between the two runs, give or take two months: KDP came back to the
        # index in 2022, four years after DPS became KDP.
        between = lambda d, lo, hi: lo - timedelta(days=62) <= d <= hi + timedelta(days=62)
        for r in runs:
            before = [p for p in runs if p["last"] < r["first"]]
            after = [n for n in runs if n["first"] > r["last"]]
            pred_run = max(before, key=lambda p: p["last"]) if before else None
            succ_run = min(after, key=lambda n: n["first"]) if after else None
            pred = pred_run["symbol"] if pred_run else None
            succ = succ_run["symbol"] if succ_run else None
            added = [d for d in class_added.get((e, r["symbol"]), []) if timedelta(0) <= r["first"] - d <= timedelta(days=62)]
            if pred is None and r["first"] > earliest and added:  # a share class added to the index later (FOX in 2015)
                vf, how_from = min(added), "class added to the index"
            elif pred is None and r["first"] > earliest:  # a share class that appeared later (UA.C in 2016)
                vf, how_from = r["first"], "approximate (first revision showing it)"
            elif pred is None:
                vf, how_from = min(start, r["first"]), "first membership day"
            elif (pred, r["symbol"]) in exact and between(exact[(pred, r["symbol"])], pred_run["last"], r["first"]):
                vf, how_from = exact[(pred, r["symbol"])], "exact"
            else:
                vf, how_from = r["first"], "approximate (first revision showing it)"
            left = [d for d in class_left.get((e, r["symbol"]), []) if r["last"] < d <= next_stamp(r["last"])]
            if succ is None and r["last"] < latest and left:  # a share class that left the index (CMCSK in 2015)
                vt, how_to = max(left) - timedelta(days=1), "class left the index"
            elif succ is None and r["last"] < latest:  # a share class that ended while the company went on
                vt, how_to = next_stamp(r["last"]) - timedelta(days=1), "approximate"
            elif succ is None:  # membership ends are exclusive; valid_to is the last member day
                vt, how_to = (end - timedelta(days=1) if end else None), "last membership day"
            elif (r["symbol"], succ) in exact and between(exact[(r["symbol"], succ)], r["last"], succ_run["first"]):
                vt, how_to = exact[(r["symbol"], succ)] - timedelta(days=1), "exact"
            else:
                vt, how_to = min(after, key=lambda n: n["first"])["first"] - timedelta(days=1), "approximate"
            rows.append({"entity_id": e, "symbol": r["symbol"], "share_class": labels.get(r["chain"], r["chain"] if several else ""),
                         "valid_from": vf, "valid_to": vt, "dated_by": how_from, "dated_to": how_to,
                         "first_seen": r["first"], "last_seen": r["last"]})
    rows = pd.DataFrame(rows)
    for f in fixes:  # explicit listing windows: share classes, and tickers whose dates can't be inferred
        if f["action"] == "window":
            hit = (rows.entity_id == find(f["cik"])) & (rows.symbol == f["symbol"])
            rows.loc[hit, ["valid_from", "dated_by"]] = [date.fromisoformat(f["date_from"]), "exact"]
            if f["date"]:
                rows.loc[hit, ["valid_to", "dated_to"]] = [date.fromisoformat(f["date"]), "exact"]
    explicit = [f for f in fixes if f["action"] == "rows"]  # hand-written rows replace a company's generated ones
    if explicit:
        rows = rows[~rows.entity_id.isin({find(f["cik"]) for f in explicit})]
        add = [{"entity_id": find(f["cik"]), "symbol": f["symbol"], "share_class": f["share_class"],
                "valid_from": date.fromisoformat(f["date_from"]),
                "valid_to": date.fromisoformat(f["date"]) if f["date"] else None, "dated_by": "exact", "dated_to": "exact",
                "first_seen": date.fromisoformat(f["date_from"]),
                "last_seen": date.fromisoformat(f["date"]) if f["date"] else today} for f in explicit]
        rows = pd.concat([rows, pd.DataFrame(add)], ignore_index=True)
    return rows


class SymbolIndex:
    """Map a story's tags on a given day to companies, using reference/identity.csv.

    A tag is normalised the way Wikipedia's are (BRK-B, BRK/B to BRK.B). A class-share tag that isn't listed itself
    (BRK.A, plain BRK) maps through its root to the listed class of the same company. Only S&P 500 members since
    2015 are in the table, so tags of other companies map to nothing."""

    def __init__(self, rows=None):
        rows = (pd.read_csv(OUT, dtype=str) if rows is None else rows.astype(str)).fillna("")
        self.by_symbol, self.by_root = defaultdict(list), defaultdict(list)
        for r in rows.itertuples():
            span = (pd.Timestamp(r.valid_from).date(), pd.Timestamp(r.valid_to).date() if r.valid_to not in ("", "nan", "None", "NaT") else date.max)
            self.by_symbol[r.symbol].append((*span, r.entity_id))
            if "." in r.symbol:
                self.by_root[r.symbol.split(".")[0]].append((*span, r.entity_id))

    def lookup(self, tag, day):
        tag = normalize(tag)
        for table, key in ((self.by_symbol, tag), (self.by_root, tag.split(".")[0])):
            hits = {e for a, b, e in table.get(key, ()) if a <= day <= b}
            if hits:
                return hits
        return set()

    def entities(self, tags, day):
        """(companies we know, number of distinct companies including unknown tags)."""
        known, unknown = set(), set()
        for t in tags:
            hit = self.lookup(t, day)
            known |= hit
            if not hit:
                unknown.add(normalize(t).split(".")[0])
        return known, len(known) + len(unknown)


def overlaps(rows):
    """Symbols that mean two entities on the same day."""
    out = []
    for symbol, g in rows.groupby("symbol"):
        g = g.sort_values("valid_from").to_dict("records")
        for a, b in zip(g, g[1:]):
            if a["entity_id"] != b["entity_id"] and (a["valid_to"] is None or pd.isna(a["valid_to"]) or a["valid_to"] >= b["valid_from"]):
                out.append({"symbol": symbol, "entity_a": a["entity_id"], "until": a["valid_to"], "entity_b": b["entity_id"], "from": b["valid_from"]})
    return pd.DataFrame(out)


def compare(wiki, find, members):
    """Entities Wikipedia shows that our membership lacks, and the reverse, ignoring differences within LAG_DAYS
    of that entity's own membership change."""
    spans = defaultdict(list)
    for r in members.itertuples():
        spans[r.entity].append((r.member_from, r.member_to or date.max))
    inside = lambda e, s: any(a <= s < b for a, b in spans.get(e, ()))
    near = lambda e, s: any(abs((s - a).days) <= LAG_DAYS or (b != date.max and abs((s - b).days) <= LAG_DAYS)
                            for a, b in spans.get(e, ()))
    missing, extra = defaultdict(list), defaultdict(list)
    ours_any = set(spans)
    for s in wiki.stamps:
        theirs = {find(c) for c in wiki.ciks_at[s]}
        for e in theirs:
            if not inside(e, s) and not near(e, s):
                missing[e].append(s)
        for e in ours_any - theirs:
            if inside(e, s) and not near(e, s):
                extra[e].append(s)
    return missing, extra


def build_all(today):
    fixes = read_fixes()
    snapshots = load_snapshots()
    spell_map = spells(snapshots, since=SINCE)
    wiki = Wiki(apply_wiki_fixes(wiki_months(today), fixes))
    segs = apply_segment_fixes(absorb_lag(resolve_spells(spell_map, wiki)), fixes)
    find, links = chains(wiki, fixes)
    segs["entity"] = segs.cik.map(lambda c: find(c) if c else "")
    segs = merge_same_entity(segs)
    members = periods(segs, fixes)
    members["entity"] = members.cik.map(lambda c: find(c) if c else "")
    resolved = members[members.entity != ""]
    rows = timelines(wiki, find, resolved, fixes, name_changes(today), today)
    names = {r["cik"]: r["name"] for r in fixes if r["action"] == "name"}
    return {"fixes": fixes, "spell_map": spell_map, "wiki": wiki, "segs": segs, "find": find, "links": links,
            "members": members, "rows": rows, "names": names}


def write_tables(b):
    wiki, find, members, rows = b["wiki"], b["find"], b["members"], b["rows"]
    resolved = members[members.entity != ""]
    ent_ciks = defaultdict(list)
    for cik, g in wiki.w.groupby("cik"):
        ent_ciks[find(cik)].append((g.stamp.min(), cik))
    for c in resolved.cik.unique():  # CIKs only the fixes know
        if not any(c == x for _, x in ent_ciks[find(c)]):
            ent_ciks[find(c)].append((date.min, c))
    entities = []
    for e, g in resolved.groupby("entity"):
        ciks = [c for _, c in sorted(ent_ciks[e])]
        name = b["names"].get(e) or wiki.name.get(ciks[-1]) or wiki.name.get(e, "")
        entities.append({"entity_id": e, "name": name, "ciks": " ".join(ciks),
                         "first_member": g.member_from.min(), "last_member": None if g.member_to.isna().any() else g.member_to.max()})
    entities = pd.DataFrame(entities).sort_values("name")
    REFERENCE.mkdir(exist_ok=True)
    entities.to_csv(REFERENCE / "entities.csv", index=False)
    rows.sort_values(["entity_id", "valid_from", "symbol"]).to_csv(OUT, index=False)
    m = resolved.assign(source_ticker=resolved.ticker)[["entity", "member_from", "member_to", "source_ticker", "how", "to_exact"]]
    m.rename(columns={"entity": "entity_id"}).sort_values(["entity_id", "member_from"]).to_csv(REFERENCE / "memberships.csv", index=False)
    return entities


def main():
    today = last_complete_day() + timedelta(days=1)
    b = build_all(today)
    wiki, find, members, rows, links = b["wiki"], b["find"], b["members"], b["rows"], b["links"]
    entities = write_tables(b)
    resolved = members[members.entity != ""]
    missing, extra = compare(wiki, find, resolved)
    clash = overlaps(rows)
    unresolved = members[members.entity == ""]
    approx = rows[rows.dated_by.str.startswith("approximate")]
    boundaries = members[~members.to_exact.astype(bool)]
    classes = rows[rows.share_class != ""].sort_values(["entity_id", "share_class", "valid_from"])
    checked = {f["share_class"] for f in b["fixes"] if f["action"] in ("class", "rows")}
    unlabelled = classes[~classes.share_class.isin(checked)].drop_duplicates(["entity_id", "share_class"])
    ent_name = dict(zip(entities.entity_id, entities.name))
    lines = [
        "# Identity audit",
        "",
        f"Generated by `python -m data_pipeline.identity` on {date.today()}. Tables: `reference/entities.csv`, "
        "`reference/identity.csv` (tickers by date), `reference/memberships.csv` (membership by company). Hand-checked "
        "corrections, each with its evidence: `reference/identity_fixes.csv`.",
        "",
        "## Summary",
        "",
        f"- Membership spells since {SINCE}: {sum(len(v) for v in b['spell_map'].values())} for {len(b['spell_map'])} tickers, "
        f"split into {len(b['segs'])} segments that each belong to one company.",
        f"- Companies: {len(entities)}. Ticker rows: {len(rows)}, of which {len(approx)} carry an approximate start date.",
        f"- CIK changes on an unchanged ticker: {len(links)} ({int(links.joined.sum()) if len(links) else 0} joined as one company).",
        f"- Segments with no company: {len(unresolved)}. Boundaries inside a spell without a checked date: {len(boundaries)}.",
        f"- Tickers meaning two companies on the same day: {len(clash)}.",
        f"- Companies listing more than one share class: {classes.entity_id.nunique()} ({len(unlabelled)} classes without a checked label).",
        f"- Companies on Wikipedia's list but not in our membership (away from their own changes): {len(missing)}; the reverse: {len(extra)}.",
        "",
        "## Open items",
        "",
        *([f"- Unresolved: {r.ticker} {r.spell_start}..{r.spell_end} ({r.how})" for r in unresolved.itertuples()] or ["- No unresolved segments."]),
        *[f"- Boundary not checked: {r.ticker} after {r.last} ({wiki.name.get(r.cik, r.cik)})" for r in boundaries.itertuples()],
        *[f"- Overlap: {r.symbol} means {r.entity_a} until {r.until} and {r.entity_b} from {r._5}" for r in clash.itertuples()],
        *[f"- Missing from our membership: {wiki.name.get(e, e)} ({e}), {len(ss)} revisions {ss[0]}..{ss[-1]}" for e, ss in missing.items()],
        *[f"- Not on Wikipedia: {e}, {len(ss)} revisions {ss[0]}..{ss[-1]}" for e, ss in extra.items()],
        *[f"- Share class without a checked label: {ent_name.get(r.entity_id, r.entity_id)}, chain starting {r.symbol}" for r in unlabelled.itertuples()],
        "",
        "## Share classes",
        "",
        "Companies listing more than one class at once. Each class is a chain of tickers; a membership period uses the "
        "class whose rows carry its ticker (`bars.spell_class`).",
        "",
        "| Company | Class | Tickers |",
        "|---|---|---|",
        *[f"| {ent_name.get(e, e)} | {k} | " + ", then ".join(f"{r.symbol} from {r.valid_from}" for r in g.itertuples()) + " |"
          for (e, k), g in classes.groupby(["entity_id", "share_class"], sort=False)],
        "",
        "## CIK changes on an unchanged ticker",
        "",
        "| Ticker | From | To | Between | Kind | Joined |",
        "|---|---|---|---|---|---|",
        *[f"| {r.symbol} | {r.cik_from} {r.name_from} | {r.cik_to} {r.name_to} | {r.last_old} and {r.first_new} | {r.kind} | {'yes' if r.joined else 'no'} |"
          for r in links.itertuples()],
        "",
        "## Ticker rows with an approximate start",
        "",
        "These start on the first monthly revision that showed the ticker. A hand-checked rename date replaces each.",
        "",
        *[f"- {r.symbol} ({wiki.name.get(r.entity_id, r.entity_id)}): from {r.valid_from}" for r in approx.itertuples()],
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:16]))
    print(f"... open items: {len(unresolved)} unresolved, {len(boundaries)} boundaries, {len(clash)} overlaps, {len(missing)} missing, {len(extra)} extra; {len(approx)} approximate starts")


if __name__ == "__main__":
    main()
