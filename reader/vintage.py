"""The vintage rule (PLAN 5.2 and 9.11): each story is read by the ChronoBERT vintage from the year before it was
published, in New York time.

The year comes from created_at, not from when the story became available: a story published at 23:50 on
2019-12-31 becomes available in 2020, but the 2019 vintage could have trained on it, so it gets the 2018 vintage.

The older-vintage rerun (research/audit/cutoff.md section 10.1, M3 step 7) reads every story again one vintage
older: offset 1 gives a story from year Y the vintage Y-2, capped at 2023 (2016's stories by 2014, 2025 and 2026 by
2023). The offset is 0 everywhere else, and OFFSETS lists the only values allowed."""
import pandas as pd

FIRST, LAST = 2015, 2024  # the vintages that read news: 2015's stories are left out (M2 decision 2), so the 2014
# vintage, which PLAN 9.13 also lists, serves only the cutoff check (reader/cutoff.py) and the older-vintage rerun
OFFSETS = (0, 1)  # 0 is the rule; 1 is the older-vintage rerun, and only that check may use it


def check_offset(offset):
    """The offset itself, if it is one of OFFSETS; an error otherwise."""
    if isinstance(offset, bool) or offset not in OFFSETS:
        raise ValueError(f"vintage_offset must be one of {OFFSETS}")
    return offset


def vintage_for(created_at, offset=0):
    """The vintage year for each story's created_at (UTC times): the year before, capped at the latest vintage, so
    news from 2025 and 2026 is read by the 2024 model (PLAN 5.2). With offset 1, each one a year older (Y-2, capped
    at 2023)."""
    check_offset(offset)
    year = pd.to_datetime(pd.Series(created_at), utc=True).dt.tz_convert("America/New_York").dt.year
    v = (year - 1 - offset).clip(upper=LAST - offset)
    if (v < FIRST - offset).any():
        raise ValueError(f"no vintage before {FIRST - offset}: a story from {FIRST} or earlier can't be read")
    return v


def breaches(embeddings, stories, offset=0):
    """Embedding rows not read by exactly the vintage the rule names for their story (should be none), or, with
    offset 1, the vintage a year older. A missing story counts too."""
    x = embeddings.merge(stories[["story_id", "created_at"]], on="story_id", how="left")
    known = x.created_at.notna()
    want = pd.Series(pd.NA, index=x.index, dtype="Int64")
    want[known] = vintage_for(x.created_at[known], offset).to_numpy()
    return x[~known | (x.vintage_year != want).fillna(True)]
