# Benchmarks for the evaluation: SPY and sectors

Written by `python -m data_pipeline.benchmarks` on 2026-11-22. Counts only, no prices.

## SPY

- 2721 sessions, 2016-01-04 to 2026-10-28, from Alpaca's SIP feed, raw and fully adjusted.
- Sessions with no return (the first): 1.

## Sectors

- 142 monthly revisions of Wikipedia's list, 2014-12-29 to 2026-09-25; 70995 (revision, company) rows.
- 839 sector runs for 741 of the 746 companies in `reference/entities.csv`; 89 companies changed sector at least once.
- (Revision, company) pairs left out because one revision showed two sectors: 1.
- Sector names merged across spellings: Communications Services as Communication Services, Telecommunications Services as Telecommunication Services.
- Companies in `entities.csv` with no sector: 5.
- CIKs on Wikipedia with no entity: 0 (companies outside the membership since 2016).
- Sectors seen: Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Information Technology, Materials, Real Estate, Telecommunication Services, Utilities.
