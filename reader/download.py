"""Download the pinned ChronoBERT vintages (reader/vintages.json) into DATA_DIR/hf, and check every file.

Each vintage is fetched at its pinned commit, only the files the model needs, and then checked: the weights by size
and SHA-256, the four small files by their git object ids. A vintage already in the cache is checked, not fetched
again, and a stopped download resumes. The weights are safetensors, so loading them later runs no code.

Usage: python -I reader/download.py [year ...]   (all 11 by default)
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_pipeline.settings import DATA_DIR  # noqa: E402

os.environ.setdefault("HF_HOME", str(DATA_DIR / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
from huggingface_hub import snapshot_download  # noqa: E402

PINS = json.loads((ROOT / "reader" / "vintages.json").read_text(encoding="utf-8"))
WEIGHTS = "model.safetensors"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def git_oid(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def problems(folder, pin):
    """What doesn't match one vintage's pins (empty when everything does)."""
    out = []
    w = Path(folder) / WEIGHTS
    if not w.exists():
        out.append("no weights")
    elif w.stat().st_size != pin["weights_bytes"]:
        out.append(f"weights are {w.stat().st_size:,} bytes, not {pin['weights_bytes']:,}")
    elif sha256(w) != pin["weights_sha256"]:
        out.append("the weights' SHA-256 differs")
    for name, oid in PINS["files"].items():
        p = Path(folder) / name
        if not p.exists():
            out.append(f"no {name}")
        elif git_oid(p) != oid:
            out.append(f"{name} differs")
    return out


def main():
    years = sys.argv[1:] or sorted(PINS["vintages"])
    bad = 0
    for y in years:
        pin = PINS["vintages"][y]
        folder = snapshot_download(pin["repo"], revision=pin["commit"], allow_patterns=[WEIGHTS, *PINS["files"]])
        found = problems(folder, pin)
        bad += bool(found)
        print(f"{y} {pin['repo']} at {pin['commit'][:12]}: {'; '.join(found) if found else 'all files match'}",
              flush=True)
    print(f"{len(years) - bad} of {len(years)} vintages match their pins")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
