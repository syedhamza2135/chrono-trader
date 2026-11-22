"""The reader run's counts, speeds and disk use, for research/audit/reader.md (M2 step 5). Reads the run's log, the
vintage manifests and the store's embeddings files. Prints counts, times and sizes only, never a headline.
Usage: python research/reader_stats.py
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline.settings import DATA_DIR  # noqa: E402

READER, STORE = DATA_DIR / "reader", DATA_DIR / "store"
PART = re.compile(r"vintage (\d+) part (\d+): (\d+) headlines, ([\d.]+) a second, at (.+) New York")


def size(pattern):
    return sum(os.path.getsize(f) for f in glob.glob(str(pattern), recursive=True) if os.path.isfile(f))


def main():
    lines = (READER / "run.log").read_text(encoding="utf-8").splitlines()
    print("first log line:", lines[0])
    print("last log line:", lines[-1])
    parts = {}
    for line in lines:
        m = PART.match(line)
        if m:
            v, _, k, s, t = m.groups()
            parts.setdefault(int(v), []).append((int(k), float(s), t))
    total, seconds = 0, 0.0
    print("vintage | manifest count | parts | headlines read | headlines a second (mean, min, max) | last part, New York")
    for v, ps in sorted(parts.items()):
        man = json.loads((READER / f"v{v}" / "manifest.json").read_text(encoding="utf-8"))
        k = sum(p[0] for p in ps)
        sec = sum(p[0] / p[1] for p in ps)
        total, seconds = total + k, seconds + sec
        print(f"{v} | {man['count']} | {len(ps)} of {len(man['parts'])} | {k} | {k / sec:.1f}, {min(p[1] for p in ps)},"
              f" {max(p[1] for p in ps)} | {ps[-1][2]}")
    print(f"total {total} headlines, {seconds / 3600:.2f} hours of reading, {total / seconds:.1f} a second")
    print("leftover .tmp files:", len(glob.glob(str(READER / "v*" / "*.tmp"))))
    print(f"parts on disk: {size(READER / 'v*' / '**'):,} bytes")
    for f in ("embeddings.parquet", "embeddings_last.npy", "embeddings_avg.npy", "embeddings.json"):
        print(f"{f}: {os.path.getsize(STORE / f):,} bytes")
    meta = json.loads((STORE / "embeddings.json").read_text(encoding="utf-8"))
    print("embeddings.json:", {k: meta[k] for k in ("rows", "story_set_sha256", "first_year", "cap", "versions")})
    print("pinned vintages:", {v: p["commit"][:12] for v, p in meta["vintages"].items()})


if __name__ == "__main__":
    main()
