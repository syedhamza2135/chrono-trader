r"""Skeptic check of L2: are the 119 at_close labels on non-member days series cut by the 14-day window?
Counts and dates only. Run from the worktree root with CHRONO_ENV_FILE set (see check_m1.py)."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from data_pipeline import store  # noqa: E402

K = ["entity_id", "share_class"]
S = store.STORE
counts = json.loads((S / "counts.json").read_text())
print("counts:", {k: counts.get(k) for k in ("labels_at_close", "exits_stopped_trading", "exits_window_cut",
                                            "exits_failed", "data_end")})
lab = pd.read_parquet(S / "labels.parquet")
bars = pd.read_parquet(S / "bars.parquet", columns=K + ["date", "member", "volume"])
ac = lab[lab.at_close]
last_mem = bars[bars.member].groupby(K).date.max().rename("last_member")
last_bar = bars.groupby(K).date.max().rename("last_bar")
x = ac.merge(last_mem, left_on=K, right_index=True, how="left").merge(last_bar, left_on=K, right_index=True)
x["end_member"] = x.merge(bars[K + ["date", "member"]].rename(columns={"date": "end"}), on=K + ["end"]).member.values
non = x[~x.end_member]
gap = (non.end - non.last_member).dt.days
print("non-member at_close:", len(non), "| end == series' last bar:", int((non.end == non.last_bar).sum()),
      "| calendar days from last member day to end:", gap.value_counts().sort_index().to_dict())
print("   start day == end day:", int((non.date == non.end).sum()), "| start a member day:",
      int(non.merge(bars[K + ["date", "member"]], on=K + ["date"]).member.sum()))
mem = x[x.end_member]
print("member at_close:", len(mem), "| end == last member day:", int((mem.end == mem.last_member).sum()))
