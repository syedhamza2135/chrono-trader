# M3 review, step 8: the skeptic (Opus, 23 Nov)

Branch `claude/m3-review-76bcd4` at `89f35f7`. I tried to refute the seven medium findings. A finding stands only if
my own check shows it. Nothing fixed, nothing committed, no `.env`. Only counts, turnover, Sharpe ratios, ICs and
t values were printed.

My script: `C:\Users\syedh\AppData\Local\Temp\claude\a742097078b03236\6cc4007d-fcb6-47d2-8b04-650f79c5109d\scratchpad\skeptic\sk_s3.py`
(run with `D:\venvs\chrono-trader\Scripts\python.exe`, about a minute). I also reran the judge's
`judge_recompute.py` in the same scratchpad.

Result: 7 stand. 1 stays medium (S3-1); 6 drop to low.

| id | verdict | rating (was medium) |
|---|---|---|
| S3-1 | stands | medium |
| S3-2 | stands | low |
| D3-4 | stands in part | low |
| D3-8 | stands | low |
| K3-5 | stands | low |
| K3-6 | stands | low |
| K3-8 | stands | low |

## S3-1: the "matched" baselines are matched on hold, not on turnover. Stands, medium.

- **What the docs promised.** Turnover, not just hold. `research/m3_kickoff.md:483-484` (inside the hashed plan
  block): "each holding as many sessions as the chosen trial, so their turnover is matched (the band is Track A's
  alone)". `research/m3_kickoff.md:540` (the owner's ruling 4): "so turnover is matched". `agent/baselines.py:16-17`:
  "so its turnover matches a Track A trial that holds as long". The dev report's section is only titled "Matched
  baselines" (`research/m3_dev_report.md:77`). So the stated claim is false, not just the fairness.
- **Check** (`sk_s3.py`, S3-1 part): mean daily turnover from 2017 from each book's 5 bps equity file, Sharpe at
  0 and 5 bps from the replays, and days on which the targets change.
- **Printed.** live: turnover 0.389, target-change days 152, Sharpe 0.183 before and -0.243 after. reversal: 0.641,
  152, 0.096 and -0.438. random_1 to 5: turnover 0.654 to 0.670, 151 or 152 days, Sharpe before -1.175 to 0.510
  (random_5 0.510), after -2.067 to -0.387 (best random_5 -0.387). momentum: 0.123, 146, 0.500 and 0.405.
- **Reading.** The hold is matched (same trade days). Turnover is not: the baselines trade about 1.7 times as much.
  The ranking flips as stated: before costs random_5 (0.51) beats live (0.18); after costs live beats every random
  seed. Against reversal there is no flip (live ahead both ways). Momentum beats live both ways.
- **Why medium, not lower.** A false statement in three places, one of them in the frozen block, and it changes a
  reported ranking that a reader would take as "live beats random after costs". Not high: the dev pick (T09) does
  not use the baselines, and no sealed result depends on it yet.
- **Note for the fix.** Line 484 is inside the hashed block (`m3_kickoff.md:435-499`), so a correction there changes
  the hash. Correct it outside the block, in the report and in `agent/baselines.py`.

## S3-2: no single rule for live against the 5 placebo seeds. Stands, low.

- **Check, rules.** PLAN H3 (`PLAN.md:357`, digest `plan_rules.md:209` cites the older L347): "beats both the
  price-only twin and the shuffled-news placebo", paired, one-sided, Newey-West. `PLAN.md:361` and `:607` ask only
  for the seed spread. Kickoff decision 6 (`m3_kickoff.md:161-166`) sets 5 seeds and nothing on how they combine.
  `grep` for "mean of the", "across seeds", "seed mean", "each seed" in PLAN, the kickoff and the digest finds no
  rule. `eval/report.py:115-117` tests each seed on its own; `:232` uses a seed mean only for a rolling chart.
- **Check, numbers** (`sk_s3.py`, S3-2 part). Paired NW t of live minus each placebo, 753 days: 1.82, 1.94, 0.53,
  0.91, -0.72. Live minus the daily mean of the 5: mean 0.0068, t 1.14. A third rule, live's mean IC against the 5
  seeds' means as 5 points (df 4), gives t 1.84. So the answer moves with the rule chosen.
- **Why low.** No M3 doc or number is wrong, and no dev conclusion changes. PLAN puts the final form of H1 to H3 in
  `PREREG.md` (`PLAN.md:351`: "Draft pre-registered hypotheses (finalized in `PREREG.md`)"), which does not exist yet
  and is the scheduled place for this rule. It must be carried into PREREG as a required item; it is not an M3 defect.

## D3-4: the kickoff's result summary is selective. Stands in part, low.

- **Check.** Read `m3_kickoff.md:558-566` and `m3_dev_report.md:52-64, 77-99`.
- **Printed (read).** The summary says every trial loses after 5 bps, Sharpe 0.18 before and -0.24 after, retraining
  beats the end-of-2016 twin by 0.0179 (t 2.61), the reading adds 0.0069 (t 0.74, "not significant"), no switch-day
  warning; lines 563-566 add that placebo seed 5 beats live and the seed t values spread widely. It opens with
  "`research/m3_dev_report.md` holds the results". The report shows the end-of-2017 twin gap +0.0061 (t 0.87), the
  end-of-2018 twin -0.0150 (t -1.76, 2019 only, 251 days), momentum Sharpe 0.40 after costs and IC 0.0218, and the
  long-only book at 0.83 against equal weight 1.12 and SPY 1.15. None of these is in the summary.
