# M4 review: Opus skeptic (24 Nov 2026)

Scope: the seven findings G4-1, R4-1, R4-2, K4-1, K4-2, K4-3 and K4-4, at `095a855` on `claude/m4-review`. I tried to
refute each with my own check. Nothing in the repo, the sealed run or `D:\chrono-data` was changed, rerun or rescored.
Nothing committed. My only script is a short rank count, run inline (below). No prices or headlines are quoted here.

| id | verdict | rating in | my rating |
|---|---|---|---|
| G4-1 | stands | medium | medium |
| R4-1 | stands | medium | medium |
| R4-2 | stands | medium | medium |
| K4-1 | stands in part (the branch name is right) | high | medium |
| K4-2 | stands, and is wider than reported | medium | medium |
| K4-3 | stands; absorbs G4-4 | medium | medium |
| K4-4 | stands | medium | low |

## G4-1: stands, medium

- **PREREG's words** (`PREREG.md:135-137`): the full suite, with `CHRONO_SLOW_LEAKS=1`, "passes on the clean tree at
  the code-plus-PREREG commit before `seal.lock` is written, and again at the lock's commit before the sealed run
  starts". "If either fails, no part runs."
- **Times.** `git log --format='%h %ci' a9a216e..095a855`: 7b9a138 at 21:45:15 +05:00, 8c683f5 at 22:30:59 +05:00,
  423a9c2 at 22:31:26 +05:00, that is 11:45:15, 12:30:59 and 12:31:26 New York. `seal.lock` `written_at`
  2026-11-23T12:31:11, and `sim/seal.py:100-101` stamps it in America/New_York. `D:\chrono-data\sealed\runs.jsonl`:
  main `started_at` 2026-11-23T12:33:20 (same clock, `sim/seal.py:194`), older_vintage 21:20:52, both `again: false`,
  commit 423a9c2. So 12 s from 8c683f5 to the lock and 1 min 54 s from 423a9c2 to main's start. Every suite log I
  found ran 31 to 52 minutes, without the slow test. Confirmed.
- **Could another run satisfy the words?** No.
  - A run at 7b9a138 is not "the code-plus-PREREG commit". The code is the same (`git diff --stat 7b9a138 8c683f5 --
    . ':!PREREG.md'` is empty), so it would test the same code. But the only suite on record for step 3 is "534 pass
    and 1 skip" (`research/m4_kickoff.md:278`), and the one skip is the slow leak test (`tests/test_leaks.py:310`
    skips unless `CHRONO_SLOW_LEAKS=1`). That run was also before 7b9a138, since 7b9a138 commits the note that
    reports it.
  - An uncommitted tree of 8c683f5 is not "the clean tree at" the commit, and 7b9a138 to 8c683f5 is 45 min 44 s,
    too short for a full suite plus the slow test with time to write and commit.
  - The second gate is not redundant in PREREG's terms. At 423a9c2 the real repo holds a `seal.lock` for the first
    time, and no earlier suite ran with one present (`tests/test_report.py:171` replays in the real repo and counts on
    no lock matching its made-up settings; `tests/test_sim.py` uses temp folders). I did not find a test that would
    fail with the lock present, so this is a gap in evidence, not a known failure.
- **Search for a log.** `find` over the session scratchpads, `D:\chrono-data` and the repo for `*.log` and `*.txt`
  with a pytest result: 8 suite logs on 23 Nov, every one ending "1 skipped"; after 18:40 +05:00 on 23 Nov, none
  except this review's own `pytest_m4.log` (still running). `D:\chrono-data\runs\m4_sealed_logs` holds one line per
  part log and `status.txt`; none mentions a suite. The lead's status memory records the owner's "Yes, seal and run"
  and the brief (fill PREREG, write and commit the lock, seal check, main then older_vintage). It names no suite run.
- **Validity or disclosure?** Disclosure. The outcome is Failure (`PREREG.md:141`), which needs no leak test, and a
  leak could only inflate a result that already failed. But it is a pre-registered precondition that was skipped and
  is not stated in the report (`grep -i "suite\|SLOW" research/m4_sealed_report.md`: 0 hits). Medium is right: not
  high, since no number or label can move; not low, since PREREG made it a gate. The judge's fix (a dated note, and a
  slow-leak suite on a clean checkout of 423a9c2, recorded beside the report) stands. Note that the code at
  095a855 equals 8c683f5's (`git diff --stat 8c683f5 095a855` lists only the report, the lock, two settings files
  and two ledger rows).

## R4-1: stands, medium

- **PREREG's words** (`PREREG.md:148-150`): "Known limits, stated in the report": only the 2016 vintage has evidence
  for its cutoff and 2026 was never checked; the sectors are a present-day list; the store's data ends on 2026-10-28.
- **Check.** `grep -n -i -c` on `research/m4_sealed_report.md` (569 lines) for "known limit", "limit", "2016
  vintage", "cutoff", "never checked", "2026 was", "present-day", "present day", "ends on", "data end": 0 hits each.
  "2026-10-28" has 4 hits, all the sealed end inside `seal.lock` and the ledger rows (lines 4, 7, 8), never as the
  store's last day. "sector" has 4 hits (273, 275, 287), which say "Wikipedia's list as of each date", the opposite
  of PREREG's wording (R4-4).
