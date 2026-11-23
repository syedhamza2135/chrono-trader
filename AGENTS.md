# Chrono-trader: notes for the agent

Orientation and the owner's standing rules. The design and every decision are in `PLAN.md`; the commands are in
`README.md`.

## What this is

An AI that lives through US stock market history once, in order. Each trading day it sees only what was public before
it decides, and it reads the news with language models whose training ended before that day (ChronoBERT vintages).
Track A comes first: a time-locked reader plus a monthly ridge learner that ranks the 50 most-traded S&P 500 members.
The repo is the private GitHub repo `syedhamza2135/chrono-trader`, branch `master`.

## Start here

- **Work as `PLAYBOOK.md` says:** read the project-status memory first, then work in the hierarchy (a lead, one task
  session at a time, and the subagent types in `.claude/agents/`: `chrono-scout`, `chrono-digest`, `chrono-checker`,
  `chrono-judge`, `chrono-skeptic`). Keep briefs narrow and results in files.
- M0, the data audit, and its review are done. M1, the time wall, is built, reviewed twice and merged into master
  (8 Nov), with a few items left: read `research/m1_kickoff.md` first (sections "Session 1" to "Session 4"). M2,
  the reader, is reviewed and merged into master (`6894217`, 22 Nov): read `research/m2_kickoff.md` and
  `research/audit/reader.md`. The embeddings table is in the store.
- M3, Track A on the dev years, is built (steps 1 to 7) and reviewed (step 8) on the branch
  `claude/m3-kickoff-56264f`, with the review's fixes on `claude/m3-review-76bcd4`: read `research/m3_kickoff.md`
  (the owner's six decisions, the build order, steps 1 to 7 and the M4 entry rules). The dev results are in
  `research/m3_dev_report.md` (23 Nov): the chosen configuration is T09, `{"band": 15, "hold": 5}`. The older-vintage
  check is in `research/m3_older_vintage.md` (no warning). The review is `research/review_m3_2026-11-23.md`.
- M4, the seal and the sealed run, has started on the branch `claude/m4-kickoff`: read `research/m4_kickoff.md`
  (the owner's decisions, the seal's design and steps 1 to 3); the draft `PREREG.md` is in the repo root. Nothing
  is sealed, and the sealed years are still shut.
- `research/audit/m0_review.md` records the review and its fixes. `research/brief_check.md` records the check of a
  research brief and what the plan took from it.

## Standing rules

- **Secrets.** Alpaca's keys live only in `.env`, which git ignores and the owner fills in. Never read, print or commit
  `.env`, and never ask for keys in chat. Scripts load it at runtime. In a git worktree, set `CHRONO_ENV_FILE` to the
  main checkout's `.env` instead of copying it.
- **Licensing.** Raw news and price data never go into git or any public repo. The only exceptions are
  `reference/price_events.csv` (prices and evidence) and short headline quotes inside its evidence notes.
- **Disk.** Data and anything big live on D: (`D:\chrono-data`). The Python environment is `D:\venvs\chrono-trader`,
  linked as the repo's `.venv`. C: is nearly full.
- **Removing files.** Move them to the Recycle Bin. Never delete permanently.
- **Dates.** New York dates throughout.
- **Facts.** Never invent a number, date, result or source. Every claim needs evidence someone can check.
- **Docs.** Plain English, short sentences, no em-dashes.
- **Git.** Commit or push only when the owner asks, and ask again for each one. Claude Code's auto-mode check blocks
  pushes to master, so the owner runs the push. Commits and pull requests carry no Claude attribution: no
  Co-Authored-By trailer and no "Generated with Claude Code" line.
- **Usage limits.** The owner stops work at 90% of the 5-hour limit. Run agents one at a time, check usage before
  each, and at 85% save the state and stop. Never Fable; Opus at high effort for judgement.
- **Privacy.** Never send the owner's email address to any service.
- **Accounts.** Creating accounts (Alpaca and others) is the owner's step.

## Commands

- Tests: `.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` (534 pass and 1 skip, in about 35 to 52
  minutes on 23 Nov, after M4 step 3; the skip is the slow leak test, which runs only with `CHRONO_SLOW_LEAKS=1`). In a worktree with no `.venv` link, use
  `D:\venvs\chrono-trader\Scripts\python.exe`.
- The time wall: agents get only `world.view.View` (`World` is in `world/world.py`); `sim.simulator.run(world, agent, first, last)` is the daily loop,
  and `eval.leaks.non_interference` is the check every agent must pass.
- Pipeline modules are listed in `README.md`. Reruns that must reproduce M0 are pinned to the original dates; the
  pinned runners are in `D:\chrono-data\review\scripts\`.
