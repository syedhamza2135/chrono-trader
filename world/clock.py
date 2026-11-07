"""The trading clock: NYSE sessions, and the New York times of day that the availability rules use.

Every time is a UTC pandas Timestamp. A New York date and time of day becomes UTC through the tz database, so
daylight saving is handled: 9:00 in New York is 14:00 UTC in winter and 13:00 UTC in summer. Sessions, and their
early closes at 13:00, come from the NYSE calendar in exchange_calendars. Dates are New York dates, stored as naive
midnight timestamps."""
import datetime as dt
from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd

NY = "America/New_York"
DECISION = dt.time(9, 0)  # the agent decides at 9:00 New York time, before the open
OPEN = dt.time(9, 30)
CLOSE = dt.time(16, 0)
MIDNIGHT = dt.time(0, 0)


@lru_cache(maxsize=1)
def nyse():
    return xcals.get_calendar("XNYS")


def _offset(clock_time):
    return pd.Timedelta(hours=clock_time.hour, minutes=clock_time.minute, seconds=clock_time.second)


def at(day, clock_time):
    """The UTC time of `clock_time` in New York on one date."""
    return (pd.Timestamp(day).normalize() + _offset(clock_time)).tz_localize(NY).tz_convert("UTC")


def at_each(days, clock_time):
    """The UTC time of `clock_time` in New York on each date of a Series (same index)."""
    days = pd.to_datetime(pd.Series(days)).dt.normalize()
    return (days + _offset(clock_time)).dt.tz_localize(NY).dt.tz_convert("UTC")


class Clock:
    """NYSE sessions from `first` to `last`, and the times the daily loop and the rules use."""

    def __init__(self, first="2015-01-01", last="2026-12-31"):
        self.sessions = nyse().sessions_in_range(first, last)

    def is_session(self, day):
        return pd.Timestamp(day).normalize() in self.sessions

    def decision_time(self, day):
        return at(day, DECISION)

    def open_time(self, day):
        return nyse().session_open(pd.Timestamp(day).normalize())

    def close_time(self, day):
        """16:00 New York time, or 13:00 on an early close."""
        return nyse().session_close(pd.Timestamp(day).normalize())

    def between(self, first, last):
        s = self.sessions
        return s[(s >= pd.Timestamp(first)) & (s <= pd.Timestamp(last))]

    def next_session(self, day):
        return self.sessions[self.sessions.searchsorted(pd.Timestamp(day).normalize(), side="right")]

    def previous_session(self, day):
        return self.sessions[self.sessions.searchsorted(pd.Timestamp(day).normalize(), side="left") - 1]
