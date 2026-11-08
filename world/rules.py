"""The availability rules (PLAN 5.1): when each kind of record became public. They are conservative on purpose.

| Record | available_at |
|---|---|
| News story | Its `updated_at` plus 15 minutes. Stories edited more than 3 days after publishing are dropped |
| Daily bar for day d (close, high, low, volume, trade count, VWAP, and the bar's first-trade open) | 16:00 New York time on day d, also on an early close. The vendor's bar timestamp (midnight) is never used |
| Official opening price for day d | 9:30 New York time on day d. Only the simulator uses it |
| Return label for day d | The open that ends it: 9:30 on its end date. A company's last label ends at its last close (after a failure it is -1, a total loss), and shows at the next session's open like any other, so a failure halted before the next open (SVB on 2023-03-10) isn't known early |
| S&P 500 membership change | 0:00 New York time on its effective date |

Each rule is one function, so the availability test, and the planted leak that swaps one out, have one place to look.
"""
import pandas as pd

from .clock import CLOSE, MIDNIGHT, OPEN, at_each, nyse

NEWS_DELAY = pd.Timedelta(minutes=15)  # the free plan delivers news about 15 minutes late
MAX_EDIT_LAG = pd.Timedelta(days=3)  # a story edited later than this is dropped: its timing means nothing
# A company's records from outside its S&P 500 memberships: the store keeps, and views show, those dated up to
# HISTORY_BEFORE before a membership (from that membership's start: the stock picker's year, the features' 60 days)
# and up to HISTORY_AFTER after one (at their own time: to sell a removed stock). Calendar days.
HISTORY_BEFORE = pd.Timedelta(days=400)
HISTORY_AFTER = pd.Timedelta(days=14)


def story(updated_at):
    return pd.to_datetime(pd.Series(updated_at), utc=True) + NEWS_DELAY


def keep_story(created_at, updated_at):
    """False for stories edited more than 3 days after publishing."""
    return (pd.to_datetime(pd.Series(updated_at), utc=True) - pd.to_datetime(pd.Series(created_at), utc=True)) <= MAX_EDIT_LAG


def bar(dates):
    return at_each(dates, CLOSE)


def official_open(dates):
    return at_each(dates, OPEN)


def label(ends, at_close, end_open_time=None):
    """When the open that ends each label prints: 9:30 on its end date, or later where the official open printed
    later (a delayed opening; `end_open_time`). Where the label ends at a close (a company's last trading day), 9:30
    on the next session."""
    ends = pd.to_datetime(pd.Series(ends)).dt.normalize()
    at_close = pd.Series(at_close, index=ends.index).astype(bool)
    sessions = nyse().sessions
    after = pd.Series(sessions[sessions.searchsorted(ends.to_numpy(), side="right")], index=ends.index)
    out = at_each(ends.where(~at_close, after), OPEN)
    if end_open_time is not None:
        printed = pd.to_datetime(pd.Series(end_open_time, index=ends.index), utc=True)
        out = out.where(at_close | printed.isna() | (printed <= out), printed)
    return out


def membership(dates):
    return at_each(dates, MIDNIGHT)
