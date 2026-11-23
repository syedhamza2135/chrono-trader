# M4 step 1: judge's check of the seal build (23 Nov)

The question: does the M4 step 1 build do what PLAN 9.12 (`PLAN.md:630-635`) and 5.5 items 3 to 5
(`PLAN.md:329-335`) require, without opening a way into the sealed years?

What was read: `git diff` of `sim/seal.py`, `sim/simulator.py`, `world/world.py`, `tests/test_sim.py` and
`tests/test_vintage_offset.py` on branch `claude/m4-kickoff` (uncommitted, on master `a9a216e`); the new files
`research/m4_sealed_run.py` and `tests/test_seal.py`; `research/m4_kickoff.md` sections "How the seal works today"
and "Gaps the sealed run would hit". A few lines beyond those, named where used: `eval/trials.py:25-51`,
`world/world.py:261-296` and `:338-386`, `reader/embed.py:345-346`, `.gitignore`, `git ls-files runs`.

Nothing under `D:\chrono-data` was opened, the sealed runner was not run, and no `seal.lock` was written in the repo.
Every probe below runs on made-up git repos in a temp folder and on the synthetic world, with the sealed start moved
to 2017-03-01. The probe script is
`C:\Users\syedh\AppData\Local\Temp\claude\8332137c1e82c791\df273834-5403-4436-8fa3-60141de37d52\scratchpad\j4\probe.py`
(run it with `D:\venvs\chrono-trader\Scripts\python.exe probe.py`). `tests/test_seal.py` and
`tests/test_vintage_offset.py` pass (22 passed).

## Findings

### J4-1 (high). The second sealed part can never pass the seal: the runner dirties the tree after the first

- **Where.** `research/m4_sealed_run.py:127-128` calls `eval.trials.record`, which writes `runs/trials.csv` and
  `runs/settings/<hash>.json` under the repo (`eval/trials.py:25`, `:41-50`). Both are tracked or not ignored
  (`.gitignore` keeps `!runs/trials.csv` and `!runs/settings/`; `git ls-files runs` lists 21 files).
  `sim/seal.py:124` refuses a dirty tree.
- **What is wrong.** After `run main` finishes, the tree shows ` M runs/trials.csv` and `?? runs/settings/`. Then
  `run older_vintage` (or `run main --again`) fails with "the working tree isn't clean". Committing the ledger
  doesn't help: any commit after the lock commit breaks `_commit_matches` (`sim/seal.py:95-100`), by design.
- **Failure case.** Probe P2: a made-up repo that tracks `runs/trials.csv`, lock for both parts committed alone.
  The older_vintage check passes before `trials.record` and is refused right after it.
- **Why it matters.** Not a leak. But the sealed event as built can't be completed, and the fix would be improvised
  between the two sealed runs, after main's outcomes exist. The tests miss it because `test_seal.py` never calls
  the runner's `run_step`.
- **Fix.** Keep the sealed runs from touching git: have `run_step` write its ledger row to `DATA_DIR/sealed/`
  (next to the run log), and copy the rows into `runs/trials.csv` in one commit after every sealed part has run.
  Add a test that runs both parts back to back on a repo that tracks `runs/trials.csv`.

### J4-2 (medium). The check accepts a lock that git never saw

- **Where.** `sim/seal.py:97-98`: `if head == sealed: return True`.
- **What is wrong.** The lock records HEAD when it is written, so HEAD can equal the recorded commit only while the
  lock is uncommitted. An uncommitted lock passes the clean-tree check (`sim/seal.py:124`) only if git ignores it:
  through `.git/info/exclude`, a global excludes file, or a later `.gitignore` line. `git status --porcelain` doesn't
  list ignored files. So this branch accepts exactly the case the design means to refuse. The lock is then no dated
  record, and it can be rewritten between runs with no trace in git.
- **Failure case.** Probe P1: write the lock, add `seal.lock` to `.git/info/exclude`, don't commit. `seal.check`
  passes. Editing the lock afterwards also passes.
- **Fix.** Drop the `head == sealed` branch. Accept only "HEAD's one parent is the sealed commit and HEAD changes
  only `seal.lock`", and also require that `seal.lock` is tracked and matches HEAD's blob (for example
  `git ls-files --error-unmatch seal.lock` and an empty `git status --porcelain --ignored -- seal.lock`). The fake
  git in `tests/test_sim.py:124-128` then needs a parent; give it one.

### J4-3 (medium). `replay` reaches sealed outcomes under the seal without `begin`

- **Where.** `sim/simulator.py:254-272`. It calls `seal.check` (`:262`) but never `seal.begin`, and nothing ties it
  to a sealed run that has started.
