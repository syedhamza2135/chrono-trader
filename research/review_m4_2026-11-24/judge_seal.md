# M4 review: the seal and the sealed run's integrity (judge, 24 Nov 2026)

Scope: `git log a9a216e..095a855` on `claude/m4-review` (6401ee7, 7b9a138, 8c683f5, 423a9c2, 095a855). The sealed
run itself ran in the worktree `m3-kickoff-56264f` (branch `claude/m4-kickoff`, same commits). Nothing was rescored,
rerun, changed or committed. The real run log was only read (still 2 lines after the checks).

Question: was the sealed run done exactly once, at the sealed commit, under the sealed settings and pre-fixed dates,
and could anything after 2019 have reached a dev choice?

Scripts, all in `C:\Users\syedh\AppData\Local\Temp\claude\a742097078b03236\6cc4007d-fcb6-47d2-8b04-650f79c5109d\scratchpad\m4\`:
- `g4_hashes.py <repo> <worktree>...`: PREREG hash at 8c683f5 against `seal.lock`, its CRLF variant, the working
  files, the attributes, and both settings hashes recomputed from the recorded settings files (repo and D: ledger).
- `g4_settings_now.py <repo>`: the runner's `full_settings(part)` recomputed now (code at HEAD, data footers on D:).
- `g4_seal_rule.py <repo>`: `seal.check` on the real lock and PREREG with HEAD posed as each commit in scope (real
  git answers parents and changed paths), then `seal.begin` on a copy of the run log.
- `g4_runs.py`: each sealed book's first and last decision and equity dates and its replays (dates and counts only),
  and the sealed live agents' dev-year decisions against M3's T09 and older-vintage dev runs.
- `g4_pre_seal_dates.py`: every run output written before the seal ends by 2019-12-31.

Times below are New York unless marked local (the laptop is UTC+5, so local minus 10 hours).

## Timeline (from git reflog of `m3-kickoff-56264f`, D: file times, the run log and the ledger)

| NY time, 23 Nov | Event | Evidence |
|---|---|---|
| 10:41 | 6401ee7 (seal code) | reflog |
| 10:42 to 10:53 | T09 dev check at 6401ee7, tree dirty | `runs/trials.csv` row `20261123T105249_c7780628` (dirty True); `D:\chrono-data\runs\m4_dev\T09_check` times |
| 11:45 | 7b9a138 (PREREG with placeholders, writer) | reflog |
| 12:30:59 | 8c683f5 (PREREG filled; diff 7b9a138..8c683f5 is PREREG.md only, 3 lines) | reflog, `git diff --stat` |
| 12:31:11 | `seal.lock` written | `seal.lock:10`, worktree file time 22:31:11 local |
| 12:31:26 | 423a9c2 (seal.lock alone) | reflog |
| 12:33:20 | main starts (run log entry 1); `D:\chrono-data\sealed\` created at that second | `runs.jsonl`, folder time 22:33:20 local |
| 21:20:16 | main ends, 527.2 min, exit 0 | `m4_sealed_logs\main.log`, `status.txt`, ledger row |
| 21:20:52 | older_vintage starts (entry 2) | `runs.jsonl` |
| 22:05:12 | older_vintage ends, 44.5 min, exit 0 | `older_vintage.log`, `status.txt`, ledger row |
| 22:06 to 22:48 | replays of all 27 books | `replay.log` |
| 22:50:40 | writer writes the report | `report.log`, report file time |
| 22:50:59 | `ledger` copies the rows | repo `runs/trials.csv` and settings file times |
| 22:51:40 | 095a855 | reflog |

HEAD in that worktree stayed 423a9c2 from 12:31:26 to 22:51:40 (no reflog entry between).

## Findings

### G4-1 (medium). The pre-registered leak-test gate was not run

- **Rule.** `PREREG.md:135-137`: the full suite with `CHRONO_SLOW_LEAKS=1` passes on the clean tree at the
  code-plus-PREREG commit before `seal.lock` is written, and again at the lock's commit before the sealed run starts.
  "If either fails, no part runs." This was the fix for skeptic P-6 (`research/audit/m4_prereg_skeptic.md:119-127`).
  PLAN L364 ("every leak test passes") and kickoff step 4 (`research/m4_kickoff.md:155`).
- **What happened.** 12 seconds passed between 8c683f5 (12:30:59) and the lock (12:31:11), and 1 minute 54 seconds
  between 423a9c2 (12:31:26) and main's start (12:33:20). The suite takes 35 to 52 minutes without the slow leak test
  (`AGENTS.md:56-57`). So neither run can have happened at those commits, in any checkout. The last suite on record
  is "534 pass and 1 skip" after step 3 (`research/m4_kickoff.md:278`), and the 1 skip is the slow leak test. The
  `.hypothesis` cache in the run's worktree was last touched at 11:05 NY, before 7b9a138. The sealed report does not
  mention the gate (`grep -i "suite\|leak test\|SLOW" research/m4_sealed_report.md` finds nothing).
- **Effect.** It does not change the outcome. Failure needs no leak test (`PREREG.md:141-142`), and a leak could only
  inflate a result that already failed. But the run started without a gate that PREREG made a precondition, and the
  report as published does not say so.
- **Check.** The timeline table: `git -C ..\m3-kickoff-56264f reflog --date=iso` and `cat D:\chrono-data\sealed\runs.jsonl`.
- **Fix.** Add a dated note under the report stating the deviation; run the suite with `CHRONO_SLOW_LEAKS=1` on a
  clean checkout of 423a9c2 (its code equals 8c683f5's) and record the result there, beside the report, never instead.

### G4-2 (low). The dev check ran at 6401ee7 on a dirty tree, not at the code commit PREREG names

- **Rule.** `PREREG.md:16-19`: T09 reruns on the dev years "at the code commit", 7b9a138.
- **What happened.** Ledger row `20261123T105249_c7780628`: commit 6401ee7, dirty True. `m4_t09_check.py` itself was
  first committed in 7b9a138.
- **Why it is low.** `git diff --stat 6401ee7 8c683f5 -- sim agent world reader data_pipeline research/m3_dev_runs.py
  research/m3_trial_plan.py` is empty. And the sealed run itself settles it: main/live's decisions to 2019-12-31
  equal M3's T09 run on all 817 days, and the older part's equal M3's older-vintage dev run (`g4_runs.py`).
- **Fix.** One line in the dated note.

### G4-3 (low). The time order has only local evidence

- `research/m4_kickoff.md:197` says the owner's push puts the lock on GitHub before the sealed run, as its dated
  record. `git ls-remote origin` today shows only `refs/heads/master` at a9a216e: no M4 commit or lock is on GitHub.
- Commit dates, file times, the run log and the ledger all agree, so I found nothing wrong. But all of it is local
  and editable.
- **Fix.** The owner pushes `claude/m4-kickoff`; the note says the push came after the run.

### G4-4 (low). No dated record of steps 4 and 5

- `research/m4_kickoff.md` ends at "Steps 2 and 3" (`:244-279`) and is unchanged after 7b9a138. Nothing in the repo
  records the owner's go for the sealed run (`research/m4_kickoff.md:10`), the seal time or the suite runs. I can't
  verify the go from files: unsettled, not a finding of fault.
- **Fix.** Add a steps 4 to 6 section to the kickoff note with the timeline above.

### G4-5 (info). `seal.lock` is committed with CRLF

- `sim/seal.py:158` uses `write_text` on Windows, which writes CRLF; `.gitattributes:4-6` marks it `-text`, so git keeps
  the CRLF bytes (12 CR in `git show 423a9c2:seal.lock`). The comment says "keep their LF bytes". No effect: the lock is
  read as JSON and its own hash is recorded nowhere. PREREG.md has no CR and is unaffected.

### G4-6 (info). What the commit rule can't see

- `sim/seal.py:104-108` with `:133-134` is sound against honest error (G4 check 2). It can't see: git replace refs or
  grafts that fake a parent, ignored files (not in `git status --porcelain`), the venv's packages, modules imported
  after `check`, and edits during a run. Only deliberate action reaches these. Replays rechecked the clean tree 27
  times between 22:06 and 22:48, so the tree was clean then too.

## What was checked and found right

1. **Hashes** (`g4_hashes.py`, `g4_settings_now.py`). SHA-256 of `git show 8c683f5:PREREG.md` equals the lock's
   "prereg" (97e15094...92ca). The blob has no CR; a CRLF copy would hash differently (a98b6594...), but
   `.gitattributes` (added in 7b9a138, the same commit that adds PREREG) makes it `-text`, and both working copies
   match. PREREG.md has only two commits, 7b9a138 and 8c683f5: it did not change after the seal. Both settings
   hashes recompute from the recorded settings files, in the repo and in `D:\chrono-data\sealed\ledger`, and again from
   the code at HEAD and the data footers now (data unchanged since). The settings name the part, first 2016-01-04,
   last 2026-10-28, T09 `{"band": 15, "hold": 5}`, and offset 1 for older_vintage only.
2. **Commit rule** (`g4_seal_rule.py`; `tests/test_seal.py`, 14 pass in 30 s). `git diff 8c683f5 423a9c2` is
   `seal.lock` only, and 423a9c2's one parent is 8c683f5. With HEAD posed as 423a9c2 both parts pass; posed as
   7b9a138, 8c683f5 or 095a855 both are refused on "commit". A code change can't pass: it has to be in HEAD (a
   second change in the lock commit or a later commit fails) or in the tree (dirty fails).
3. **Once.** The run log holds exactly two starts, main n=1 and older_vintage n=1, both `again` false, both at
   423a9c2 with the lock's hashes. The `sealed\` folder was created at main's start second, so no earlier start
   existed. One run line per part, exit 0 for both, no `--again`, and the deflated Sharpe's trial count is 8.
   `seal.begin` refuses a second start of either part on a copy of the log (`g4_seal_rule.py`), which closes the M1
   open item ("refusing a second sealed run belongs to M4"). A refused attempt leaves no trace by design
   (`PREREG.md:53`), and none could open a sealed view.
4. **Dates** (`g4_runs.py`). Every book's equity ends 2026-10-28; live starts 2016-01-04; live_frozen_2019 runs
   2020-01-02 to 2026-10-28, 1,715 sessions, as `PREREG.md:33` fixes. Both parts are complete; all 27 books have their
   0, 5, 10 and 20 bps replays. `sim/simulator.py:150-157` ties the run's dates to the settings' (J4-4).
5. **Scoring code.** `git diff --stat 8c683f5 095a855 -- eval research/m4_sealed_report.py research/m4_sealed_run.py
   sim agent world reader data_pipeline` is empty. The writer ran at HEAD 423a9c2 before `ledger` (22:50:40, then
   22:50:59), in PREREG's order (`PREREG.md:49-51`). The committed report equals the writer's file
   (`git diff --quiet HEAD -- research/m4_sealed_report.md` in the run's worktree; file time equals `report.log`'s).
6. **Nothing after 2019 before the freeze.** The only ledger rows reaching 2020 or later are the two sealed rows,
   logged at 21:20 and 22:05 NY, after the lock. All 179 run outputs with a date column under `m3_dev`, `m4_dev` and the
   M3 timing folders end by 2019-12-31 (`g4_pre_seal_dates.py`), and every one predates 22:32 local. T09 was chosen on
   dev (stage2 at 06:27 local). The T09 check stopped at `research/m3_trial_plan.py:25` (2019-12-31), and its World
   refuses sealed views (`world/world.py:360`). PREREG's sealed-years numbers (1,715 sessions, lag 7) come from the
   calendar, not from outcomes.
7. **The offset change** (gap 6). `world/world.py:303` still refuses an offset World built with `allow_sealed`;
   the view's own offset refusal was removed, so only `sim/simulator.py:158` opens it, after `_offset`
   (`:184-195`) admits it only as the older_vintage part and the part only with offset 1. The offset is in the hash.
   Reviewed in `research/audit/m4_seal_judge.md:154-157`.
8. **Earlier fixes hold.** J4-1 (ledger outside git, `research/m4_sealed_run.py:133-134`), J4-2 (`sim/seal.py:108`),
   J4-3 (`sim/simulator.py:268-270`), J4-4 and J4-7 (`_open` inside the `try`), P-3 (order). P-6's text is in PREREG but
   was not carried out (G4-1). I did not recheck the writer checker's three fixes beyond the code being unchanged.

## Verdict

The sealed result is valid as a Failure. It ran once per part, at 423a9c2 (8c683f5 plus the lock alone), under the
sealed settings and dates, and was scored by unchanged code. I found no path for post-2019 outcomes into a dev
choice. One pre-registered precondition, the leak-test suite before and after the lock, was skipped and is not
disclosed (G4-1). It can't turn the Failure into a different outcome, but it needs a dated note.
