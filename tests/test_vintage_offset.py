"""Tests for the older-vintage rerun's vintage_offset (research/audit/cutoff.md section 10.1, M3 step 7): the rule
with offset 1 by hand, the default World still refusing a wrong-vintage row, the offset World refusing the rule's
own vintage, the sealed years shut to an offset World, and the offset in the run's settings. Synthetic tables only."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from agent.track_a import TrackA  # noqa: E402
from eval import leaks  # noqa: E402
from reader import vintage as V  # noqa: E402
from sim import seal, simulator  # noqa: E402
from world.clock import Clock  # noqa: E402
from world.world import World, embedding_problems  # noqa: E402

NY = "America/New_York"


def ny(s):
    return pd.Timestamp(s, tz=NY).tz_convert("UTC")


def test_offset_one_gives_the_vintage_a_year_older_by_hand():
    created = pd.Series([ny("2016-06-01 10:00"), ny("2016-12-31 23:50"), ny("2017-01-01 00:10"),
                         ny("2019-12-31 23:50"), ny("2024-03-01 12:00"), ny("2025-03-01 12:00"),
                         ny("2026-10-01 12:00")])
    assert list(V.vintage_for(created)) == [2015, 2015, 2016, 2018, 2023, 2024, 2024]  # the rule, unchanged
    assert list(V.vintage_for(created, 1)) == [2014, 2014, 2015, 2017, 2022, 2023, 2023]  # 2025 and 2026 by 2023


def test_only_offsets_0_and_1_are_accepted():
    created = pd.Series([ny("2018-06-01 10:00")])
    for bad in (2, -1, True, 0.5, "1"):
        with pytest.raises(ValueError, match="vintage_offset"):
            V.vintage_for(created, bad)
    with pytest.raises(ValueError, match="no vintage before 2014"):
        V.vintage_for(pd.Series([ny("2015-06-01 10:00")]), 1)


def older(tables):
    """make_embeddings' rows with each vintage a year older, as the older reader writes them."""
    emb = synthetic.make_embeddings(tables)
    created = emb.story_id.map(tables["stories"].set_index("story_id").created_at)
    return emb.assign(vintage_year=V.vintage_for(created, 1).to_numpy())


def test_the_default_world_still_refuses_a_wrong_vintage_row():
    tables = synthetic.make_tables(0)
    emb = synthetic.make_embeddings(tables)
    World(**tables, embeddings=emb)  # the rule's vintages: accepted
    one = emb.copy()
    one.loc[7, "vintage_year"] -= 1  # a single row read a year older
    with pytest.raises(ValueError, match="1 rows were not read by the vintage the rule names"):
        World(**tables, embeddings=one)
    with pytest.raises(ValueError, match="not read by the vintage the rule names"):
        World(**tables, embeddings=older(tables))  # the whole older table
    with pytest.raises(ValueError, match="not read by the vintage the rule names"):
        World(**tables, embeddings=older(tables), vintage_offset=0)


def test_the_offset_world_takes_the_older_table_and_refuses_the_rules_vintage():
    tables = synthetic.make_tables(0)
    w = World(**tables, embeddings=older(tables), vintage_offset=1, embedding_window_days=None)
    assert w.vintage_offset == 1
    v = w.view(Clock().decision_time("2017-03-15"))
    assert len(v.embeddings) and set(v.embeddings.rows.vintage_year) <= {2014, 2015}
    with pytest.raises(ValueError, match="not read by the vintage 1 year older"):
        World(**tables, embeddings=synthetic.make_embeddings(tables), vintage_offset=1)
    mixed = older(tables)
    mixed.loc[3, "vintage_year"] += 1  # one row with the rule's vintage
    assert embedding_problems(mixed, tables["stories"], 1) == ["1 rows were not read by the vintage 1 year older"]
    with pytest.raises(ValueError, match="vintage_offset"):
        World(**tables, embeddings=older(tables), vintage_offset=2)


def test_the_offset_is_fixed_when_the_world_is_built():
    tables = synthetic.make_tables(0)
    w = World(**tables, embeddings=older(tables), vintage_offset=1)
    with pytest.raises(AttributeError):
        w.vintage_offset = 0
    assert World(**tables).vintage_offset == 0


