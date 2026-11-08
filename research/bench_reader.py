"""Benchmark the reader on this laptop's CPU with real headlines from the event store (M2 kickoff,
research/m2_kickoff.md). Prints counts, losses and timings only, never a headline.

1. Token lengths of every story in story_entities. All 11 vintages share one tokenizer (identical files on Hugging
   Face), so one count serves them all.
2. Headlines a second for the two poolings the reader stores (the mean of the last layer, and the mean over the 22
   layers' outputs), in random order as research/bench_chronobert.py did, and sorted by length, at a few batch sizes
   and thread counts. Also checks that a headline's embedding doesn't depend on its batch.
3. A pilot of the cutoff check's measure: one vintage's masked-word loss on samples from three years, with fixed
   masks (15% of each headline's tokens, at least one).

The model comes from DATA_DIR/hf, offline, at a pinned commit.

Usage: python research/bench_reader.py [n_headlines] [n_per_year]
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_pipeline.settings import DATA_DIR  # noqa: E402

os.environ.setdefault("HF_HOME", str(DATA_DIR / "hf"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import torch  # noqa: E402
from transformers import AutoModel, AutoModelForMaskedLM, AutoTokenizer  # noqa: E402

MODEL, REVISION = "manelalab/chrono-bert-v1-20151231", "01122aa3fd7a07879a524b6897c41e55c1db091a"
STORE = DATA_DIR / "store"
MAXLEN = 128


class _PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD)] + [(n, ctypes.c_size_t) for n in (
        "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
        "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]


def peak_mb():
    """This process's peak working set (Windows)."""
    k, p = ctypes.windll.kernel32, ctypes.windll.psapi
    k.GetCurrentProcess.restype = ctypes.c_void_p
    p.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMC), wt.DWORD]
    m = _PMC()
    m.cb = ctypes.sizeof(_PMC)
    p.GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(m), m.cb)
    return m.PeakWorkingSetSize / 1e6


def headlines():
    ids = pq.read_table(STORE / "story_entities.parquet", columns=["story_id"]).column("story_id").unique()
    t = pq.read_table(STORE / "stories.parquet", columns=["story_id", "created_at", "headline"])
    t = t.filter(pc.is_in(t["story_id"], value_set=ids))
    df = t.to_pandas()
    df["year"] = df.created_at.dt.tz_convert("America/New_York").dt.year
    return df


def lengths(tok, texts, chunk=50_000):
    out = np.empty(len(texts), dtype=np.int32)
    for i in range(0, len(texts), chunk):
        enc = tok(texts[i:i + chunk])["input_ids"]
        out[i:i + len(enc)] = [len(x) for x in enc]
    return out


def embed(model, tok, texts, lens, batch, sort):
    order = np.argsort(lens, kind="stable") if sort else np.arange(len(texts))
    last = np.empty((len(texts), 768), np.float32)
    avg = np.empty((len(texts), 768), np.float32)
    info = {}
    with torch.inference_mode():
        for i in range(0, len(texts), batch):
            idx = order[i:i + batch]
            enc = tok([texts[j] for j in idx], padding=True, truncation=True, max_length=MAXLEN, return_tensors="pt")
            out = model(**enc, output_hidden_states=True)
            mask = enc["attention_mask"].unsqueeze(-1).float()
            n = mask.sum(1)
            last[idx] = ((out.last_hidden_state * mask).sum(1) / n).numpy()
            layers = torch.stack(out.hidden_states[1:])
            avg[idx] = ((layers * mask).sum(2) / n).mean(0).numpy()
            if not info:
                info = {"hidden_states": len(out.hidden_states),
                        "last_layer_equals_last_hidden_state": bool(torch.allclose(out.hidden_states[-1],
                                                                                   out.last_hidden_state))}
    return last, avg, info


def masked_loss(mlm, tok, texts, rng, batch=64):
    """Each headline's mean masked-token loss, with 15% of its non-special tokens masked (at least one)."""
    enc = tok(texts, truncation=True, max_length=MAXLEN)["input_ids"]
    losses = np.empty(len(texts))
    order = np.argsort([len(e) for e in enc], kind="stable")
    with torch.inference_mode():
        for i in range(0, len(texts), batch):
            idx = order[i:i + batch]
            width = max(len(enc[j]) for j in idx)
            ids = torch.full((len(idx), width), tok.pad_token_id)
            att = torch.zeros((len(idx), width), dtype=torch.long)
            labels = torch.full((len(idx), width), -100)
            for r, j in enumerate(idx):
                e = enc[j]
                ids[r, :len(e)] = torch.tensor(e)
                att[r, :len(e)] = 1
                inner = np.arange(1, len(e) - 1)  # not [CLS] or [SEP]
                k = max(1, int(round(0.15 * len(inner))))
                pick = torch.from_numpy(rng.choice(inner, size=k, replace=False))
                labels[r, pick] = ids[r, pick]
                ids[r, pick] = tok.mask_token_id
            h = mlm.model(input_ids=ids, attention_mask=att).last_hidden_state
            sel = labels != -100
            logits = mlm.decoder(mlm.head(h[sel]))
            ce = torch.nn.functional.cross_entropy(logits, labels[sel], reduction="none")
            rows = sel.nonzero()[:, 0]
            per = torch.zeros(len(idx)).index_add_(0, rows, ce) / sel.sum(1)
            losses[idx] = per.numpy()
    return losses


