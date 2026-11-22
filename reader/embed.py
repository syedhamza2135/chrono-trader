"""The reader job (M2 step 3; research/m2_kickoff.md decision 4): every story in story_entities from 2016 on, its
headline read by the vintage the rule names (reader/vintage.py), into two float16 embeddings of 768 values each.
A pipeline job, like data_pipeline: it may read the whole store, but it reads headlines as text only (no price,
return or label) and never prints or saves one. It writes to D: only (DATA_DIR/reader and DATA_DIR/store).

Each row: story_id, vintage_year, available_at, n_tokens, emb_last, emb_avg.
- available_at is rules.embedding of the story's updated_at at the time of reading (review finding M-3). The World
  refuses a row whose available_at differs from its story's, so a story edited after it was read can't be served
  with an old vector.
- emb_last is the mean over the headline's tokens ([CLS] and [SEP] included, padding left out) of the last layer's
  output, after ModernBERT's final norm. emb_avg is the mean over the 22 layers' outputs of the same token mean.
- Cap of 256 tokens, above the longest headline (176), so nothing is cut in practice.

The run goes one vintage at a time, oldest first. A vintage's stories, in story_id order, are cut into parts of
5,000. Each part is sorted by token count, read in batches of 64 on 4 threads, and written as
DATA_DIR/reader/v{vintage}/part-{n:04d}.parquet under a temporary name, then renamed. A restart skips finished parts,
so a stop loses at most one part. Each vintage folder holds manifest.json, the parts' story ids (as counts, first,
last and a hash); a restart whose story set differs stops instead of mixing two sets.

Usage (python -m reader.embed ...):
  run             every vintage, resuming where it stopped
  smoke N         the first N stories of each of the 2015 and 2024 vintages, into DATA_DIR/reader/smoke
  finish          check every part and write DATA_DIR/store/embeddings.parquet and embeddings.json (step 5), then
                  the arrays
  arrays          write DATA_DIR/store/embeddings_last.npy and embeddings_avg.npy from embeddings.parquet, in its
                  row order, and record them in embeddings.json: World.load maps them read-only (judge J-3)

For M5 (review finding L-P8): embed_ids and read_stories work on any set of stories, so a morning job can read that
day's new stories with the vintage the rule names, with this same code.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_pipeline.settings import DATA_DIR  # noqa: E402
from reader import vintage as V  # noqa: E402
from world import rules  # noqa: E402

FIRST_YEAR = 2016  # 2015's stories are left out (M2 decision 2)
PART = 5000
BATCH = 64
CAP = 256
DIM = 768
OUT = DATA_DIR / "reader"
STORE = DATA_DIR / "store"


# ---------------------------------------------------------------- the stories

def select(stories, story_entities):
    """The stories to read: every story in story_entities created in New York year FIRST_YEAR or later and kept by
    rules.keep_story, with its vintage and available_at. Columns: story_id, created_at, updated_at, headline,
    vintage_year, available_at. Sorted by story_id."""
    ids = pd.unique(story_entities.story_id)
    s = stories[stories.story_id.isin(ids)].drop_duplicates("story_id")
    year = pd.to_datetime(s.created_at, utc=True).dt.tz_convert("America/New_York").dt.year
    s = s[(year >= FIRST_YEAR).to_numpy() & rules.keep_story(s.created_at, s.updated_at).to_numpy()].copy()
    s["vintage_year"] = V.vintage_for(s.created_at).to_numpy()
    s["available_at"] = rules.embedding(s.updated_at).to_numpy()
    return s.sort_values("story_id", ignore_index=True)


def read_stories():
    """select() on the store's tables (headlines are held in memory only)."""
    st = pd.read_parquet(STORE / "stories.parquet", columns=["story_id", "created_at", "updated_at", "headline"])
    se = pd.read_parquet(STORE / "story_entities.parquet", columns=["story_id"])
    return select(st, se)


def parts(story_ids):
    """story_ids (sorted) cut into parts of PART."""
    return [story_ids[i:i + PART] for i in range(0, len(story_ids), PART)]


def ids_hash(ids):
    return hashlib.sha256(np.asarray(ids, dtype="int64").tobytes()).hexdigest()