- **What is wrong.** PLAN 9.12 says there is one sealed run. With a valid lock, anyone can pass the sealed settings
  to `replay` with a made-up `Run` (any targets on any sealed dates) and get its sealed equity. The run log stays
  empty, so no trial is counted. This is the one route through `sim.simulator` to sealed outcomes that skips the
  once-guard. (The store itself is open to any script, kickoff gap 7; this finding is about the guarded API.)
- **Failure case.** Probe P4: lock committed, run log empty, `replay` of a one-row made-up decision table on
  2017-03-01 to 2017-03-03 (made-up "sealed" dates) returns equity rows; the run log still has 0 entries.
- **Fix.** In `replay`, when the dates reach the sealed years, require a run log entry for the settings' part with
  the same settings hash (a `seal.require_started(settings)` helper), and test that a replay before any start is
  refused.

### J4-4 (medium). The sealed dates in the settings don't bind the run's dates

- **Where.** `sim/simulator.py:117-142` (`settings_run`, `settings_many`) hash the caller's settings but never
  compare `first` and `last` with the arguments. The runner puts `first` and `last` into the settings
  (`research/m4_sealed_run.py:80-81`), so the hash looks as if it covers the dates.
- **What is wrong.** A call with the sealed settings and any other `first` or `last` passes the seal. The run log
  catches it as the part's one start, so it can't be repeated without `again`. But PLAN 5.5 item 5 fixes the sealed
  window (2020-01-01 to the last session before the seal), and the lock should enforce it, not the runner's habit.
- **Failure case.** Probe P3: lock sealed on settings naming 2016-01-04 to 2017-06-30; `run_many` from 2017-03-01 to
  2017-03-03 with those settings passes and opens 3 sealed sessions.
- **Fix.** Let `settings_run` and `settings_many` add `first` and `last` from the arguments (as strings of the
  sessions), or refuse in `_open` when the settings carry dates that differ from the arguments. Test both.

### J4-5 (low). The runner test is a tautology

- **Where.** `tests/test_seal.py:243-261`, against `research/m4_sealed_run.py:88-95`.
- **What is wrong.** The test claims the sealed settings "equal what run_many computes from a World with the same
  window and offset". Both sides use a `SimpleNamespace`, never a `World`, and the test hard-codes window 90. It
  can't catch a World whose `embedding_window_days` or `vintage_offset` attribute differs from the stand-in.
- **Fix.** Build `World(**synthetic.make_tables(0), ...)` with the default window, once with offset 0 and once with
  the older embeddings and offset 1, and assert `settings_many(world, ...) == R.full_settings(part)`.

### J4-6 (low). The trial ledger undercounts a crashed or first sealed run

- **Where.** `research/m4_sealed_run.py:126-128`; `eval/trials.py:62-65` counts only rows with a trial name.
- **What is wrong.** The first sealed run is recorded with `trial=""`, so `trials.count` doesn't count it. A first
  run that crashes after `begin` leaves no ledger row at all; the `--again` rerun then appears alone as
  `sealed_main_2`. The run log has both starts, so nothing is lost, but the ledger PLAN 5.5 item 2 names shows one.
- **Fix.** Name every sealed row (`sealed_<part>_<n>`), and write a "started" row at `begin` (in the DATA_DIR ledger
  of J4-1), not only after a finished run.

### J4-7 (info). `_open` runs before the `try`

- **Where.** `sim/simulator.py:165` and `:227`.
- **What is wrong.** `allow_sealed` is set inside `_open`, before the `try` whose `finally` restores it. Nothing
  between them can raise in practice (`decisions = []`, `year = None`), so this is not a live path. An interrupt in
  that gap would leave the World open.
- **Fix.** Optional: save `was_allowed` first and call `_open` inside the `try`.

### J4-8 (info). `PREREG.md` is hashed from working-tree bytes

- **Where.** `sim/seal.py:57-59`.
- **What is wrong.** This repo checks out with CRLF conversion (git warns "LF will be replaced by CRLF"). The same
  commit on Linux (the forward test, PLAN 5.5 item 6) would hash `PREREG.md` differently and fail the check.
  Not a problem for the local sealed run.
- **Fix.** When the forward test is built, hash the committed blob (`git cat-file blob HEAD:PREREG.md`) instead.

### J4-9 (info). The data fingerprint is weaker than its description

- **Where.** `research/m4_sealed_run.py:61-65`.
- **What is wrong.** The embeddings' "arrays record" (`reader/embed.py:345-346`) holds the row count, the story ids'
  hash, file names, width, type and the Parquet footer, not a hash of the `.npy` vectors. And the fingerprint comes
  from the runner's path constants, not from the World that `world_of` loads. Both match today, and
  `load_embeddings` (`world/world.py:273-296`) ties the arrays to the Parquet rows, so this is a note.
- **Fix.** None needed for M4. Say in PREREG what the fingerprint covers.

### J4-10 (info). The once-guard lives in one file outside git

