"""Benchmark ChronoBERT on this laptop's CPU, reading real Alpaca headlines.

Measures tokens per headline, headlines per second, and peak memory, for both attention modes the
plan flagged (sdpa and eager), producing the two embeddings the reader stores: the mean of the
last layer, and the mean over all layers. Model files are cached under DATA_DIR/hf, not on C:.

Usage: python research/bench_chronobert.py [n_headlines]
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_pipeline import alpaca  # noqa: E402
from data_pipeline.settings import DATA_DIR  # noqa: E402

os.environ.setdefault("HF_HOME", str(DATA_DIR / "hf"))
import torch  # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402

MODEL = "manelalab/chrono-bert-v1-20151231"


def headlines(n):
    out = []
    for body in alpaca.pages("/v1beta1/news", start="2016-01-04T00:00:00Z", end="2016-01-15T23:59:59Z",
                             limit=50, sort="asc", include_content="false"):
        out += [s["headline"] for s in body.get("news", []) if s.get("headline")]
        if len(out) >= n:
            return out[:n]
    return out


def embed(model, tok, texts, batch=64):
    last_means, all_means = [], []
    with torch.inference_mode():
        for i in range(0, len(texts), batch):
            enc = tok(texts[i:i + batch], padding=True, truncation=True, max_length=64, return_tensors="pt")
            out = model(**enc, output_hidden_states=True)
            mask = enc["attention_mask"].unsqueeze(-1).float()
            pool = lambda h: (h * mask).sum(1) / mask.sum(1)  # noqa: E731
            last_means.append(pool(out.last_hidden_state))
            all_means.append(torch.stack([pool(h) for h in out.hidden_states[1:]]).mean(0))
    return torch.cat(last_means), torch.cat(all_means)


def peak_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1e6
    except ImportError:
        return float("nan")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    texts = headlines(n)
    tok = AutoTokenizer.from_pretrained(MODEL)
    lengths = sorted(len(tok(t)["input_ids"]) for t in texts)
    print(f"{len(texts)} headlines | tokens per headline: median {lengths[len(lengths) // 2]}, "
          f"p95 {lengths[int(len(lengths) * 0.95)]}, max {lengths[-1]} | torch threads {torch.get_num_threads()}")
    for attn in ("sdpa", "eager"):
        try:
            model = AutoModel.from_pretrained(MODEL, attn_implementation=attn).eval()
        except Exception as exc:
            print(f"{attn}: failed to load: {exc}")
            continue
        embed(model, tok, texts[:64])  # warm-up
        t0 = time.perf_counter()
        try:
            last, mean_all = embed(model, tok, texts)
        except Exception as exc:
            print(f"{attn}: failed to run: {exc}")
            continue
        secs = time.perf_counter() - t0
        rate = len(texts) / secs
        print(f"{attn}: {rate:.0f} headlines/s ({secs:.1f}s) | embeddings {tuple(last.shape)} and {tuple(mean_all.shape)} "
              f"| finite {bool(torch.isfinite(last).all() and torch.isfinite(mean_all).all())} | process memory {peak_mb():.0f} MB "
              f"| 1M headlines ≈ {1e6 / rate / 3600:.1f} h, 3M ≈ {3e6 / rate / 3600:.1f} h")
        del model


if __name__ == "__main__":
    main()