- **Against the finding.** The end-of-2016 twin is the principled one to quote: it is the twin frozen at the start
  of the evaluated span (2017 to 2019), the dev analogue of H2's end-of-2019 twin for the sealed years, and it has
  the most days (753). The summary also states three unfavourable results. So it is short and points to the
  report, not misleading on its face.
- **For the finding.** Momentum beating live on both IC and Sharpe, and the long-only book trailing both long-only
  benchmarks, are headline facts a reader of the summary would want. Their absence leans the summary favourable.
- **Rating low:** a completeness gap in a summary that names its full source. The one-sentence fix stands.

## D3-8: the lead's reading of the 10.1 gate. Stands, low.

- **Check.** Read `research/audit/cutoff.md:762-800` and `m3_kickoff.md:608-621`; reran `judge_recompute.py`.
- **Text.** 10.1 (b) at `cutoff.md:779` says "above zero, one-sided at 5%"; 10.2 (a) at `:793` says the same. The
  gate at `:780` says only "isn't above zero in the first place". The same section adds the test words each time it
  means a test, so the plain reading of the gate is the point estimate. The finding's textual point holds.
- **Printed.**
  `gate point estimate > 0: open=True a=False b=False -> no warning`;
  `gate one-sided 5%: open=False a=False b=False -> not informative`.
  Inputs (`m3_older_vintage.md` table): rule's news effect +0.00687 (t 0.74, p 0.23), older +0.00692, rule minus
  older -0.00005 (p 0.50). (a) fails since +0.00692 is not below half of +0.00687; (b) fails.
- **Timing.** The reading was made after the dev result (`210bfaf`, 2026-11-23 08:10 +0500) and committed in
  `001d01c` (14:28 +0500), before the older run's result. The kickoff says so itself (line 608).
- **Why low.** No outcome changes: "no warning" under either reading. The deviation is disclosed, and both docs
  already say no reading gives a warning (`m3_kickoff.md:620-621`, `m3_older_vintage.md:60-61, 68-69`). What remains is a
  wording rule for PREREG (freeze the gate as the point estimate) and the label "not informative" on top of
  `m3_older_vintage.md:3`, which rests on the stricter reading.

## K3-5: the code map is stale. Stands, low.

- **Check.** `sed -n 3p docs/digests/code_map.md`; `git log -1 -- docs/digests/code_map.md`; `grep -c` for each
  M2 and M3 module name.
- **Printed.** "Commit dd40a5f. Date 2026-11-21."; last commit on the file `c0a9b7f` 2026-11-21. Zero mentions each
  of track_a, baselines, placebo, stats.py, switch_day, report.py, charts.py, trials.py, benchmarks, embed.py,
  reader/cutoff, download.py. `code_map.md:80` lists `eval/metrics.py (18 lines)`; `:98` says "The embedding job is
  not built yet".
- **Why low.** PLAYBOOK.md:92-93 says to run `git log -1 -- <source>` before using a digest and refresh it first if
  the source changed, and PLAYBOOK.md:97 puts the digest refresh at the start of every review. Staleness between
  refreshes is the expected state, and the playbook already catches it at use. It needs a refresh before M4, not a
  medium flag. (The live risk is the PLAN digest's line numbers, D3-13: H3 is cited as L347, now `PLAN.md:357`.)

## K3-6: README lists no M3 module and only step 7's commands. Stands, low.

- **Check.** `grep -c` in `README.md` for track_a, baselines, placebo, switch_day, eval/report, charts, trials,
  benchmarks, m3_dev_runs, m3_compare_timing, track_a_timing, m3_trial_plan, eval/stats, eval/metrics: 0 each.
  `git diff master..HEAD -- README.md`: two added lines, the `reader.embed run-older` row and the
  `m3_older_vintage.py` row (README.md:73-74). `README.md:22` still says "a toy agent in `agent/`", and
  `README.md:32` "Nothing is trained yet."
- **Count.** `git diff --name-status master..HEAD -- agent eval data_pipeline` shows 10 added modules
  (agent: track_a, baselines, placebo; data_pipeline: benchmarks; eval: benchmarks, charts, report, stats,
  switch_day, trials) plus `eval/metrics.py` extended. "11 new" is 10 new and one grown; the substance holds.
- **Why low.** Every missing command is documented with its arguments in `research/m3_kickoff.md` (186, 276, 320,
  501, 510, 523) and in module docstrings, so nothing is unreproducible. The project's habit is to update README when
  a milestone finishes (M2 did it in `3d1df9b`), and M3 is still in review. AGENTS.md says the commands are in
  README, so it must be done before the merge.

## K3-8: the kickoff's status section is stale. Stands, low.

- **Check.** Read `m3_kickoff.md:1-26`; `grep` for step headings; `git log master..HEAD`.
- **Printed (read).** Line 5: "Nothing in M3 is built yet." Line 21: "344 pass and 1 skips, in 6 to 11 minutes".
  Line 23: "Uncommitted." All 8 M3 commits exist (`9d04ced` to `89f35f7`). The checker missed line 5, and also each
  step heading's "uncommitted" tag (lines 185, 200, 228, 283, 353, 432), now false. Step 7's heading (569) still
  says "started" though its result is at 615-621. Step 8 appears only as a row of the build-order table (184) and as "the step 8 review" (609).
- **Against the finding.** Each step does have its own section saying it is done or built, with checkpoints
  (`83a35cd` at 548, `210bfaf` at 567) and step 7's result. So the state can be read from the body. PLAYBOOK makes
  the project-status memory, not this note, the live state.
- **Why low.** No result is wrong, and the body records each step. But the top of the note, which AGENTS.md sends
  readers to, says the opposite of the truth. A short status line at the top fixes it.