- **Where.** `sim/seal.py:34`, `:161-188`.
- **What is wrong.** Deleting `runs.jsonl`, pointing `seal.RUNS_LOG` elsewhere or changing `DATA_DIR` resets the
  guard. Two processes started together could both log a first run. This is discipline, as PLAN expects, and one
  job at a time is the rule.
- **Fix.** None needed. The report of M4 step 6 should quote the run log's entries.

## What was checked and found right

- **No sealed view without check and begin in `run` and `run_many`.** `_open` (`sim/simulator.py:145-155`) runs
  `_offset`, then `seal.check`, then `seal.begin`, then sets `allow_sealed`. A refusal at any step leaves
  `allow_sealed` as it was. `test_a_refused_run_opens_nothing_and_logs_nothing` shows a dirty tree logs nothing.
  `finally` restores the old value after the run (`:173-174`, `:243-244`).
- **Begin before views.** The log line is written at the end of `begin` (`sim/seal.py:184-188`), after its own
  refusals and before `allow_sealed` is set. A crash after `begin` still counts as a start.
- **Once per part.** A second start is refused without `again`; `again` on a part that never started is refused; a
  start without a known `sealed_part` is refused (`sim/seal.py:165-176`). Tested at `tests/test_seal.py:128-143` and
  through `run_many` at `:210-214`.
- **Part hash.** Settings without `sealed_part` look up `None` in the lock and fail (`sim/seal.py:103-105`). A part
  missing from the lock fails (`tests/test_seal.py:57-58`).
