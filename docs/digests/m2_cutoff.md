Source commit 3d1df9b, 22 Nov 2026. Digest of the cutoff decision.
Sources: reader/cutoff.py, reader/probes2.csv, research/audit/cutoff.md (lines 316 to 795), research/audit/probes2_judge.md, tests/test_cutoff.py, and files in D:\chrono-data\reader\cutoff\probes2. Line numbers are in the file named in each line. No headline text, no prices, no event wording is reproduced. Probe ids are used only as labels.

## The probe rules in code (reader/cutoff.py)
- cutoff.py:34-37 On 21 Nov 2026 the owner chose "Stronger probes". The loss check and the first probe set (probes.csv) stay as record and decide nothing. The rules that decide are probe2_lo, probe2_threshold, probe2_cell, probe2_last and probe2_outcomes.
- cutoff.py:59 VINTAGES are 2014 to 2024. cutoff.py:72 PROBES2 is reader/probes2.csv.
- cutoff.py:73 MARGIN is 3.0. cutoff.py:74 MIN_INFORMATIVE is 3. cutoff.py:75 FAIL_FLAGS is 2.
- cutoff.py:367 BASE is 3 (judge finding 4 of probes2_judge.md).
- Scoring. cutoff.py:315-323 `candidate_inputs`: the sentence with one candidate in the blank, token ids, and the token positions the candidate fills. Raises ValueError if the candidate fills no token.
- cutoff.py:326-335 `candidate_logprob`: all of the candidate's tokens masked at once, log-softmax, summed log-probability.
- cutoff.py:338-341 `probe_score`: the answer's share among the candidates, as a log. Element 0 is the answer.
- cutoff.py:553-570 `run_probes`: for every vintage and probe, scores [answer, *wrong]. Writes a parquet of probe_id, vintage, score, and a json holding the probes file's SHA-256.
- cutoff.py:370-374 `probe2_lo(scores, V)`: median score of the vintages from V-3 to V-1 (from 2014 on). It leaves V out.
- cutoff.py:377-384 `probe2_threshold` T: the 95th percentile of (score minus lo) over honest cells, never below MARGIN/2 (1.5). An honest cell is a probe of year E (2016 to 2025) and a vintage from 2015 to E-2.
- cutoff.py:387-398 `probe2_cell(scores, E, V, t)`: needs 2014 < V < E <= 2024. lo is `probe2_lo`. hi is the median of vintages from E to 2024. Informative when hi - lo >= MARGIN. Flagged when informative and score >= max((lo+hi)/2, lo + t). Returns (informative, flagged, lo, hi).
- cutoff.py:401-408 `probe2_last` (2025 probes, vintage 2024): lo is `probe2_lo(2024)`, the median of 2021 to 2023. Usable when lo <= -MARGIN. Flagged when usable and 2024's score >= lo + t.
- cutoff.py:411-448 `probe2_outcomes`:
  - 420-421 raises ValueError unless the table holds every probe and every vintage.
  - 426 T is computed from the table.
  - 427 q is the mean of informative flags over the probes of 2016 to 2024, each judged on vintage E-1.
  - 429-435 each vintage V from 2015 to 2024 is judged on the probes of year V+1. For V below 2024 it uses `probe2_cell`. For V = 2024 it uses `probe2_last`. n is the count informative (or usable). For 2024, n = q times the usable count (436-437).
  - 439-444 outcome: fail when flags >= 2, else pass when n >= 3, else too weak.
  - 445-447 later-year flags (probes of V+2 to 2024) and early flags (events in months 1 to 3) are reported and decide nothing.
  - 448 returns (outcomes, q, T).
- Outcome names in the probe2 path are pass, fail and too weak (cutoff.py:439-444).
- `probe_flags` (cutoff.py:344-360) belongs to the first probe set. It is not used by the probes2 path.

