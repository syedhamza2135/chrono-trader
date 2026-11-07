"""A made-up world for the leak tests: 60 companies over real NYSE sessions, with joins, removals, missing official
opens and stories. Its labels come from data_pipeline.store.labels, so the store's rule runs here too. Not a test
module (no test_ prefix)."""
import numpy as np
import pandas as pd

from data_pipeline import store
from world.clock import Clock

FIRST, LAST = "2016-01-04", "2017-06-30"


def make_tables(seed=0, n=60):
    rng = np.random.default_rng(seed)
    days = Clock().between(FIRST, LAST).astype("datetime64[ns]")
    ents = [f"E{i:02d}" for i in range(n)]
    member_from = [pd.Timestamp("2010-01-04")] * n
    member_to = [pd.NaT] * n
    for i in range(50, 55):  # five join in September 2016
        member_from[i] = pd.Timestamp("2016-09-01")
    for i in range(55, 58):  # three join in March 2017, after the leak tests' first decision
        member_from[i] = pd.Timestamp("2017-03-01")
    for i in range(40, 43):  # three leave in March 2017
        member_to[i] = pd.Timestamp("2017-03-01")
    member_to[43] = pd.Timestamp("2016-06-01")  # E43 leaves in June 2016 and rejoins in April 2017 (a second row)
    bars, opens = [], []
    for i, e in enumerate(ents):
        ret = rng.normal(0.0003, 0.015, len(days))
        close = 50 * np.exp(np.cumsum(np.log1p(ret)))
        prev = np.r_[close[0], close[:-1]]
        bar_open = prev * (1 + rng.normal(0, 0.004, len(days)))
        volume = np.exp(rng.normal(14 + i / 20, 0.3, len(days))).round()
        member = (days >= member_from[i]) & ((days < member_to[i]) if member_to[i] is not pd.NaT else True)
        ret_col = ret.copy()
        ret_col[0] = np.nan
        bars.append(pd.DataFrame({"entity_id": e, "share_class": "", "symbol": f"S{i:02d}", "date": days,
                                  "open": bar_open, "high": np.maximum(bar_open, close) * 1.01,
                                  "low": np.minimum(bar_open, close) * 0.99, "close": close, "volume": volume,
                                  "trades": (volume / 100).round(), "vwap": (bar_open + close) / 2, "ret": ret_col,
                                  "incomplete": False, "member": member, "no_trade": False}))
        official = bar_open * (1 + rng.normal(0, 0.001, len(days)))
        official[rng.random(len(days)) < 0.01] = np.nan  # a few stock-days without an official open
        opens.append(pd.DataFrame({"entity_id": e, "share_class": "", "date": days, "open": official}))
    bars = pd.concat(bars, ignore_index=True)
    opens = pd.concat(opens, ignore_index=True).dropna(subset=["open"]).reset_index(drop=True)
    labels = store.labels(bars, opens, data_end=days[-1])
    stamps = pd.to_datetime(rng.choice(days.to_numpy(), 3000)) + pd.to_timedelta(rng.integers(0, 86400, 3000), unit="s")
    created = pd.Series(stamps).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    updated = created + pd.to_timedelta(rng.integers(0, 3600, 3000), unit="s")
    who = rng.choice(ents, 3000)
    stories = pd.DataFrame({"story_id": np.arange(3000), "created_at": created, "updated_at": updated,
                            "headline": [f"news {k}" for k in range(3000)], "symbols": [[w] for w in who]})
    story_entities = pd.DataFrame({"story_id": np.arange(3000), "entity_id": who})
    membership = pd.DataFrame({"entity_id": ents + ["E43"], "member_from": member_from + [pd.Timestamp("2017-04-03")],
                               "member_to": pd.to_datetime(pd.Series(member_to + [pd.NaT]))})
    gap = (bars.entity_id == "E43") & (bars.date >= pd.Timestamp("2017-04-03"))
    bars.loc[gap, "member"] = True
    return {"bars": bars, "labels": labels, "opens": opens, "stories": stories, "story_entities": story_entities,
            "membership": membership}