def set_hash(story_ids, updated_at):
    """A hash of each story_id with its updated_at (review finding L-P7): it changes if a story is edited."""
    ns = pd.to_datetime(pd.Series(updated_at), utc=True).dt.tz_convert(None).astype("datetime64[ns]").astype("int64")
    pairs = np.stack([np.asarray(story_ids, dtype="int64"), ns.to_numpy()], axis=1)
    return hashlib.sha256(np.ascontiguousarray(pairs).tobytes()).hexdigest()


def manifest(vintage, stories):
    """The parts of one vintage's stories, for manifest.json, with the pinned weights that read them (judge J-4: a
    restart or finish under other pins stops)."""
    from reader import cutoff
    pin = cutoff.PINS["vintages"].get(str(int(vintage)), {})
    ids = stories.story_id.to_numpy()
    return {"vintage": int(vintage), "weights": {"repo": pin.get("repo"), "commit": pin.get("commit")},
            "count": int(len(ids)), "part_size": PART, "ids_sha256": ids_hash(ids),
            "parts": [{"n": n, "count": int(len(p)), "first": int(p[0]), "last": int(p[-1]), "ids_sha256": ids_hash(p)}
                      for n, p in enumerate(parts(ids))]}


# ---------------------------------------------------------------- the model

def embed_ids(model, encoded, batch=BATCH, pad_id=0):
    """Both poolings for each headline's token ids (lists, [CLS] and [SEP] included), read in batches sorted by
    length. model is a ModernBertModel. Returns (last, avg) as float32 arrays in the input order."""
    import torch
    n = len(encoded)
    last = np.empty((n, model.config.hidden_size), np.float32)
    avg = np.empty((n, model.config.hidden_size), np.float32)
    order = np.argsort([len(e) for e in encoded], kind="stable")
    with torch.inference_mode():
        for i in range(0, n, batch):
            idx = order[i:i + batch]
            width = max(len(encoded[j]) for j in idx)
            ids = torch.full((len(idx), width), pad_id, dtype=torch.long)
            att = torch.zeros((len(idx), width), dtype=torch.long)
            for r, j in enumerate(idx):
                ids[r, :len(encoded[j])] = torch.tensor(encoded[j])
                att[r, :len(encoded[j])] = 1
            out = model(input_ids=ids, attention_mask=att, output_hidden_states=True)
            mask = att.unsqueeze(-1).float()
            count = mask.sum(1)
            last[idx] = ((out.last_hidden_state * mask).sum(1) / count).float().numpy()
            layers = torch.stack(out.hidden_states[1:])
            avg[idx] = ((layers * mask).sum(2) / count).mean(0).float().numpy()
    return last, avg


def encode(tok, texts, cap=CAP):
    enc = tok(list(texts), truncation=True, max_length=cap)["input_ids"]
    return [list(e) for e in enc]


# ---------------------------------------------------------------- the parts

def part_table(rows, n_tokens, last, avg):
    """One part as an Arrow table: story_id, vintage_year, available_at, n_tokens, emb_last, emb_avg (float16
    fixed-size lists)."""
    import pyarrow as pa

    def vec(x):
        x16 = np.ascontiguousarray(x.astype(np.float16))
        if not np.isfinite(x16).all():
            raise ValueError("an embedding is not finite in float16")
        return pa.FixedSizeListArray.from_arrays(pa.array(x16.reshape(-1), type=pa.float16()), x.shape[1])

    return pa.table({"story_id": pa.array(rows.story_id.to_numpy(dtype="int64")),
                     "vintage_year": pa.array(rows.vintage_year.to_numpy(dtype="int16")),
                     "available_at": pa.array(pd.to_datetime(rows.available_at, utc=True)),
                     "n_tokens": pa.array(np.asarray(n_tokens, dtype="int16")),
                     "emb_last": vec(last), "emb_avg": vec(avg)})


def write_atomic(table, path):
    import pyarrow.parquet as pq
    tmp = path.with_name(path.name + ".tmp")
    pq.write_table(table, tmp)
    os.replace(tmp, path)


def check_manifest(folder, want):
    """Write manifest.json, or check that the one there describes the same story set."""
    path = folder / "manifest.json"
    if path.exists():
        have = json.loads(path.read_text(encoding="utf-8"))
        if have != want:
            raise SystemExit(f"{path} describes another story set; move the folder away to start that vintage again")
    else:
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(want, indent=1), encoding="utf-8")