- **Rating.** The vintage limit is the context for both leak checks' "no warning", and none of the three limits is
  stated. Medium holds. No number changes.

## R4-2: stands, medium

- **PREREG's words** (`PREREG.md:95-97`): the baselines "are compared with live **before costs**. The after-cost rows
  are shown, marked as not turnover-matched, since only live has the band."
- **Check.** Report lines 219-241: heading "## Matched baselines" (from `eval/report.py:138`), then the long-short and
  long-only tables, `sharpe_after_costs` before `sharpe_before_costs`, with no mark and no sentence. `grep -c -i`
  for "turnover-matched" and "not matched": 0; "before costs": 1 hit, line 82, the deflated Sharpe table.
- **Why it is not lower.** I ranked the 8 long-short books (live, momentum, reversal, 5 random seeds) by each Sharpe
  column, printing ranks only (inline Python over report lines 223-234). After costs live is 4th of 8, behind
  random_3, momentum and reversal. Before costs, the comparison PREREG names, live is 7th of 8, behind 6 books. So the
  unmarked after-cost column, placed first under a heading that says "Matched", lifts live by 3 places. It changes no
  test, but it tilts the reading toward live. Medium holds.

## K4-1: stands in part, high lowered to medium

- **Check.** `AGENTS.md:27-29`: M4 "has started on the branch `claude/m4-kickoff`", "steps 1 to 3", "the draft
  `PREREG.md`", "Nothing is sealed, and the sealed years are still shut". `git log -- AGENTS.md`: last changed in
  7b9a138, so it misses 8c683f5, 423a9c2 and 095a855. The seal, the run and the Failure result are not in it. Stale
  and false. Confirmed.
- **Refuted part: the branch name.** `git log -1 095a855 --format=%D` prints `HEAD -> claude/m4-review,
  claude/m4-kickoff`. M4's commits are on `claude/m4-kickoff`, which is right. `claude/m4-review` is the review's
  branch, not M4's.
- **Why medium, not high.** The harmful act a reader could take, a second sealed run, is refused in code:
  `sim/seal.py:186-188` raises unless `again=True` once a part has a start in `runs.jsonl`, which now holds both
  parts. And a reader told the years are "still shut" would keep them shut, not open them. What it costs is a wrong
  picture of the state and no sealed result for the next session. Real, and AGENTS is read first, so not low. But it
  can't change the result or let a leak in, so not high.

## K4-2: stands, medium, and wider than reported

- **Check.** `grep -n "^## \|sealed years stay shut" README.md`: Status runs from line 7 to 41 and ends with M3. No
  M4 paragraph. The commands are listed (88-90). Confirmed.
- **Missed by the checker.** `README.md:39` says "The sealed years stay shut." That is now false, the same error as
  K4-1. With a false sentence, not just a gap, medium holds.

## K4-3: stands, medium; G4-4 belongs with it

- **Check.** `research/m4_kickoff.md:15` ("Uncommitted"), `:188` ("Step 1, built on 23 Nov (uncommitted)"), `:244`
  ("Steps 2 and 3 (23 Nov, uncommitted)"). The file has 279 lines and ends with the step 3 suite. `git log --
  research/m4_kickoff.md`: 7b9a138 and 6401ee7 only. No steps 4 to 6, no result. Confirmed.
- **G4-4.** The owner's go is recorded, but only outside git: the lead's status memory has the owner's "Yes, seal and
  run" (23 Nov), the brief, the seal commits, the start at 22:32 local and the result. So the judge's "can't verify
  the go from files" is true of the repo, not of all files. The repo has no dated record of the go, the seal, the
  run or the skipped suite gate. That is one gap with K4-3 and G4-1, and one fix: a steps 4 to 6 section in the
  kickoff note with the timeline above, the owner's words and the G4-1 deviation. The kickoff note is the milestone
  note AGENTS sends a reader to, so medium holds. G4-4 can stay low as a separate line or be folded in here.

## K4-4: stands, medium lowered to low

- **Check.** `docs/digests/code_map.md:3`: "Commit 89f35f7 plus the M3 review fixes (uncommitted)". `git log -1 --
  docs/digests/code_map.md`: a2a5f3e. `wc -l`: `sim/seal.py` 199 (digest heading at line 61 says 62),
  `sim/simulator.py` 280 (digest 241), `eval/report.py` 288 (digest 270). `git log a2a5f3e..095a855 -- sim/seal.py
  sim/simulator.py eval/report.py world/world.py`: 7b9a138 and 6401ee7. The seal section lists only `SealError`,
  `sealed_start`, `settings_hash`, `Git` and `check`. Stale. Confirmed.
- **Why low.** `PLAYBOOK.md:92-93` already handles this: "Before using one, run `git log -1 -- <source>`; if the
  source changed since, refresh the digest first." A digest goes stale whenever code changes; the defect is only
  that this review did not refresh it first, which the rule exists to catch. It misleads no reader who follows the
  rule and touches no result. Refresh it before the next use and in the merge commit.

## What would change these verdicts

- G4-1: a log of a suite with `CHRONO_SLOW_LEAKS=1` and 0 skipped, on clean trees at 8c683f5 and 423a9c2, timed
  before 12:31:11 and 12:33:20 New York on 23 Nov. I found none.
- K4-1: if `claude/m4-kickoff` were not M4's branch. It is.
