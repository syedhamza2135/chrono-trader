# M4 kickoff (23 Nov 2026)

Read this first when M4 starts. It covers where things stand, how the seal works today and what it lacks, what
`PREREG.md` must fix in advance, the steps of M4, and the decisions the owner must make. This session read code and
docs only. It opened nothing from the sealed years, ran nothing, and used one scout (Sonnet) for the seal lookups.

PLAN 8, step 6 (`PLAN.md:399`): "write `PREREG.md`, seal, run the sealed years once, and write the report." PLAN 9.2,
M4, "Done when" (`PLAN.md:446`): "`PREREG.md` is hashed into `seal.lock`, and the sealed report is published as-is".

**The sealed run happens once, and only on the owner's explicit go.** Nothing in this note starts it.

## Where things stand

- **M3 is merged into master** as `a9a216e` and pushed. The M3 branch ends at `a2a5f3e`, the review's fixes. This note
  is on the branch `claude/m4-kickoff`, cut from master `a9a216e`. Uncommitted.
- **Tests.** 513 pass and 1 skip, in 38 minutes 35 seconds (`research/review_m3_2026-11-23_fixes.md:32-34`).
- **The chosen configuration** is T09, `{"band": 15, "hold": 5}`, the stage 2 winner (`research/m3_dev_report.md:4`).
  Its dev results, all over 753 IC days from 2017-01-03 to 2019-12-30:
  - mean daily rank IC 0.0076, Newey-West t 1.38 (`m3_dev_report.md:114`);
  - the end-of-2016 twin gap +0.0179, t 2.61. The end-of-2017 gap is +0.0061, t 0.87. The end-of-2018 gap is
    -0.0150, t -1.76 (`m3_dev_report.md:59`, `62`, `64`). Most of the 2016 gap is the twin doing badly
    (`research/review_m3_2026-11-23.md:154-155`);
  - the news effect over the price-only twin is +0.0069, t 0.74 (`m3_dev_report.md:70`). Against the 5 placebo seeds
    the paired t runs from -0.72 to 1.94, and it is 1.14 against the seeds' daily mean (`m3_dev_report.md:71-75`,
    `review_m3_2026-11-23.md:86-87`);
  - the long-short Sharpe is -0.24 after 5 bps and 0.18 before costs. Momentum is 0.40 after costs
    (`m3_dev_report.md:85-86`). The long-only book has 0.83, against 1.12 for equal weight and 1.15 for SPY
    (`m3_dev_report.md:99-101`);
  - the deflated Sharpe is 0.0315 with 8 trials (`m3_dev_report.md:199`);
  - the switch-day check gives no warning: the pooled difference is -0.0107, p 0.62 (`m3_dev_report.md:284-286`).
- **The older-vintage check** (step 7) gives **no warning** under the owner's plain reading of the gate. The rule's
  news effect is +0.00687 (t 0.74). The older one is +0.00692, and the rule's run minus the older run is -0.00005 a
  day (t -0.01). So (a) and (b) both fail. The t of 0.74 is well below 1.645, so the check had little power on dev
  (`research/m3_kickoff.md:635-643`).
- **The M4 entry rules** (the owner, 23 Nov, `research/m3_kickoff.md:645-657`). These go into PREREG:
  1. The older-vintage gate is the point estimate: "above zero" means the news effect's mean is above zero. The
     outcome is "warning" or "no warning", never "passed". When the news effect's t is below 1.645, the report adds a
     power note.
  2. PREREG decides whether the sealed baselines get the band. Until then, compare them with live before costs.
  3. One placebo test: live against the daily mean of the 5 placebo seeds' ICs. Each seed is shown as spread only.
- **Open items from the M3 review** (none blocks M4, but each needs a line in PREREG or the report):
  - S3-3: the deflated Sharpe's trial variance comes from after-cost Sharpes. It is 0.03, 0.11 or 0.32 depending on
    which Sharpes are used (`review_m3_2026-11-23.md:90-92`). PREREG should fix one and report the others.
  - S3-5: the 5 random-ranking seeds lean negative (t -2.30), most likely by chance (`review_m3_2026-11-23.md:95-97`).
  - D3-10: the step 7 runs came from different commits (`review_m3_2026-11-23.md:115-117`). A sealed older-vintage
    run should use the same commit as the main sealed run.
  - S3-10: Sharpe is over zero, with no borrow fee or short rebate (`review_m3_2026-11-23.md:161`). The report says so.
  - The Newey-West lag stays 6. A monthly-means column is a fair robustness check (`review_m3_2026-11-23.md:190-193`).
  - W3-5: an agent could make its read-only vectors writeable (`review_m3_2026-11-23.md:144-145`). No agent does.
