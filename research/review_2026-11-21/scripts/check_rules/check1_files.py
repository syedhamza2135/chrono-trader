"""Check 1: tracked files by extension, risky types, big files, and risky files ever added on any branch."""
import subprocess, os, collections, sys
def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
files = [f for f in git("ls-files").splitlines() if f]
ext = collections.Counter(os.path.splitext(f)[1] or "(none)" for f in files)
print("tracked files:", len(files))
print("by extension:", dict(ext.most_common()))
risky = {".parquet", ".csv", ".json", ".jsonl", ".zip", ".gz", ".feather", ".pkl", ".pickle", ".npy", ".npz", ".db", ".sqlite", ".bin", ".pt", ".safetensors", ".tar", ".xlsx"}
print("\nTracked risky-extension files (name, bytes, lines, header columns only):")
for f in files:
    e = os.path.splitext(f)[1].lower()
    if e in risky:
        size = os.path.getsize(f)
        with open(f, "rb") as fh:
            data = fh.read()
        lines = data.count(b"\n")
        hdr = data.split(b"\n", 1)[0].decode("utf-8", "replace").strip()[:120] if e == ".csv" else ""
        print(f"  {f}\t{size}\t{lines} lines\t{'header: ' + hdr if hdr else ''}")
print("\nTracked files over 200 KB:")
n = 0
for f in files:
    s = os.path.getsize(f)
    if s > 200_000:
        print(" ", f, s); n += 1
print("count:", n)
print("\nAll tracked files over 50 KB (for context):")
for f in files:
    s = os.path.getsize(f)
    if s > 50_000: print(" ", f, s)
print("\nEver added on any branch with risky extension or big blob:")
out = git("log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:")
added = sorted({l for l in out.splitlines() if l.strip()})
print("distinct files ever added (all refs):", len(added))
for f in added:
    e = os.path.splitext(f)[1].lower()
    if e in risky or f.startswith("data/") or ".env" in f:
        print("  ", f)
# big blobs in all history
print("\nBlobs over 200 KB in any commit on any ref:")
revs = git("rev-list", "--all", "--objects")
p = subprocess.run(["git", "cat-file", "--batch-check=%(objecttype) %(objectname) %(objectsize) %(rest)"], input=revs, capture_output=True, text=True, encoding="utf-8", errors="replace")
cnt = 0
for l in p.stdout.splitlines():
    parts = l.split(" ", 3)
    if parts[0] == "blob" and int(parts[2]) > 200_000:
        print("  ", parts[1][:10], parts[2], parts[3] if len(parts) > 3 else ""); cnt += 1
print("count:", cnt)