def run_vintage(vintage, stories, model, tok, folder, log=print):
    """Read one vintage's stories into folder, part by part, skipping finished parts."""
    check_manifest(folder, manifest(vintage, stories))
    for n, ids in enumerate(parts(stories.story_id.to_numpy())):
        path = folder / f"part-{n:04d}.parquet"
        if path.exists():
            continue
        rows = stories.iloc[n * PART:n * PART + len(ids)]
        assert (rows.story_id.to_numpy() == ids).all()
        t0 = time.time()
        enc = encode(tok, rows.headline)
        last, avg = embed_ids(model, enc, pad_id=tok.pad_token_id)
        write_atomic(part_table(rows, [len(e) for e in enc], last, avg), path)
        log(f"vintage {vintage} part {n}: {len(ids)} headlines, {len(ids) / (time.time() - t0):.1f} a second, "
            f"at {pd.Timestamp.now(tz='America/New_York'):%Y-%m-%d %H:%M} New York")


def load_model(vintage):
    """The vintage's ModernBertModel (the encoder of its pinned, checked masked-word model)."""
    from reader import cutoff
    return cutoff.load_vintage(vintage).model.eval()


def cmd_run(stories=None, out=OUT, vintages=None, log=print):
    from reader import cutoff
    stories = read_stories() if stories is None else stories
    tok = cutoff.tokenizer()
    log(f"{len(stories)} stories, story set SHA-256 {set_hash(stories.story_id, stories.updated_at)}")
    for v in vintages or sorted(stories.vintage_year.unique()):
        mine = stories[stories.vintage_year == v].reset_index(drop=True)
        folder = out / f"v{v}"
        n_parts = len(parts(mine.story_id.to_numpy()))
        if folder.exists() and all((folder / f"part-{n:04d}.parquet").exists() for n in range(n_parts)):
            check_manifest(folder, manifest(v, mine))
            log(f"vintage {v}: all {n_parts} parts done")
            continue
        log(f"vintage {v}: {len(mine)} stories in {n_parts} parts")
        run_vintage(v, mine, load_model(v), tok, folder, log)
    log("run finished")


def cmd_smoke(n):
    stories = read_stories()
    pick = pd.concat([stories[stories.vintage_year == v].head(n) for v in (2015, 2024)], ignore_index=True)
    folder = OUT / "smoke"
    if folder.exists() and any(folder.iterdir()):
        raise SystemExit(f"{folder} is not empty; move it away first")
    cmd_run(pick, folder)


def read_part(path):
    """One part: (rows, last, avg), the other columns as a DataFrame and the two vectors as 2-D float16 arrays."""
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    df = t.drop(["emb_last", "emb_avg"]).to_pandas()
    out = []
    for c in ("emb_last", "emb_avg"):
        col = t.column(c).combine_chunks()
        out.append(col.flatten().to_numpy(zero_copy_only=False).reshape(len(df), col.type.list_size).copy())
    return df, out[0], out[1]