def ranges(n=256):
    """How large the two poolings get, against float16's range (largest finite value 65,504) and precision."""
    df = headlines()
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    rng = np.random.default_rng(2)
    idx = rng.choice(np.flatnonzero((df.year >= 2016).to_numpy()), size=n, replace=False)
    texts = [df.headline.iat[i] for i in idx]
    lens = lengths(tok, texts)
    model = AutoModel.from_pretrained(MODEL, revision=REVISION, attn_implementation="sdpa").eval()
    torch.set_num_threads(4)
    order = np.argsort(lens, kind="stable")
    per_layer = []
    with torch.inference_mode():
        for i in range(0, n, 64):
            enc = tok([texts[j] for j in order[i:i + 64]], padding=True, truncation=True, max_length=MAXLEN,
                      return_tensors="pt")
            out = model(**enc, output_hidden_states=True)
            mask = enc["attention_mask"].unsqueeze(-1).float()
            per_layer.append(torch.stack([(h * mask).sum(1) / mask.sum(1) for h in out.hidden_states]).numpy())
    pooled = np.concatenate(per_layer, axis=1)  # (23, n, 768): the embeddings' output, then the 22 layers
    last, avg = pooled[-1], pooled[1:].mean(0)
    for name, x in (("emb_last", last), ("emb_avg", avg)):
        h = x.astype(np.float16).astype(np.float32)
        rel = np.abs(h - x) / np.maximum(np.abs(x), 1e-12)
        print(f"{name}: largest |value| {np.abs(x).max():.1f}, 99.9th percentile {np.percentile(np.abs(x), 99.9):.2f},"
              f" median {np.median(np.abs(x)):.3f} | as float16: finite {bool(np.isfinite(h).all())}, largest "
              f"relative rounding error {rel.max():.1e}")
    print("largest |token mean| by layer (0 is the embeddings' output): "
          + ", ".join(f"{k} {np.abs(pooled[k]).max():.0f}" for k in range(pooled.shape[0])))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "ranges":
        return ranges(int(sys.argv[2]) if len(sys.argv) > 2 else 256)
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    per_year = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    t0 = time.perf_counter()
    df = headlines()
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    texts = df.headline.tolist()
    lens = lengths(tok, texts)
    print(f"{len(texts):,} headlines tokenized in {time.perf_counter() - t0:.0f}s (with loading) | tokens incl. "
          f"[CLS] and [SEP]: median {int(np.median(lens))}, p95 {int(np.percentile(lens, 95))}, p99 "
          f"{int(np.percentile(lens, 99))}, max {lens.max()} | over 64: {int((lens > 64).sum()):,}, over {MAXLEN}: "
          f"{int((lens > MAXLEN).sum()):,} | total tokens {int(np.minimum(lens, MAXLEN).sum()):,}")
    for y in sorted(df.year.unique()):
        m = (df.year == y).to_numpy()
        print(f"  {y}: {int(m.sum()):,} headlines, median {int(np.median(lens[m]))} tokens, mean {lens[m].mean():.1f}")

    rng = np.random.default_rng(0)
    pool = np.flatnonzero((df.year >= 2016).to_numpy())
    sample = rng.choice(pool, size=n, replace=False)
    st, sl = [texts[i] for i in sample], lens[sample]
    print(f"benchmark sample: {n} headlines from 2016 on, mean {sl.mean():.1f} tokens (all from 2016 on: "
          f"{lens[pool].mean():.1f}) | peak memory so far {peak_mb():.0f} MB")
    model = AutoModel.from_pretrained(MODEL, revision=REVISION, attn_implementation="sdpa").eval()
    embed(model, tok, st[:64], sl[:64], 64, True)  # warm-up
    ref = None
    for threads, batch, sort in ((4, 64, False), (4, 64, True), (4, 256, True), (8, 64, True)):
        torch.set_num_threads(threads)
        t1 = time.perf_counter()
        last, avg, info = embed(model, tok, st, sl, batch, sort)
        secs = time.perf_counter() - t1
        rate = n / secs
        same = "" if ref is None else (f" | max diff from the first run: last {np.abs(last - ref[0]).max():.1e}, "
                                       f"avg {np.abs(avg - ref[1]).max():.1e}")
        if ref is None:
            ref = (last, avg)
        print(f"threads {threads}, batch {batch}, {'sorted' if sort else 'random order'}: {rate:.1f} headlines/s "
              f"({secs:.0f}s) | finite {bool(np.isfinite(last).all() and np.isfinite(avg).all())} | {info}"
              f" | peak memory {peak_mb():.0f} MB{same}")
    del model

    torch.set_num_threads(4)
    mlm = AutoModelForMaskedLM.from_pretrained(MODEL, revision=REVISION, attn_implementation="sdpa").eval()
    rng = np.random.default_rng(1)
    for y in (2015, 2016, 2017):
        idx = rng.choice(np.flatnonzero((df.year == y).to_numpy() & (lens > 2)), size=per_year, replace=False)
        t1 = time.perf_counter()
        loss = masked_loss(mlm, tok, [texts[i] for i in idx], np.random.default_rng(y))
        secs = time.perf_counter() - t1
        print(f"vintage 2015, {y} headlines: masked-word loss {loss.mean():.3f} (standard error "
              f"{loss.std(ddof=1) / np.sqrt(len(loss)):.3f}, n {len(loss)}) | {len(loss) / secs:.1f} headlines/s | "
              f"peak memory {peak_mb():.0f} MB")


if __name__ == "__main__":
    main()
