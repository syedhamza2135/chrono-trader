# M3 review, step 8: the judge on the result documents (23 Nov)

Question: do the dev result documents follow the rules frozen before the results, and was every pick made by those
rules? Branch `claude/m3-review-76bcd4` at `89f35f7`. Read: `research/m3_kickoff.md` 435 to 626 (and 108 to 130,
270 to 330 for context), `research/m3_trial_plan.py`, `runs/trials.csv`, seven `runs/settings/*.json`,
`research/m3_dev_report.md`, `research/m3_older_vintage.md`, `research/m3_older_vintage.py` 1 to 128,
`research/audit/cutoff.md` 762 to 800, `docs/digests/plan_rules.md` (9.2, 9.10), and the run summaries
`D:\chrono-data\runs\m3_dev\stage1.json`, `stage2.json`, `older_result.json`, `stage1.log`. No raw data. Nothing fixed.

Ratings: 0 high, 2 medium, 6 low, 5 info.

## The rerunnable check

Saved as `judge_recompute.py` (any folder), run with `D:\venvs\chrono-trader\Scripts\python.exe judge_recompute.py`.
It reads only the three summary files.

```python
import json, math
from statistics import NormalDist
N = NormalDist()
D = "D:/chrono-data/runs/m3_dev/"
s1 = json.load(open(D + "stage1.json")); s2 = json.load(open(D + "stage2.json")); o = json.load(open(D + "older_result.json"))
m1 = s1["measures"]; order1 = ["T01", "T02", "T03"]
best = max(m1[t]["mean_ic"] for t in order1)
tied = [t for t in order1 if best - m1[t]["mean_ic"] <= 0.001]
print("stage1 tied", tied, "-> pick", tied[0], "| T03-T01 =", m1["T03"]["mean_ic"] - m1["T01"]["mean_ic"])
m2 = s2["measures"]
best = max(v["sharpe_after_costs"] for v in m2.values())
tied = [t for t, v in m2.items() if best - v["sharpe_after_costs"] <= 0.05]
pick = min(tied, key=lambda t: m2[t]["daily_turnover"])
srt = sorted(m2, key=lambda t: -m2[t]["sharpe_after_costs"])
print("stage2 tied", tied, "-> pick", pick, "| gap to 2nd", m2[srt[0]]["sharpe_after_costs"] - m2[srt[1]]["sharpe_after_costs"])
r, ol, d = o["news_effect_rule"], o["news_effect_older"], o["rule_minus_older"]
a = ol["mean"] < 0.5 * r["mean"]; b = d["p"] < 0.05
for name, gate in [("point estimate > 0", r["mean"] > 0), ("one-sided 5%", r["mean"] > 0 and r["p"] < 0.05)]:
    print(f"gate {name}: open={gate} a={a} b={b} ->", ("warning" if a and b else "no warning") if gate else "not informative")
print("rule-older 95% CI", d["mean"] - 1.96 * d["se"], d["mean"] + 1.96 * d["se"], "vs news effect", r["mean"])
ann = [m1[t]["sharpe_after_costs"] for t in order1] + [m2[t]["sharpe_after_costs"] for t in ["T05","T06","T07","T08","T09"]]
dly = [x / math.sqrt(252) for x in ann]; mu = sum(dly) / len(dly)
V = sum((x - mu) ** 2 for x in dly) / (len(dly) - 1); g = 0.5772156649; n = 8
sr0 = math.sqrt(V) * ((1 - g) * N.inv_cdf(1 - 1 / n) + g * N.inv_cdf(1 - 1 / (n * math.e)))
sr, sk, ku, T = m2["T09"]["sharpe_after_costs"] / math.sqrt(252), -0.2506, 7.1519, 754
print("dsr", N.cdf((sr - sr0) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)))
```

Output on 23 Nov:

```
stage1 tied ['T01', 'T03'] -> pick T01 | T03-T01 = 0.0006671690011381881
stage2 tied ['T09'] -> pick T09 | gap to 2nd 0.21649612608534258
gate point estimate > 0: open=True a=False b=False -> no warning
gate one-sided 5%: open=False a=False b=False -> not informative
rule-older 95% CI -0.00931381662397045 0.009210784819703721 vs news effect 0.006868941692391689
dsr 0.0315...
```