- **Known limit carried from M2.** Only the 2016 vintage has evidence for its cutoff, and 2026 was never checked
  (`research/m3_kickoff.md:25-27`). Every sealed result that leans on the news carries this limit.

## How the seal works today

Every line below was read on master `a9a216e`.

- **`seal.lock`** is JSON with three fields: `settings`, `prereg` and `commit` (`sim/seal.py:4`). The code only reads
  it (`sim/seal.py:47-52`). Nothing writes it except a test helper (`tests/test_sim.py:104-110`). Neither
  `seal.lock` nor `PREREG.md` exists.
- **The sealed start** is `reference/split.json`'s `periods.sealed.start`, read by `sim/seal.py:20-22` and by a copy
  in `world/world.py:57-59`. The file gives 2020-01-02 to 2026-10-28, 1,715 sessions (`reference/split.json:28-32`).
  PLAN says 2020-01-01 (`PLAN.md:335`). That is a holiday, so the first sealed session is the same.
- **The check**, `seal.check(first, last, settings)` (`sim/seal.py:43-62`):
  - it returns if `last` is before the sealed start (45-46);
  - it raises `SealError` if there is no `seal.lock` (48-49) or no settings (50-51);
  - it compares the SHA-256 of the settings (`settings_hash`, 25-26: sorted JSON), the SHA-256 of `PREREG.md`'s bytes
    and `git rev-parse HEAD` with the lock, and raises on any mismatch (55-60);
  - it raises if `git status --porcelain` shows anything (61-62).
- **`allow_sealed`.** A World refuses any view at or after the sealed start unless `allow_sealed` is set
  (`world/world.py:357-361`). A World with a `vintage_offset` refuses them always (`world/world.py:302-303`, `358-359`).
- **How a run opens the sealed years.** `sim.simulator.run` builds its settings from the caller's, the costs, the
  agent's class and parameters and the embedding window (`sim/simulator.py:122-124`). It refuses an offset World
  (125), calls `seal.check` (126), and sets `allow_sealed` only when that passes and `last` is sealed (127-129). It
  restores the old value at the end (139). `run_many` does the same (`sim/simulator.py:186-194`, `213`), with every
  agent's class and parameters and the freeze list in the settings. `replay` checks the seal too (M3 review W3-4).
- **Tests.** `tests/test_sim.py:125`, `:131` and `:152`; `tests/test_world.py:192`; `tests/test_report.py:162`;
  `tests/test_leaks.py:344` (which files may open the sealed years by hand); `tests/test_vintage_offset.py:88`, `:109`.

### Gaps the sealed run would hit

1. **The seal can never pass on the real repo as built.** `seal.lock` is not in `.gitignore`. Left untracked, it
   makes the tree dirty (`sim/seal.py:61-62`). Committed, it moves HEAD away from the commit it records
   (`sim/seal.py:57`). The tests use a fake git (`tests/test_sim.py:113-122`), so they don't see this. A fix to
   review in step 1: commit `seal.lock` alone, on top of the sealed commit, and let the check accept HEAD when its
   parent is the recorded commit and the only change is `seal.lock`. That keeps the lock in git as a dated record.
2. **No seal writer.** Step 1 builds one: it hashes `PREREG.md` and the sealed run's settings and records the commit.
3. **No one-run guard.** PLAN says a second sealed run "needs an explicit flag and is logged as another trial"
   (`PLAN.md:634`). Nothing in the code does this. `seal.check` has no state, so one lock allows any number of runs.
   Step 1 adds a marker written when a sealed run starts, a refusal when it exists, and a flag that allows a second
   run and logs it as a trial.
4. **No sealed runner.** The dev harness, `research/m3_dev_runs.py`, has fixed dev dates (`research/m3_trial_plan.py:25`,
   `research/m3_dev_runs.py:36`). Its labels stop at 2019-12-31 (`research/m3_dev_runs.py:48-51`), and so does SPY
   (`:197`). It calls `run_many` with no settings (`:148`), so it fails closed on a sealed date. M4 needs its own
   runner. It takes its dates from `split.json`, puts `first` and `last` into the settings (nothing adds them now),
   and cuts the labels at the sealed end.