## How the probe file hash is frozen and checked
- cutoff.py:306-307 `file_sha256` is the SHA-256 of the file's bytes.
- cutoff.py:572-580 `cmd_probes2`:
  - 574-575 stops with SystemExit if `probes2\scores.parquet` already exists ("the probes are scored once").
  - 577 computes the SHA-256 of both probes2.csv and cutoff.py at scoring time and prints them.
  - 579 scores all probes with every vintage, writing scores.parquet and a probes_sha256 json via `run_probes`.
  - 580 writes scores.json with both hashes after scoring.
- cutoff.py:583-590 `cmd_report_probes2`: reads scores.json. Stops with SystemExit if the current probes2.csv hash differs from the one stored at scoring (586-587). It prints the cutoff.py hash at the run and now (588-589) and does not stop if they differ.
- The freeze itself (the hashes at 16:00 and 16:21 New York) is recorded only in research/audit/cutoff.md 8.7 and 8.8. Nothing in cutoff.py reads a hash that was written before scoring.

## When scores are computed relative to the freeze, and code paths that could score before a freeze
- Per cutoff.md:541-548 (8.7) and 596-602 (second freeze): no vintage had scored a probe of probes2.csv at either freeze. The folder D:\chrono-data\reader\cutoff\probes2 did not exist at either time.
- Scoring happens only in `cmd_probes2` (cutoff.py:572-580), which is reached from `main` (cutoff.py:687-688). `run_probes` (cutoff.py:553) is also called by `cmd_run` (cutoff.py:617-620) with the default arguments PROBES and "probes", so it scores the first set (probes.csv), not probes2.csv.
- No code path in cutoff.py scores probes2.csv other than `cmd_probes2`. `cmd_probes2` has no check that a freeze exists or that the hashes equal frozen values. It records the hashes at scoring time.
- Facts from D: and git that bear on timing (no judgement made):
  - The current probes2.csv SHA-256 starts eed31d91, and the current cutoff.py SHA-256 starts 8bae55f5. Both equal the second-freeze hashes in cutoff.md:598-599, and both equal the hashes in scores.json and on the first line of run_probes2.log.
  - scores.json and scores.parquet files were written on 22 Nov 2026 at 02:35 (the machine's local time, +0500), which is 16:35 on 21 Nov in New York. The second freeze is stated as 16:21 New York on 21 Nov.
  - git history holds one commit for probes2.csv, cutoff.py, tests/test_cutoff.py and cutoff.md in this branch: e53c114, dated 22 Nov 2026 10:32 +0500. So git does not show the freeze moments.
  - The first freeze hashes in cutoff.md:545-546 (5dac4506, 06f106d0) are not the current files' hashes. That is the judge's finding set (see below).

## reader/probes2.csv (81 lines: 1 header and 80 rows)
- Columns (6): probe_id, event_date (YYYY-MM-DD, New York), sentence (one {} for the answer), answer, wrong (four wrong answers separated by |), source (a Wikipedia article title).
- No "type" column exists. Every probe_id has the form q + year + letter.
- Probes per target year (event_date year): 2016 8, 2017 8, 2018 8, 2019 8, 2020 8, 2021 8, 2022 8, 2023 8, 2024 8, 2025 8. Total 80. None for 2015 or 2026.
- Letters a to h: 10 each (one per year each).
- Wrong answers per probe: 4 for all 80.
- Event month counts (Jan to Dec): 9, 7, 8, 4, 7, 7, 7, 9, 8, 5, 5, 4. Events in January to March: 24.
- Loader: cutoff.py:291-303 `load_probes` derives event_year and event_month from event_date, and splits `wrong` on |.

## research/audit/cutoff.md, sections 8.1 to 10.2 (lines 316 to 795)
- 316-321 Section 8 header: the owner chose "Stronger probes". Each vintage's cutoff is settled on named-event probes, not on masked-word loss. Written before any vintage scored a probe of probes2.csv.
- 323-334 (8.1) Why the first probes were weak: in 17 of 22 first probes the answer had a different token count from some wrong answer. And no margin: any gap could count as informative.
- 336-441 (8.2) The probes: 80 events, 8 per year 2016 to 2025. Each is public, dated, has an answer not public before 1 January of the event's year, four wrong answers of the same kind, and equal token counts (checked by `test_probes2_candidates_have_the_answers_token_count`). The 2014 vintage reads no news so there are no 2015 events. No probe covers 2026 (judge finding 5 of 21 Nov stands, line 358). The table at 359-441 lists the rows as of the second freeze.
- 443-447 (8.3) Scoring: each candidate fills the blank with all its tokens masked at once. A probe's score is the answer's log share among five candidates (0 certain, -1.61 no preference).
- 449-478 (8.4) The flag rule with its margin: lo from V-3 to V-1 (leaves V out); hi is the median of E to 2024; informative when hi - lo >= 3 (about a factor of 20); T is the 95th percentile of honest cells, at least 1.5; flagged when informative and the score is at least both (lo+hi)/2 and lo+T. For 2025 probes: lo is the median of 2021 to 2023, usable when lo <= -3, and 2024 flagged when its score >= lo + T. Margin pilot on the first run's scores: margin 2, 3, 4 give 11, 8, 4 informative cells with 2, 1, 0 flags.
- 480-515 (8.5) Outcomes: each vintage V from 2015 to 2024 is judged on the 8 probes of year V+1. Fail at 2 or more flags. Pass at n of 3 or more. Otherwise too weak. One flag is tolerated. 2024 uses n = q times usable. The 2014 vintage has no outcome. A failing or too weak vintage is reported, not replaced; only the owner replaces one. A simulation table (lines 495-505) gives honest-fail rates of 0.004 to 0.037 and leaky-fail rates of 0.887 to 1.000.
- 512-515 Limits listed: a leak of a few weeks touches only early events; 2024's power is borrowed; a gross leak raises T a little; 2026 is not covered.
- 517-539 (8.6) Fact check by a chrono-checker (Sonnet) on 21 Nov 2026: 80 rows, 11 flagged. One replaced (q2016e), three reworded, one re-dated, one wrong answer swapped, five kept with reasons. 10 deals could not be confirmed or ruled out as reported the year before. One such leak can flag one probe.
- 541-548 (8.7) First freeze: 16:00 New York, 21 Nov 2026. probes2.csv SHA-256 starts 5dac4506. cutoff.py starts 06f106d0. tests/test_cutoff.py passed 24 tests.
- 550-594 (8.8) The judge (see below) and the changes before the run. 14 probes replaced, then a second chrono-checker checked the 25 new or changed rows: 23 had no problem, 2 fixed (q2023f re-dated and reworded; q2025d source renamed).
- 596-600 Second freeze: 16:21 New York, 21 Nov 2026. probes2.csv starts eed31d91. cutoff.py starts 8bae55f5. tests/test_cutoff.py passed 27 tests, including the real-tokenizer length check.
- 603-611 (8.9) Results: commands `probes2` and `report-probes2`. scores.parquet has 880 rows (80 probes by 11 vintages). The run used the second freeze's files, at the run and at the report. T is 1.631. q is 0.097 (7 of 72).
- Results table summary (lines 613-626, rule outcomes; flags are probe ids):
  - 2015: probes 8, informative 1, flags none, too weak.
  - 2016: probes 8, informative 3, flags 1 (q2017f), pass.
  - 2017: 8, 0, none, too weak.
  - 2018: 8, 0, none, too weak.
  - 2019: 8, 0, none, too weak.
  - 2020: 8, 1, none, too weak.
  - 2021: 8, 0, none, too weak.
  - 2022: 8, 2, flags 1 (q2023c), too weak.
  - 2023: 8, 0, none, too weak.
  - 2024: 8 probes, n 0.292 (3 usable times q), none, too weak.
  - Totals: 0 fail, 1 pass, 9 too weak. No flag fell in January to March. Later-year flags: q2018b (2015 and 2016), q2019e (2016 and 2017), q2024g (2017). These decide nothing.
  - D:\chrono-data\reader\cutoff\probes2\report.json agrees: q 0.0972, T 1.6312, and the same outcomes, flags and informative counts for 2015 to 2022.
- 628-647 Reading, not part of the rules: in 9 probes every vintage already favours the answer. In 18 no vintage ever scores above -3. Only 7 of 72 probes were informative for the vintage just before their event. The q2017f flag reads as drift (score rises steadily from 2014). The q2023c flag shows its step a year before the event. One flag fails nothing.
- 649-733 The full score table (80 probes by 11 vintages; not reproduced here).
- 735-745 (8.10) What waits for the owner: 2016 passes at the edge (exactly 3 informative, 1 flag); too weak means the probes could not tell, not that the vintage leaked; the q2023c flag on 2022; power (only 7 of 72, more probes would help only in the same proportion); 2026 not covered.
- 747-757 (9) The owner's decision (21 Nov 2026 New York; 22 Nov where the owner is): "Accept, go on". All 11 vintages accepted as published. No vintage replaced. The rule in reader/vintage.py stays. Evidence: only 2016 supported (passed at the edge); the other nine that read news are too weak to judge; none failed but that is not evidence they are clean; the q2023c flag was seen and accepted; the 2014 vintage needs no outcome; 2026 never checked. Recorded as a known limit of M2, also in research/m2_kickoff.md.
- 759-795 (10) Two planned checks, nothing run. Both use daily rank IC (`eval/metrics.daily_rank_ic`), news effect = live agent IC minus price-only twin IC, Newey-West errors.
  - 10.1 (761-777) Older-vintage rerun: read each story by Y-2 not Y-1, same code into D:\chrono-data\reader_older, about 14 more hours. Needs a `vintage_offset` the World accepts only for this check, with its own test. Warning when the news effect with the older vintage is less than half the rule's and the paired daily IC difference is above zero (one-sided 5%). Starts only on the owner's word, after M3 has a result.
  - 10.2 (779-795) Switch-day check in M3's evaluation, no new run: first 20 sessions of each year against the rest. Warning when the pooled difference is above zero (one-sided 5%) or in at least half the years the first-20 mean exceeds the rest by more than two standard errors. Limits: news memory half-life is 5 sessions; dev years give few switches; repeated on sealed years when they open.

## research/audit/probes2_judge.md: each must-fix and where the doc says it was fixed
Verdict (line 172): do not run as frozen. Must change first (lines 172-176): finding 1, finding 2 (six probes), the clearest cases of finding 3, finding 5 (five wrong answers). Then rerun the token-count test and record new hashes (178-179).
- Finding 1, High (34-48): 2024 rule had no margin and a far baseline. Doc says fixed in cutoff.md:558-561 (8.8 item 1): lo for 2024 is the median of 2021 to 2023, a 2025 probe counts only at lo <= -3, 2024's n is q times usable, and the flag floor became T. In code: cutoff.py:401-408, 377-384, 436-437.
- Finding 2, High (50-66): six answers tied to their sentence before the event year (q2016g, q2020f, q2018e, q2019b, q2025e, q2023d). Doc says all six replaced (cutoff.md:562-563). In the CSV: q2016g line 8, q2018e 22, q2019b 27, q2020f 39, q2023d 61, q2025e 78, each now a different answer.
- Finding 3, Medium (70-95): predictable answers. Doc says the clearest were replaced: q2016c, q2017c, q2022f, q2025c, q2025d, q2023f, and also q2024h and q2016a (cutoff.md:564-567). In the CSV: q2016a line 2, q2016c 4, q2017c 12, q2022f 55, q2023f 63, q2024h 73, q2025c 76, q2025d 77. The doc kept q2017b, q2018b, q2019e, q2022c, q2023a, q2024e, q2025a, at most one per year.
- Finding 4, Medium (97-105): one-flag tolerance. Doc says kept, with lo from V-3 to V-1 and calibrated T (cutoff.md:568-569). In code cutoff.py:367-374 and 377-384.
- Finding 5, Medium (107-116): wrong answers also true. Doc says done (cutoff.md:570-571): q2020d wrong answer now Arrival (CSV line 37), q2020c now forty (line 36), q2019f now Ryanair (line 31), q2023h now Dongkuk Steel (line 65), q2020b now Norway (line 35).
- Finding 6, Low (120-130): wordings that give the answer away. Doc says not changed (cutoff.md:572-573): they can only be uninformative.
- Finding 7, Low (132-140): code gaps. Doc says done (cutoff.md:574-576): `probes2` refuses to overwrite scores.parquet (cutoff.py:574-575) and records both hashes (cutoff.py:577, 580); `report-probes2` stops on a probes2.csv change (cutoff.py:586-587); `probe2_outcomes` raises unless it has every probe and vintage (cutoff.py:420-421). The doc does not say the cutoff.py hash mismatch now stops the report. In code it only prints (cutoff.py:588-589).
- Finding 8, Low (142-143): weak test. Doc says replaced (cutoff.md:577-578) by `test_probe2_lo_uses_the_three_vintages_before_v_and_leaves_v_out`, now at tests/test_cutoff.py:282. New tests also cover the usable rule, the full-table check and T.
- Finding 9, notes (145-150): n = 3 with one flag passes; q and usable count decide whether 2024 can pass; equal token counts do not mean equal make-up. Doc says these stand as limits (cutoff.md:579-581).
- Judge's confirmed-right list (lines 9-28) refers to the first freeze's hashes and line numbers 366-425 of cutoff.py; the file has changed since.

## tests/test_cutoff.py: tests that concern probes2 (file has 27 test functions in all)
- :238 `test_probes2_file_is_well_formed`: 80 unique ids, 8 per year 2016 to 2025, date starts with the year, one blank per sentence, 4 distinct wrong answers not equal to the answer, a source present, and no answer from a list of 15 first-set answers reused.
- :255 `test_probes2_candidates_have_the_answers_token_count`: with the real pinned tokenizer (skipped if not on D:), every candidate fills the same number of tokens and decodes back to itself.
- :266 `test_probe2_cell`: flat scores are not informative; a gap of exactly 3 is informative; halfway flags; a gap of 2 is not informative; a call with E = 2025 raises ValueError.
- :282 `test_probe2_lo_uses_the_three_vintages_before_v_and_leaves_v_out`: lo for 2018, 2019, 2016 and 2015 uses exactly the vintages the rule names.
- :292 `test_probe2_last`: usable and flag cases of the 2025 rule, with lo from 2021 to 2023 only.
- :304 `test_probe2_outcomes_needs_the_full_table`: a missing probe, or a missing vintage, raises ValueError.
- :315 `test_probe2_honest_vintages_pass_and_q_is_one`: on a made-up table where vintages know their event year, all 10 vintages pass, q is 1.0, and there are no flags.
- :324 `test_probe2_a_leaky_vintage_fails_and_its_neighbours_do_not`: 2018 knowing 2019 fails with 8 flags and the other vintages pass; 2024 knowing 2025 fails alone.
- :334 `test_probe2_one_flag_is_tolerated_and_no_signal_is_too_weak`: one flag on 2018 still passes; a table where nothing is learned gives q 0 and all too weak.
- :345 `test_probe2_later_year_flags_are_reported_but_do_not_decide`: a vintage leaking only into a later year gets 8 later flags and still passes.
- :351 `test_probe2_threshold_follows_the_honest_drift`: T is 1.5 with no drift, above 1.5 with noise, and a larger t can turn a flag off.
- Helper `_table` is at tests/test_cutoff.py:228 (not a test).

## Not found or not digested
- Nothing in the code or git shows the freeze moments themselves. Only cutoff.md 8.7 and 8.8, scores.json and file times bear on it.
- The full score table (cutoff.md:649-733) is not reproduced, by design.
