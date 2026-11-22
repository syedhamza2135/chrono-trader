Source commit 3d1df9b, 22 Nov 2026. Digest of every finding in research/audit/cutoff_judge.md, research/audit/probes2_judge.md and research/audit/embed_judge.md.
Each line: id, claim, the fix the docs say was made, and where the fix is visible in the code or data at this commit. "Status" is what the docs say. "Seen at" is what was found in the files. Nothing is judged here.
Doc lines are given as file:line of the finding, then the file:line of the stated fix.

## Status lines in research/audit/reader.md
- reader.md:111-112 First judge: no embedding before its story, no wrong-vintage row; one must-change, J-1, "fixed".
- reader.md:113-116 Second judge: no leak through the wall. Must-change J3-1 and should-change J3-2 "both are fixed".
- reader.md:52 J-4 is cited as done (each manifest records the pinned repo and commit). reader.md:55, 73 J-3 is cited as done. reader.md:71 J-1 is cited as done.
- reader.md has no status line for J-2, J-5, J-6, J3-3, J3-4, or for the cutoff_judge.md and probes2_judge.md findings.
- reader.md:93-97 states the vintage decision and its known limit (2026 never checked; nine vintages too weak).
- Extra, not asked: research/m2_kickoff.md:325-327 lists J-5 and J-6 as open notes; kickoff:354 says J-5 stays an option.

## A. research/audit/cutoff_judge.md (judge of 21 Nov 2026, on the loss check)
Doc says the fixes in research/audit/cutoff.md section 4 (lines 91-108). The loss check later decided nothing (cutoff.py:34-37).
- CJ-1 High (cutoff_judge.md:42-53): a partial leak passes the check. Fix stated (cutoff.md:95-99): the report adds each vintage's spillover G(V, V+1) / G(V, V), description only. The January-to-March split was left for the owner. Seen at: cutoff.py:645-650 (spillover table in `cmd_report`, commented "added after the rules (judge finding 1), outside the outcomes"). No January-to-March split found in cutoff.py. cutoff.md:314 and 267 say findings 1 and 5 were not folded into the stronger-probes run.
- CJ-2 Medium (55-62): "too weak" leaves a leaky vintage in use. Fix stated (cutoff.md:100-101): until the owner rules on M-4, a too-weak vintage blocks the reader run like a fail. Seen at: process only, no code. cutoff.md:747-757 (section 9) records that the owner accepted all 11 vintages ("Accept, go on"), and embed_judge.md:92-94 says the gate is process, not code.
- CJ-3 Medium (64-73): the N rule sizes power on G, not on check B. Fix stated (cutoff.md:102-103): "No change: the pilot already picked the largest N, 2,000". Seen at: cutoff.py:277-286 `pick_n` unchanged (still sizes on d_own).
- CJ-4 Low (75-79): probes for 2015 events can never flag. Fix stated (cutoff.md:104): listed under "4 to 6, low"; no change recorded. Seen at: the probes2 set has no 2015 events (cutoff.md:354-355). cutoff.py:344-360 `probe_flags` unchanged.
- CJ-5 Low (81-85): no check covers 2026. Fix stated: none. cutoff.md:358, 745, 757 say it is still not covered. Seen at: no code.
- CJ-6 Low (87-91): dedup depends on input order if a story_id repeats. Fix stated (cutoff.md:104-106): the sample now stops on a repeated story_id, and the redrawn sample has the same SHA-256. Seen at: cutoff.py:108-109 (`draw_sample` raises ValueError "duplicate story ids"). The judge's other spot, `headlines()` (cutoff.py:188-198), has no uniqueness assert in it.

