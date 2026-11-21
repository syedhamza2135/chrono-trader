#!/bin/bash
# Git, tests and doc-structure numbers. Run from the worktree root.
echo "## master tip"; git rev-parse --short master; git log -1 --format='%h %cd' --date=format-local:'%Y-%m-%d %H:%M' master
echo "## dd40a5f commit date in New York time"; TZ=America/New_York git log -1 --format='%cd' --date=format-local:'%Y-%m-%d %H:%M %Z' dd40a5f
echo "## commits reachable from master"; git rev-list --count master
echo "## table hashes: exists, subject"
for h in 78e0c40 0b87aab 130c849 043080f 69e777b b7d78d9 3f1825a af1aaf9 93d8f70 90ecb8a 658db1c 2ace1c3; do
  printf "%s " $h; git log -1 --format='%h %s' $h 2>&1 | head -1
done
echo "## old hashes still known to git (should be refs/original or backups only)"
for h in c409871 e425969 212bafa cd0a0e2 4d5bb0d 9a1508f e56e09a 7b4a200 b2b9441 c9c09cf 87bacdc 4ebbe24; do
  printf "%s " $h; git cat-file -t $h 2>&1 | head -1
done
echo "## branches"; git branch -a --list '*claude*' '*backup*' | head -20
echo "## commits whose message holds Co-Authored-By, reachable from master and claude branches"
git log master claude/m1-kickoff-832c2d claude/awesome-panini-89f869 --grep='Co-Authored-By' -i --format='%h' 2>/dev/null | wc -l
echo "## same, from backup/pre-rewrite refs"
git for-each-ref --format='%(refname)' 'refs/heads/backup/pre-rewrite/*' 
git log $(git for-each-ref --format='%(refname)' 'refs/heads/backup/pre-rewrite/*') --grep='Co-Authored-By' -i --format='%h' 2>/dev/null | sort -u | wc -l
echo "## Generated with Claude Code lines in master history"; git log master --grep='Generated with' -i --format='%h' | wc -l
echo "## tests added in dd40a5f"; git diff 658db1c dd40a5f -U0 -- tests | grep -c '^+def test_'
git diff 658db1c dd40a5f -U0 -- tests | grep '^+def test_'
echo "## agents"; ls .claude/agents | wc -l; ls .claude/agents
echo "## tests summary line"; tail -1 research/review_2026-11-21/tests_output.txt
echo "## skip reason"; grep -n -i "skip" research/review_2026-11-21/tests_output.txt | head -3
echo "## incomplete rule"; grep -n "TRAILING, MIN_BARS\|INCOMPLETE_TRADES =" data_pipeline/prices.py
echo "## verify_prints HEADER length"; /d/venvs/chrono-trader/Scripts/python.exe - <<'P'
import ast
t = ast.parse(open("research/verify_prints.py", encoding="utf-8").read())
for n in t.body:
    if isinstance(n, ast.Assign) and any(getattr(x, "id", "") == "HEADER" for x in n.targets):
        print("HEADER entries:", len(n.value.elts), [e.value for e in n.value.elts if hasattr(e, "value")][-4:])
P
echo "## m0_review counts"; sed -n 15p research/audit/m0_review.md | cut -c1-120
awk '/^### Lookahead/{s="lookahead"} /^### Identity/{s="identity"} /^### Prices/{s="prices"} /^### Docs: audit/{s="audit"} /^### Docs: PLAN/{s="plan"} /^### Refuted/{s="refuted"} /^### Checked/{s="done"} /^[0-9]+\. /{c[s]++; if ($0 ~ /Major/) maj++} END{for(k in c) print k, c[k]; print "major", maj}' research/audit/m0_review.md
echo "## m1_kickoff list sizes"
awk 'NR>=108 && NR<=137 && /^[0-9]+\. /{n++} END{print "leak review items (lines 108-137):", n}' research/m1_kickoff.md
awk 'NR>=151 && NR<=173 && /^[0-9]+\. /{n++} END{print "second review items (lines 151-173):", n}' research/m1_kickoff.md
echo "## store.md diff between 658db1c and dd40a5f"; git diff 658db1c dd40a5f --stat -- research/audit/store.md; git diff 658db1c dd40a5f -U0 -- research/audit/store.md | grep '^[+-]-' | cut -c1-160
echo "## tests mention universe_preview"; grep -ln "universe_preview" tests/*.py
echo "## 4 to 6 minutes: pytest seconds"; grep -o "in [0-9.]*s ([0-9:]*)" research/review_2026-11-21/tests_output.txt
