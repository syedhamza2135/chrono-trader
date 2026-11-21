"""Check 5: find date and time handling sites in code dirs. Prints file:line only (no code), grouped by pattern."""
import subprocess, re, collections
DIRS = ["world", "sim", "eval", "agent", "reader", "data_pipeline"]
PATTERNS = {
    "utcnow": r"utcnow|utcfromtimestamp",
    "naive now/today": r"datetime\.now\(|date\.today\(|datetime\.today\(|Timestamp\.now\(|Timestamp\.today\(|[^.\w]today\(\)|time\.time\(",
    "utc named": r"timezone\.utc|utc=True|tz=\"UTC\"|\"UTC\"|tz_convert\(\"UTC\"\)|\bUTC\b",
    "tz_localize": r"tz_localize",
    "tz_convert": r"tz_convert",
    ".date() or .dt.date": r"\.date\(\)|\.dt\.date",
    "fromisoformat with Z": r"fromisoformat\(.*Z",
}
for name, pat in PATTERNS.items():
    out = subprocess.run(["git", "grep", "-nE", pat, "--", *DIRS], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    sites = [l.split(":", 2)[:2] for l in out.splitlines()]
    print(f"{name}: {len(sites)} sites")
    by = collections.defaultdict(list)
    for f, n in sites: by[f].append(n)
    for f, ns in by.items(): print(f"  {f}: {', '.join(ns)}")
print("code files with no date or time handling hits at all:")
files = subprocess.run(["git", "ls-files", *DIRS], capture_output=True, text=True).stdout.split()
allpat = "|".join(PATTERNS.values())
for f in files:
    if f.endswith(".py") and not re.search(allpat, open(f, encoding="utf-8").read()): print("  ", f)
