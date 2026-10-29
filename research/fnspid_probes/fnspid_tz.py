"""Test which clock FNSPID's timed Benzinga rows use (true UTC, US/Pacific, or ET shifted the wrong way).

Usage: python -I fnspid_tz.py <chunk> [<chunk> ...]   (All_external.csv chunks)
"""
import collections
import re
import sys
from datetime import datetime

sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0].rsplit("\\", 1)[0])
from fnspid_probe import rows_from  # noqa: E402


def dst(d):
    # US daylight saving: second Sunday of March to first Sunday of November (approximate by month is enough here)
    return 4 <= d.month <= 10 or (d.month == 3 and d.day > 14) or (d.month == 11 and d.day < 7)


def main():
    rows = []
    for p in sys.argv[1:]:
        rows += rows_from(p, "all")
    bz = []
    for r in rows:
        if "benzinga.com" not in r["Url"]:
            continue
        d = datetime.strptime(r["Date"], "%Y-%m-%d %H:%M:%S UTC")
        bz.append((d, r))
    timed = [(d, r) for d, r in bz if not (d.hour == 0 and d.minute == 0 and d.second == 0)]
    print(f"benzinga rows {len(bz)}, with a time of day {len(timed)}")
    by_year = collections.defaultdict(lambda: [0, 0])
    for d, r in bz:
        by_year[d.year][0] += 1
        by_year[d.year][1] += 0 if (d.hour == 0 and d.minute == 0 and d.second == 0) else 1
    print("year: rows / timed:", {y: tuple(v) for y, v in sorted(by_year.items())})
    pats = {
        "mid-day": re.compile(r"mid-?day", re.I),
        "52-week": re.compile(r"52-week (highs|lows)", re.I),
        "pre-market": re.compile(r"pre-?market", re.I),
        "after-hours": re.compile(r"after-?hours", re.I),
        "movers from": re.compile(r"movers from", re.I),
    }
    for name, pat in pats.items():
        hits = [(d, r) for d, r in timed if pat.search(r["Article_title"])]
        if not hits:
            continue
        summer = collections.Counter(f"{d:%H}" for d, _ in hits if dst(d))
        winter = collections.Counter(f"{d:%H}" for d, _ in hits if not dst(d))
        print(f"\n{name}: n={len(hits)}  stored hour in DST months {sorted(summer.items())}  in winter {sorted(winter.items())}")
        for d, r in hits[:8]:
            print(f"    {d:%Y-%m-%d %a %H:%M:%S}  {r['Article_title'][:80]}")
    # analyst-rating headlines: brokers usually publish before the open
    rat = [(d, r) for d, r in timed if re.search(r"(Maintains|Upgrades|Downgrades|Initiates|Reiterates)", r["Article_title"])]
    print(f"\nanalyst-rating rows with a time: {len(rat)}; stored hours", sorted(collections.Counter(d.hour for d, _ in rat).items()))
    allh = collections.Counter(d.hour for d, _ in timed)
    print("all timed benzinga rows, stored hour histogram:", [allh.get(h, 0) for h in range(24)])


if __name__ == "__main__":
    main()