5. **The feature list is not named in the lock** (`PLAN.md:635`). The features live in `agent/track_a.py` at the
   sealed commit, and the agent's parameters are in the settings hash. So the commit covers them. PREREG says so.
6. **The older-vintage check can't run on sealed dates.** The offset World refuses them by design
   (`world/world.py:302-303`, `sim/simulator.py:151-152`). Running it sealed needs a reviewed change (decision 2).
7. **The seal guards runs, not files.** The sealed labels and prices sit in the store, and any script could read
   them. Only the rule on `allow_sealed=True` (`tests/test_leaks.py:344`) and discipline guard this. M4's scripts read
   sealed outcomes only after the sealed run, through its runner.

## What `PREREG.md` must fix in advance

1. **The sealed dates.** Sessions from 2020-01-02 to 2026-10-28 (`reference/split.json:30-31`), unless decision 1
   picks a later end. The run lives from 2016-01-04, as on dev, so the agent learns through the warm-up and the dev
   years first. IC days run from 2020-01-02 to the last session whose label ends by the sealed end.
2. **The code and settings.** The sealed commit, the settings hash of the sealed `run_many` call, and the hash of
   `PREREG.md` itself, all in `seal.lock`. The agent is T09 with the parameters in
   `runs/settings/eed2890b...f377ff.json`, unchanged. The review changed `agent/track_a.py` after the dev runs (W3-3,
   `review_m3_2026-11-23_fixes.md:13`), so step 2 checks that the sealed commit gives the same dev decisions.
3. **The primary hypothesis and its test.** PLAN names three, H1 to H3 (`PLAN.md:353-357`), with Holm's correction
   across them (`PLAN.md:359`), and success needs H2 and H3 (`PLAN.md:363-366`). PREREG keeps that family. It also
   names H2, "it learned", as the primary one: one-sided, paired, Newey-West, live against the twin frozen at the
   first session of 2020 (`sim/simulator.py:182`, `202-204`).
4. **The secondary tests and the correction.** H1: live's mean IC above zero. H3: live beats both the price-only twin
   and the placebo mean. H3 holds only if both paired tests hold, so H3's p is the larger of the two. Holm runs over
   the three p values at a family level of 5%. Newey-West with lag 6, as on dev. Nothing else is tested. Sharpe,
   drawdowns, turnover, exposures, regimes, shocks and coefficient life are reported, not tested (`PLAN.md:359`).
5. **The twins, the placebo and the baselines.** The frozen twins at each year end, with the end-of-2019 twin
   pre-registered for H2. The price-only twin. The placebo with the same 5 seeds, tested as one daily mean (entry
   rule 3). Random ranking with 5 seeds, momentum, reversal, equal weight and SPY. The band: decision 4.
6. **The costs.** 5 bps per side for the after-cost rows (`sim/simulator.py:26`), and the sensitivity at 0, 5, 10
   and 20 bps (`research/m3_kickoff.md:55`). The tests are on IC, so costs don't touch H1 to H3. Sharpe is over zero,
   with no borrow fee (S3-10). The deflated Sharpe uses one stated source for its variance (S3-3), with 8 trials
   plus any sealed rerun.
7. **The two leak checks and their warning rules,** frozen in words.
   - The switch-day check, as `research/audit/cutoff.md:785-798` fixed it, on the sealed years. It is a cut of the
     live and price-only runs. 1 January 2026 is not a vintage switch: the 2024 vintage reads both 2025 and 2026
     (`reader/vintage.py:12`, `30`). PREREG says which years count. The recommendation is the switches from 2020 to
     2025, with 2026 reported apart.
   - The older-vintage check, as `cutoff.md:778-782` fixed it, with entry rule 1's plain gate and power note. It runs
     only if decision 2 says so.
   - What a warning means: decision 3.
8. **Success, failure and "not informative".**
   - Success: every leak test passes, and H2 and H3 both hold after Holm (`PLAN.md:363-366`).
   - Failure: a clean run in which H2 or H3 fails. "A clean 'it didn't learn' is also a valid result, reported as-is"
     (`PLAN.md:368`).
   - Void: the seal check fails, the run stops before its last session, or a leak test fails on the sealed commit.
     A void run is reported as void. A second run needs the flag and counts as a trial (`PLAN.md:634`).
   - "Not informative" applies only to the older-vintage check when its gate is closed, never to H1 to H3.
