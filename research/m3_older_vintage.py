"""M3 step 7: the older-vintage rerun (research/audit/cutoff.md section 10.1; decision 3 in research/m3_kickoff.md).

Every story is read again by the vintage a year older (reader/vintage.py, offset 1) into DATA_DIR/reader_older:
  python -m reader.embed run-older       the reading, detached, one vintage at a time (resumes where it stopped)
  python -m reader.embed finish-older    checks every part, writes the table and its two arrays
Then, one step per call, each holding the PC awake in its own process:
  python research/m3_older_vintage.py space    D:'s free space against the main table's files
  python research/m3_older_vintage.py count    the older table against the main one: rows, story ids, vintages
  python research/m3_older_vintage.py run      the chosen configuration (stage2.json), unchanged, on the older table
  python research/m3_older_vintage.py result   the warning rule, exactly as frozen, into m3_dev/older_result.json
The note on the result is research/m3_older_vintage.md, written by hand from that file.

The rule (cutoff.md 10.1, quoted): a warning if both "(a) the news effect with the older vintage is less than half
the news effect with the rule's; (b) the paired daily difference in IC (the rule's run minus the older run) is above
zero, one-sided at 5%." And: "If the news effect isn't above zero in the first place, the check says nothing, and
the report says so." "Above zero" means above zero at one-sided 5%, the test (b) uses (the lead's reading of 23 Nov,
made after the dev result, in research/m3_kickoff.md step 7). The news effect on a day is the agent's daily rank IC minus the price-only twin's that day. The
price-only twin reads no news, so its run from the comparison pass serves both. Dev years only: IC days whose
labels end by 2019-12-31, and the run stops on 2019-12-31. The run is a row of runs/trials.csv with no trial name,
so it adds nothing to the trial count.
"""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
import pandas as pd  # noqa: E402

import m3_dev_runs as dev  # noqa: E402
from agent.track_a import TrackA  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402
from eval import metrics, stats, trials  # noqa: E402
from reader.embed import OLDER, stay_awake  # noqa: E402
from sim import simulator  # noqa: E402
from world.world import World  # noqa: E402

STORE = DATA_DIR / "store"
OUT = dev.OUT / "older"
NOTE = ROOT / "research" / "m3_older_vintage.md"
MAIN_ROWS = 502712  # the main table's rows (research/audit/reader.md)
ALPHA = 0.05


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def space():
    free = shutil.disk_usage(str(DATA_DIR)).free
    need = sum((STORE / f).stat().st_size for f in ("embeddings.parquet", "embeddings_last.npy",
                                                    "embeddings_avg.npy"))
    parts = sum(p.stat().st_size for p in (DATA_DIR / "reader").glob("v*/part-*.parquet"))
    log(f"D: free {free / 1e9:.2f} GB; the main table and arrays {need / 1e9:.2f} GB; the main parts "
        f"{parts / 1e9:.2f} GB; so the older run needs about {(need + parts) / 1e9:.2f} GB")
    return free, need + parts


def count():
    import numpy as np
    from reader.vintage import vintage_for
    main = pd.read_parquet(STORE / "embeddings.parquet", columns=["story_id", "vintage_year", "available_at"])
    old = pd.read_parquet(OLDER / "embeddings.parquet", columns=["story_id", "vintage_year", "available_at"])
    st = pd.read_parquet(STORE / "stories.parquet", columns=["story_id", "created_at"]).set_index("story_id")
    out = {"main_rows": len(main), "older_rows": len(old),
           "same_story_ids": bool(np.array_equal(np.sort(main.story_id.to_numpy()), np.sort(old.story_id.to_numpy()))),
           "same_available_at": bool(main.set_index("story_id").available_at.sort_index().equals(
               old.set_index("story_id").available_at.sort_index())),
           "older_is_rule_minus_one": bool((old.vintage_year.to_numpy() ==
                                            vintage_for(old.story_id.map(st.created_at), 1).to_numpy()).all()),
           "older_by_vintage": {str(k): int(v) for k, v in old.vintage_year.value_counts().sort_index().items()},
           "main_by_vintage": {str(k): int(v) for k, v in main.vintage_year.value_counts().sort_index().items()}}
    out["ok"] = (out["main_rows"] == out["older_rows"] == MAIN_ROWS and out["same_story_ids"]
                 and out["same_available_at"] and out["older_is_rule_minus_one"])
    (dev.OUT / "older_count.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    log(json.dumps(out))
    return out


def run():
    s2 = json.loads((dev.OUT / "stage2.json").read_text(encoding="utf-8"))
    kw = s2["chosen_kw"]
    world = World.load(embeddings_store=OLDER, vintage_offset=1)
    agent = TrackA(**kw)
    s = {**dev.settings_of(s2["winner"], 2, kw, agent), "check": "older_vintage", "vintage_offset": 1,
         "embeddings_store": "reader_older"}
    t0 = time.time()
    r = simulator.run(world, agent, dev.FIRST, dev.LAST, cost_bps=dev.COST,
                      settings={"check": "older_vintage", "plan_sha256": s["plan_sha256"]})
    dev.save(r, OUT)
    trials.record(s, dev.FIRST, dev.LAST, ["live_older_vintage"], OUT, trial="", status="run")
    log(f"older-vintage run of {s2['winner']} {kw}: {(time.time() - t0) / 60:.1f} min, "
        f"{r.decisions.date.nunique()} decision days, forced sales {r.stats['forced_sales']}, "
        f"unmarked {r.stats['unmarked']}, fits {len(agent.fits)}")


def result():
    s2 = json.loads((dev.OUT / "stage2.json").read_text(encoding="utf-8"))
    world = World.load(embeddings=False)
    labels = dev.dev_labels(world)

    def ic(d):
        return metrics.within(metrics.daily_rank_ic(dev.load(d).decisions, labels), dev.DEV_FIRST, dev.IC_LAST)

    rule, older, price = ic(dev.OUT / "compare" / "live"), ic(OUT), ic(dev.OUT / "compare" / "price_only")
    effect_rule = stats.nw_mean((rule - price).dropna().to_numpy())
    effect_older = stats.nw_mean((older - price).dropna().to_numpy())
    diff = stats.nw_mean((rule - older).dropna().to_numpy())
    above = effect_rule["mean"] > 0 and effect_rule["p"] < ALPHA
    a = effect_older["mean"] < 0.5 * effect_rule["mean"]
    b = diff["p"] < ALPHA
    out = {"chosen": s2["winner"], "chosen_kw": s2["chosen_kw"], "ic_rule": stats.nw_mean(rule.to_numpy()),
           "ic_older": stats.nw_mean(older.to_numpy()), "ic_price_only": stats.nw_mean(price.to_numpy()),
           "news_effect_rule": effect_rule, "news_effect_older": effect_older, "rule_minus_older": diff,
           "news_effect_above_zero_at_5pct": bool(above), "a": bool(a), "b": bool(b),
           "warning": bool(above and a and b) if above else None,
           "outcome": ("warning" if a and b else "no warning") if above else
           "not informative: the rule's news effect is not above zero at one-sided 5%, so the check says nothing "
           "(the lead's reading, 23 Nov); (a), (b) and the numbers are descriptive only, outside the frozen rule"}
    (dev.OUT / "older_result.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    log(json.dumps(out, default=float))
    return out


if __name__ == "__main__":
    stay_awake()
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    {"space": space, "count": count, "run": run, "result": result}.get(step, lambda: print(__doc__))()
