"""View: what an agent may see at time t. It is the only thing an agent may import from this project.

A view holds copies of the records visible at t (world/world.py sets when each record becomes visible), and nothing
else: no reference to the World, and no array that reaches later rows. Its key columns are plain strings.

Tables:
- bars: entity_id, share_class, symbol, date, open (the bar's first trade), high, low, close, volume, trades, vwap,
  ret (the close-to-close total return, with corrections), incomplete, member (a member that day), no_trade
- labels: entity_id, share_class, date, end, label (the open-to-open total return from the official open on `date` to
  the official open on `end`, or to the close on `end` where `at_close`: a company's last trading day), at_close
- stories: story_id, created_at, updated_at, headline, symbols
- story_entities: story_id, entity_id (the single-firm filter's companies)
Every table has visible_at, the time its row entered the views.
"""
from .clock import NY


class View:
    """The records visible at time t, and the S&P 500 members at t. today is t's New York date, and sessions are the
    NYSE sessions up to today."""

    def __init__(self, t, sessions, members, joined, bars, labels, stories, story_entities):
        self.t = t
        self.today = t.tz_convert(NY).tz_localize(None).normalize()
        self.sessions = sessions[sessions <= self.today].copy()
        self.members = members
        self.joined = joined
        self.bars = bars
        self.labels = labels
        self.stories = stories
        self.story_entities = story_entities
