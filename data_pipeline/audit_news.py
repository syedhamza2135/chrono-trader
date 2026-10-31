"""Audit the downloaded news and write research/audit/news.md. Works on whatever months exist so far.

Checks, by year:
- which sources the feed carries; everything after that uses Benzinga only, the source the plan reads
- volume, symbols per story, and the share kept by the single-firm filter (at most 2 companies, counted after
  mapping each tag to a company on the story's date with the identity table; a tag of a company outside the
  table counts as one company of its own)
- edit lags (how often and how late stories change after publishing)
- timestamps against session recaps ("22 Stocks Moving In Thursday's Pre-Market Session"): a recap
  stamped before its session began would mean timestamps run early, which is the leak that matters
- coverage of the companies the picking rule would choose (research/audit/universe_preview.csv)
- which ticker a renamed company's stories carry (FB or META)

Usage: python -m data_pipeline.audit_news
"""
from datetime import date

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .settings import DATA_DIR, ROOT

NEWS = DATA_DIR / "news"
OUT = ROOT / "research" / "audit"
FIRST_YEAR = 2015
BENZINGA = {"benzinga", ""}  # Benzinga's stories carried a blank source label until January 2022
COLUMNS = ["id", "created_at", "updated_at", "headline", "source", "url", "symbols"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
RECAP = r"\b(" + "|".join(DAYS) + r"|today)['’]s (pre-market|mid-day|after-hours) session"
WINDOWS = {"pre-market": (4.0, 9.5), "mid-day": (11.0, 14.0), "after-hours": (16.0, 20.0)}


def companies(df):
    """Per story: the companies its tags name on its date (identity table), and how many distinct companies it
    names, counting a tag outside the table as one company."""
    from .identity import SymbolIndex, normalize

    index = SymbolIndex()
    ex = df[["id", "ny", "symbols"]].explode("symbols").dropna(subset=["symbols"])
    ex["day"] = ex.ny.dt.date
    pairs = ex[["symbols", "day"]].drop_duplicates().reset_index(drop=True)
    found = [index.lookup(t, d) for t, d in zip(pairs.symbols, pairs.day)]
    pairs["entity"] = ["|".join(sorted(s)) for s in found]
    pairs["company"] = [e or "?" + normalize(t).split(".")[0] for e, t in zip(pairs.entity, pairs.symbols)]
    ex = ex.merge(pairs, on=["symbols", "day"], how="left")
    per = ex.groupby("id").agg(n_companies=("company", "nunique"),
                               entities=("entity", lambda s: tuple(sorted({e for e in s if e}))))
    out = df.join(per, on="id")
    out["n_companies"] = out.n_companies.fillna(0).astype(int)
    out["entities"] = out.entities.apply(lambda e: e if isinstance(e, tuple) else ())
    return out


def reading_load(single, uni):
    """Per year from 2016: single-firm stories naming a company that is an S&P 500 member on the story's New York
    date (reference/memberships.csv), and those naming one of the year's picked companies."""
    members = pd.read_csv(ROOT / "reference" / "memberships.csv", dtype=str)
    members["member_from"] = pd.to_datetime(members.member_from)
    members["member_to"] = pd.to_datetime(members.member_to).fillna(pd.Timestamp.max)
    s = single[single.year >= 2016].assign(day=lambda x: pd.to_datetime(x.day))
    j = s.merge(members, left_on="entities", right_on="entity_id")
    j = j[(j.member_from <= j.day) & (j.day < j.member_to)]
    picked = set(zip(uni.year, uni.entity_id))
    j["picked"] = [(y, e) in picked for y, e in zip(j.year, j.entities)]
    return [{"year": y, "members": g.id.nunique(), "picked": g[g.picked].id.nunique()} for y, g in j.groupby("year")]


def load():
    frames = [pq.read_table(p, columns=COLUMNS).to_pandas().assign(file_month=p.stem) for p in sorted(NEWS.glob("*.parquet"))]
    df = pd.concat(frames, ignore_index=True)
    df["created"] = pd.to_datetime(df["created_at"], utc=True)
    df["updated"] = pd.to_datetime(df["updated_at"], utc=True)
    df = df.sort_values("updated").drop_duplicates("id", keep="last")
    df["year"] = df.created.dt.year
    df["n_symbols"] = df.symbols.apply(len)
    df["lag_h"] = (df.updated - df.created).dt.total_seconds() / 3600
    df["ny"] = df.created.dt.tz_convert("America/New_York")
    return df


def recaps(df):
    """Session recaps, each marked inside its session's window, late, or early (stamped before the session began)."""
    found = df.headline.str.lower().str.extract(RECAP)
    rec = df.loc[found[0].notna(), ["year", "ny", "headline"]].assign(day=found[0], session=found[1])
    created = rec.ny.dt.day_of_week
    since = (created - rec.day.map({d: i for i, d in enumerate(DAYS)}).fillna(created)) % 7  # "today" is the day it was created
    hour = rec.ny.dt.hour + rec.ny.dt.minute / 60
    lo, hi = rec.session.map(lambda s: WINDOWS[s][0]), rec.session.map(lambda s: WINDOWS[s][1])
    rec["status"] = np.select([(since == 0) & (hour < lo), (since == 0) & (hour <= hi), since == 6],
                              ["early", "inside", "early"], "late")  # since == 6: the named day is tomorrow
    rec["fits_stamp_day"] = hour.between(lo, hi)  # an early recap that fits the session it was stamped in: a weekday typo
    return rec


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()
    months = sorted(p.stem for p in NEWS.glob("*.parquet"))
    # Each month was fetched by its start and end; this shows which timestamp Alpaca filters on.
    updated_inside = (df.updated_at.str[:7] == df.file_month).mean()
    created_earlier = (df.created_at.str[:7] < df.file_month).mean()
    df["label"] = df.source.replace("", "(blank)")
    links = df.groupby("label").url.apply(lambda s: s.str.contains("benzinga.com", regex=False).mean())
    sources = df[df.year >= FIRST_YEAR].groupby(["year", "label"]).size().unstack(fill_value=0)
    blank_until = df[df.source == ""].ny.max()
    first_seen = df[~df.source.isin(BENZINGA)].groupby("source").ny.min()
    total = len(df)
    df = df[df.source.isin(BENZINGA)].drop(columns=["url", "label"])
    older = int((df.year < FIRST_YEAR).sum())
    df = companies(df[df.year >= FIRST_YEAR])

    by_year = df.groupby("year").agg(
        stories=("id", "size"),
        no_symbol=("n_symbols", lambda s: (s == 0).mean()),
        single_firm=("n_companies", lambda s: ((s >= 1) & (s <= 2)).mean()),
        single_firm_by_tags=("n_symbols", lambda s: ((s >= 1) & (s <= 2)).mean()),
        edited_15m=("lag_h", lambda s: (s > 0.25).mean()),
        edited_1d=("lag_h", lambda s: (s > 24).mean()),
        edited_3d=("lag_h", lambda s: (s > 72).mean()),
        headline_words=("headline", lambda s: s.str.split().str.len().median()),
    )

    rec = recaps(df)
    rec_table = rec.groupby(["session", "year"]).status.value_counts().unstack(fill_value=0)
    rec_table = rec_table.reindex(columns=["inside", "late", "early"], fill_value=0)
    early = rec[rec.status == "early"].sort_values("ny")

    cov_rows, load_rows = [], []
    uni_path = OUT / "universe_preview.csv"
    if uni_path.exists():
        uni = pd.read_csv(uni_path, dtype={"entity_id": str})
        mask = (df.n_companies >= 1) & (df.n_companies <= 2)
        single = df.loc[mask, ["id", "year", "entities"]].assign(day=df.loc[mask, "ny"].dt.date).explode("entities")
        single = single.dropna(subset=["entities"])
        load_rows = reading_load(single, uni)
        for y in sorted(set(uni.year) & set(df.year)):
            picked = uni[uni.year == y]
            label = dict(zip(picked.entity_id, picked.symbol))
            s = single[(single.year == y) & single.entities.isin(label)]
            per_name = s.groupby("entities").size().reindex(list(label), fill_value=0)
            days = s.groupby("entities")["day"].nunique().reindex(list(label), fill_value=0)
            thin = per_name[per_name < 10]
            cov_rows.append({"year": y, "names": len(label), "median_stories": int(per_name.median()),
                             "min_stories": int(per_name.min()), "min_name": label[per_name.idxmin()],
                             "thin": ", ".join(f"{label[n]} ({c})" for n, c in thin.items()) or "-",
                             "median_days_with_news": int(days.median())})
    coverage = pd.DataFrame(cov_rows)

    tagged = df[["year", "ny", "symbols"]].explode("symbols")
    rename = tagged[tagged.symbols.isin(["FB", "META"])].groupby(["year", "symbols"]).size().unstack(fill_value=0)
    first_meta = tagged.loc[tagged.symbols == "META", "ny"].min()

    by_year.to_csv(OUT / "news_by_year.csv")
    pd.DataFrame(load_rows, columns=["year", "members", "picked"]).to_csv(OUT / "news_reading_load.csv", index=False)
    lines = [
        "# News audit",
        "",
        f"Generated by `python -m data_pipeline.audit_news` on {date.today()}, from {len(months)} downloaded months "
        f"({months[0]} to {months[-1]}): {total:,} unique stories after de-duplicating by id, "
        f"{len(df):,} of them Benzinga stories created since {FIRST_YEAR}.",
        "",
        "## Query window",
        "",
        f"{updated_inside:.2%} of stories have their `updated_at` inside the month whose query returned them, and "
        f"{created_earlier:.2%} were created in an earlier month. Alpaca filters by update time, so each story is stored once, "
        "under the month of its latest edit.",
        "",
        "## Sources",
        "",
        "| Year | " + " | ".join(sources.columns) + " |",
        "|---|" + "---|" * len(sources.columns),
        *[f"| {y} | " + " | ".join(f"{v:,}" for v in row) + " |" for y, row in sources.iterrows()],
        "",
        "Stories linking to benzinga.com, by source label: " + ", ".join(f"{k} {v:.1%}" for k, v in links.items()) + ".",
        f"The blank label is Benzinga's: its last story was created {blank_until:%Y-%m-%d %H:%M} New York time, "
        "when the label became `benzinga`.",
        *[f"First `{name}` story: {first:%Y-%m-%d %H:%M} New York time." for name, first in first_seen.items()],
        f"Everything below keeps Benzinga stories only (blank or `benzinga` label) and leaves out {older:,} stories "
        f"created before {FIRST_YEAR} and edited later.",
        "",
        "## Volume, symbols and edits by year",
        "",
        "| Year | Stories | No symbol | Kept by single-firm filter (1 to 2 companies) | Edited >15 min later | >1 day | >3 days | Median headline words |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {y} | {int(r.stories):,} | {r.no_symbol:.0%} | {r.single_firm:.0%} | {r.edited_15m:.1%} | {r.edited_1d:.1%} | "
          f"{r.edited_3d:.1%} | {r.headline_words:.0f} |" for y, r in by_year.iterrows()],
        "",
        "## Session recaps against their timestamps (created_at in New York time)",
        "",
        "Headlines such as \"22 Stocks Moving In Thursday's Pre-Market Session\". Windows: pre-market 4:00 to 9:30, "
        "mid-day 11:00 to 14:00, after-hours 16:00 to 20:00. A late stamp only delays a story. An early one, before the "
        "session began, would leak the future into the past, so early is the column that matters.",
        "",
        "| Session | Year | Recaps | Inside | Late | Early |",
        "|---|---|---|---|---|---|",
        *[f"| {s} | {y} | {r.sum():,} | {r.inside:,} | {r.late:,} | {r.early:,} |"
          for s in WINDOWS if s in rec_table.index for y, r in rec_table.loc[s].iterrows()],
        "",
        f"Early stamps ({len(early)}):" if len(early) else "No early stamps.",
        *[f"- {r.ny:%Y-%m-%d %a %H:%M}: {r.headline}" + (" (the stamp fits that session on the day it was published, "
          "so the weekday in the headline is likely a typo)" if r.fits_stamp_day else "") for r in early.head(20).itertuples()],
        "",
        "## Coverage of the stocks the rule would pick (single-firm stories per year)",
        "",
        "Tags are mapped to companies on each story's date with the identity table (`reference/identity.csv`), so PCLN in "
        "2016 counts for Booking, META in 2021 (Roundhill's ETF) for nobody, and BRK-B, BRK/B and plain BRK for Berkshire.",
        "",
        "| Year | Names | Median stories per name | Fewest (name) | Under 10 stories | Median days with news |",
        "|---|---|---|---|---|---|",
        *[f"| {r.year} | {r.names} | {r.median_stories} | {r.min_stories} ({r.min_name}) | {r.thin} | {r.median_days_with_news} |"
          for r in coverage.itertuples()],
        "",
        "## Reading load (single-firm stories, 2016 on)",
        "",
        "Stories passing the single-firm filter that name a company which is an S&P 500 member on the story's date, and "
        "those naming one of that year's picked companies. Hours assume the measured 6.5 headlines a second on the "
        "laptop's CPU; embeddings take 3 KB a story (two poolings of 768 float16 values).",
        "",
        "| Year | About members | About picked companies |",
        "|---|---|---|",
        *[f"| {r['year']} | {r['members']:,} | {r['picked']:,} |" for r in load_rows],
        *([f"| Total | {sum(r['members'] for r in load_rows):,} | {sum(r['picked'] for r in load_rows):,} |",
           "",
           f"About members: {sum(r['members'] for r in load_rows) / 6.5 / 3600:.0f} hours to read and "
           f"{sum(r['members'] for r in load_rows) * 3072 / 1e9:.1f} GB of embeddings. About picked companies: "
           f"{sum(r['picked'] for r in load_rows) / 6.5 / 3600:.0f} hours."] if load_rows else []),
        "",
        "## Renamed company: stories tagged FB or META, by year",
        "",
        f"First META tag: {first_meta:%Y-%m-%d}.",
        "",
        "| Year | " + " | ".join(rename.columns) + " |",
        "|---|" + "---|" * len(rename.columns),
        *[f"| {y} | " + " | ".join(str(v) for v in row) + " |" for y, row in rename.iterrows()],
    ]
    (OUT / "news.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
