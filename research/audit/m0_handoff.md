# M0 handoff (31 Oct 2026)

**Done.** A later session on 31 Oct 2026 finished all seven next steps below. The answers to PLAN.md 9.3 are in
[audit.md](audit.md); this note stays as the record of the first session's work and findings.

Where the M0 data audit stands, so the next session can pick it up without the conversation. Nothing below is
committed yet; the last commit is `4d5bb0d` on `master` (pushed to the private GitHub repo).

## Done this session (uncommitted)

- **Membership to today.** `data_pipeline/wikipedia.py` (new) fetches and parses Wikipedia's S&P 500 list, its
  change log and one revision per month since 2015 (cached in `D:\chrono-data\membership\wikipedia\`, 142
  revisions). `python -m data_pipeline.membership` extends fja05680 (which stops at 2026-08-18) with the change log
  and Alpaca renames, writes `components_extended.csv`, and reports in `research/audit/membership.md`. The final
  list matches Wikipedia's 503 exactly.
- **Identity builder.** `data_pipeline/identity.py` resolves every membership spell to a CIK revision by revision,
  groups CIKs into companies (a reorganisation joins; a ticker that passes to another company splits), places
  boundaries, adds missing members, builds ticker timelines and checks overlaps. Outputs: `reference/entities.csv`,
  `reference/identity.csv`, `reference/memberships.csv`, `research/audit/identity.md`. `SymbolIndex` maps news
  tags to companies by date (BRK/B and plain BRK to Berkshire, META in 2021 to nobody, DOC in 2023 to nobody).
- **Hand-checked corrections:** `reference/identity_fixes.csv` (written, not yet applied by a run). Every row has its
  evidence; rows marked "Unchecked" or "from memory" still need a source.
- **Prices.** `data_pipeline/bars.py` now downloads from the identity table (`D:\chrono-data\bars\plan.csv` says which
  file serves which member days); `data_pipeline/prices.py` (new) stitches bars per company;
  `data_pipeline/audit_prices.py` is rewritten per company (survivorship, shared histories, zero volume, large moves
  with official prints, adjustment events, trading days, one-class-per-company picking preview).
  `data_pipeline/audit_news.py` now counts companies for the single-firm filter and coverage.
- **Tools:** `research/identity_evidence.py` (local evidence: wiki, cik, changes, members, renames, tags, news, grep,
  bars, prices, alpaca) and `research/verify_prints.py` (official auction prints). Results of the print check:
  `D:\chrono-data\audit\official_prints.csv` (raw prices, so not in git). Scratch scripts copied to
  `D:\chrono-data\audit\scripts\`.
- **Price corrections:** `reference/price_events.csv` (Nordstrom 2018-03-26 rebuilt from clean trades; Biogen halts).
- **Tests:** `tests/test_identity.py` (pytest 9.2.0 installed in the venv; add it to `requirements.txt`). On the draft
  tables 38 pass; the 4 failures are the cases the fixes resolve.

## Findings to record in PLAN.md

- The membership file labels early periods with later tickers (about 25 pairs: YHOO as AABA, PCLN as BKNG, TSO as
  ANDV and more), joins two companies that shared a ticker into one spell (IR: Trane then the former Gardner Denver;
  CB: Chubb Corp then ACE; JCI: Johnson Controls then Tyco; AGN; FOX/FOXA; FTI), and leaves out ACE (2015), Tyco
  (2015-2016) and Actavis (early 2015). For 2018-2020 the old pipeline used Gardner Denver's prices for Ingersoll-Rand.
- Wikipedia's CIK column lags events by months or years (Fox 18 months, Medtronic 4 years) and has a few plain errors.
- Alpaca's adjusted prices get some spin-offs badly wrong, applying the distribution ratio as a split multiplier:
  WestRock 2016-05-16 (-84.5% adjusted, about +3.6% true), TEGNA 2017-06-01, Aptiv 2017-12-05, Arconic/Howmet
  2020-04-01, Raytheon Technologies 2020-04-03, Aimco 2020; Under Armour's 2016-04-08 class C dividend is not adjusted
  at all. Check Xerox 2017-01-03, DuPont 2019-06-03, 3M 2024-04-01, Honeywell 2026-06-29, Fortive 2025-06-30.
- Alpaca's daily close matches the official closing auction (300 random days: p99 0.06%); its daily open is the day's
  first trade, within 0.6% of the official open at p99 but far off on chaotic days: 2023-01-24 (the NYSE opening
  glitch: LLY, MA, MS, XOM, ZTS and others 5-18% off), March 2020, 2020-11-09. A few closes are wrong (HLT 2020-03-18
  48.22 vs official 56.68; MRO 2020-03-09; CHK 2016-02-08; PXD 2020-03-09).
- Moderna 2026-08-19 (+177%) is real (cancer vaccine Phase 3 results, 199M shares).
- Zero-volume bars on member days are halts or days after a last trade (Biogen's two FDA-panel halts are confirmed by
  headlines).
- The plan's price-audit row is stale: 267 large moves and 14 reversals, not 134 and 8 (the old run missed current
  members because file names depended on the run date).
- Alpaca filters the corporate-actions name changes by processing date; CBS to VIAC shows 2020-02-13 though VIAC
  started 2019-12-05.

## Next steps, in order

1. Share-class chains: give each ticker row a class chain (explicit `rows` fixes carry `share_class`), and make
   `bars.plan()` pick the chain that holds a membership spell's ticker, so Under Armour, Discovery, Alphabet, Fox and
   News Corp each fetch the right class.
2. `python -m data_pipeline.identity`; read the open items in `research/audit/identity.md`; `python -m pytest tests`.
3. `python -m data_pipeline.bars` (about 63 new fetches), then `python -m data_pipeline.audit_prices` and
   `python -m data_pipeline.audit_news`.
4. Re-check the conflicting official prints by print size (the largest print is the listing exchange's auction), then
   add verified open/close overrides to `reference/price_events.csv` (start with 2023-01-24).
5. Spin-off corrections: for each event above, the distribution terms, the spun-off company's close
   (`identity_evidence.py alpaca`) and the true total return, into `reference/price_events.csv`.
6. Verify the rows marked "Unchecked" in `reference/identity_fixes.csv` (a small web check, or one workflow with
   few agents; the first attempt with nine agents hit the session limit and returned nothing).
7. `split.json` (dev/sealed split by counts only), `research/audit/audit.md` answering each question in PLAN 9.3,
   PLAN.md and README updates, then ask before committing and pushing.
