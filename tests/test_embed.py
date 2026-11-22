"""Tests for the reader job (reader/embed.py), on synthetic stories, a tiny random ModernBERT and a made-up
tokenizer: no store, no real weights. The last test feeds the job's own rows to the World, so the job's output
passes the time wall's checks (review finding M-3)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from reader import embed as E  # noqa: E402
from world import rules  # noqa: E402
from world.world import World, embedding_problems  # noqa: E402

torch = pytest.importorskip("torch")


def tiny():
    from transformers import ModernBertConfig, ModernBertModel
    torch.manual_seed(0)
    cfg = ModernBertConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=3,
                           num_attention_heads=2, pad_token_id=0, bos_token_id=1, eos_token_id=2, cls_token_id=1,
                           sep_token_id=2, max_position_embeddings=128)
    return ModernBertModel(cfg).eval()


class Tok:
    """A made-up tokenizer: [CLS], one id per word, [SEP]."""
    pad_token_id = 0

    def __call__(self, texts, truncation=True, max_length=256):
        ids = [[1] + [4 + sum(map(ord, w)) % 60 for w in t.split()][: max_length - 2] + [2] for t in texts]
        return {"input_ids": ids}


def stories(n=40, seed=0):
    rng = np.random.default_rng(seed)
    created = pd.to_datetime(rng.choice(pd.date_range("2015-06-01", "2025-06-01", freq="h"), n), utc=True)
    updated = created + pd.to_timedelta(rng.integers(0, 7200, n), unit="s")
    words = ["alpha", "beta", "gamma", "delta", "rise", "fall", "deal", "chip"]
    text = [" ".join(rng.choice(words, int(rng.integers(1, 12)))) for _ in range(n)]
    st = pd.DataFrame({"story_id": rng.permutation(np.arange(1000, 1000 + n)), "created_at": created,
                       "updated_at": updated, "headline": text})
    return st


def test_select_keeps_2016_on_with_the_rules_vintage_and_time():
    st = stories(200)
    st.loc[3, "updated_at"] = st.loc[3, "created_at"] + pd.Timedelta(days=4)  # dropped by keep_story
    se = pd.DataFrame({"story_id": np.r_[st.story_id.to_numpy(), st.story_id.to_numpy()[:5]]})  # repeats too
    got = E.select(st, se)
    ny = pd.to_datetime(got.created_at, utc=True).dt.tz_convert("America/New_York").dt.year
    assert (ny >= 2016).all() and got.story_id.is_monotonic_increasing and got.story_id.is_unique
    assert st.loc[3, "story_id"] not in set(got.story_id)
    want = ((pd.to_datetime(got.created_at, utc=True).dt.tz_convert("America/New_York").dt.year - 1).clip(upper=2024))
    assert (got.vintage_year == want).all()
    assert (pd.to_datetime(got.available_at, utc=True) == rules.embedding(got.updated_at)).all()
    old = pd.to_datetime(st.created_at, utc=True).dt.tz_convert("America/New_York").dt.year < 2016
    assert not set(st.story_id[old]) & set(got.story_id)


def test_an_embedding_does_not_depend_on_its_batch_and_leaves_padding_out():
    m = tiny()
    enc = Tok()(list(stories(30).headline))["input_ids"]
    last, avg = E.embed_ids(m, enc, batch=8)
    for i, e in enumerate(enc):
        l1, a1 = E.embed_ids(m, [e], batch=1)
        assert np.allclose(last[i], l1[0], atol=1e-4) and np.allclose(avg[i], a1[0], atol=1e-4)
    e = torch.tensor([enc[0]])
    with torch.inference_mode():
        out = m(input_ids=e, attention_mask=torch.ones_like(e), output_hidden_states=True)
    assert np.allclose(last[0], out.last_hidden_state[0].mean(0).numpy(), atol=1e-4)
    assert np.allclose(avg[0], torch.stack(out.hidden_states[1:])[:, 0].mean(1).mean(0).numpy(), atol=1e-4)


def test_a_part_round_trips_in_float16(tmp_path):
    st = E.select(stories(20), pd.DataFrame({"story_id": stories(20).story_id}))
    rng = np.random.default_rng(1)
    last, avg = rng.normal(0, 3, (len(st), 32)), rng.normal(0, 300, (len(st), 32))
    E.write_atomic(E.part_table(st, [5] * len(st), last, avg), tmp_path / "p.parquet")
    back, bl, ba = E.read_part(tmp_path / "p.parquet")
    assert np.array_equal(bl, last.astype(np.float16)) and bl.dtype == np.float16
    assert np.array_equal(ba, avg.astype(np.float16))
    assert (back.story_id.to_numpy() == st.story_id.to_numpy()).all()
    assert (pd.to_datetime(back.available_at, utc=True).to_numpy() == pd.to_datetime(st.available_at, utc=True).to_numpy()).all()
    assert not list(tmp_path.glob("*.tmp"))
    with pytest.raises(ValueError):
        E.part_table(st, [5] * len(st), last * 1e6, avg)  # beyond float16


def _run(monkeypatch, st, out):
    from reader import cutoff
    monkeypatch.setattr(E, "PART", 7)
    monkeypatch.setattr(E, "load_model", lambda v: tiny())
    monkeypatch.setattr(cutoff, "tokenizer", lambda: Tok())
    E.cmd_run(st, out, log=lambda *a: None)


def _all_rows(out):
    frames = []
    for p in sorted(out.glob("v*/part-*.parquet")):
        d, last, avg = E.read_part(p)
        d["emb_last"], d["emb_avg"] = list(last), list(avg)
        frames.append(d)
    return pd.concat(frames, ignore_index=True).sort_values("story_id", ignore_index=True)


def test_a_stop_and_a_restart_give_the_same_rows_as_one_run(monkeypatch, tmp_path):
    st = E.select(stories(60), pd.DataFrame({"story_id": stories(60).story_id}))
    _run(monkeypatch, st, tmp_path / "a")
    one = _all_rows(tmp_path / "a")
    assert len(one) == len(st) and set(one.story_id) == set(st.story_id)
    _run(monkeypatch, st, tmp_path / "b")
    victims = sorted((tmp_path / "b").glob("v*/part-*.parquet"))[::2]
    for p in victims:
        p.unlink()  # a stop: these parts never got written
    (victims[0].with_name(victims[0].name + ".tmp")).write_bytes(b"half a part")  # and one was cut off mid-write
    _run(monkeypatch, st, tmp_path / "b")
    two = _all_rows(tmp_path / "b")
    pd.testing.assert_frame_equal(one.drop(columns=["emb_last", "emb_avg"]), two.drop(columns=["emb_last", "emb_avg"]))
    for c in ("emb_last", "emb_avg"):
        assert np.allclose(np.stack(one[c]).astype(float), np.stack(two[c]).astype(float), atol=1e-2)


def test_a_restart_on_another_story_set_stops(monkeypatch, tmp_path):
    st = E.select(stories(60), pd.DataFrame({"story_id": stories(60).story_id}))
    _run(monkeypatch, st, tmp_path)
    with pytest.raises(SystemExit, match="another story set"):
        _run(monkeypatch, st.iloc[1:].reset_index(drop=True), tmp_path)


def test_the_jobs_rows_pass_the_time_wall(monkeypatch, tmp_path):
    tables = synthetic.make_tables(0)
    st = E.select(tables["stories"], tables["story_entities"])
    _run(monkeypatch, st, tmp_path)
    rows = _all_rows(tmp_path)
    assert embedding_problems(rows, tables["stories"]) == []
    w = World(**tables, embeddings=rows[["story_id", "vintage_year", "available_at", "emb_last", "emb_avg"]])
    v = w.view(pd.Timestamp("2017-03-15 14:00", tz="UTC"))
    assert set(v.embeddings.rows.story_id) == set(v.story_entities.story_id) & set(rows.story_id)


def test_the_set_hash_changes_when_a_story_is_edited():
    st = stories(10)
    h = E.set_hash(st.story_id, st.updated_at)
    st.loc[4, "updated_at"] += pd.Timedelta(seconds=1)
    assert E.set_hash(st.story_id, st.updated_at) != h
