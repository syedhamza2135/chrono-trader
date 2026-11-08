# M1 kickoff (7 Nov 2026)

Read this first when M1 starts. It says where things stand, what M1 has to deliver, what to decide at the start, and
how to run it inside the usage limits. M1 starts after a fresh 5-hour usage window.

## Session 1 (7 Nov): measured and proposed

This session started with the 5-hour window already at 82%, so it built nothing. It measured the official-opens fetch
and wrote the plan below. Work happens on the branch `claude/m1-kickoff-832c2d`, in the worktree
`.claude\worktrees\m1-kickoff-832c2d`. Nothing is committed yet. This note, `AGENTS.md` and `CLAUDE.md` were untracked
in the main checkout and are copied here, so they go in with M1's first commit. The main checkout still has its own
untracked copies, and git will refuse to merge this branch into master until those copies are moved away.

**Measured: Alpaca has a historical auctions endpoint, and it works on the free plan.** `/v2/stocks/auctions` with
`feed=sip` returns one record per stock-day: `o` holds the opening auction prints and `c` the closing ones, each with
price, size, exchange, condition and time. The probes are `research/probe_auctions.py` and
`research/probe_auction_pages.py`. They print counts and prices only, and they were run from the main checkout so that
its `data_pipeline` loads `.env` at runtime.
- 5 stocks over 2023-01-23 to 2023-01-25 took one request and 1.3 seconds. On 2023-01-24, the NYSE's delayed openings
  are exactly the ones in `reference/price_events.csv`: LLY 340 on N (16,693 shares at 09:38:25), MA 376 on N (8,632
  shares at 09:39:56) and XOM 110.39 on N (198,488 shares at 09:37:03).
- 2023's 50 preview picks over the whole year took 12 requests and 22 seconds. All 50 came back with all 250 sessions:
  12,500 stock-day records and 90,153 prints. The page limit of 10,000 seems to count prints, not days.
- The NYSE's opening print appears twice, under conditions O and Q at the same time. Nasdaq's appears under exchange
  codes Q and T. Small prints from other exchanges are mixed in, so the listing exchange's largest print is the one to
  take, as in `research/verify_prints.py`.

**So the trades method isn't needed for the job.** The rerun of 912 stock-days with it took about an hour. With the
auctions endpoint, all of it is a few minutes.

**Decisions (the owner approved them on 7 Nov, for the build to start after the 5-hour reset):**
1. **Which stock-days.** Every stock-day that has a bar, not only the picks. The job follows the bar download plan
   (`D:\chrono-data\bars\plan.csv`, 787 rows): the same symbol, period and `asof` for each row. Estimate from the 2023
   measurement: about 2 requests per row for 10 years of one symbol, so about 1,600 requests, under 10 minutes at 180
   a minute. This removes the risk that M1's picker differs from the preview, and it keeps the closing prints too.
