"""Check 3: look for raw price rows and headline-like text in tracked files. Prints file:line ranges and counts only."""
import subprocess, re, os, collections
files = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
DATE = re.compile(r"\b(19|20)\d\d-\d\d-\d\d\b")
DEC = re.compile(r"(?<![\w.])\d+\.\d{2,}(?![\w.])")
def ranges(nums):
    out = []; s = p = None
    for n in nums:
        if s is None: s = p = n
        elif n == p + 1: p = n
        else: out.append((s, p)); s = p = n
    if s is not None: out.append((s, p))
    return out
print("3a: lines with a date and 3+ decimal numbers (looks like a price row), per file")
tot = 0
for f in files:
    if f == "research/review_2026-11-21": continue
    try: lines = open(f, encoding="utf-8").read().splitlines()
    except Exception: continue
    hit = [i + 1 for i, l in enumerate(lines) if DATE.search(l) and len(DEC.findall(l)) >= 3]
    if hit:
        tot += len(hit)
        print(f"  {f}: {len(hit)} lines of {len(lines)}; ranges {ranges(hit)[:6]}{' ...' if len(ranges(hit))>6 else ''}")
print("  total:", tot)
print("3b: same test, any file with lines holding 4+ decimals and no date (bare number rows)")
for f in files:
    try: lines = open(f, encoding="utf-8").read().splitlines()
    except Exception: continue
    hit = [i + 1 for i, l in enumerate(lines) if len(DEC.findall(l)) >= 4 and not DATE.search(l)]
    if len(hit) >= 5: print(f"  {f}: {len(hit)} lines; ranges {ranges(hit)[:5]}")
print("3c: price_events.csv columns and counts (the allowed exception)")
import csv
rows = list(csv.DictReader(open("reference/price_events.csv", encoding="utf-8")))
print("  rows:", len(rows), "symbols:", len({r['symbol'] for r in rows}), "date range:", min(r['date'] for r in rows), max(r['date'] for r in rows))
ev = [r['evidence'] for r in rows]
print("  evidence lengths: max", max(map(len, ev)), "chars; over 300 chars:", sum(len(e) > 300 for e in ev), "; empty:", sum(not e.strip() for e in ev))
q = [len(re.findall(r"[\"'\u201c][^\"'\u201d]{20,}[\"'\u201d]", e)) for e in ev]
print("  quoted spans over 20 chars in evidence: rows", sum(1 for x in q if x), "total", sum(q))
long_q = []
for i, e in enumerate(ev):
    for m in re.findall(r"[\"\u201c]([^\"\u201d]{60,})[\"\u201d]", e): long_q.append((i + 2, len(m)))
print("  quoted spans over 60 chars (csv line, length):", long_q[:15], "count", len(long_q))
print("3d: tests/ and fixtures: files, sizes, and use of real data")
for f in files:
    if f.startswith("tests/") and not f.endswith(".py"): print("  non-py in tests:", f, os.path.getsize(f))
print("  tests/ py files:", sum(f.startswith('tests/') and f.endswith('.py') for f in files), "; conftest/fixtures dir:", [f for f in files if 'fixture' in f or 'conftest' in f])
print("3e: tests that read reference/ or the data directory (file:line)")
out = subprocess.run(["git", "grep", "-nE", r"reference/|CHRONO_DATA_DIR|data_dir|D:[\/]+chrono-data|read_parquet|read_csv", "--", "tests"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
c = collections.Counter(l.split(":")[0] for l in out.splitlines())
for f, n in c.items(): print(f"  {f}: {n} lines")
