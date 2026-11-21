"""Correct the PLAN line numbers in docs/digests/plan_rules.md (review of 21 Nov, L-P9), and carry them through this
branch's PLAN edits. For each "- L<n>" line, the cited line is moved by -1, 0 or +1 to the PLAN line (at dd40a5f) that
shares the most words with it, as the skeptic's check l8_digest_offsets.py scores it; ties keep the cite. Then every
L number is mapped from PLAN at dd40a5f to the working PLAN.md with difflib. Prints counts only, no PLAN text.

Usage: python research/review_2026-11-21_fixes/fix_digest_lines.py [--write]
"""
import difflib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
old = subprocess.run(["git", "show", "dd40a5f:PLAN.md"], capture_output=True, encoding="utf-8", cwd=ROOT).stdout
old = old.splitlines()
new = (ROOT / "PLAN.md").read_text(encoding="utf-8").splitlines()
digest_path = ROOT / "docs" / "digests" / "plan_rules.md"
dig = digest_path.read_text(encoding="utf-8").splitlines()

mapping = {}
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
    for k in range(i2 - i1):
        mapping[i1 + k + 1] = j1 + min(k, max(j2 - j1 - 1, 0)) + 1  # an edited block maps onto its new block


def words(s):
    return {w.lower() for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9,.']{3,}", s)}


moved = remapped = 0
out = []
for d in dig:
    m = re.match(r"- L(\d+)(?:-(\d+))?:\s*(.*)", d)
    off = 0
    if m and words(m.group(3)):
        n, w = int(m.group(1)), words(m.group(3))
        score = {o: len(w & words(old[n + o - 1])) for o in (-1, 0, 1) if 1 <= n + o <= len(old)}
        best = max(score, key=lambda o: (score[o], -abs(o)))
        off = best if score[best] > score.get(0, 0) else 0
        moved += off != 0

    def fix(x, off=off):
        global remapped
        n = int(x.group(1)) + off
        m2 = mapping.get(n, n)
        remapped += m2 != int(x.group(1))
        return f"L{m2}"
    if m:
        head, rest = d.split(":", 1)
        d = re.sub(r"L(\d+)", fix, head) + ":" + rest
        d = re.sub(r"(?<=-)(\d+)(?=:)", lambda x: str(mapping.get(int(x.group(1)) + off, int(x.group(1)) + off)), d, count=1) \
            if m.group(2) else d
    out.append(d)
print(f"digest lines whose cite moved by one: {moved}; L numbers changed in all: {remapped}")
if "--write" in sys.argv:
    out[0] = out[0].replace("Line numbers refer to PLAN.md.", "Line numbers refer to PLAN.md, corrected on 2026-11-21 "
                            "for the review's fixes (L-P9, research/review_2026-11-21_fixes/fix_digest_lines.py).")
    digest_path.write_text("\n".join(out) + "\n", encoding="utf-8")