## B. research/audit/probes2_judge.md (judge of 22 Nov 2026, on the frozen probe rules)
Doc says the fixes in research/audit/cutoff.md 8.8 (lines 550-601).
- P2-1 High (probes2_judge.md:34-48): 2024 rule has no margin and a far baseline. Fix stated (cutoff.md:558-561): lo for 2024 is the median of 2021 to 2023; a 2025 probe counts only when lo <= -3; n is q times usable; the flag floor became T. Seen at: cutoff.py:401-408 (`probe2_last`), cutoff.py:377-384 (`probe2_threshold`), cutoff.py:436-437 (n = q * n for 2024).
- P2-2 High (50-66): six answers tied to their sentence before the event year. Fix stated (cutoff.md:562-563): all six replaced. Seen at: probes2.csv line 8 (q2016g), 22 (q2018e), 27 (q2019b), 39 (q2020f), 61 (q2023d), 78 (q2025e); each holds a new answer (Portugal, Thailand, Nationals, Beirut, Palestine, Cook).
- P2-3 Medium (70-95): more answers predictable before the year. Fix stated (cutoff.md:564-567): clearest replaced: q2016c, q2017c, q2022f, q2025c, q2025d, q2023f; also q2024h and q2016a. Seven kept, one per year at most. Seen at: probes2.csv line 4 (q2016c), 12 (q2017c), 55 (q2022f), 76 (q2025c), 77 (q2025d), 63 (q2023f), 73 (q2024h), 2 (q2016a).
- P2-4 Medium (97-105): one flag tolerated, two fail, honest fail rate not shown. Fix stated (cutoff.md:568-569): rule kept; lo from V-3 to V-1; calibrated T; simulated rates in cutoff.md:495-505. Seen at: cutoff.py:367 (BASE 3), 370-374 (`probe2_lo`), 377-384, 75 (FAIL_FLAGS 2).
- P2-5 Medium (107-116): wrong answers also true or nearly so. Fix stated (cutoff.md:570-571): five swapped. Seen at: probes2.csv line 37 (q2020d now has Arrival), 36 (q2020c now has forty), 31 (q2019f has Ryanair), 65 (q2023h has Dongkuk Steel), 35 (q2020b has Norway). The old wrong answers are absent from those rows.
- P2-6 Low (120-130): wordings that give the answer to every vintage. Fix stated (cutoff.md:572-573): not changed, since they can only lower power. Seen at: not changed in probes2.csv (rows still present).
- P2-7 Low (132-140): small code gaps (report does not stop on a hash mismatch; `probes2` overwrites scores; only probes2.csv hash recorded; missing probe shrinks q silently). Fix stated (cutoff.md:574-576). Seen at: cutoff.py:574-575 (refuses an existing scores.parquet), cutoff.py:577 and 580 (both hashes recorded), cutoff.py:586-587 (report stops if probes2.csv changed), cutoff.py:420-421 (`probe2_outcomes` raises unless every probe and vintage). The report only prints, and does not stop, when the cutoff.py hash differs (cutoff.py:588-589).
- P2-8 Low (142-143): `test_probe2_cell` does not test leaving V out. Fix stated (cutoff.md:577-578): a new test replaces it. Seen at: tests/test_cutoff.py:282 (`test_probe2_lo_uses_the_three_vintages_before_v_and_leaves_v_out`), plus tests at 292, 304, 351.
- P2-9 Notes (145-150): n = 3 with one flag passes; 2024 may turn on one probe; equal token counts are not equal make-up. Fix stated (cutoff.md:579-581): stand as limits. Seen at: no code change. The 2016 vintage passed at exactly n = 3 with 1 flag (cutoff.md:626, 735-737).
- Verdict (probes2_judge.md:170-179): must change first were 1, 2, the clearest of 3, and 5. All four are marked done in cutoff.md:558-571. New hashes recorded at cutoff.md:596-599; the second chrono-checker pass is at cutoff.md:589-595.

## C. research/audit/embed_judge.md, first judge (22 Nov 2026, on the time wall)
- J-1 Must-change (embed_judge.md:18-44): an embedding's presence shows a rejoin early (a story with an embedding and no visible link names a hidden company). 1,989 real stories, 6 companies. Fix stated (121-126): `visible_at` embeddings branch takes the earliest visible_at of the story's links, never earlier than the story's time, NEVER for a story with no link. Seen at: world/world.py:110-120; World passes story_entities at world/world.py:307-308; eval/leaks.py:50-52 (late_rows passes story_entities); eval/leaks.py:104-111 (shift keeps available_at equal to the story's). Tests: tests/test_embeddings_wall.py:281 (rejoin pair), :297 (counting agent), :304 (gap story hidden), :229 (independent early check against links), tests/test_embeddings_store.py:89 (EQT gap on the real store).
- J-2 Should-change (46-55): leak checks cannot see J-1. Fix stated (126): closed by J-1's fix; "embeddings equal stories" assertions now read "embeddings equal linked stories". Seen at: tests/test_embeddings_wall.py:43 (set equals story_entities ids), tests/test_embed.py:142 (embedded stories among the linked ones), eval/leaks.py:50-52, 105-107.
- J-3 Note (57-62): the real table has no way into the World. Fix stated (128 and kickoff:346): left for step 5, then done: `World.load` reads the table. Seen at: world/world.py:332-341 and 256-277. Tests: tests/test_embeddings_store.py:70, tests/test_embed.py:169.
- J-4 Note (64-70): which weights read each part is not recorded at run time. Fix stated (127): manifest.json records each vintage's pinned repo and commit, before the full run. Seen at: reader/embed.py:98-103 (manifest weights), 166-175 (`check_manifest`), 211 and 253 (checked on restart and `finish`). D: file: reader\v2024\manifest.json holds the repo and commit.
- J-5 Note (72-78): L-P7 misses an edit that keeps `updated_at`. Fix stated (128): left as a note. Seen at: reader/embed.py:87-91 (`set_hash` still uses updated_at only). kickoff:354 says the headline hash stays an option.
- J-6 Notes (80-93), five sub-items:
  - a. A 2015 story row is refused by `vintage_for`'s own ValueError, with no test. Fix stated: left as a note (128, kickoff:326). Seen at: reader/vintage.py:17-18 (the ValueError). No test for a refused 2015 row was found in tests/test_embed.py, test_embeddings_wall.py or test_embeddings_store.py.
  - b. A repeated story_id in `stories` is accepted. Fix stated: left as a note (kickoff:326, "refuse repeated story ids"). Seen at: world/world.py:111 and reader/embed.py:63 both still use `drop_duplicates`. No refusal in `World.__init__`. (tests/test_embeddings_wall.py:124 tests a repeat in the embeddings table, which is refused at world/world.py:195-196.)
  - c. `.map` turning float64 if an id is missing. The judge found no effect. Seen at: world/world.py:112-120 (the embeddings branch now uses `reindex` and `get_indexer`).
  - d. L-P8, an M5 morning job: a row's true time is the later of the story's time and the compute time. Fix stated: note it in the M5 item. Seen at: reader/embed.py:28-29 and world/rules.py:31-33 docstrings name L-P8 and M-3. The equality check at world/world.py:201-204 is unchanged.
  - e. M-4: nothing in code ties the reader run to the cutoff outcome. Judge says it is a process gate, fine. No fix.

