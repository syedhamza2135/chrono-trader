"""A toy agent for M1, so the leak tests can run the whole loop before Track A's agent exists (M3).

It sees only the views the loop hands it, and it keeps what it saw in its own memory.
- Picking (PLAN 5.1 and 9.5): on the year's first decision, the `n_picks` members with the highest median daily
  dollar volume (raw close times volume) over the year before, ranked on each company's best class, without
  incomplete bars. In 2016 the first pick is on the first trading day of April, from January to March. A pick that
  leaves the index drops out until the next pick.
- Features, from the bars up to the last close: r1, r5 and r20 (log total returns) and vol20 (the standard deviation
  of the last 20 daily returns). A missing value counts as 0.
- Learning: on the first decision of each month, once `warmup` sessions have been lived, refit a scaler and a ridge
  on every row it has lived whose label is in the view. The target is the log label minus that day's mean. Until
  the first fit, the score is minus r5 (short-term reversal).
- Policy: long the top `n_side` and short the bottom `n_side`, at weights of plus and minus 1 / n_side.

`fits` records, for each refit, the decision time and the latest `visible_at` of its training labels, so the label
embargo test can check them.
"""
import numpy as np
import pandas as pd

from world.view import View  # noqa: F401 (the one import an agent may make from this project)

FEATURES = ["r1", "r5", "r20", "vol20"]


class ReversalAgent:
    def __init__(self, n_picks=50, n_side=10, penalty=1.0, warmup=126, first_pick="2016-04-01"):
        self.n_picks, self.n_side, self.penalty, self.warmup = n_picks, n_side, penalty, warmup
        self.first_pick = pd.Timestamp(first_pick)
        self.params = {"n_picks": n_picks, "n_side": n_side, "penalty": penalty, "warmup": warmup,
                       "first_pick": first_pick}
        self.picks, self.pick_year = [], None
        self.month, self.lived = None, 0
        self.memory = []  # feature rows it has seen: date, entity_id, share_class, features
        self.beta = self.mean = self.std = None
        self.fits = []

    # The stock list
    def pick(self, v):
        lo = pd.Timestamp(2016, 1, 1) if v.today.year == 2016 else v.today - pd.DateOffset(years=1)
        b = v.bars
        b = b[(b.date >= lo) & (b.date < v.today) & ~b.incomplete.astype(bool)]
        b = b[b.entity_id.astype(str).isin(v.members)]
        dv = (b.close * b.volume).groupby([b.entity_id.astype(str), b.share_class.astype(str)]).median()
        dv = dv.rename("dv").reset_index().sort_values(["dv", "entity_id", "share_class"], ascending=[False, True, True])
        best = dv.drop_duplicates("entity_id").head(self.n_picks)
        return list(zip(best.entity_id, best.share_class))

    # Features up to the last close
    def features(self, v, picks):
        b = v.bars
        recent = b[b.date >= v.today - pd.Timedelta(days=45)]
        key = pd.Series(list(zip(recent.entity_id.astype(str), recent.share_class.astype(str))), index=recent.index)
        recent = recent[key.isin(set(picks))]
        rows = []
        for (e, c), g in recent.groupby([recent.entity_id.astype(str), recent.share_class.astype(str)]):
            r = np.log1p(g.sort_values("date").ret.to_numpy(dtype=float))
            r = np.nan_to_num(r)
            rows.append((e, c, r[-1:].sum(), r[-5:].sum(), r[-20:].sum(), r[-20:].std() if len(r) > 1 else 0.0))
        f = pd.DataFrame(rows, columns=["entity_id", "share_class", *FEATURES])
        return pd.DataFrame({"entity_id": [e for e, _ in picks], "share_class": [c for _, c in picks]}).merge(
            f, on=["entity_id", "share_class"], how="left").fillna(0.0)

    # Learning
    def refit(self, v):
        lab = v.labels[["entity_id", "share_class", "date", "label", "visible_at"]].astype(
            {"entity_id": str, "share_class": str})
        mem = pd.concat(self.memory, ignore_index=True)
        x = mem.merge(lab, on=["entity_id", "share_class", "date"])
        if x.empty:
            return
        x = x.sort_values(["date", "entity_id", "share_class"], ignore_index=True)
        y = np.log1p(x.label.to_numpy(dtype=float))
        y = y - x.assign(y=y).groupby("date").y.transform("mean").to_numpy()
        X = x[FEATURES].to_numpy(dtype=float)
        self.mean, self.std = X.mean(axis=0), X.std(axis=0)
        self.std[self.std == 0] = 1.0
        Z = (X - self.mean) / self.std
        self.beta = np.linalg.solve(Z.T @ Z + self.penalty * np.eye(Z.shape[1]), Z.T @ y)
        self.fits.append({"t": v.t, "latest_label": x.visible_at.max(), "rows": len(x)})

    def score(self, f, v):
        if self.beta is None:
            return -f.r5.to_numpy(dtype=float)
        return ((f[FEATURES].to_numpy(dtype=float) - self.mean) / self.std) @ self.beta

    def rank(self, f):
        """Long the top n_side, short the bottom n_side, by prediction (ties by company id)."""
        f = f.sort_values(["prediction", "entity_id", "share_class"], ascending=[False, True, True], ignore_index=True)
        n = min(self.n_side, len(f) // 2)
        f["position"] = 0.0
        f.loc[: n - 1, "position"] = 1.0 / self.n_side
        f.loc[len(f) - n:, "position"] = -1.0 / self.n_side
        return f[["entity_id", "share_class", "prediction", "position"]]

    def decide(self, v):
        if v.today < self.first_pick:
            return None
        if self.pick_year != v.today.year:
            self.picks, self.pick_year = self.pick(v), v.today.year
        if self.month != (v.today.year, v.today.month):
            self.month = (v.today.year, v.today.month)
            if self.lived >= self.warmup and self.memory:
                self.refit(v)
        self.lived += 1
        live = [p for p in self.picks if p[0] in v.members]
        if not live:
            return None
        f = self.features(v, live)
        self.memory.append(f.assign(date=v.today))
        return self.rank(f.assign(prediction=self.score(f, v)))
