# Judge: the stronger-probe freeze, the 8.9 result and the owner's decision (M2 review, 22 Nov 2026)

Commit 3d1df9b, branch claude/m2-review-43e1a3. Scope: `git diff 7081fba..3d1df9b` for reader/cutoff.py,
reader/probes2.csv, research/audit/cutoff.md (lines 316 to 795) and research/audit/probes2_judge.md. Read first:
docs/digests/m2_cutoff.md and the cutoff_judge and probes2_judge lines of docs/digests/m2_prior_findings.md. No model
was run and nothing was edited. Times below are New York unless marked +0500 (the laptop's clock).

The re-derivation script is
`C:\Users\syedh\AppData\Local\Temp\claude\166f9164ebdccd7e\9de82187-73a0-485c-b919-d5de64e3fe28\scratchpad\rederive.py`
(run with `D:\venvs\chrono-trader\Scripts\python.exe -I`). It loads `D:\chrono-data\reader\cutoff\probes2\scores.parquet`,
runs `reader.cutoff.probe2_outcomes`, compares it with `report.json`, and recomputes T, q and every outcome a second
time from the words of cutoff.md 8.4 and 8.5 without the module's rule functions.

## What I checked and found right

- **Hashes.** The worktree's `reader/probes2.csv` hashes to `eed31d91...d5bd` and `reader/cutoff.py` to
  `8bae55f5...3e3b` (`sha256sum`). Both equal the second freeze (cutoff.md:598-599), `probes2\scores.json`, the
  first line of `run_probes2.log` and the first line of `report_probes2.md`. The build worktree
  (reverent-sanderson-da34d6) has the same two hashes. The committed probes2.csv (`git show e53c114:reader/probes2.csv`)
  has the same hash, protected by `.gitattributes:1-3`. For cutoff.py see C-2.
- **The run looks like one run.** `run_probes2.log` has one hash line and 11 "probes scored for vintage" lines.
  `scores.parquet` has 880 rows, 80 probes by 11 vintages, no duplicates, no missing scores, the largest score
  -0.0011 (all at or below 0, as a log share must be).
- **The file times are in the claimed order.** probes2.csv created 15:49:40 and last written 16:20:26; test_cutoff.py
  last written 16:16:53; probes2_judge.md written 16:09:54 and never changed since; probe_margin_pilot.py 16:15:19
  (it reads the first set's `n2000/probes.parquet`, not the new probes); probe_rules_sim.py 16:18:18 (made-up scores);
  cutoff.py last written 16:20:51; run_probes2.log created 16:21:25; the `probes2` folder created 16:21:26;
  scores.parquet and scores.json 16:35:22; report.json 16:35:35; cutoff.md last written 17:06:53. Every edit to the
  probe file and the rule code comes before the first file of the run.
- **The first freeze has a second witness.** probes2_judge.md:4 and 11-12, written at 16:09:54, record that no
  probe of the new set was scored and that the files matched the first-freeze hashes `5dac4506` and `06f106d0`.
- **The outcome table in 8.9 follows from the saved scores.** The module and the independent recomputation agree
  with each other and with report.json on every vintage: T = 1.6312 (360 honest cells), q = 0.0972 (7 of 72),
  outcomes 2015 too weak (n 1), 2016 pass (n 3, flag q2017f), 2017 to 2021 too weak (n 0, 0, 0, 1, 0), 2022 too weak
  (n 2, flag q2023c), 2023 too weak (n 0), 2024 too weak (n 0.292 = q times 3 usable). No flag falls in January to
  March. This matches cutoff.md:613-626 cell for cell.
- **The q2023c flag is computed right.** For 2022: score -3.07, lo -7.14 (median of 2019 to 2021), hi -3.50
  (median of 2023 and 2024), gap 3.64 (informative), midpoint -5.32, lo + T -5.51. The score clears both by about 2.2,
  so the flag is not a near miss. The q2017f flag on 2016: score -4.92, lo -7.10, hi -3.10, gap 4.01, midpoint -5.10,
  lo + T -5.47.
- **The words of 8.10 and 9 match the numbers.** "2016 passes at the edge: exactly 3 informative probes and 1 flag"
  (cutoff.md:738-739) is exact. "Too weak means the probes could not tell, not that the vintage leaked" and "None
  failed, but that is not evidence they are clean" (cutoff.md:752-753) do not oversell. "Only the 2016 vintage is
  supported by evidence: it passed ... at the edge" (cutoff.md:750) is fair.
- **The owner's decision is recorded as a known limit, with its date.** cutoff.md:747-757 gives the date (21 Nov
  New York, 22 Nov local), the words "Accept, go on", that no vintage is replaced, the q2023c flag as seen and
  accepted, 2026 as never checked, and calls it a known limit of M2. The same record is in
  research/m2_kickoff.md:271-279 and research/audit/reader.md:90-105.
- **Section 10 is stated as plans.** The heading says "plans only, nothing run" (cutoff.md:759), and both checks are
  written in the future tense with their warning rules fixed before any result. 10.1 says it starts only on the
  owner's word after M3 (cutoff.md:776-777). 10.1's offset mapping (2025 and 2026 read by 2023) is consistent with
  "one year older than the rule's".

## C-1. The second freeze can't be checked by anyone but the author, and the doc states it as fact

- **Severity:** medium.
- **Where:** research/audit/cutoff.md:316-321 and 596-600; reader/cutoff.py:572-580.
- **Evidence.** The only records that the probe list, the rules and T's procedure were fixed before any score are:
  (1) file times on the owner's laptop, which git does not keep and the author controls; (2) the hashes that
  `cmd_probes2` prints and saves at scoring time (cutoff.py:577, 580), which prove the scored files equal today's
  files, not that they were fixed before a score; (3) the doc's own text. All four files arrived in one commit
  (e53c114, 22 Nov 10:32 +0500, about eight hours after the run), and cutoff.md was last written at 17:06:53, after the
  run, so no record of the second-freeze hashes is shown to exist before the first score. The second freeze at
  "16:21" is in fact 34 seconds after the last write to cutoff.py (16:20:51) and the same minute as the run's first
  file (run_probes2.log created 16:21:25, folder 16:21:26), so the freeze and the start of scoring are one event.
  Nothing in the code needs a freeze: `cmd_probes2` refuses only when `scores.parquet` exists, and its message says
  to move the file away to rerun (cutoff.py:574-575), so an earlier scored-and-moved run would leave no trace. I found
  no sign of one: the times above are in order and the log shows one run. The first freeze is better supported, by
  probes2_judge.md (C-1 is about the second). Line 319 also says "This section was written before any vintage scored",
  but 8.9, 8.10, 9 and 10 are in the same section 8 numbering or file and were written after; the claim holds at most
  for 8.1 to 8.8.
- **Rerun.** `git log --format="%h %ad" -- reader/probes2.csv reader/cutoff.py research/audit/cutoff.md`; in
  PowerShell, `Get-Item` on the files listed above with CreationTime and LastWriteTime.
- **Fix:** next time commit the frozen files (or send their hashes to the owner) before scoring, have `cmd_probes2`
  refuse unless the hashes equal that committed record, and reword 8.1 to 8.8 to say what supports the freeze.

## C-2. The recorded cutoff.py hash is the CRLF working copy's, not the committed file's

- **Severity:** low.
- **Where:** research/audit/cutoff.md:545-546 and 598-599; .gitattributes:1-3.
- **Evidence.** `git show 3d1df9b:reader/cutoff.py | sha256sum` gives `70045341...36ce`. The same bytes with CRLF
  line ends (`| sed 's/$/\r/' | sha256sum`) give the recorded `8bae55f5...3e3b`. `git ls-files --eol reader/cutoff.py`
  shows i/lf w/crlf; core.autocrlf is true. `.gitattributes` keeps only `reader/*.csv` as bytes. So on any checkout
  without autocrlf (Linux, CI, a clone with other settings), the hash in 8.8 can't be reproduced from git, and
  `report-probes2` would print a different "now" hash without stopping (C-3).
- **Fix:** record in 8.8 that the cutoff.py hash is of the CRLF working copy and add the committed (LF) hash
  `7004534124287875504bd044498c0d36696d3adbc3ffb3ece99c32b1418336ce`.

## C-3. report-probes2 still only prints a cutoff.py change (earlier finding P2-7, partly fixed)

- **Severity:** low.
- **Where:** reader/cutoff.py:586-589.
- **Evidence.** The probes2.csv check raises SystemExit (586-587); the cutoff.py hashes are printed side by side
  (588-589) and the report goes on. The doc does not claim more (cutoff.md:574-576), so it is honest, but the rule code
  could change between run and report with only a printed line to show it.
- **Fix:** raise SystemExit when `shas["cutoff_sha256"] != file_sha256(__file__)`, comparing LF-normalised bytes.

## C-4. The reading of q2023c rests on an unchecked fact that does not explain the step

- **Severity:** low.
- **Where:** research/audit/cutoff.md:640-643.
- **Evidence.** The doc gives a 2023 event "(from memory, not checked)" next to the flag. AGENTS.md's Facts rule asks
  for checkable evidence. And a May 2023 event can't reach a vintage that ends in 2022 unless that vintage leaked, so as
  placed it reads as an explanation when it is not one. The stronger argument is in the numbers and not spelled out:
  q2023b's event is in February 2023 and q2023c's in August 2023 (probes2.csv event_date), and 2022 shows no knowledge
  of q2023b (-6.96) while it scores q2023c like 2023 and 2024 (-3.07 against -3.24 and -3.76). A leak of the training
  end into 2023 would reach February before August, so the pattern points to something in 2022's own news rather than a
  time leak. Also, 2022's only evidence is 2 informative probes, of which 1 flags; "too weak" is right by the rules but
  hides that split.
- **Fix:** drop or check and cite the parenthetical, add the February-before-August argument, and state "1 of 2
  informative probes flags 2022".

## C-5. One sentence of the reading covers 5 of the 7 informative cells, not all

- **Severity:** low.
- **Where:** research/audit/cutoff.md:629-630.
- **Evidence.** "Where a probe could tell, the vintage before the event looks like the older ones." The 7 cells
  informative for V = E-1 are q2016b, q2017c, q2017e, q2017f, q2021e, q2023b, q2023c (re-derived). Two of them flag
  (q2017f, q2023c), and in q2023c the 2022 vintage scores like the later ones, not the older ones.
- **Fix:** write "in 5 of the 7 informative cells".

## C-6. 2016's pass counts its flagged probe among the three

- **Severity:** info.
- **Where:** research/audit/cutoff.md:619 and 738-739.
- **Evidence.** The three probes informative for 2016 are q2017c (gap 6.67), q2017e (12.96) and q2017f (4.01), and
  q2017f is the one that flags. So the pass rests on two clean informative probes and one flagged one, which the rule
  allows (FAIL_FLAGS 2, MIN_INFORMATIVE 3, cutoff.py:74-75). "At the edge" already says this in substance.
- **Fix:** add "two clean, one flagged" after "exactly 3 informative probes".

## C-7. The owner's words reach the doc through the lead

- **Severity:** info.
- **Where:** research/audit/cutoff.md:749 and 761-762.
- **Evidence.** Section 9 quotes "Accept, go on", and section 10 says the owner's request came "via the lead". There
  is no owner-written record in the repo to check against. This is normal for the project's way of working, but it
  means the decision's only record is the author's.
- **Fix:** have the owner confirm section 9 when committing it (a line in the commit message would do).

## Earlier fixes

| Item | Holds? | Where |
|---|---|---|
| P2-1 2024 rule (lo 2021-2023, usable at lo <= -3, n = q x usable, floor T) | yes | cutoff.py:401-408, 436-437, 377-384 |
| P2-2 six tied answers replaced | yes (new answers in rows 8, 22, 27, 39, 61, 78) | reader/probes2.csv |
| P2-3 clearest predictable answers replaced | yes (rows 2, 4, 12, 55, 63, 73, 76, 77) | reader/probes2.csv |
| P2-4 lo from V-3 to V-1, calibrated T, one flag tolerated | yes | cutoff.py:367-374, 377-384, 75 |
| P2-5 five wrong answers swapped | yes (old wrong answers absent from all five rows) | reader/probes2.csv rows 31, 35, 36, 37, 65 |
| P2-6 giveaway wordings | kept by choice, harmless to outcomes | cutoff.md:572-573 |
| P2-7 code gaps | partly: no overwrite, both hashes, full-table check hold; cutoff.py change only printed (C-3) | cutoff.py:574-575, 577, 580, 420-421, 588-589 |
| P2-8 test of leaving V out | yes; file has 27 tests | tests/test_cutoff.py:282 |
| P2-9 notes | stand as limits, as stated | cutoff.md:579-581 |
| CJ-1 spillover added, description only | yes | cutoff.py:645-650 |
| CJ-2 too weak blocks the run | superseded by the owner's acceptance | cutoff.md:747-757 |
| CJ-3 N sizing | not changed, as stated | cutoff.md:102-103 |
| CJ-4 2015 events can't flag | moot for probes2 (no 2015 events) | cutoff.md:354-355 |
| CJ-5 2026 not covered | still open, recorded as a limit | cutoff.md:745, 757 |
| CJ-6 duplicate story ids | yes in the sample; `headlines()` has no check | cutoff.py:108-109, 188-198 |
