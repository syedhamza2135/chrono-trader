# For each "- L<n>" line of docs/digests/plan_rules.md, score how many of its words appear in PLAN line n, n-1 and n+1.
# Prints only digest line numbers, cited PLAN lines and the best offset. No PLAN text is printed.
import re, sys
root = sys.argv[1]
plan = open(root + "/PLAN.md", encoding="utf-8").read().splitlines()
dig = open(root + "/docs/digests/plan_rules.md", encoding="utf-8").read().splitlines()
def words(s): return {w.lower() for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9,.']{3,}", s)}
rows = []
for i, d in enumerate(dig, 1):
    m = re.match(r"- L(\d+)(?:-(\d+))?:\s*(.*)", d)
    if not m: continue
    n = int(m.group(1)); w = words(m.group(3))
    if not w: continue
    sc = {}
    for off in (-1, 0, 1):
        k = n + off
        if 1 <= k <= len(plan): sc[off] = len(w & words(plan[k - 1]))
    best = max(sc, key=lambda o: (sc[o], -abs(o)))
    rows.append((i, n, best, sc))
bad = [r for r in rows if r[2] != 0 and r[3][r[2]] > r[3].get(0, 0)]
print("digest lines with an L cite:", len(rows), " best match not at the cited line:", len(bad))
# group runs
runs = []
for r in bad:
    if runs and r[0] - runs[-1][-1][0] <= 3 and r[2] == runs[-1][-1][2]: runs[-1].append(r)
    else: runs.append([r])
for g in runs:
    print(f"digest {g[0][0]}-{g[-1][0]}: PLAN L{g[0][1]}-L{g[-1][1]} cited, best offset {g[0][2]:+d}, lines {len(g)}")
