"""The vintage rule (PLAN 5.2 and 9.11): each story is read by the ChronoBERT vintage from the year before it was
published, in New York time.

The year comes from created_at, not from when the story became available: a story published at 23:50 on
2019-12-31 becomes available in 2020, but the 2019 vintage could have trained on it, so it gets the 2018 vintage."""
import pandas as pd

FIRST, LAST = 2014, 2024  # the vintages PLAN 9.13 lists


def vintage_for(created_at):
    """The vintage year for each story's created_at (UTC times): the year before, capped at the latest vintage, so
    news from 2025 and 2026 is read by the 2024 model (PLAN 5.2)."""
    year = pd.to_datetime(pd.Series(created_at), utc=True).dt.tz_convert("America/New_York").dt.year
    v = (year - 1).clip(upper=LAST)
    if (v < FIRST).any():
        raise ValueError(f"no vintage before {FIRST}: a story from {FIRST} or earlier can't be read")
    return v


def breaches(embeddings, stories):
    """Embedding rows not read by exactly the vintage the rule names for their story (should be none). A missing
    story counts too."""
    x = embeddings.merge(stories[["story_id", "created_at"]], on="story_id", how="left")
    known = x.created_at.notna()
    want = pd.Series(pd.NA, index=x.index, dtype="Int64")
    want[known] = vintage_for(x.created_at[known]).to_numpy()
    return x[~known | (x.vintage_year != want).fillna(True)]