def cmd_finish(out=OUT, store=STORE):
    """Check every vintage's parts against its manifest and the store's current stories, then write
    store/embeddings.parquet (one part at a time) and embeddings.json."""
    import pyarrow.parquet as pq
    from reader import cutoff
    stories = read_stories()
    writer, total = None, 0
    target = store / "embeddings.parquet"
    tmp = target.with_name(target.name + ".tmp")
    try:
        for v in sorted(stories.vintage_year.unique()):
            mine = stories[stories.vintage_year == v].reset_index(drop=True)
            folder = out / f"v{v}"
            check_manifest(folder, manifest(v, mine))
            for n, ids in enumerate(parts(mine.story_id.to_numpy())):
                t = pq.read_table(folder / f"part-{n:04d}.parquet")
                if not np.array_equal(t.column("story_id").to_numpy(), ids):
                    raise SystemExit(f"vintage {v} part {n} holds other stories")
                want = rules.embedding(mine.updated_at.iloc[n * PART:n * PART + len(ids)]).reset_index(drop=True)
                have = pd.Series(t.column("available_at").to_pandas()).reset_index(drop=True)
                if not (pd.to_datetime(have, utc=True) == want).all():
                    raise SystemExit(f"vintage {v} part {n}: a story changed after it was read; read it again")
                t = t.drop(["n_tokens"])
                writer = writer or pq.ParquetWriter(tmp, t.schema)
                writer.write_table(t)
                total += t.num_rows
    finally:
        if writer is not None:
            writer.close()
    drop_arrays(store)  # a stop between here and the arrays leaves no entry that vouches for old arrays (J3-2)
    os.replace(tmp, target)
    import torch
    import transformers
    meta = {"rows": total, "story_set_sha256": set_hash(stories.story_id, stories.updated_at),
            "first_year": FIRST_YEAR, "cap": CAP, "batch": BATCH, "part": PART,
            "poolings": {"emb_last": "token mean of the last layer, after the final norm",
                         "emb_avg": "mean over the 22 layers of the token mean"},
            "vintages": {str(v): cutoff.PINS["vintages"][str(v)] for v in sorted(stories.vintage_year.unique())},
            "versions": {"torch": torch.__version__, "transformers": transformers.__version__}}
    (store / "embeddings.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"wrote {target} ({total} rows)")
    cmd_arrays(store)


ARRAYS = {"emb_last": "embeddings_last.npy", "emb_avg": "embeddings_avg.npy"}


def parquet_footer(path):
    """The size of a Parquet file and the SHA-256 of its footer (the file metadata: every column chunk's offsets,
    sizes and the row groups), which changes when any part of the data is rewritten."""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        fh.seek(size - 8)
        n = int.from_bytes(fh.read(4), "little")
        fh.seek(size - 8 - n)
        footer = fh.read(n)
    return {"bytes": size, "footer_sha256": hashlib.sha256(footer).hexdigest()}


def drop_arrays(store):
    """Remove the arrays entry from embeddings.json, if any, before a file it vouches for is replaced."""
    path = store / "embeddings.json"
    if path.exists():
        meta = json.loads(path.read_text(encoding="utf-8"))
        if meta.pop("arrays", None) is not None:
            path.write_text(json.dumps(meta, indent=1), encoding="utf-8")


def cmd_arrays(store=STORE):
    """Write the two vector columns of store/embeddings.parquet as .npy files (rows in the table's order), one row
    group at a time, under temporary names then renamed, and record them in embeddings.json."""
    import pyarrow.parquet as pq
    f = pq.ParquetFile(store / "embeddings.parquet")
    n = f.metadata.num_rows
    ids = np.empty(n, dtype="int64")
    tmp = {c: store / (name + ".tmp") for c, name in ARRAYS.items()}
    maps = {c: np.lib.format.open_memmap(tmp[c], mode="w+", dtype=np.float16, shape=(n, DIM)) for c in ARRAYS}
    at = 0
    for batch in f.iter_batches(columns=["story_id", *ARRAYS]):
        k = batch.num_rows
        ids[at:at + k] = batch.column("story_id").to_numpy()
        for c in ARRAYS:
            maps[c][at:at + k] = batch.column(c).flatten().to_numpy(zero_copy_only=False).reshape(k, DIM)
        at += k
    if at != n:
        raise SystemExit(f"read {at} rows of {n}")
    for m in maps.values():
        m.flush()
    del maps, m
    drop_arrays(store)
    for c, name in ARRAYS.items():
        os.replace(tmp[c], store / name)
    meta_path = store / "embeddings.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["arrays"] = {"rows": int(n), "ids_sha256": ids_hash(ids), "files": dict(ARRAYS), "dim": DIM,
                      "dtype": "float16", "parquet": parquet_footer(store / "embeddings.parquet")}
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"wrote {', '.join(ARRAYS.values())} ({n} rows of {DIM})")


def stay_awake():
    """Ask Windows not to idle-sleep while this process runs (SetThreadExecutionState; no setting is changed, and it
    ends with the process). A closed lid still sleeps."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED


def main(argv):
    if argv[:1] == ["run"]:
        stay_awake()
        cmd_run()
    elif argv[:1] == ["smoke"] and len(argv) == 2:
        cmd_smoke(int(argv[1]))
    elif argv[:1] == ["finish"]:
        cmd_finish()
    elif argv[:1] == ["arrays"]:
        cmd_arrays()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
