"""The dev/sealed split (PLAN.md 5.5), confirmed with counts only, written to reference/split.json.

Warm-up 2016 (the stock list is picked on the first trading day of April), dev years 2017 to 2019, sealed years
from 2020-01-01 to the last trading day before the seal. Each period gets counts that show it has enough data:
trading sessions, member company-days, picked stock-days and stories, the stories counted by New York date from
the period's first session to its last. Nothing here reads a price, a return or any other outcome, so the split
can be fixed before anyone has seen how the periods went. Stories about the picked companies aren't counted here,
because the picks are ranked on price times volume (news_reading_load.csv has those counts).

Inputs: the NYSE calendar, reference/memberships.csv, and the news audit's counts per New York date
(research/audit/news_by_day.csv, from `python -m data_pipeline.audit_news`).

Usage: python -m data_pipeline.split [last day of data, default today]
"""
import json
import sys
from datetime import date

import exchange_calendars as xcals
import pandas as pd

from .settings import ROOT

REFERENCE = ROOT / "reference"
AUDIT = ROOT / "research" / "audit"
PICKS_PER_YEAR = 50
PERIODS = {  # PLAN.md 5.5
    "warm_up": ("2016-01-01", "2016-12-31", "watch only; the stock list is picked on the first trading day of April"),
    "dev": ("2017-01-01", "2019-12-31", "tune freely; every run logged in runs/trials.csv"),
    "sealed": ("2020-01-01", None, "run once after the seal; ends on the last trading day before the seal"),
}


def counts(start, end, sessions, members, daily):
    days = sessions[(sessions >= pd.Timestamp(start)) & (sessions <= pd.Timestamp(end))]
    member_days = 0
    for _, g in members.groupby("entity_id"):  # a company listing two classes counts once a day
        on = pd.Series(False, index=days)
        for r in g.itertuples():
            hi = r.member_to - pd.Timedelta(days=1) if pd.notna(r.member_to) else days.max()
            on |= (days >= r.member_from) & (days <= hi)
        member_days += int(on.sum())
    first_pick = days[days >= pd.Timestamp(2016, 4, 1)][0] if start.startswith("2016") else days[0]
    news = daily[(daily.date >= days[0]) & (daily.date <= days[-1])]  # New York dates, first session to last
    return {
        "start": str(days[0].date()), "end": str(days[-1].date()), "sessions": len(days),
        "first_pick": str(first_pick.date()), "picked_stock_days": PICKS_PER_YEAR * int((days >= first_pick).sum()),
        "member_company_days": member_days,
        "benzinga_stories": int(news.stories.sum()),
        "single_firm_stories_about_members": int(news.members.sum()),
    }


def main(last_day=None):
    daily = pd.read_csv(AUDIT / "news_by_day.csv", parse_dates=["date"])
    members = pd.read_csv(REFERENCE / "memberships.csv", dtype=str)
    members["member_from"] = pd.to_datetime(members.member_from)
    members["member_to"] = pd.to_datetime(members.member_to)
    last_day = last_day or str(date.today())
    sessions = xcals.get_calendar("XNYS").sessions_in_range("2016-01-01", last_day)
    out = {
        "rule": "PLAN.md 5.5: warm-up 2016, dev 2017 to 2019, sealed 2020-01-01 to the last trading day before the seal",
        "counts_only": "No prices, returns or other outcomes were read to make this file.",
        "data_through": str(sessions[-1].date()),
        "periods": {},
    }
    for name, (start, end, note) in PERIODS.items():
        out["periods"][name] = {"note": note, **counts(start, end or str(sessions[-1].date()), sessions, members, daily)}
    (REFERENCE / "split.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:2])
