"""Check the reader's smoke run (DATA_DIR/reader/smoke) row by row against the store and the rules (M2 step 3).
Prints counts, ids, times and vector statistics only, never a headline.
Usage: python research/check_smoke.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reader import embed as E  # noqa: E402
from reader.vintage import vintage_for  # noqa: E402
from world import rules  # noqa: E402
from world.world import embedding_problems  # noqa: E402


def main():
    folder = E.OUT / "smoke"
    parts = sorted(folder.glob("v*/part-*.parquet"))
    print("parts:", [str(p.relative_to(folder)) for p in parts], "| leftover .tmp files:", len(list(folder.rglob("*.tmp"))))
    import pyarrow.parquet as pq
    print("columns:", pq.read_schema(parts[0]))
    rows, last, avg = zip(*(E.read_part(p) for p in parts))
    rows, last, avg = pd.concat(rows, ignore_index=True), np.concatenate(last), np.concatenate(avg)
    st = pd.read_parquet(E.STORE / "stories.parquet", columns=["story_id", "created_at", "updated_at"])
    st = st.set_index("story_id")
    s = st.loc[rows.story_id]
    print(f"rows {len(rows)}, unique story ids {rows.story_id.nunique()}, by vintage {rows.vintage_year.value_counts().to_dict()}")
    print("vintage equals the rule for every row:", bool((vintage_for(s.created_at).to_numpy() == rows.vintage_year.to_numpy()).all()))
    want = rules.embedding(s.updated_at.reset_index(drop=True))
    print("available_at equals the story's updated_at + 15 min for every row:",
          bool((pd.to_datetime(rows.available_at, utc=True).reset_index(drop=True) == want).all()))
    ny = pd.to_datetime(s.created_at, utc=True).dt.tz_convert("America/New_York")
    print("New York created dates by vintage:", {int(v): (str(ny[rows.vintage_year.to_numpy() == v].min().date()),
                                                          str(ny[rows.vintage_year.to_numpy() == v].max().date()))
                                                  for v in sorted(rows.vintage_year.unique())})
    print("the World's checks on these rows:", embedding_problems(rows.assign(emb_last=list(last), emb_avg=list(avg)),
                                                                 st.reset_index()) or "none")
    print("first five rows:")
    print(rows.head(5).to_string())
    for name, x in (("emb_last", last), ("emb_avg", avg)):
        xf = x.astype(np.float32)
        print(f"{name}: shape {x.shape}, dtype {x.dtype}, all finite {bool(np.isfinite(xf).all())}, max |x| "
              f"{np.abs(xf).max():.1f}, row norms {np.linalg.norm(xf, axis=1).min():.1f} to "
              f"{np.linalg.norm(xf, axis=1).max():.1f}, identical rows {len(x) - len(np.unique(x, axis=0))}")
    print("n_tokens: min", int(rows.n_tokens.min()), "median", float(rows.n_tokens.median()), "max", int(rows.n_tokens.max()))
    # read five stories of each vintage again, one at a time, and compare
    from reader import cutoff
    tok = cutoff.tokenizer()
    heads = pd.read_parquet(E.STORE / "stories.parquet", columns=["story_id", "headline"]).set_index("story_id")
    for v in sorted(rows.vintage_year.unique()):
        model = E.load_model(int(v))
        idx = np.flatnonzero(rows.vintage_year.to_numpy() == v)[[0, 1, 2, 63, 127]]
        enc = E.encode(tok, heads.loc[rows.story_id.iloc[idx], "headline"])
        print(f"vintage {v}: token counts match n_tokens: {[len(e) for e in enc] == rows.n_tokens.iloc[idx].tolist()}")
        l1, a1 = E.embed_ids(model, enc, batch=1)
        dl = np.abs(l1 - last[idx].astype(np.float32)).max()
        da = np.abs(a1 - avg[idx].astype(np.float32)).max()
        print(f"vintage {v}: read alone against the batch: max difference emb_last {dl:.4f}, emb_avg {da:.4f}")
        other = E.load_model(2016 if v == 2015 else 2023)
        lo, _ = E.embed_ids(other, enc, batch=1)
        print(f"vintage {v}: another vintage gives other vectors: max difference {np.abs(lo - l1).max():.3f}")


if __name__ == "__main__":
    main()
