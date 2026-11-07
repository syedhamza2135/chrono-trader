# M0 review: findings and fix plan (2 Nov 2026)

A read-only review of the committed M0 work in four areas (lookahead, identity, prices, docs). A skeptic agent tried to
refute every finding. The review finished on 2 Nov. The fixes finished on 7 Nov, in three phases; only the commit is left.

## Where things stand

- **Committed and pushed:** `9a1508f` (the M0 audit) and `e56e09a` (36 more distribution corrections;
  `reference/price_events.csv` has 116 rows). 53 tests pass.
- **Uncommitted in the working tree (11 files):** the spin-off session's Fortune Brands fix. Two `identity_fixes.csv` rows
  (FBHS until 2022-12-14, FBIN from 2022-12-15), regenerated identity tables and bar plan (pinned to the original run
  date), four new bar files, `price_events.csv` row 117 (MasterBrand spin-off: FBIN -6.9% raw, +5.5% true), reruns of the
  price audit, news audit and split, and the docs updated to match (809 ticker rows, 88 fixes, 66 member days without a
  bar, 54 row changes, 500,742 headlines, 388,442 sealed single-firm stories). The M0 session wasn't told; it waits.
- **Review result:** 33 findings confirmed (2 major, 31 minor) and 2 refuted. The docs area ran in two halves against
  the working tree: `docs-audit` (audit.md) and `docs-plan` (README, PLAN.md, m0_handoff.md, and the licensing and
  em-dash rules). The other areas read `9a1508f`. The identity findings still hold in the working tree: it has no BMS,
  MBC, FCPT, TFCFA or TFCF rows, and AMCR still starts on 2019-06-07.