The hash check, per commit (a short Python over `git show <c>:research/m3_kickoff.md`, the same block rule as
`research/m3_trial_plan.py` lines 32 to 39):

```
9a17c8a no block
83a35cd 4a9a45a1238aad3b704a18f27c9bac046e13bbadf981ff642fc3d78986861e2f
210bfaf 4a9a45a1...861e2f
001d01c 4a9a45a1...861e2f
89f35f7 4a9a45a1...861e2f
working tree (python research/m3_trial_plan.py): 4a9a45a1...861e2f
```

## Findings

### D3-1 (info): the frozen block did not change after the first dev run. Right.

- The block is `research/m3_kickoff.md` 435 to 499. Its hash is `4a9a45a1...` at every M3 commit that has it and in
  the working tree, equal to the hash recorded at line 503 and in every run row's settings file (for example
  `runs/settings/d305229a...json`, `eed2890b...json`, `0f452837...json`).
- Order: `83a35cd` is dated 2026-11-23 05:05:19 +0500. `stage1.log` line 1 says T01 ended at 05:15:52 +0500 after
  10.1 minutes, so it started about 05:05:45, after the commit. T01's ledger row is clean at `83a35cd`.
  `210bfaf` (08:10:50 +0500) comes after the comparison pass row (21:55:57 New York, 07:55:57 +0500).
- Between `83a35cd` and `210bfaf` only docs, AGENTS.md, settings files and the ledger changed
  (`git diff --stat 83a35cd 210bfaf`), so the "dirty" rows ran the committed code, as the kickoff says at 562.

### D3-2 (low): the first freeze cannot be checked.

- Evidence: `research/m3_kickoff.md` 504 to 507 gives the first hash `9e1c10f4...` and says only rulings 1 and 4
  changed the block. At `9a17c8a`, the commit of the planned rows (`runs/trials.csv` rows 2 to 11), the kickoff has
  no plan block (`git show 9a17c8a:research/m3_kickoff.md`, "no block"). The planned settings carry `9e1c10f4...`
  (`runs/settings/9d54d2d3...json`), but no copy of that text exists in git.
- Impact: small. The re-freeze came before any run (D3-1), and the owner's rulings at 535 to 541 say what changed.
  But no one can confirm the tie margins and stage rules were the same in the first freeze.
- PLAN reference: 5.5 and 9.2 M4 (pre-register before results). Fix: say at line 505 that the first freeze's text
  was not committed; for PREREG, commit the frozen text before logging any row against its hash.

### D3-3 (info): both picks follow the frozen rules exactly. Right.

- Stage 1 (kickoff 469 to 471): T03 leads T01 by 0.000667, inside 0.001, so the earlier trial, T01, wins. T02 is
  0.0109 behind. `stage1.json` "winner": "T01".
- Stage 2 (kickoff 472 to 474): the pool is T01 and T05 to T09. T09 has -0.2432, T06 -0.4597; the gap is 0.216,
  far outside 0.05, and T09 also has the lowest turnover (0.389), so the tie rule could not change the pick.
  `stage2.json` "winner": "T09".
- IC is identical across T01 and T05 to T09 (0.0076265, t 1.3803), as the plan expects (kickoff 470, 553).
- The ledger holds one run row per planned trial, T04 dropped before any run (row 11, 17:39 New York, before T01's
  run at 19:15). No trial was added, rerun or replaced.

### D3-4 (medium): the kickoff's result summary picks the favourable numbers.

- Evidence: `research/m3_kickoff.md` 558 to 561 says "Retraining beats the end-of-2016 twin by 0.0179 of daily IC
  (t 2.61)". The report's twin table (`research/m3_dev_report.md` 56 to 64) also shows the end-of-2017 twin gap at
  +0.0061 (t 0.87) and the end-of-2018 twin beating the live agent in 2019 (-0.0150, t -1.76). The summary leaves
  out three losers the report shows: 12-1 momentum beats the chosen configuration after costs (Sharpe 0.40 against
  -0.24) and on IC (0.0218 against 0.0076) (report 83 to 84); and the long-only book trails equal weight and SPY
  (0.83 against 1.12 and 1.15) (report 97 to 99).
