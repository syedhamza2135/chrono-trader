"""S&P 500 membership history: snapshots by date, and each ticker's membership spells.

The base is fja05680/sp500 (compiled from Wikipedia), which stops at its last update. `python -m
data_pipeline.membership` extends it to today with Wikipedia's change log, checks it against the current
list and against monthly revisions of the list, writes components_extended.csv, and writes the report
research/audit/membership.md. Everything else reads the extended file once it exists.

Tickers are the ones the source used, mostly the ones in use at the time (FB until 2022-06-09, then META).
Some early spells carry a later ticker (AABA for Yahoo); the identity table corrects those.
"""
import csv
from datetime import date, datetime

from .settings import DATA_DIR, ROOT

SOURCE = DATA_DIR / "membership" / "components_updated.csv"
EXTENDED = DATA_DIR / "membership" / "components_extended.csv"
REPORT = ROOT / "research" / "audit" / "membership.md"
CHECK_FROM = date(2015, 1, 1)


def load_snapshots(path=None):
    """[(date, frozenset of tickers)], oldest first. Each snapshot holds until the next one."""
    path = path or (EXTENDED if EXTENDED.exists() else SOURCE)
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            tickers = frozenset(t.strip() for t in rec["tickers"].split(",") if t.strip())
            rows.append((date.fromisoformat(rec["date"]), tickers))
    rows.sort()
    return rows


def members_on(day, snapshots):
    current = frozenset()
    for d, tickers in snapshots:
        if d > day:
            break
        current = tickers
    return current


def spells(snapshots, since):
    """{ticker: [(start, end)]} for spells still running on or after `since`.

    `end` is the first snapshot date without the ticker, or None if it's still a member.
    """
    out, opened, previous = {}, {}, frozenset()
    for d, tickers in snapshots:
        for t in tickers - previous:
            opened[t] = d
        for t in previous - tickers:
            out.setdefault(t, []).append((opened.pop(t), d))
        previous = tickers
    for t, start in opened.items():
        out.setdefault(t, []).append((start, None))
    kept = {}
    for t, runs in out.items():
        runs = [(s, e) for s, e in runs if e is None or e >= since]
        if runs:
            kept[t] = sorted(runs)
    return kept


def extend(snapshots, changes, renames=()):
    """Apply the change log after the last snapshot, plus renames of members (the change log only records
    additions and removals). `renames` are Alpaca name changes: {old_symbol, new_symbol, process_date}.
    Returns (snapshots, problems)."""
    last, members = snapshots[-1][0], set(snapshots[-1][1])
    out, problems = list(snapshots), []
    renames = [{"date": date.fromisoformat(r["process_date"]), "removed": r["old_symbol"], "added": r["new_symbol"],
                "rename": True} for r in renames if r["process_date"] > last.isoformat()]
    for day in sorted({c["date"] for c in changes if c["date"] > last} | {r["date"] for r in renames}):
        for r in (r for r in renames if r["date"] == day and r["removed"] in members):
            members.discard(r["removed"])
            members.add(r["added"])
        for c in (c for c in changes if c["date"] == day):
            if c["removed"]:
                if c["removed"] not in members:
                    problems.append(f"{day}: removes {c['removed']}, which isn't a member")
                members.discard(c["removed"])
            if c["added"]:
                if c["added"] in members:
                    problems.append(f"{day}: adds {c['added']}, which is already a member")
                members.add(c["added"])
        if frozenset(members) != out[-1][1]:
            out.append((day, frozenset(members)))
    return out, problems


def main():
    from . import wikipedia as wp
    from .identity import name_changes

    today = wp.today()
    base = load_snapshots(SOURCE)
    log = wp.changes(wp.current(wp.HISTORY, today))
    now = {r["symbol"] for r in wp.constituents(wp.current(wp.LIST, today))}
    snapshots, problems = extend(base, log, name_changes(date.fromisoformat(today)))
    final = snapshots[-1][1]

    # The extended file against the list as Wikipedia showed it on the 1st of each month. Tickers differ
    # wherever the file uses a later ticker for an earlier period; the identity audit compares companies.
    monthly = []
    first = CHECK_FROM
    while first <= date.fromisoformat(today):
        stamp, text = wp.revision(wp.LIST, first.isoformat())
        shown = {r["symbol"] for r in wp.constituents(text)}
        as_of = datetime.fromisoformat(stamp.replace("Z", "+00:00")).date()
        ours = members_on(as_of, snapshots)
        monthly.append((first, as_of, len(shown), sorted(ours - shown), sorted(shown - ours)))
        first = date(first.year + (first.month == 12), first.month % 12 + 1, 1)

    with open(EXTENDED, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "tickers"])
        for d, tickers in snapshots:
            w.writerow([d.isoformat(), ",".join(sorted(tickers))])

    added = [s for s in snapshots if s[0] > base[-1][0]]
    lines = [
        "# Membership audit",
        "",
        f"Generated by `python -m data_pipeline.membership` on {today}.",
        "",
        "## Extension",
        "",
        f"fja05680/sp500 stops at {base[-1][0]}. Wikipedia's change log adds {len(added)} snapshots after it "
        f"({', '.join(str(s[0]) for s in added) or 'none'}).",
        *[f"- Problem: {p}" for p in problems],
        f"The extended file ends with {len(final)} members. Wikipedia's list today has {len(now)}: "
        + ("they match exactly." if final == now else f"only in ours {sorted(final - now)}, only in Wikipedia's {sorted(now - final)}."),
        "",
        "## The file against Wikipedia's list, month by month",
        "",
        "The list as it stood at the start of each month (the revision's own date is used, since editors can lag).",
        "Tickers are compared as written. Most differences are the file using a later ticker for an earlier period",
        "(AABA where Wikipedia shows YHOO) or a day or two of editor lag. `research/audit/identity.md` compares",
        "companies instead.",
        "",
        "| Month | Revision date | Rows | Only in our file | Only on Wikipedia |",
        "|---|---|---|---|---|",
        *[f"| {m:%Y-%m} | {a} | {n} | {' '.join(x) or '-'} | {' '.join(y) or '-'} |" for m, a, n, x, y in monthly if x or y],
        "",
        f"Months that match exactly: {sum(1 for *_, x, y in monthly if not x and not y)} of {len(monthly)}.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