9. **What gets published as-is.** The sealed report from the writer, unedited: every test, every check, every
   baseline and seed, the ledger rows, `seal.lock`, and `PREREG.md`'s hash. Later notes go below it, dated, and never
   change a number. It holds aggregates only, never raw prices or headlines (AGENTS.md, Licensing). "Published" means
   committed to the private repo, unless the owner says otherwise.

## The steps of M4

| Step | What | Who | Laptop | Agent usage |
|---|---|---|---|---|
| 1 | Close the seal's gaps 1 to 4, plus 6 if decision 2 says so: the lock and git, the writer, the one-run guard with its flag, the sealed runner. Tests for each, with a real git repo in a temp folder, not a fake | A task session; one judge (Opus, high) on the seal code; a skeptic on any finding | The full suite, about 40 minutes | A share of one window, near M3's review: about 20% to 26% (`research/m3_kickoff.md:191`). An estimate |
| 2 | The dev check: the sealed runner, stopped at 2019-12-31 at the candidate commit, gives the same T09 decisions as the dev run | A task session; one checker (Sonnet) | One comparison pass, about 88 minutes (`research/m3_kickoff.md:571`) | Little |
| 3 | Write `PREREG.md` from this note and the owner's decisions. The owner reads and approves the text | A task session; one skeptic (Opus) against PLAN 5.5, the entry rules and this note | None | About 10% to 15%. An estimate |
| 4 | Seal: commit the code and `PREREG.md`, write `seal.lock`, commit it, run the full suite on the clean tree | The owner gives the go; the lead or the owner commits | About 40 minutes | Little |
| 5 | **The sealed run, once, only on the owner's explicit go.** Detached, as the reader ran | The task session starts it; nobody looks at results until it ends | About 4 to 6 hours. An estimate: the dev pass took 87.7 minutes for about 1,000 sessions, and this run covers about 2,700 | Waiting |
| 6 | The sealed report: the writer runs; a checker reproduces the headline numbers; the report is committed as-is | A task session; one checker | Minutes | About 10%. An estimate |

The owner pushes, as before. Steps 1 and 3 can overlap, since PREREG's text does not depend on the code. Step 4
needs both, plus step 2.

## Owner decisions

**Decided on 23 Nov.** The owner answered: "Whatever is better" (relayed by the lead, who took all six
recommendations as the better choice). So all five decisions below are decided as recommended. The sixth is the
switch-day years in PREREG item 7: the switches from 2020 to 2025 count, and 2026 is reported apart.

1. **The sealed end date.** Recommended: **2026-10-28**, the store's last day (`reference/split.json:31`). Why: a
   later end needs fresh prices, auctions, news, a new store and a new reading, with their audits, right before the
   seal. The days between the sealed end and the forward test's first day are scored by neither, and the report says
   so.
2. **The older-vintage check on the sealed years.** Recommended: **yes**. It is one more agent in the sealed event,
   reading `D:\chrono-data\reader_older` at the same commit, after a reviewed change that lets an offset World open
   sealed dates under the seal only. Why: on dev the check had little power (t 0.74), and the sealed years are read by
   the 2019 to 2024 vintages, none of which has cutoff evidence (`research/m3_kickoff.md:25-27`). The table already covers every story. The cost is gap 6's change, its test
   and about one more run's time.
3. **What a warning means.** `cutoff.md:782` leaves it to the owner. Recommended: **a warning in either check means
   H3 is not claimed as skill from reading**, whatever its p. Every number is still reported. Why: deciding it after
   the result would let the result choose the rule. A warning points at the reader, not the learner, so it leaves H1
   and H2 alone.
4. **The baselines' band.** Recommended: **as on dev**, hold 5 with no band, compared with live before costs. Why:
   the baselines are reported, not tested. A banded baseline would be new code and a new variant, added just before
   the seal and never run on dev.
5. **The test design in PREREG item 4:** H2 as the primary, Holm over H1 to H3 at 5%, H3's p as the larger of its
   two, lag 6, and no other tests. Recommended: **approve as written**. Why: it follows PLAN 5.5 and the entry rules,
   and the only choice it adds, H3 needing both tests, is what PLAN's "beats both" says (`PLAN.md:357`).

## Step 1, built on 23 Nov (uncommitted)

