"""Check 2: .env or key-like material anywhere in history. Prints names, file:line, never values."""
import subprocess, re, collections
def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
print("2a: paths ever in history (all refs) that look like env or key files")
paths = {l for l in git("log", "--all", "--name-only", "--pretty=format:").splitlines() if l.strip()}
hits = sorted(p for p in paths if re.search(r"(^|/)\.env|\.pem$|\.key$|secret|credential|\.p12$", p, re.I))
print("  distinct paths in history:", len(paths)); print("  matches:", hits)
print("2b: tracked env files now:", [f for f in git("ls-files").splitlines() if re.search(r"(^|/)\.env", f)])

PAT = r"APCA|ALPACA_API|ALPACA_SECRET|SECRET|key_id|api_key|apikey|AKIA|sk-[A-Za-z0-9]{20}|ghp_[A-Za-z0-9]{20}|PK[A-Z0-9]{18}"
refs = [r.split()[0] for r in git("for-each-ref", "--format=%(refname:short)").splitlines()]
print("2c: git grep at the tip of each ref, file:line only; 'assigned' marks a line that assigns a non-empty value")
seen = collections.OrderedDict()
for ref in refs:
    out = git("grep", "-n", "-I", "-E", PAT, ref, "--", ".", ":!research/review_2026-11-21")
    for l in out.splitlines():
        # format ref:file:line:text
        rest = l[len(ref) + 1:]
        f, ln, text = rest.split(":", 2)
        assigned = bool(re.search(r"(APCA\w*|ALPACA\w*|SECRET\w*|key_id|api_key)\s*[=:]\s*['\"]?[A-Za-z0-9/+_\-]{8,}", text, re.I))
        seen.setdefault((f, ln, assigned), []).append(ref)
for (f, ln, a), rs in seen.items():
    print(f"  {f}:{ln} assigned={a} refs={len(rs)}")
print("  total distinct file:line:", len(seen), " assigned:", sum(1 for k in seen if k[2]))

print("2d: history search (-G) for key-like diffs, commit and file only")
out = git("log", "--all", "-G", PAT, "--name-only", "--pretty=format:@%h")
cur = None; res = collections.defaultdict(set)
for l in out.splitlines():
    if l.startswith("@"): cur = l[1:]
    elif l.strip(): res[l].add(cur)
for f, cs in sorted(res.items()):
    if f.startswith("research/review_2026-11-21"): continue
    print(f"  {f}: {len(cs)} commits")
print("2e: lines in history diffs that assign a non-empty literal to a key-like name (count only)")
out = git("log", "--all", "-p", "-G", PAT, "--pretty=format:@%h")
n = 0; where = collections.Counter(); cur=None; curf=None
for l in out.splitlines():
    if l.startswith("@"): cur = l[1:]
    elif l.startswith("+++ b/"): curf = l[6:]
    elif l.startswith("+") and re.search(r"(APCA\w*|ALPACA\w*|SECRET\w*|key_id|api_key)\s*[=:]\s*['\"]?[A-Za-z0-9/+_\-]{16,}", l, re.I):
        n += 1; where[curf] += 1
print("  count:", n, dict(where))
