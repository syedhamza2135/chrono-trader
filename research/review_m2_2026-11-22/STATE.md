# M2 review state (22 Nov 2026)

Session: m2-review worktree, branch claude/m2-review-43e1a3 at 3d1df9b. Scope git diff 7081fba..3d1df9b.
Parts go in this folder. Report: research/review_m2_2026-11-22.md. Nothing committed.

Stages: 1 digests (Sonnet) | 2 judge wall (Opus) | 3 judge job (Opus) | 4 judge cutoff (Opus) | 5 checker docs (Sonnet) | 6 skeptics on medium/high (Opus) | 7 report.

Log:
- 22 Nov, start: usage 26% of 5-hour window.
- Stage 1 done: digests docs/digests/m2_wall.md, m2_job.md, m2_cutoff.md, m2_prior_findings.md. Digest notes: probe freeze times only in cutoff.md and file times, not git; cmd_probes2 has no pre-written hash check; no test for refused 2015 row; no World refusal of repeated story_ids in stories (J-6a/b).
- Stage 2 start: usage 33%. Judge wall -> judge_wall.md.
- Stage 2 done: judge_wall.md, 0 high 0 medium 0 low 1 info (W-1 scramble keeps sign pattern). Earlier wall fixes hold.
- Stage 3 start: usage 40%. Judge job -> judge_job.md.
- Stage 3 done: judge_job.md, 0 high 1 medium 3 low 2 info. E-1 medium (manifest lacks cap, pooling, tokenizer, library and code version; a restart after upgrade could mix vectors). Needs skeptic.
- Stage 4 start: usage 44%. Judge cutoff -> judge_cutoff.md.
- Stage 4 done: judge_cutoff.md, 0 high 1 medium 4 low 2 info. C-1 medium (freeze not checkable by others: file times plus hashes saved at scoring; one commit 8 hours later; cmd_probes2 never checks a freeze). Needs skeptic.
- Stage 5 start: usage 49%. Checker docs -> checker_docs.md.
- Stage 5 done: checker_docs.md. reader.md MATCH 57, MISMATCH 5 (embeddings.json bytes 3,108 vs 3,281; world_memory times), UNVERIFIED 1 (ran during tests), NOT RUN 2. cutoff.md 8.9 MATCH 29, MISMATCH 1 (cutoff.py hash is CRLF copy; git 70045341), NOT RUN 1. No style or licensing break.
- Stage 6 start: usage 54%. One skeptic on E-1 and C-1 -> skeptic.md.
- Stage 6 done: skeptic.md (copied from scratchpad). E-1 and C-1 confirmed, both lowered to low.
- Stage 7 done: research/review_m2_2026-11-22.md. 0 high, 0 medium, 10 low, 7 info; 6 owner questions. Nothing committed.