The owner's go: "Whatever is better", with the lead's brief to close the seal's gaps. Nothing was sealed, no
`seal.lock` was written in the repo, and nothing ran in the sealed years.

- **The lock and git (gap 1).** `seal.lock` records the sealed commit and is committed alone, straight after it. The
  check accepts HEAD only when its one parent is the sealed commit, it changes `seal.lock` and nothing else, and
  `seal.lock` is tracked (`sim/seal.py`, `_commit_matches`). The tree must be clean, so the lock read is the one in
  git, and an uncommitted lock is refused even if git ignores it (judge J4-2). Why not git-ignore it: an ignored lock leaves no record in git, so nobody could later check when the seal
  was made or what it held. A committed lock is dated by its commit, and the owner's push puts it on GitHub before the
  sealed run. Any later commit, even an empty one, breaks the match.
- **The writer (gap 2).** `seal.write({part: settings})` hashes each part's settings and `PREREG.md`, and records HEAD,
  the sealed dates and the time. It refuses a lock that exists, a missing `PREREG.md`, a dirty tree, an unknown part,
  a part whose settings name another part, and a lock without "main".
- **Once (gap 3).** `seal.begin` writes each sealed run's start to `D:\chrono-data\sealed\runs.jsonl`, after the check
  passes and before any sealed view opens. The log is outside git and shared by every checkout. A part that has
  started before is refused, even after a crash, unless `again=True`. Such a rerun is recorded as trial
  `sealed_<part>_<n>`, so it counts as another trial (PLAN 9.12). The first sealed run of a part has no trial name,
  since it runs the chosen dev trial; the run log holds every start, a crashed one included (judge J4-6, left as is).
- **The dates (judge J4-4).** A sealed run's settings must name its first and last sessions, equal to the run's own,
  so the lock fixes the sealed window.
- **Replay (judge J4-3).** `replay` in the sealed years needs a logged start of the same part with the same settings.
  The `Simulator` class itself is not guarded, like the store's files (gap 7).
- **The ledger (judge J4-1).** While the sealed parts run, their ledger rows go to `D:\chrono-data\sealed\ledger`,
  outside git. A row in the repo would dirty the tree, and the seal would refuse the next part. After the last part,
  `python research/m4_sealed_run.py ledger` copies them into `runs/trials.csv` and `runs/settings/`, for one commit
  after the sealed runs.
- **The parts.** The lock holds one settings hash per part: "main" (live, its twins, the price-only twin, the 5 placebo
  seeds and the baselines) and "older_vintage" (live on the older table). A sealed run names its part as
  `sealed_part`.
- **The older-vintage part (gap 6, decision 2).** A World with `vintage_offset` 1 still can't be built with
  `allow_sealed`, and its views refuse sealed dates by hand. Only `sim.simulator.run` and `run_many` open them, and
  only for the "older_vintage" part under the same seal. The "older_vintage" part also refuses a World without the
  offset.