2. **How to fetch.** A new `data_pipeline/auctions.py`: one Parquet file per plan row under
   `D:\chrono-data\auctions\`, resumable, through the shared rate limiter in `data_pipeline/alpaca.py`. The event store
   then takes each stock-day's official open as the listing exchange's largest opening print. The listing exchange is
   the exchange of the day's largest auction print, opening or closing, as in the print check.
3. **Check it against the print check.** On the 787 stock-days in `D:\chrono-data\audit\official_prints.csv`, the
   job's opens and closes must equal the prints found there.
4. **Days with no opening print** on the listing exchange (for example a halt all day): count them first, then decide
   the simulator's rule.
5. **Build order.** Each step comes with its tests:
   1. The auctions job and its check (it is quick and unblocks the simulator).
   2. The event store (PLAN 9.4).
   3. `world/`: the clock, the availability rules and `World.view(t)`.
   4. `sim/`: fills at the official open, costs, accounting, `reference/price_events.csv` and exits.
   5. A toy agent (5-day reversal) and the daily loop, so the leak tests can run end to end.
   6. `eval/`: the daily rank IC.
   7. The leak tests: non-interference with hypothesis, the planted leaks, the label embargo and both import
      boundaries. Then the rest of PLAN 9.11 (the vintage test runs on an empty embeddings table until M2).
6. **Agents.** The build steps depend on each other, so the main session builds them one after another. After each
   step, one review agent hunts for leaks in it, with usage checked before and after.

**A small fix to make first.** `data_pipeline/settings.py` loads `.env` from the repo that holds the code, so a script
run from a worktree finds no keys. An optional `CHRONO_ENV_FILE` variable, naming the `.env` to load, would let the
worktree use the main checkout's `.env` without copying it.

## Session 2 (7 Nov, after the reset): built

The build started at 3% of a fresh window. Everything is on the branch `claude/m1-kickoff-832c2d`, uncommitted.

**Built, in the approved order:**
1. `CHRONO_ENV_FILE` in `data_pipeline/settings.py`, with tests.
2. `data_pipeline/auctions.py`, the official auction prints. All 787 bar files were fetched in about 15 minutes (the
   files' write times), with no failures. Results are in `research/audit/auctions.md`:
   - 1,873,240 of 1,877,968 stock-days with a bar have an auction record on an NYSE session.
   - 680 records fall on Saturday 2024-07-20, which had no session. They look like exchange test data and are left
     out.
   - It agrees with the M0 print check on all 785 opens and 783 closes the check judged on plan stock-days. Two
     print-check days (ARNC on 2020-04-01 and 04-03) are the spun-off Arconic Corp, not a plan stock-day.
   - 521 member stock-days have no official open (267 on 2023-01-24, 108 on 2018-01-24, 66 on 2022-03-08). On
     LLY's 2018-01-24 and 2019-08-12, the trades tape has no auction print either, so the gaps are in the source.
   - 246 opens printed more than an hour late. None has an earlier opening print on its listing exchange, and only
     1 is on a member day.
3. `data_pipeline/store.py`, the event store in `D:\chrono-data\store`. Counts are in `research/audit/store.md`.
   It applies all of `reference/price_events.csv`, and its 54 overridden opens equal the auctions' opens.
4. `world/`: the clock, the rules and `World.view(t)`.
5. `sim/`: the simulator, the daily loop and the seal.
6. `agent/reversal.py`, a toy agent: the yearly pick, four price features, and a monthly scaler and ridge.
7. `eval/`: the daily rank IC, and `eval/leaks.py` (the non-interference check).
8. Tests for PLAN 9.11: `tests/test_world.py`, `test_store.py`, `test_sim.py`, `test_leaks.py`, `test_boundaries.py`
   and `test_suites.py`. Before the review, 210 passed and 1 skipped (the embeddings table, M2).

**The strongest check so far.** Through `World.view`, the toy agent's stock picks match
`research/audit/universe_preview.csv` exactly: all 550 picks in 11 years, in the same order. The preview was computed
from the raw files in M0, so this checks the store's company series, the view's membership rule and the picker
together. It runs as a test.

**Decisions taken under the approved plan** (also in PLAN's decisions list):
- The simulator trades a stock only at its official open. With none, the stock isn't traded that day, and its holding
  waits for its next official open.
- A label runs from one official open to the next through the corrected close-to-close returns. The closes cancel,
  so a wrong close can't move a label. A company that stops trading exits at its last traded close, and that label
  shows at the next session's open.
- The store keeps a company's days outside membership only up to 400 days before and 14 days after a membership.
  IHS Markit's INFO file holds another security in 2025.
- A view shows a company only once it has joined the S&P 500, with its earlier history from its join.

**Found and fixed while building:**
- The first missing-open count (34,148) was a bug in the job's summary. The right count is 521.
- The "scramble" perturbation first only swapped late values among themselves. That keeps the mean and spread, so a
  scaler fitted on all the data got through. It now rescales the values too, and the planted leak is caught.
- A planted leak that trains on unrealized labels shows only at a refit's decision. The label embargo test catches it
  on any day.

**The leak review (one agent, about 20% of the window).** It confirmed 10 findings, each with code or a script
(scripts under the session's scratchpad `review\` folder). All are fixed except where noted:
1. A company that leaves and later rejoins (EQT, PCG, FSLR, KDP, ILMN, CHK) showed bars and story links during its
   gap, which says it rejoins. Now each record shows from the start of the membership it was kept for:
   `world/world.py`, `known_from`. Tested on EQT in the real store.
2. The views' category columns listed every company and ticker in the store, META before it existed. Views now hold
   plain strings.
3. View columns were slices of the whole tables, so `.base` reached every later row. Views now hold copies. A test
   follows `.base` from every column.
4. A company with no membership row overflowed the join time to the smallest int64 and showed everything. The
   arithmetic is now int64 throughout, and the delete perturbation no longer triggers it.
5. `from world.view import World` passed the boundary test. `World` now lives in `world/world.py`, `world/view.py`
   defines only `View`, and the test checks imported names and flags references (aliases, `vars`, `.base`). The leak
   harness gives agents no World unless a planted leak asks for one.
6. The leak checks had blind spots: shift keeps values, scramble kept signs, rows held back until a join were never
   perturbed, and the test days missed the pick and refit days. Now records are perturbed by when they become
   visible, scramble flips signs, every planted leak must be caught by one of the three modes, the check days
   include the pick and refit days, and the synthetic world has later joins and a rejoin. Three new planted leaks
   (future breadth, a 28-day peek at the pick, companies not yet joined) are caught.
7. Corrections applied only to member bars. They now apply to every bar the store keeps. **Not done:** EQT's
   2018-11-13 Equitrans spin-off needs a `total_return` row in `reference/price_events.csv` (its evidence needs
   ETRN's first close), and the 125 labels that start on a member day and end on a non-member day weren't reviewed
   (none ends at a close). EQT is never a pick.
8. A holding with no label from its official open froze. It is now sold at that open, and `Run.stats` counts it.
9. The seal guarded only `sim.run`. Views now refuse the sealed years unless the seal holds (or a data audit opens
   them explicitly), and the seal hashes the run's whole settings, the costs and the agent's parameters included.
   **Not done:** refusing and logging a second sealed run (PLAN 9.12) is M4's.
10. A label counted as available at 9:30 even when its official open printed later. It now shows when that open
   printed (`end_open_time` in the labels).

After the fixes: 225 tests pass and 1 skips, in 3 to 4 minutes.

**Open questions for the owner** (all three settled on 8 Nov, Session 4):
1. Failed banks (SVB, First Republic, Signature) exit at their last close, by PLAN's rule "leaves at its last
   available price". For SVB that is its close on 2023-03-09, before the shares became nearly worthless. Keep it, or
   count a failure as a total loss?
2. A stock-day with no official open is never traded. The alternative is Alpaca's first trade, which is the
   provisional open M0 rejected.
3. Before merging into master, the main checkout's untracked `AGENTS.md`, `CLAUDE.md` and `research/m1_kickoff.md`
   must move away, or git will refuse the merge.

## Session 3 (8 Nov): a second review, and the attribution

A second review of PR #1 (one agent, about 26% of a window) found 10 more problems. Each was shown with a script (in
the session's scratchpad `review2\` folder), and each is fixed:
1. A view's story tags were still views into one array of every story's tags, as Parquet reads list columns. They
   are now tuples of their own (`world/world.py`, `_plain`), and the test reads the tags back from Parquet.
2. A few bar files hold 12 bars after the data end (to 2026-10-30). The simulator's data end moved with them, and it
   sold every holding on 2026-10-28. The store now ends on the data's last day, and a test checks it.
3. The perturbations could bring hidden records into view: a swapped company id, or a date moved into a membership
   window. A changed record that would show by t is now dropped, and a test checks that the perturbed view at t
   equals the original in every mode.
4. An agent could read the store from disk with `pd.io.parquet.get_engine(...).read(...)`, which no check saw. The
   boundary test now names those, and its docstring says the leak check can't see reads from disk.
5. The listing exchange was chosen each day from that day's largest print. On 2026-08-20 Alpaca's records for Nasdaq
   stocks hold no Nasdaq closing print, so 9 member stock-days took an NYSE Arca opening print of 1 to 25 shares.
   It is now the venue of most days' largest print over the 21 sessions around the day. Two real opens came back
   (COF on 2016-10-13, CXO on 2017-10-09), so 519 member stock-days now lack an official open, and 218 opens printed
   more than an hour late.
6. The comparison missed a prediction that is NaN in one run only. It now flags it.
7. The vintage rule gave 2026 news a 2025 model. It now stops at 2024, the check asks for exactly the rule's
   vintage, and PLAN 5.2 says the publication year counts.
8. The property test drew 5 of its 14 check days. Every check day now runs, each with one of the three modes in turn.
9. Six mergers counted as window cuts. The exits are now 103 stopped and 119 cut.
10. This note said 117 labels end on a non-member day. The store has 125 that start on a member day and end on one.

The reviewer's own scripts, rerun on the fixed code, show each one fixed. After the fixes: 255 tests pass and 1
skips, in 4 to 5 minutes.

**The non-member screen (8 Nov).** One agent screened the 48,935 non-member bars the store keeps, as M0 screened
member days: the adjusted against the raw move (more than 4% apart), and adjusted returns below the price-only
return. It flagged 12 days, and further screens (Alpaca's dividend and spin-off records, moves above 25%, drops and
opening gaps) found more. Eight are splits Alpaca adjusted right. Three needed rows, now in
`reference/price_events.csv` (125 rows):
- EQT on 2018-11-13: the Equitrans spin-off, 0.8 ETRN per share, which Alpaca applies as a split. +1.82% instead
  of -57.15%. EQT's last member-day label (2018-11-12) was -58.21%, and it is -0.70% with the row.
- DPS on 2018-07-10: the $103.75 special dividend paid with the Keurig merger. +1.84% instead of +11.45%.
- CCE on 2016-05-31: the merger into Coca-Cola European Partners, one share and $14.50 in cash per CCE share (CCE's
  8-K exhibit on SEC EDGAR, and Cahill Gordon & Reindel's notice). +3.41% instead of -24.70%. CCE's last member-day
  label (2016-05-27) ended here: it was -24.99%, and it is +0.58% with the row.
Of the 125 labels that start on a member day and end on a non-member day, EQT's and CCE's were the wrong ones.
Left open, and none reaches a label or a feature the agents use: Wyndham's 2018-06-01 spin-off of Wyndham Hotels
(Alpaca applies nothing, and the ratio is in neither the store nor Alpaca's records), Hilton's 2017-01-04 reverse
split and two spin-offs (114 sessions before it joined), and TechnipFMC's 2021-02-16 Technip Energies spin-off (no
dollar price for the new shares). A smaller distribution that Alpaca never applied could still be missed before
2019, since Alpaca's spin-off records start in 2019.

**Attribution.** On 8 Nov the owner asked to drop the Co-Authored-By trailer everywhere. Their Claude Code user
settings now hide it (`attribution` with empty texts and no session link), AGENTS.md's Git rule says so, and the
memory records it. New commits carry no attribution. The 9 older commits that carried the line (8 on master, and
the M1 branch's first) were rewritten on 8 Nov, messages only (Session 4).

## Session 4 (8 Nov): the owner's decisions and the cleanup

The owner settled the three open questions of Session 2 and asked for M1's leftovers to be finished before M2's build.

- **A failed company is a total loss.** SVB Financial, Signature Bank and First Republic each have a `failure` row in
  `reference/price_events.csv`. `store.failures` marks a company whose `failure` row falls within a week after its
  last traded bar, and `store.labels` makes its exit label -1 instead of the return to its last close. The simulator
  marks holdings by their labels, so a holding in a failed company ends at zero, and a short gains its full value.
  An acquired company still exits at its last traded close. In the rebuilt store, exactly three labels are -1: SVB's
  from its 2023-03-09 open, Signature's from 2023-03-10 and First Republic's from 2023-04-28. Every other count in
  `research/audit/store.md` is unchanged. Three new tests cover the rule, and the full suite passes: 258 tests,
  with 1 skip.
- **A stock-day with no official open stays untraded.** The owner kept the rule rather than fall back to Alpaca's
  first trade.
- **The history was rewritten, messages only.** `git filter-branch --msg-filter` dropped the Claude Co-Authored-By
  line from the 9 commits that had it. A script compared all 12 commits on master and both `claude/` branches with
  local backups: the same trees, authors, committers and dates, and messages that differ only by that line. The
  backups are the local branches under `backup/pre-rewrite/` and filter-branch's `refs/original/`, never pushed.
  GitHub can still show the old commits through PR #1's history until GitHub Support purges them. The prices and
  headlines the M0 review found in old commits stay there, as the owner chose. The docs and the memory now use the
  new hashes:

  | Old | New | Commit |
  |---|---|---|
  | `c409871` | `78e0c40` | Add the research plan, its review, and the FNSPID probes |
  | `e425969` | `0b87aab` | Set up Alpaca access and record the first audit results |
  | `212bafa` | `130c849` | Add the M0 data pipeline and the price audit |
  | `cd0a0e2` | `043080f` | Add the news audit and record its results in the plan |
  | `4d5bb0d` | `69e777b` | Add a README and note the GitHub remote in the plan |
  | `9a1508f` | `b7d78d9` | Finish the M0 data audit: identity table, price corrections, split |
  | `e56e09a` | `3f1825a` | Correct more of Alpaca's distribution adjustments |
  | `7b4a200` | `af1aaf9` | Fix the M0 review findings and adopt the checked parts of a research brief |
  | `b2b9441` | `93d8f70` | Build M1: the time wall, the event store and the official opens |
  | `c9c09cf` | `90ecb8a` | Fix the second review's ten findings in M1 |
  | `87bacdc` | `658db1c` | Correct three distributions on days outside membership |
  | `4ebbe24` | `2ace1c3` | Start M2 (on M2's branch, `claude/awesome-panini-89f869`) |

- **The merge.** The main checkout's untracked `AGENTS.md`, `CLAUDE.md` and `research/m1_kickoff.md` held nothing
  this branch lacks (`CLAUDE.md` identical, the other two older versions), so they went to the Recycle Bin. The main
  checkout's master fast-forwards to this branch, and the owner's push of master merges PR #1.

## Where things stand

- **M0, the data audit, is done, and its review is closed.** The review's 33 findings are fixed in commit `af1aaf9`,
  pushed on 7 Nov. Master is the repo's only branch, and it matches the local copy. `research/audit/m0_review.md`
  records how the fixes were made and the decisions taken along the way.
- **A research brief was checked on 7 Nov** (`research/brief_check.md`). Its adopted parts are in PLAN.md: batch
  against sequential learning, memory ablation for Track B, a standalone environment, seeds, regime reporting, a
  masking diagnostic and as-of economic data. Its single-market MVP from 1999 is deferred to a later long replay.
- **131 tests pass.**
- **The data on D: is final for M0:** daily bars for 787 plan rows and 719 companies, 2,260,406 news stories from
  January 2015 to October 2026, and the new print check (`D:\chrono-data\audit\official_prints.csv`).

## What M1 has to deliver

PLAN.md section 9.2: M1 is done when every test in section 9.11 passes, every planted leak gets caught, and the
simulator has the listing exchange's official opening auction print for every stock-day it trades. The pieces:

1. **The event store** (PLAN 9.4). Parquet tables built from the M0 outputs: raw and adjusted bars with the
   incomplete flag, stories with `available_at` (the update time plus 15 minutes, Benzinga only, stories edited more
   than 3 days late dropped), story-to-company links after the single-firm filter, membership and identity. The
   embeddings arrive in M2.
2. **The time wall, `world/`** (PLAN 5.1 and 9.5). The clock (NYSE sessions, early closes and daylight saving), the
   availability rule for each source, and `World.view(t)`, which returns only what was available at time t. Training
   labels must be realized by day k-2 at 9:00 on day k.
3. **The simulator, `sim/`.** Fills at the open, costs, portfolio accounting, the corrections in
   `reference/price_events.csv`, and exits at the last available price for acquired companies (a total loss for failed ones, since 8 Nov).
4. **The parts of `eval/` the tests need**, such as the daily rank IC. The rest comes in M3.
5. **The test suites** in PLAN 9.11, including both import boundaries.
6. **The official opens.** A `data_pipeline` job, which may see everything, fetches the listing exchange's opening
   auction print for every stock-day the simulator can trade, resumes after a stop, and stays inside Alpaca's rate
   limit. Until it has run, Alpaca's open is provisional (PLAN's decisions list, 4 Nov).

Suggested, not in PLAN: a toy agent, for example a 5-day reversal ranking, so the leak tests can run the whole loop
before Track A's real agent exists in M3.

## Decisions to make at the start

- **Which stock-days get official opens.** The 50 picks of each year come to about 135,000 stock-days (PLAN 9.13).
  M1's own stock picker could differ from the audit's preview, so fetching a few extra stocks a year is safer.
- **How to fetch them.** These figures are estimates to measure on a sample first:
  - One stock-day at a time with the method in `research/verify_prints.py` costs a few requests each. The rerun on
    4 Nov took about an hour for 912 stock-days, so 135,000 would take days.
  - Alpaca's trades endpoint takes several symbols at once. If one paged request for a narrow window around 9:30
    covers all 50 stocks of a day, the job would need a few thousand requests instead. Delayed opens would still
    need the wider window.
- **The build order, and how many agents to use.**

## Running it inside the usage limits

What this project has measured:
- A phase of seven agents (the docs phase, 7 Nov) used about half of a 5-hour window.
- Four agents running at once filled most of a window in under an hour (4 Nov).
- The owner stops work at 90% of the 5-hour limit.

So start right after a reset, run one agent at a time, check usage between agents, and stop and save the state before
90%. A workflow keeps its finished agents if it stops, but only the session that started it can resume it. M1 will
probably take two or three windows (an estimate).

## Open questions for the owner

- Whether to rewrite git history to remove the prices and headlines the review found in commits already pushed (the
  repo is private). On 8 Nov the owner chose to leave them: the rewrite changed commit messages only.
- Claude Code's auto-mode check blocks pushes to master, so the owner runs `git push` or adds a permission rule.