- Impact: the report itself is complete, so no number is wrong. But the kickoff note is what the owner and later
  sessions read first, and it frames retraining as a win when only one of three twins supports it on dev.
- PLAN reference: 9.10 (frozen-twin gaps by year after each snapshot); AGENTS.md "Facts". Fix: add one sentence at
  561 naming the end-of-2018 gap, momentum's lead and the long-only shortfall.

### D3-5 (info): the report shows everything PLAN 9.2 and 9.10 name. Right.

- PLAN 9.2 L435 (digest `docs/digests/plan_rules.md` 259): IC by quarter (report 34 to 50), frozen twins (52 to 64),
  placebo and price-only twin (66 to 75), matched baselines for both books (77 to 99), holding-period variants (101
  to 124), costs (126 to 144), exposures (147 to 186). PLAN 9.10 (digest 367 to 376): both books' statistics,
  deflated Sharpe (189 to 195), seed spread (197 to 226), regimes and coefficient life (228 to 268, labelled "not
  tested"), charts (284 to 290; the five SVG files exist in `D:\chrono-data\runs\m3_dev_report_charts`).
- The frozen plan's list (kickoff 490 to 498) is also met, including the switch-day check (report 270 to 282). Its
  warning rules match `cutoff.md` 793 to 794, and both come out "no" (2018's first-20 lead is 0.0375 with se 0.0371,
  about one standard error).
- The deflated Sharpe recomputes to 0.0315 with the sample variance of the 8 trials' daily Sharpe ratios and N 8.
  N 8 follows the frozen plan (kickoff 496); the step 5 note at kickoff 379 said "rows", which would be 19 or 20, but
  the frozen text governs and the ledger's placeholder rows are not trials.

### D3-6 (low): the trial table hides the stage 1 margin and the dropped trial.

- Evidence: `research/m3_dev_report.md` 103 to 112 shows T03 above T01 (0.0083 against 0.0076) with T01 marked the
  winner. Line 4 states the tie rule, but no line gives the 0.00067 margin. T04 appears only in the ledger dump
  (line 17 and 23), not in the trial table.
- Fix: one line under the table: "T03 led T01 by 0.00067, inside the 0.001 tie; T04 was dropped before any run."

### D3-7 (info): the report's ledger line is a snapshot.

- `research/m3_dev_report.md` 10 names the ledger by the kickoff worktree's absolute path and counts 19 rows; the
  ledger now has 20 (the older-vintage row). Correct for when it was written. Fix if regenerated: a repo-relative path.

### D3-8 (medium): the lead's reading of the 10.1 gate.

- Evidence: `cutoff.md` 780 says "If the news effect isn't above zero in the first place, the check says nothing".
  The lead reads it as one-sided 5% (`research/m3_kickoff.md` 608 to 614; `research/m3_older_vintage.py` 16 to 17,
  coded as `above = mean > 0 and p < ALPHA` at line 112).
- The natural reading: the point estimate. Section 10 adds "one-sided at 5%" every time it means a test (10.1 (b) at
  779; 10.2 (a) at 793). The gate sentence has no such words. Its job is to keep (a) meaningful: "less than half the
  news effect" makes no sense when that effect is zero or negative. The lead's reading is defensible but stronger
  than the text.
- Both ways (check above): the rule's news effect is +0.00687 (t 0.74, p 0.23). (a) fails, since +0.00692 is not
  below +0.00343. (b) fails, p 0.50. Point-estimate reading: gate open, outcome "no warning". Lead's reading: gate
  closed, "not informative". No warning either way, so no result changes. Only the label differs.
- Process: the ruling was made after the dev result (the news effect was in `210bfaf`, 08:10 +0500), and the docs
  say so. It was committed in `001d01c` (14:28:51 +0500), about 1.5 hours before the older run ended (16:15:36
  +0500, ledger row 21), so it was blind to the older result. That keeps it from being a breach that steered an
  outcome. It is still a post-result interpretation, and it went in the direction that switches the alarm off: under
  it, a drop on dev could not have warned. For a leak alarm, the more sensitive reading is the safer default.
- Verdict: a minor process deviation, honestly recorded and harmless here, not a breach. The docs should not call
  the outcome only "not informative" without also saying "no warning under the plain reading" (the older-vintage
  doc does say this at 68 to 69; good).
- PLAN reference: 5.5 (no change to frozen rules after results). Fix for PREREG: freeze the gate in words, as "the
  rule's mean news effect is above zero (point estimate)"; apply (a) and (b) as written; report the outcome as
  "warning" or "no warning", never "passed", with the news effect's t and a power note when that t is below 1.645;
  name both runs' commit (see D3-10).

### D3-9 (low): "just as well" claims an equivalence the numbers do not show.

- Evidence: `research/m3_older_vintage.md` 62 to 63: "the agent ranks stocks just as well with news read by a model
  whose training ended a year earlier". The paired difference is -0.00005 with se 0.00473
  (`older_result.json`), so its 95% interval is -0.0093 to +0.0092, wider than the whole news effect (+0.0069).
- The section is labelled descriptive, and line 64 hedges, so this is wording only. Fix: "the two runs' mean IC
  differ by -0.00005 a day; the interval (-0.009 to +0.009) is too wide to show the two are alike."

### D3-10 (low): the two runs compared come from different commits.

- Evidence: the rule's run is `m3_dev/compare/live` (`research/m3_older_vintage.py` 108, run at `83a35cd`, ledger
  row 20); the older run is at `001d01c` (row 21). Between them `world/world.py`, `sim/simulator.py`,
  `reader/vintage.py`, `reader/embed.py` and `eval/leaks.py` changed (`git diff --stat 83a35cd 001d01c -- agent sim
  eval world reader`; `agent/` did not). The doc (38 to 39) names `001d01c` but not the cross-commit comparison.