def test_an_offset_world_never_opens_the_sealed_years():
    tables = synthetic.make_tables(0)
    with pytest.raises(PermissionError, match="never opens the sealed years"):
        World(**tables, embeddings=older(tables), vintage_offset=1, allow_sealed=True)
    w = World(**tables, embeddings=older(tables), vintage_offset=1)
    w.allow_sealed = True  # as sim.simulator.run sets it under a seal: still refused
    with pytest.raises(PermissionError, match="vintage_offset"):
        w.view(Clock().decision_time(str(seal.sealed_start().date())))
    w.view(Clock().decision_time("2017-03-15"))  # a dev date is fine


class Idle:
    params = {}

    def decide(self, view):
        return None

    def freeze(self):
        return Idle()


def test_the_runner_refuses_an_offset_world_for_any_sealed_date(monkeypatch):
    tables = synthetic.make_tables(0)
    w = World(**tables, embeddings=older(tables), vintage_offset=1)
    monkeypatch.setattr(seal, "check", lambda *a, **k: None)  # even with a seal that holds
    last = str(seal.sealed_start().date())
    with pytest.raises(PermissionError, match="vintage_offset may not run into the sealed years"):
        simulator.run(w, Idle(), "2017-01-03", last, settings={})
    with pytest.raises(PermissionError, match="vintage_offset may not run into the sealed years"):
        simulator.run_many(w, {"live": Idle()}, "2017-01-03", last, settings={})
    assert w.allow_sealed is False


def test_the_offset_goes_into_the_runs_settings_and_their_hash(monkeypatch):
    tables = synthetic.make_tables(0)
    seen = []
    monkeypatch.setattr(seal, "check", lambda first, last, settings, **k: seen.append(settings))
    rule = World(**tables, embeddings=synthetic.make_embeddings(tables))
    off = World(**tables, embeddings=older(tables), vintage_offset=1)
    for w in (rule, off):
        simulator.run(w, Idle(), "2017-01-03", "2017-01-05", settings={})
        simulator.run_many(w, {"live": Idle()}, "2017-01-03", "2017-01-05", settings={})
    run_rule, many_rule, run_off, many_off = seen
    assert "vintage_offset" not in run_rule and "vintage_offset" not in many_rule  # old hashes stay as they were
    assert run_off["vintage_offset"] == 1 and many_off["vintage_offset"] == 1
    assert seal.settings_hash(run_off) != seal.settings_hash(run_rule)
    assert {k: v for k, v in run_off.items() if k != "vintage_offset"} == run_rule


def test_the_older_reader_writes_rows_the_offset_world_takes(monkeypatch, tmp_path):
    pytest.importorskip("torch")
    import test_embed as T
    from reader import cutoff
    from reader import embed as E
    tables = synthetic.make_tables(0)
    st = E.select(tables["stories"], tables["story_entities"], offset=1)
    rule = E.select(tables["stories"], tables["story_entities"])
    assert list(st.story_id) == list(rule.story_id) and (st.vintage_year == rule.vintage_year - 1).all()
    monkeypatch.setattr(E, "PART", 7)
    monkeypatch.setattr(E, "load_model", lambda v: T.tiny())
    monkeypatch.setattr(cutoff, "tokenizer", lambda: T.Tok())
    E.cmd_run(st, tmp_path, log=lambda *a: None, offset=1)
    import json
    m = json.loads(next(tmp_path.glob("v*/manifest.json")).read_text(encoding="utf-8"))
    assert m["vintage_offset"] == 1 and "vintage_offset" not in E.manifest(2015, rule)
    rows = T._all_rows(tmp_path)[["story_id", "vintage_year", "available_at", "emb_last", "emb_avg"]]
    assert embedding_problems(rows, tables["stories"], 1) == []
    World(**tables, embeddings=rows, vintage_offset=1)
    with pytest.raises(ValueError, match="not read by the vintage the rule names"):
        World(**tables, embeddings=rows)
    assert np.isfinite(np.stack(rows.emb_last).astype(float)).all()


@pytest.mark.parametrize("how", leaks.HOW)
def test_non_interference_for_the_chosen_configuration_on_the_older_table(how):
    """T09's settings (band 15, hold 5), with the made-up world's shorter fit schedule, on an offset World."""
    base = synthetic.make_tables(0)
    tables = {**base, "embeddings": older(base)}
    make = lambda: TrackA(fit_after_months=2, min_val_months=1, band=15, hold=5)  # noqa: E731
    assert leaks.non_interference(tables, make, "2016-10-03", "2017-03-15", how, seed=4, vintage_offset=1) == []
