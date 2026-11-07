"""Skill metrics, computed after a run from its decisions and the realized labels."""
import pandas as pd


def daily_rank_ic(decisions, labels, min_stocks=10):
    """The Spearman correlation, each day, between the predictions and the realized labels (open-to-open total
    returns) across the stocks predicted that day (PLAN 9.10). Days with fewer than `min_stocks` stocks with both
    are left out. Returns a Series by date."""
    key = ["entity_id", "share_class", "date"]
    lab = labels[key + ["label"]].astype({"entity_id": str, "share_class": str})
    d = decisions[key + ["prediction"]].astype({"entity_id": str, "share_class": str})
    d["date"], lab["date"] = pd.to_datetime(d.date), pd.to_datetime(lab.date)
    x = d.merge(lab, on=key).dropna(subset=["prediction", "label"])
    out = {}
    for day, g in x.groupby("date"):
        if len(g) >= min_stocks:
            out[day] = g.prediction.rank().corr(g.label.rank())
    return pd.Series(out, name="rank_ic", dtype=float).sort_index()