## D. research/audit/embed_judge.md, second judge (22 Nov 2026, on World.load and the mapped arrays)
- J3-1 Must-change (142-151): two wall tests fail after the rename to `_last` and `_avg`. Fix stated (216-217): the two tests use `_last` and `_avg`, and `FutureEmbedding` pairs rows with vectors through `e.order`. Seen at: tests/test_embeddings_wall.py:72 (`w.embeddings._last`, `_avg`), :151 (`e._last[e.order, 0]`), :212 (planted leak still caught).
- J3-2 Should-change (153-167): arrays check covers story ids, not vectors; a stop in `finish` or `arrays` leaves a stale entry. Fix stated (218-222): `cmd_finish` and `cmd_arrays` drop the `arrays` entry before replacing a file it vouches for; the entry records the Parquet size and footer SHA-256; `load_embeddings` refuses arrays written for another file; new tests. Seen at: reader/embed.py:269 (`drop_arrays` in `finish`), 329 (in `arrays`), 299-306 (`drop_arrays`), 287-296 (`parquet_footer`), 334-335 (entry records `parquet`); world/world.py:244-253 and 271-273 (refusal); tests/test_embed.py:210 and :228. D: file: embeddings.json `arrays.parquet` holds bytes 1480328055 and a footer hash (61eefea5).
- J3-3 Note (169-177): leak tools need the DataFrame path; `perturb` given an `Embeddings` raises AttributeError; non-interference with embeddings runs on synthetic frames only. Fix stated (225): stays a note. Seen at: eval/leaks.py:63 (`v.copy()` on each table) unchanged. Tests build the DataFrame form (tests/test_embeddings_wall.py:20-21).
- J3-4 Notes (179-190), four sub-items:
  - a. dtype and width not checked on load. Fix stated (223): now checked. Seen at: world/world.py:274-276.
  - b. On Windows an open map locks the file; `cmd_arrays` stops with PermissionError and leaves two .tmp files (about 772 MB each). Fix stated (223-224): stays a note. Seen at: reader/embed.py:315-331 unchanged. No .tmp file is in D:\chrono-data\store at this time.
  - c. A late view gathers nearly every row, about 1.5 GB per view. Fix stated: none, a memory note for M3. Seen at: world/world.py:236-241; reader.md:76-87 gives measured memory for views.
  - d. The refusals run on the mapped path's rows; no test plants a bad row in a mapped store. Fix stated: none needed. Seen at: world/world.py:304-306 (`embedding_problems` runs for both forms).

## Counts
- cutoff_judge.md: 6 findings (1 High, 2 Medium, 3 Low). probes2_judge.md: 9 findings (2 High, 3 Medium, 4 Low or notes). embed_judge.md first judge: J-1 to J-6 (J-6 has 5 sub-items). Second judge: J3-1 to J3-4 (J3-4 has 4 sub-items).
- Docs say fixed: CJ-1 (partly), CJ-6, P2-1, P2-2, P2-3, P2-5, P2-7, P2-8, J-1, J-2, J-3, J-4, J3-1, J3-2, J3-4a.
- Docs say left as notes or limits: CJ-2 (process gate, later owner decision), CJ-3, CJ-4, CJ-5, P2-4 (rule kept), P2-6, P2-9, J-5, J-6, J3-3, J3-4b to d.

## Not found
- No code was found for the January-to-March split of CJ-1.
- No test was found for a refused 2015 embedding row (J-6a), and no World refusal for a repeated story_id in stories (J-6b).
- No status line on cutoff_judge.md or probes2_judge.md findings exists in research/audit/reader.md. Their fixes are recorded in research/audit/cutoff.md sections 4 and 8.8.