- **The sealed runner (gap 4).** `research/m4_sealed_run.py`: `settings`, `dev-check` (step 2), `seal`, and
  `run main` or `run older_vintage`, with `--again`. Its dates come from `reference/split.json`, and it passes its
  settings, with `first`, `last` and a data fingerprint (each store table's size and Parquet footer hash, and the
  embeddings' arrays record). So the seal also covers which data the run reads.
- **The simulator.** `settings_run` and `settings_many` give the whole settings a run checks, and the writer uses the
  same function. The seal opens inside the `try` whose `finally` shuts it, after the simulators are built (J4-7).
- **Tests.** `tests/test_seal.py`, 14 tests, each on a real git repo in a temp folder: the lock committed alone
  passes; an uncommitted lock, an ignored lock, a lock dropped from git, a later commit, an empty commit, a lock
  committed with another change and an edited `PREREG.md` all fail; the writer's refusals; each part once unless
  `again`; full sealed runs of both parts through `run_many` on made-up records, with the made-up world's sealed start
  moved into its own dates; dates that differ from the settings'; a replay before any start; the ledger kept out of
  git until it is copied; and the runner's sealed settings against real Worlds. `tests/test_sim.py` and
  `tests/test_vintage_offset.py` follow the new rules.
- **The full suite after the fixes:** 527 pass and 1 skip, in 37 minutes 58 seconds on 23 Nov (pytest exit 0).
  That is 513 plus the 14 in `tests/test_seal.py`.
- **The review.** One judge (Opus, high effort, at 16% of the 5-hour window) and one skeptic (Opus, at 22%):
  `research/audit/m4_seal_judge.md`. 1 high (J4-1), 1 medium (J4-4), 4 low (J4-2, J4-3 after the skeptic, J4-5,
  J4-6) and 4 info. All four the skeptic checked stand. Fixed: J4-1 to J4-5 and J4-7. Left as notes: J4-6 (above),
  J4-8 (`PREREG.md` is hashed from the working tree's bytes, which a Linux checkout would change; the forward test
  should hash the committed blob), J4-9 (the data fingerprint holds the embeddings' arrays record, not a hash of the
  vectors; PREREG says so) and J4-10 (the run log is one file outside git; the sealed report quotes it).

## Steps 2 and 3 (23 Nov, uncommitted)

Step 1 is commit `6401ee7`.

- **Step 2, the dev check.** `research/m4_t09_check.py` reruns T09 on the dev years at `6401ee7` through the dev path
  (`sim.simulator.run`, the same agent, dates, costs and caller settings as step 6's `run_trial`), and compares its
  decisions with step 6's T09 run day by day. Its output is `D:\chrono-data\runs\m4_dev\T09_check\compare.json`, and
  its ledger row has no trial name. The result is below.
- **Step 3, `PREREG.md`** (repo root). It fixes H1 to H3 with Holm at 5% and lag 6, H2 as the main claim, H3 needing
  both its tests, the M4 entry rules, the sealed dates, both leak checks, the outcomes, the re-seal and rerun rules,
  and what is published. The code commit and the two settings hashes are placeholders, filled at the seal. PREREG
  can't name the sealed commit, since that commit holds PREREG, so it names the code commit under it.
- **The skeptic** (Opus, at 32% of the 5-hour window): `research/audit/m4_prereg_skeptic.md`, 3 high, 8 medium and 5
  low, all taken. `.gitattributes` now keeps `PREREG.md` and `seal.lock` as LF bytes (J4-8, P-9).
- **A new step before the seal (P-2).** PLAN's C-1 rule needs the scoring code committed before anything is scored.
  So `research/m4_sealed_report.py` must be built and tested on made-up records before step 4: it computes every
  number in PREREG sections 3 to 6 (H1 to H3, Holm, the placebo mean, both leak checks, the deflated Sharpe as fixed
  there, the replays' tables). Step 4 then runs the suite with `CHRONO_SLOW_LEAKS=1` before the lock and again after
  it (P-6). The sealed run's order is main, older_vintage, the replays, the writer, then `ledger` (P-3).
- **Step 2's result.** At `6401ee7`, T09's rerun gave the same decisions as step 6's run on all 817 decision days, with
  no day that differs, and the same equity rows (`compare.json`: `decisions_equal` and `equity_equal` both true; 10.6
  minutes). So the M4 seal changes and the review's W3-3 change to `agent/track_a.py` moved no dev decision. Ledger
  row `runs/trials.csv`, no trial name; settings file `runs/settings/c7780628...a8b2.json`.
- **The writer (step 3, P-2).** `research/m4_sealed_report.py` scores exactly PREREG sections 3 to 6: H1 to H3 with lag
  6 and Holm, H3 as the larger p of its two tests, the placebo's daily mean, the switch-day check on 2020 to 2025 with
  2026 apart, the older-vintage check, the outcomes and the deflated Sharpe's three versions with its variance guard.
  The descriptive part reuses `eval/report.py`'s `build` with a new `sealed=True`: no p-values, and no reading,
  variants, deflated Sharpe or switch-day sections. The dev report is unchanged with the default. The runner gained a
  `replay` step, run after both parts and before the writer and `ledger`. Tests: `tests/test_m4_sealed_report.py`, 7,
  all on made-up records.
- **The checker** (Sonnet, at 48% of the 5-hour window): `research/audit/m4_writer_check.md`. Nothing missing, no
  p-value left in the descriptive part. It found three things outside PREREG's words, all fixed: tests were still
  shown for a void main part; the "older-vintage check did not run" label was not in PREREG; and the older table
  showed p-values for two series PREREG doesn't test.
- **The full suite after step 3:** 534 pass and 1 skip, in 39 minutes 13 seconds on 23 Nov (pytest exit 0). That is
  527 plus the 7 in `tests/test_m4_sealed_report.py`.
