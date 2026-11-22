# Skeptic: E-1 and C-1 of the M2 review (22 Nov 2026)

Repo at 3d1df9b. Times are New York unless marked. No edits, no model runs, no headline text read or printed.

## E-1. The manifest does not pin cap, pooling, tokenizer, library or code version

- **Verdict:** confirmed. **Severity:** low (judge said medium).
- **What I ran and read.**
  - `reader/embed.py` lines 94-103, 166-175, 178-192, 240-281: the manifest holds vintage, repo, commit, counts and
    id hashes only; `check_manifest` compares only that; `run_vintage` skips any part whose file exists
    (line 183); `finish` records torch and transformers versions at finish time (271-278).
  - Other guards, by `grep -rn "versions|transformers|__version__"` over world, reader, tests, eval, sim: none at
    run, resume, finish or `World.load` (world/world.py:259-261 reads embeddings.json for the arrays' row hash, not
    versions). `tests/test_embed.py:75` computes emb_avg with the same `hidden_states[1:]` expression as the code, so
    it would pass under a library that stops tying the last entry. `requirements.txt:13-14` pins
    `torch==2.15.0+cpu` and `transformers==5.22.0` exactly, but nothing checks it at run time.
  - The transformers claim: `D:\venvs\chrono-trader\Lib\site-packages\transformers\utils\output_capturing.py`
    (installed 5.22.0) lines 234 and 296-305: `capture_outputs(tie_last_hidden_states=True)`, and the last
    `hidden_states` entry is replaced by `last_hidden_state`; `models/modernbert/modeling_modernbert.py:421` uses
    `@capture_outputs` and line 465 applies `final_norm`. Confirmed as stated.
- **Does it matter now.** No, for the M2 table. `D:\chrono-data\reader\run.log` has one "story set SHA-256" line and
  one "run finished" line, and no "all parts done" line; `run.err` shows ten weight loads (one per vintage) in one
  process. Parts were written from 20:46 on 21 Nov to 02:53 on 22 Nov (file times). torch and transformers
  dist-info folders date from 30 Oct, before the run. `D:\chrono-data\store\embeddings.json` records torch
  2.15.0+cpu and transformers 5.22.0, equal to what is installed. The diff of embed.py from e53c114 to 3d1df9b adds
  only the arrays functions, not a change to `embed_ids`. All parts exist, so the resume path is closed for M2.
- **Why lower.** The harm needs a restart after an upgrade or an edit, and the run is finished. The live exposure is
  the M5 morning job, which reuses `embed_ids` and is not built yet. The finding is right that nothing would catch a
  mix, so carry the fix (pin cap, pooling, tokenizer, library versions and an `embed_ids` hash, and assert them in
  the M5 job) as an M5 entry requirement rather than an M2 blocker.

## C-1. The second freeze can only be checked on the author's machine

- **Verdict:** confirmed. **Severity:** low (judge said medium).
- **What I ran and read.**
  - `git log --all --format="%h %ad %s" --date=iso -- reader/probes2.csv reader/cutoff.py research/audit/cutoff.md
    research/audit/probes2_judge.md`: one commit, e53c114 (22 Nov 10:32 +0500, 00:32 New York).
  - File times (PowerShell `Get-Item`, converted to New York) in the authoring worktree `reverent-sanderson-da34d6`:
    probes2_judge.md written 16:09:54; probes2.csv last written 16:20:26; cutoff.py 16:20:51; cutoff.md 17:06:53.
    In `D:\chrono-data\reader\cutoff`: run_probes2.log created 16:21:25, probes2 folder 16:21:26, scores.parquet
    and scores.json 16:35:22. (This review worktree's copies all date from 04:46 on 22 Nov, the checkout, so they
    prove nothing.)
  - `run_probes2.log`: its first line prints the second-freeze hashes, then 11 "probes scored" lines (2014 to 2024),
    23 lines in all: one run. `probes2/scores.json` holds the same two hashes, and `sha256sum` of the committed
    files equals them (`eed31d91...bd5bd`, `8bae55f5...3b3e`).
  - `reader/cutoff.py:572-580`: `cmd_probes2` refuses only when scores.parquet exists, and checks no freeze record.
  - `research/audit/cutoff.md:316-320` (the "written before any vintage scored" claim) and 541-600 (8.7 first
    freeze, 8.8 changes, the second freeze at 16:21). `research/audit/probes2_judge.md:11` records only the first
    freeze's hashes (prefixes `5dac4506`, `06f106d0`); nothing outside the author's machine holds the second.
  - Recycle Bin (Shell.Application namespace 10): 2 items, none named like a score, probe or report file, so no sign
    of an earlier scored run moved away.
- **Found.** Every factual claim in C-1 checks out. The freeze is 34 seconds after the last cutoff.py write and the
  same minute as the run's first file. The record is all local file times plus hashes taken at scoring. The 319
  wording claim is right: 8.9 to 10 were written after scoring.
- **Why lower.** The local evidence is coherent and in order, with one run and no trace of a discarded one. No
  vintage fails, and the owner accepted all 11 as a known limit, so no decision rests on the freeze. A weak record
  of process, with the fix cheap and for next time (commit or send the hashes before scoring, make `cmd_probes2`
  check them, reword 319), is low.