- Impact here: nil in practice, since the difference is -0.00005. `cutoff.md` 776 asks for "same code".
- Fix: state the two commits in the doc; for any sealed repeat, also rerun T09 at offset 0 on the new commit and
  show its decisions equal the old run's.

### D3-11 (info): the dirty older row is handled honestly. Right.

- `research/m3_older_vintage.md` 38 to 39 says the row is dirty from an uncommitted kickoff edit, code `001d01c`.
  `git diff 001d01c 89f35f7 -- research/m3_older_vintage.py` shows only a docstring change (lines 10 to 11), so the
  code that ran is `001d01c` in substance. The runner's docstring edit may also have been uncommitted at the time;
  the doc names only the kickoff. No effect on any number.
- The doc applies 10.1 (a) and (b) as frozen (`m3_older_vintage.py` 113 to 114), says the check "says nothing" as
  10.1 asks, labels every number below the outcome descriptive (lines 4, 59, 62), and says the check did not pass.
  Its numbers match `older_result.json` to the digits shown. The run adds no trial name, so N stays 8.

### D3-12 (low): the sealed-year line in the kickoff lacks its caveat.

- Evidence: `research/m3_older_vintage.md` 70 to 71 is clear: a sealed-year repeat "would need a new, reviewed
  change". But `research/m3_kickoff.md` 613 still says the table "can serve a sealed-year repeat if M4 adds one",
  with the refusal only in a separate bullet (577 to 579).
- Fix: add "after a new, reviewed change to the World, which now refuses sealed years with an offset" at 613.

### D3-13 (low): the PLAN digest is behind PLAN.

- Evidence: `docs/digests/plan_rules.md` line 1 records `dd40a5f`; `git log -1 -- PLAN.md` is `323f2e9`, with
  `dd60923`, `3d1df9b` and `323f2e9` changing PLAN.md since (48 lines). I used the digest's 9.2 and 9.10 lines as
  briefed and did not check them against the current PLAN.md.
- Fix: refresh the digest (or record that 9.2 and 9.10 did not change) before the PREREG work leans on it.

## The lead's ruling, in one line

The plain reading is the point estimate. Under it the outcome is "no warning"; under the lead's it is "not
informative". No warning either way. Made after the dev result but before the older result, and recorded, so a
minor deviation, not a breach. PREREG should freeze the point-estimate gate in words.
