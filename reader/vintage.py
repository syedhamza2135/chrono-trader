"""The vintage rule (PLAN 5.2 and 9.11): each story is read by the ChronoBERT vintage from the year before it was
published, in New York time.

The year comes from created_at, not from when the story became available: a story published at 23:50 on
2019-12-31 becomes available in 2020, but the 2019 vintage could have trained on it, so it gets the 2018 vintage."""
import pandas as pd

FIRST, LAST = 2014, 2024  # the vintages PLAN 9.13 lists


def vintage_for(created_at):
    """The vintage year for each story's created_at (UTC times)."""
    year = pd.to_datetime(pd.Series(created_at), utc=True).dt.tz_convert("America/New_York").dt.year
    return year - 1


def breaches(embeddings, stories):
    """Embedding rows whose vintage isn't from before its story's New York year (should be none)."""
    x = embeddings.merge(stories[["story_id", "created_at"]], on="story_id", how="left")
    year = pd.to_datetime(x.created_at, utc=True).dt.tz_convert("America/New_York").dt.year
    return x[x.created_at.isna() | (x.vintage_year >= year)]