- **Commit rule, apart from J4-2.** A merge commit has two parents and fails. A rename into `seal.lock` lists two
  paths (`diff-tree` without `-M`) and fails. A deleted lock fails on "no seal.lock". A lock committed with another
  file, an empty commit after the lock, a later code commit, an edited `PREREG.md` and an amended sealed commit all
  fail (the last because the recorded commit no longer exists as HEAD's parent). Detached HEAD changes nothing.
- **Writer against checker.** The writer hashes `settings_many` output; `run_many` checks `settings_many` output on
  the real agents and World. `World.vintage_offset` and `World.embedding_window_days` are properties
  (`world/world.py:338-346`), and `World.load` uses `EMBEDDING_WINDOW_DAYS` by default, the same value the runner's
  stand-in uses. The writer refuses an existing lock, no PREREG, a dirty tree, a missing "main", an unknown part and
  a part whose settings name another part.
- **The offset change.** The default World is unchanged. The offset World still can't be built with
  `allow_sealed`, and its views refuse sealed dates unless the runner opens them, as for the default World. `_offset`
  refuses the offset World for any sealed run that is not the "older_vintage" part, and that part without the
  offset. The offset goes into the hash, so the main part's lock can't be used with an offset World or the reverse.
  Below the sealed start nothing changes (`sim/simulator.py:183-184`).
- **Feature list (PLAN 9.12 item 4).** Covered by the commit check, since the features are code at the sealed
  commit, and by the agents' parameters in the hash (kickoff gap 5).

## Skeptic

Checked on 23 Nov by rereading the cited lines and running a new probe of my own:
`C:\Users\syedh\AppData\Local\Temp\claude\8332137c1e82c791\df273834-5403-4436-8fa3-60141de37d52\scratchpad\skeptic\check.py`
(run with `D:\venvs\chrono-trader\Scripts\python.exe check.py`). It uses made-up git repos in a temp folder, each with
the real `.gitignore` copied in, and the synthetic world with the sealed start moved to 2017-03-01. Nothing under
`D:\chrono-data` was read, the sealed runner was not run, and no `seal.lock` was written in the repo.

### J4-1: stands, high

- **Evidence.** `research/m4_sealed_run.py:127-128` calls `trials.record` with no `runs=`, so it writes to
  `ROOT / "runs"` in the repo (`eval/trials.py:30`, `:41-50`). In the real repo `git ls-files runs` lists 21 files,
  `runs/trials.csv` among them, and `git check-ignore runs/settings/x.json` finds no rule (exit 1). In the probe, a
  repo with both parts' lock committed alone passes the older_vintage check. After one `trials.record` the status is
  ` M runs/trials.csv` and `?? runs/settings/<hash>.json`, and both the older_vintage check and a main `--again`
  check are refused with "the working tree isn't clean".
- **Severity.** High is right. It fails closed, so nothing leaks, but it would stop the sealed event for certain, and
  the fix would then be made after main's outcomes exist.
- **Fix.** A simpler form of the judge's fix: `trials.record` already takes `runs=`. Pass a folder outside git, for
  example `runs=DATA_DIR / "sealed" / "ledger"`. In the probe the same call with `runs=` outside the repo leaves the
  tree clean and the older_vintage check passes. Copy those rows into `runs/trials.csv` in one commit after the last
  sealed part. Keep the judge's test of both parts back to back on a repo that tracks `runs/trials.csv`.

### J4-2: stands, low

- **Evidence.** `sim/seal.py:97-98` returns True when HEAD is the recorded commit. In the probe, an uncommitted lock
  is refused as dirty. Once `seal.lock` is in `.git/info/exclude`, the check passes, `git ls-files seal.lock` is
  empty, and a lock edited to hash other settings also passes with those settings.
- **Severity.** Low, not medium. It needs a deliberate step: nothing ignores `seal.lock` today (`git check-ignore -v
  seal.lock` in the real repo exits 1, and `core.excludesfile` is not set globally). That is the same weight as
  deleting the run log, which J4-10 rates as discipline. The fix is still worth taking, since the branch is never
  right.
- **Fix.** Simpler than the judge's. Require that `seal.lock` is tracked (`git ls-files --error-unmatch seal.lock`).
  With the existing clean-tree check, that is enough: in the probe a staged but uncommitted lock shows `A  seal.lock`,
  and a tracked lock edited while listed in `.git/info/exclude` shows ` M seal.lock`, so both are refused. A tracked,
  clean lock can't sit in the sealed commit it names, so `head == sealed` can then never hold; drop that branch too.
  The `--ignored` status check is not needed. `FakeGit` in `tests/test_sim.py:116-128` needs a parent and a tracked
  answer.

### J4-3: stands, low

- **Evidence.** `sim/simulator.py:260-262` calls `seal.check` and never `seal.begin` or anything that reads the run
  log. In the probe, with the lock committed and an empty run log, `replay` of a made-up one-row run on three made-up
  sealed sessions returns 3 equity rows, and the log still has 0 entries.
- **Severity.** Low, not medium. The judge calls this the one route through `sim.simulator` to sealed outcomes that
  skips the once-guard. It is not. `Simulator` itself reads `world.opens` and `world.labels.df` with no seal call
  (`sim/simulator.py:38-48`). In the probe, a bare `Simulator(world, 0.0)` stepped over the same three sealed
  sessions returns 3 rows with no lock check at all, and `world.labels.df` holds rows past the sealed start. So the
  check in `replay` guards against accidents, not against a script. That is kickoff gap 7.
- **Fix.** The judge's `seal.require_started(settings)` in `replay` is cheap and right for accidents; take it with
  its test. Also say in the `replay` and `Simulator` docstrings that `Simulator` is not guarded, so no one reads the
  check in `replay` as a barrier.

### J4-4: stands, medium

- **Evidence.** `settings_run` and `settings_many` (`sim/simulator.py:117-135`) never compare `first` or `last` with
  the arguments, and `_open` (`:145-155`) doesn't either. In the probe, a lock sealed on caller settings naming
  2016-01-04 to 2017-06-30 lets `run_many` from 2017-03-01 to 2017-03-03 with those settings pass. It opens 3 sealed
  sessions and logs ("main", 1), so the wrong window uses up the part's one start.
- **Severity.** Medium is right. The runner itself passes matching dates (`research/m4_sealed_run.py:119-122`), so
  only a hand call goes wrong. But that call costs the part's one clean run.
- **Fix.** The judge's second option, made firm: in `_open`, when the dates reach the sealed years, refuse unless
  the settings carry `first` and `last` and both equal the arguments as timestamps. It touches only sealed runs and
  leaves every settings dict as it is, while the first option changes what `settings_run` returns for every run.
  Test a missing date, a different `first` and a different `last`.

## Fixes (23 Nov, in the same uncommitted build)

| Finding | Fix | Test |
|---|---|---|
| J4-1 | The sealed runs write their ledger rows to `DATA_DIR/sealed/ledger`; `research/m4_sealed_run.py ledger` copies them into the repo after the last part | `test_the_sealed_ledger_stays_out_of_git_until_it_is_copied` |
| J4-2 | `_commit_matches` drops `head == sealed` and needs `seal.lock` tracked (`Git.tracked`) | `test_a_lock_git_ignores_or_drops_is_refused` |
| J4-3 | `replay` in the sealed years calls `seal.require_started`: a logged start of the part with the same settings hash | `test_a_sealed_replay_needs_a_started_run_with_its_settings` |
| J4-4 | `_open` refuses a sealed run whose settings lack `first` and `last` or name other dates | `test_a_sealed_run_must_run_the_dates_its_settings_name` |
| J4-5 | The runner test builds real Worlds, without and with the offset | `test_the_sealed_runner_seals_each_part_on_what_run_many_will_check` |
| J4-7 | `_open` runs inside the `try` whose `finally` puts `allow_sealed` back | the existing sealed-run tests |

Left as notes in `research/m4_kickoff.md` (step 1): J4-6, J4-8, J4-9 and J4-10.