- **Full results:** each finding's claim, failing case, evidence, suggested fix and the skeptic's reproduction are in
  `D:\chrono-data\review\m0_review_findings.md` (compact) and `m0_review_findings_full.md`, and in the workflow journal
  (`C:\Users\syedh\.claude\projects\C--Users-syedh-dev-portfolio--claude-worktrees-loving-murdock-d6e316\f5002915-e85d-4fe0-aeda-d118781a16c5\subagents\workflows\wf_91cba563-595\journal.jsonl`).
  They stay out of git because they quote prices and headlines. The reviewers' scratch scripts are under
  `C:\Users\syedh\AppData\Local\Temp\claude\C--Users-syedh-dev-portfolio--claude-worktrees-loving-murdock-d6e316\f5002915-e85d-4fe0-aeda-d118781a16c5\scratchpad\m0-review\`.
- **The user's order:** fix every confirmed finding, then ask before one commit with the fixes, the Fortune Brands work
  and this note.
- **Backup:** on 5 Nov the uncommitted work (phases 1 and 2, the Fortune Brands fix and this note) was pushed as
  one snapshot commit to the branch `backup/m0-review-fixes`; master is untouched. Once the single commit is on
  master, ask the user before deleting the branch.

## Confirmed findings

### Lookahead

1. **Major: the pick ranking uses another company's trading.** `universe_preview` (`data_pipeline/audit_prices.py`,
   lines 170 to 176) ranks each pick window on the live row's whole Alpaca file, including bars from before the row's
   `use_from` that belong to another security. The DWDP file has 420 bars before 2017-09-01, all identical in close and
   volume to Dow Chemical's member bars (checked again by hand: `scratchpad/m0-review/main/dwdp_check.py`). In 2018
   DowDuPont ranks 70th ($389.4M) instead of 40th ($557.5M on its own 83 days), so GM (50th, $497.1M) takes its place.
   The same splice is in the JCI 2017, FOXA/FOX 2020 and SW 2025 windows without changing a top-50 pick. PLAN.md (line
   123 and the 9.3 table, line 453) and the `bars.py` docstring wrongly say each ticker is used only inside its row,
   and `prices.load` is documented as the picker's feed, so M1 would inherit it.
   Fix: rank each company only on its own bars (its earlier rows' member days, and its own trading before it joined
   where no other company's row holds that security). Knock-on numbers: 2018 `news_reading_load.csv` picked 8,548 to
   8,427; `split.json` dev picked stories 26,317 to 26,196; the 2019 churn in `prices.md` 10 to 9.
2. **Minor: "counts only" isn't true.** `split.json` says no prices, returns or other outcomes were read (`split.py`
   line 63 and its docstring, line 5; `audit.md` lines 99 to 100), but `single_firm_stories_about_picked` comes from the
   pick preview, which ranks on close times volume. Fix: drop the field, or say prices and volumes chose the picks and
   no returns were read.
3. **Minor: 2016 coverage counted from January.** The 2016 picked-story counts and coverage include January to March,
   before the 2016-04-01 pick (3,307 of 11,788 stories). From April the median pick has 125 stories on 71 days and the
   thinnest 31 (BRK.B), not 177, 96 and 48 (`news.md`, `audit.md`, PLAN 9.3 line 484). Fix: count from each year's
   pick date.

Also found: `audit.md` said 807 ticker rows while the table had 808. The Fortune Brands update fixes it (now 809).

### Identity (all minor)

1. Bemis's two S&P 500 days (2019-06-07 and 2019-06-10) are given to Amcor, which has no bars on them. Fix: a Bemis
   member fix (BMS, 2019-06-07 to 2019-06-11, CIK checked) with a ticker row, and AMCR's start moved to 2019-06-11. The
   survivorship notes in audit.md and PLAN.md call these days before Amcor's first trade.
2. 21st Century Fox's last member day, 2019-03-19 under TFCFA/TFCF, is missing. Fix: end both 21CF memberships on
   2019-03-20 and add TFCFA and TFCF rows for 2019-03-19, so the bar plan fetches them.
3. MasterBrand (MBC), a member on 2022-12-15 and 2022-12-16, is missing. Fix: a member fix from 2022-12-15 to
   2022-12-19 and a rows fix, as for FCPT. The Fortune Brands work doesn't cover it.
4. Four Corners (FCPT) is a member on 2015-11-10 with no ticker row, so identity.csv covers 743 companies, not 744, and
   the test skips 2015. Fix: a rows fix for 0001650132 (or let `timelines()` write rows for companies only the fixes
   know), and start the test on 2015-01-01.
5. Class tags rooted on a plain listed ticker (LEN.B, CBS.A, STZ.B, BIO.B, TAP.A) map to nothing and count as an extra
   company, and pairs like FOXA/FOX and NWSA/NWS count as two companies. Fix: when a dotted tag misses, try its root,
   for class suffixes (.A, .B, .C, .K) only.

### Prices

1. **Major: incomplete bars.** Alpaca's bars for about 300 NYSE-listed members are incomplete on 2021-04-19,
   2021-10-25 and 2022-03-08: a handful of trades, and a tiny fraction of the volume of the days around them, in both
   the raw and the adjusted files. The audit only checks for zero volume. Fix: flag member bars whose volume or trade
   count is far below their trailing median, list them in prices.md, and have features treat those days' volume, range
   and VWAP as missing (or rebuild them from trades).
2. Minor: `returns()` measures a newly added company's first member-day return against another security's close (Fox
   Corp 2019-03-19, Dow Inc 2019-04-02, Smurfit Westrock 2024-07-08, DowDuPont 2017-09-01). Fix: NaN on a first member
   day or a rejoin, unless the previous bar is the same security's.
3. Minor: `verify_prints.py` records a small print from another exchange as the official close when the NYSE auction
   prints after 16:01. That affects 8 rows, including FRC 2023-03-17 and WST 2025-02-13, and DHR and IP, which
   price_events rows 94 and 110 cite. Fix: search to 16:30 for the listing exchange's print and take its largest.
4. Minor: `verify_prints.py` writes "matches" when no closing print was found, and never looks for a 13:00 early close
   (LH, BWA and FTRE on 2023-07-03, cited by price_events rows 92 and 93, and five more early-close days). Fix: a
   separate verdict when a side has no prints, the close time from the exchange calendar, and such days not counted as
   checked.
5. Minor: audit.md says the 2023-01-24 NYSE opens were 8% to 15% from Alpaca's opens. NCLH was 24% away, and PLD opened
   at 09:45:09. PLAN.md line 124 and m0_handoff.md repeat it.

### Docs: audit.md (all minor)

1. The survivorship answer calls the SVB and First Republic failures acquisitions: 6 of the 64 "after" member days
   follow bank failures (SIVB from 2023-03-10, FRC from 2023-05-01). prices.md (written by `audit_prices.py`) and
   PLAN 9.3 use the same wording. Marking failures separately also keeps an exit rule from booking them at the last
   close.
2. 1,371,717 counts member bars by share-class row, including 12 bars after the 2026-10-28 check end. Company member
   days to 2026-10-28 are 1,360,468, of which 66 have no bar, which is split.json's total. PLAN 9.3 and
   `audit_prices.py`'s label repeat the wrong figure.
3. The dividend check says only Occidental misses. Aimco 2020-11-03 (whose record Alpaca duplicates) and NortonLifeLock
   2020-02-03 miss too; both are already corrected in price_events.csv.
4. Not every distribution check took its terms from a filing or priced every piece. Ford's terms and Franklin's record
   date rest on secondary sources, and Aimco's 2020 ex-date and stock part and BDX's 2026-02-10 ex-date are inferred.
5. `unadjusted_results.csv` has no source column and lacks 3 of the 18 never-applied rows (their evidence is in
   price_events.csv). The Garrett, Resideo and Amentum checks that audit.md cites have no recorded source anywhere.
6. Renames are said to be dated by filings or Alpaca's as-of lookups, but only 14 of 35 are. Seven rest on the
   membership file's switch date alone (DD, GL, BKR, PEAK, TFC, BBWI, VIAC) and nine on Benzinga headlines or tags.
7. The sealed period's story counts include 2026-10-29, the day after its last session, because stories are summed by
   UTC calendar year.
8. 86 bar files were fetched after the first download, not 82: the Fortune Brands fix added four on 1 Nov.

### Docs: PLAN.md, README, m0_handoff.md and the user's rules (all minor)

1. `verify_prints.py` counts gaps of up to 2% as matches, so 22 checked opens and closes are wrong and uncorrected:
   OKE's 2020-03-18 close and 21 opens, including ORCL's on 2020-03-12, a sealed-period pick. Fix: judge against the
   listing exchange's print at about a cent or 0.2%, re-judge the 784 rows, add overrides for the new misses, and state
   the tolerance in PLAN 9.3 and audit.md.
2. PLAN 9.3 says the 14 large-move reversals match the official prints. Five don't (Nordstrom's bar, Hilton's close,
   and the opens of Hess, Ventas and Aptiv), and price_events.csv corrects all five.
3. The official prints row says "784 days" for 784 stock-days on 435 dates, counts 5 close exceptions where there are 6
   (Nordstrom's is left out), and its "54 days" of open misses are 54 stock-days on 17 dates.
4. Same as audit.md item 2, in PLAN 9.3.
5. Same as audit.md item 1, in PLAN 9.3.
6. "16 more distributions aren't adjusted at all" leaves out Under Armour's class C dividend: 17, or 18 with Aimco's
   2019 dividend.
7. PLAN lists XL as a spliced history, but XL is two files for two securities.
8. Same as audit.md item 7, in split.json (`split.py` sums whole calendar years).
9. The README says a few rows of price_events.csv carry single prices. 115 of its 117 rows carry prices: 60 in the price
   columns (one of them Nordstrom's whole rebuilt bar, with its volume) and 55 quoting Alpaca closes in their evidence.
10. Licensing: `correction()` in `audit_prices.py` writes the official prices into large_moves.csv and prices.md (31
    rows each), so every rerun puts prices in tracked files.
11. Licensing: hand-written prices and a share count in m0_handoff.md (Hilton, Moderna), audit.md (Eli Lilly), the
    identity_fixes.csv evidence notes (Under Armour, XL) and the `verify_prints.py` docstring (Nordstrom).
12. Licensing: Benzinga headlines quoted outside evidence notes, in news.md (five recap headlines and an example),
    `audit_news.py` (prints them, and hard-codes the example), PLAN.md and REVIEW.md.

### Refuted

- An embargo at the dev/sealed boundary: one-day open-to-open labels don't overlap, so dev never sees a sealed outcome.
- That `price_events.csv` row 100 (the SKYD warrant dividend) cites a warrant close the print check rejects.

### Checked and correct (lookahead area)

Pick windows end before the pick day; `members_on` uses the pick day; the split's boundaries and session counts; news
availability (`updated_at` plus 15 minutes, New York dates); the SymbolIndex rows for FB/META, PCLN/BKNG, DWDP/DD,
UTX/RTX and AA/ARNC/HWM; membership changes near pick dates. `universe_preview.csv` and `news_reading_load.csv`
reproduce exactly from the code.

## Fix plan

The order matters, because the reruns change numbers the docs quote.

1. **Code and data.**
   - Identity: the Bemis, 21st Century Fox, MasterBrand and Four Corners rows (CIKs checked against filings), class
     tags through their root for .A, .B, .C and .K, and the identity test from 2015-01-01.
   - Prices: `universe_preview` ranks each company on its own bars only; `returns()` gives NaN across a splice;
     incomplete bars (volume or trade count far below the trailing median) are flagged and listed in prices.md;
     `correction()` writes only the kind of correction; the "acquisition" wording and the member-day label are fixed.
   - `verify_prints.py`: the listing exchange's auction print, a tolerance of about a cent or 0.2%, the calendar's close
     time, and a "no print" verdict.
   - News and split: picked stories counted from each year's pick date, and each period's stories by New York date up
     to its last session; `single_firm_stories_about_picked` dropped from split.json or "counts only" restated;
     `audit_news.py` names stories by id and time instead of printing headlines.
2. **Reruns:** identity, the bar plan and the new bar files (BMS, TFCFA, TFCF, MBC, FCPT; needs Alpaca), the price
   audit, `verify_prints.py` (needs Alpaca) with new overrides in price_events.csv for the misses it finds, the news
   audit, the split, and pytest.
3. **Docs:** audit.md, PLAN.md, README.md, m0_handoff.md, REVIEW.md, the identity_fixes.csv evidence notes and the
   `verify_prints.py` docstring, for every finding above and the new numbers. No prices or headlines outside
   price_events.csv and the evidence-note quotes the user accepted.
4. **Check:** a skeptic pass over the diff, one finding at a time, before asking to commit.

Defaults, unless the user says otherwise:
- The prices and headlines that the licensing findings name are removed from the files from now on. They are already
  in pushed commits (private repo). Removing them from history would need a rewrite and a force-push, so that waits
  for the user.
- Incomplete bars are flagged, and those days' volume, range and VWAP are treated as missing. Rebuilding them from
  trades would need a trades download.

## Next steps

1. Phase 1, code and reference data, finished on 4 Nov (run `wf_1ec3c2a8-0e2`). The full result, with each fixer's
   numbers and phase 2 notes and each skeptic's verdicts, is saved as `D:\chrono-data\review\phase1_result.json`.
   Every finding has a fix. The skeptics confirmed all but three, which I then fixed or settled:
   - identity-5: the class-tag fallback also mapped two TSX tags (CCL.A to Carnival, PNC.A to PNC). It now covers only
     the six US class tags in the news (`CLASS_TAGS` in identity.py), with a test for the two TSX tags.
   - prices-1: the incomplete-bar rule also required low volume, so it missed 3 member bars on the bad days (PKG and
     NLSN on 2021-10-25, PSX on 2022-03-08). It now uses the trade count alone, which adds only those 3 and DELL's
     (not a member): 1,035 member bars.
   - prices-2: `returns()` leaves a first member day undefined unless another of the company's rows proves the
     previous bar is its own. That also blanks about 189 genuine first-day returns (SEDG 2021-12-20, IR 2020-03-02).
     Kept on purpose: a wrong return is worse than a missing one, and no large move or adjustment event is lost.
   131 tests pass. Beyond the findings: SBNY's failure row (price_events row 120), and two new tracked files,
   `research/audit/incomplete_bars.csv` and `research/audit/news_by_day.csv`, which belong in the commit.
2. Phase 2, in this order (from the fixers' notes in the saved result):
   1. Identity is rebuilt and pinned. Rerun only if needed, with `D:\chrono-data\review\scripts\run_identity_pinned.py`.
   2. `python -m data_pipeline.bars` (Alpaca): four new files, BMS, TFCFA, TFCF and MBC. FCPT gets none, because its
      only member day is before 2016.
   3. `python -m data_pipeline.audit_prices`.
   4. `research/verify_prints.py` into new output files (the old ones have other columns), about an hour in the
      background; the inputs and steps are in `phase1_fix_prints.json`. Then install the new `official_prints.csv`.
   5. Overrides for the new misses, appended after row 120. An offline estimate says about 150 stored 'matches' fail
      at the new tolerance, mostly opens. If it's over about 100, ask the user first.
   6. `audit_prices` again, `audit_news`, `python -m data_pipeline.split 2026-10-28`, pytest.
   Progress on 4 Nov, at 85% of the 5-hour limit:
   - Done: the pinned bar plan (787 rows for 719 companies) and the 8 new files (BMS, TFCFA, TFCF and MBC, raw and
     all), with `D:\chrono-data\review\scripts\run_bars_pinned.py`; the price audit (64 member days without a bar,
     none before a first trade; 1,035 incomplete member bars; 2018 picks DWDP, not GM); the news audit and the split,
     which don't need the print check (split.json now matches the news skeptic's figures: sealed 1,609,374 stories,
     387,796 about members).
   - Running in the background: all six print checks, one at a time, with
     `D:\chrono-data\review\scripts\run_prints_v2.sh` (log `D:\chrono-data\review\prints_v2.log`). The main input is
     `official_prints_input_v2.csv`: the old 784 rows plus 3 large moves the first input left out (UA 2016-04-08,
     ARNC 2016-11-01, RTX 2020-04-03). `prints_input2_clean.csv` drops the 14 rows with a bad asof. If it stops,
     run the same script again: each check resumes from its output file.
   - Finished at 02:03 on 5 Nov (Pakistan time), in about an hour. Main check, 787 rows: 522 match, 255 MISMATCH
     open, 4 MISMATCH close, 4 both, 2 'open only'; 198 old 'matches' now miss the open. 206 misses have no override
     yet, 204 opens and 2 closes (110 large moves, 70 phantom checks, 23 random days, 3 new). Open misses: median
     gap 0.64%; on the random days, 23 of 300. The distribution checks add 38 open misses. Over 100,
     and the user chose to leave opens to M1, which fetches the official opening
     auction for every stock-day the simulator trades. The 2 closes got overrides: rows 121 (OKE) and 122 (NTRS).
   - Done after that: `official_prints_v2.csv` installed as `official_prints.csv` (the old file kept as
     `official_prints_2026-10-31.csv`), the 2 close overrides, the price audit rerun and pytest.
   - Left for phase 3: recheck the price_events notes that cite the print check (lines 2 to 63, and the distribution
     rows from line 82) against the new outputs (`official_prints_v2.csv`, `distributions/prints*_v2.csv`; the old
     `prints*.csv` stay). Write the open decision into PLAN.md (an M1 step) and audit.md.
3. Phase 3: the docs, then a skeptic pass over every fix.
   Started on 7 Nov as run `wf_d8baf5a4-69f` (a resume works only from the session that started it): one editor for
   audit.md; two in turn for PLAN.md, first the M0 parts and then the research brief's adopted items
   (`research/brief_check.md`, also written on 7 Nov); one for README.md, m0_handoff.md, REVIEW.md and the
   price_events evidence notes. Each area then gets a skeptic. The editors write in the working tree, so after a
   stop, read `git diff` before rerunning an area.
   Finished on 7 Nov. The skeptics found no wrong numbers and 15 small wording or consistency problems, which I fixed
   by hand. All 63 print overrides agree with the new prints. 131 tests pass. The full result is saved as
   `D:\chrono-data\review\phase3_result.json`.
4. Ask the user before one commit with the fixes, the Fortune Brands work and this note, then push. The commit also
   carries `research/brief_check.md` and the brief's changes to PLAN.md, which share that file with the M0 fixes.
   Still open for the user: whether to rewrite git history to remove the prices and headlines already pushed.

Sessions: M0 `local_248fd650-6065-4c89-86f7-d716d41598f7` and spin-off `local_dd0a1d21-67ea-4383-98b7-5ec33e774c5b`,
both idle.
