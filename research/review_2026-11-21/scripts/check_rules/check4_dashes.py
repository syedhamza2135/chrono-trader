"""Check 4: em-dashes (U+2014) and en-dashes (U+2013) in .md files, tracked and untracked (not ignored). Prints file:line and a 'kind' tag, no text."""
import subprocess, re, sys
tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
untracked = subprocess.run(["git", "ls-files", "-o", "--exclude-standard"], capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
EM, EN = "\u2014", "\u2013"
def scan(files, label):
    tot_em = tot_en = tot_en_range = 0
    print(f"-- {label}: {len([f for f in files if f.endswith('.md')])} .md files")
    for f in files:
        if not f.endswith(".md"): continue
        if f == "research/review_2026-11-21/check_rules.md": continue
        lines = open(f, encoding="utf-8").read().splitlines()
        em = [i + 1 for i, l in enumerate(lines) if EM in l]
        en = [i + 1 for i, l in enumerate(lines) if EN in l]
        en_range = [i + 1 for i, l in enumerate(lines) if re.search(r"\d" + EN + r"\d", l) and not re.search(r"[^\d]" + EN + r"|" + EN + r"[^\d]", l)]
        en_dash = [n for n in en if n not in en_range]
        tot_em += len(em); tot_en += len(en_dash); tot_en_range += len(en_range)
        if em or en:
            print(f"  {f}: em-dash lines {len(em)} {em[:10]}; en-dash as dash lines {len(en_dash)} {en_dash[:10]}; en-dash only in number ranges {len(en_range)} {en_range[:10]}")
    print(f"  total lines: em {tot_em}, en as dash {tot_en}, en in number ranges {tot_en_range}")
scan([f for f in tracked if f], "tracked")
scan([f for f in untracked if f], "untracked (docs/digests and review folder)")
print("-- extra: non-md tracked files with em or en dashes (counts)")
for f in tracked:
    if f and not f.endswith(".md"):
        try: t = open(f, encoding="utf-8").read()
        except Exception: continue
        a, b = t.count(EM), t.count(EN)
        if a or b: print(f"  {f}: em {a}, en {b}")
