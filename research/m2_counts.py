"""M2 kickoff counts (research/m2_kickoff.md): which stories the reader has to embed, by New York year and vintage.

Reads the event store (DATA_DIR/store) and prints counts only, never a headline. A story is in story_entities when it
passes the single-firm filter (1 or 2 companies) and names a company in the identity table. A view shows a (story,
company) pair only when world.world.known_from allows it: inside a membership or up to 14 days after one (at the
story's own time), or up to 400 days before one (from the membership's start). Otherwise never.

Usage: python research/m2_counts.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_pipeline.settings import DATA_DIR  # noqa: E402
from reader.vintage import LAST  # noqa: E402
from world import rules  # noqa: E402
from world.clock import NY  # noqa: E402
from world.world import NEVER, known_from, spells  # noqa: E402

STORE = DATA_DIR / "store"


def main():
    st = pd.read_parquet(STORE / "stories.parquet", columns=["story_id", "created_at", "updated_at"])
    se = pd.read_parquet(STORE / "story_entities.parquet")
    m = pd.read_parquet(STORE / "membership.parquet")
    m["entity_id"] = m.entity_id.astype(str)
    assert st.story_id.is_unique
    kept =rules.keep_story(st.created_at, st.updated_at).to_numpy()
    print(f"stories {len(st):,}, kept by the 3-day rule {int(kept.sum()):,}; story_entities {len(se):,} pairs, "
          f"{se.story_id.nunique():,} stories")

    created = pd.to_datetime(st.set_index("story_id").created_at, utc=True).dt.tz_convert(NY)
    day = created.dt.tz_localize(None).dt.normalize()
    se = se.assign(entity_id=se.entity_id.astype(str), day=se.story_id.map(day).to_numpy())
    sp = spells(m)
    se["known"] = known_from(se.entity_id, se.day, sp)
    # Inside a membership on the story's day (PLAN's reading load), as opposed to the 14 days after or 400 before.
    s = sp.assign(start=sp.start.astype("datetime64[ns]"), entity_id=sp.entity_id.astype("str")).sort_values("start")
    left = se[["entity_id", "day"]].assign(i=np.arange(len(se)), day=se.day.astype("datetime64[ns]"),
                                           entity_id=se.entity_id.astype("str"))
    left = left.sort_values("day", kind="stable")
    prev = pd.merge_asof(left, s, left_on="day", right_on="start", by="entity_id", direction="backward")
    prev = prev.set_index("i").sort_index()
    se["member"] = (prev.start.notna() & (prev.end.isna() | (prev.day < prev.end))).to_numpy()
    se["visible"] = se.known != NEVER

    per = se.groupby("story_id").agg(visible=("visible", "any"), member=("member", "any"))
    per["year"] = per.index.map(created.dt.year)
    per["vintage"] = (per.year - 1).clip(upper=LAST)
    per["day"] = per.index.map(day)
    split = json.loads((ROOT / "reference" / "split.json").read_text(encoding="utf-8"))
    data_end = pd.Timestamp(json.loads((STORE / "counts.json").read_text(encoding="utf-8"))["data_end"])
    print(f"data end {data_end.date()}; split periods: "
          + ", ".join(f"{k} {v['start']} to {v['end']}" for k, v in split["periods"].items()))
    for k, v in split["periods"].items():
        g = per[(per.day >= pd.Timestamp(v["start"])) & (per.day <= pd.Timestamp(v["end"]))]
        print(f"  {k}: member on the day {int(g.member.sum()):,} "
              f"(split.json {v['single_firm_stories_about_members']:,}), visible {int(g.visible.sum()):,}")

    rows = []
    for y, g in per.groupby("year"):
        rows.append({"year": y, "vintage": int(g.vintage.iloc[0]), "single_firm": len(g),
                     "member_on_day": int(g.member.sum()), "visible_ever": int(g.visible.sum()),
                     "visible_not_member": int((g.visible & ~g.member).sum()), "never_visible": int((~g.visible).sum()),
                     "visible_after_data_end": int((g.visible & (g.day > data_end)).sum())})
    t = pd.DataFrame(rows)
    tot = t.drop(columns=["year", "vintage"]).sum()
    print(t.to_string(index=False))
    print("all years:", dict(tot))
    since = t[t.year >= 2016].drop(columns=["year", "vintage"]).sum()
    print("2016 on:", dict(since))
    by_v = t[t.year >= 2016].groupby("vintage")[["visible_ever", "member_on_day"]].sum()
    print("2016 on, by vintage:\n" + by_v.to_string())
    vis = per[per.visible & (per.year >= 2016)]
    print(f"visible from 2016, through the data end: {int((vis.day <= data_end).sum()):,}; after it: "
          f"{int((vis.day > data_end).sum()):,}")
    # The stories a view can show that PLAN's count leaves out: pairs shown from a later join, or after an exit.
    pairs = se[se.visible & ~se.member]
    # Shown from a past membership's start (the 14 days after it) or from a later one's (the 400 days before it).
    after = pairs.known.to_numpy() <= pd.DatetimeIndex(pairs.day.astype("datetime64[ns]")).tz_localize(NY).as_unit(
        "ns").asi8
    print(f"visible pairs outside a membership: {len(pairs):,} ({int(after.sum()):,} in the 14 days after one, "
          f"{int((~after).sum()):,} in the 400 days before one)")


if __name__ == "__main__":
    main()
