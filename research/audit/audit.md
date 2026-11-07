# M0 data audit: answers

The answer to each question in PLAN.md section 9.3, as of 7 Nov 2026, after the fixes from the M0 review
([m0_review.md](m0_review.md)). The detail is in the generated reports: [membership.md](membership.md),
[identity.md](identity.md), [prices.md](prices.md) and [news.md](news.md). The hand-checked tables are in
`reference/`, each row with its evidence. Every number below comes from those reports or from a command or file named
next to it. Dates are New York dates.

## News

| Question | Answer |
|---|---|
| Is news on the free plan, and at what rate limit? | Yes, at 200 requests a minute (`research/alpaca_check.py`, `research/alpaca_news_probe.py`). The full download took about 4.5 hours |
| Stories per S&P 500 member per year, 2015 to 2026. Does 2016 work as the warm-up? | Yes. Benzinga stories a year run from 107,848 (2017) to 261,738 (2024). Single-firm stories naming a member company: 33,296 in 2016, 23,843 in 2017, then rising to 65,553 in 2023 (table below). Counted from the 2016-04-01 pick, the median picked stock has 125 single-firm stories on 71 days in 2016, and the thinnest pick, Berkshire Hathaway, has 31. That is about the level of 2017 to 2019 (121 to 125 stories, 73 to 78 days) |
| Share of stories with a summary or content, by year | Not measured by year. The full download keeps headlines and metadata only (`include_content=false`), because the reader reads headlines. The samples showed an empty summary on every 2015 to 2020 story sampled, a summary on 186 of 306 stories in Sep 2026, and content on 34% to 76% of stories depending on the sample |
| How are symbols per story distributed? (sets the single-firm filter) | Each year, 80% to 88% of Benzinga stories name 1 or 2 companies once each tag is mapped to a company on the story's date, and 2% to 10% carry no symbol. The filter keeps stories naming at most 2 companies |
| Do session recaps land in their New York windows? | 12,231 recap headlines checked: 11,841 inside their window, 385 late, 5 early. Four of the early ones fit the session on the day they were stamped and name the next weekday, so they're typos. One, a mid-day list stamped 08:03 on 2018-07-13 (story 12016835), is unexplained. A late stamp only delays a story |
| Gap between `created_at` and `updated_at` | Edited more than 15 minutes after publishing: 0.0% to 2.5% of stories a year. More than 3 days: at most 0.5% in any year (2021). Availability uses `updated_at` plus the 15-minute delay, so a late edit only delays a story |

Single-firm stories per New York year (`research/audit/news_reading_load.csv`; the coverage columns are from
[news.md](news.md)). Each year's picked companies count from that year's pick date: 2016-04-01 in 2016, then the
first trading day of the year.

| Year | About member companies | About that year's 50 picked companies | Median per picked company | Fewest (company) |
|---|---|---|---|---|
| 2016 (picks from 1 Apr) | 33,296 | 8,481 | 125 | 31 (BRK.B) |
| 2017 | 23,843 | 8,205 | 124 | 28 (SLB) |
| 2018 | 26,899 | 8,427 | 125 | 35 (CHTR) |
| 2019 | 28,262 | 9,558 | 121 | 40 (PG) |
| 2020 | 36,108 | 10,954 | 146 | 57 (BRK.B) |
| 2021 | 47,382 | 18,216 | 222 | 52 (BRK.B) |
| 2022 | 58,108 | 21,576 | 278 | 84 (BRK.B) |
| 2023 | 65,553 | 22,536 | 292 | 109 (BRK.B) |
| 2024 | 64,943 | 21,746 | 319 | 113 (KO) |
| 2025 | 63,375 | 21,329 | 271 | 126 (PG) |
| 2026 (to 29 Oct) | 52,976 | 17,775 | 246 | 77 (PG) |

Reading load: 500,745 headlines about member companies, about 21 hours on the laptop's CPU and 1.5 GB of embeddings;
168,803 about picked companies, about 7 hours.

## Prices

| Question | Answer |
|---|---|
| Survivorship: does every member have bars around each January? | Yes. Every member company has bars on every picking date, 2016-04-01 and the first trading day of each year from 2017 to 2026. There are 1,360,471 company member days to 2026-10-28 (a company listed with two classes counts once a day), and 64 of them have no bar, all after a company's last trade: 58 where an acquisition closes a few days before the index removal, and 6 where a failed bank's shares stopped trading (SVB Financial from 2023-03-10, First Republic from 2023-05-01). Signature Bank's bars on its last two member days (2023-03-13 and 2023-03-14) are zero-volume fills. `price_events.csv` marks all three banks as failures, so an exit can't use the last close. The gaps the first audit found (10 names in 2016) were labelling problems that the identity table fixes |
| Identity: every rename and reused ticker among companies that ever rank in the top 50 | 93 companies rank in the top 50 at least once. Renames: UTX to RTX (2020-04-03), PCLN to BKNG (2018-02-27), FB to META (2022-06-09), ACT to AGN (Actavis became Allergan plc, 2015-06-15), DWDP to DD (2019-06-03). Two share classes: Alphabet (GOOGL class A, GOOG class C) and Comcast (CMCSA, and CMCSK until 2015-12-13). Reused tickers: AGN (Allergan Inc until 2015-03-22, then Allergan plc from 2015-06-15) and DD (E.I. du Pont until 2017-08-31, then DuPont de Nemours from 2019-06-03). In the news only, META meant Roundhill's Metaverse ETF from 2021-06-30 until Facebook took it in June 2022 |
| Corporate actions: raw to adjusted ratios, and every one-day move above 25% in a big stock | 150 member days where the adjusted and raw moves differ by more than 4%: splits, special dividends and spin-offs. 265 adjusted moves above 25% on member days, 14 of them reversed by more than 20% the next day. In the picked stocks' own years there are 10 such moves (Salesforce 2020-08-26, Meta 2022-02-03, Twitter 2022-04-04, Netflix 2022-04-20, Palo Alto Networks 2024-02-21, Intel 2024-08-02, Oracle 2025-09-10, Supermicro 2026-03-20 and 2026-06-10, Palantir 2026-08-04). Seven match the listing exchange's official auction prints. Twitter, Oracle 2025-09-10 and Supermicro 2026-03-20 miss on the open, by 0.23% to 0.48%, and match on the close: Alpaca's daily open is the day's first trade, not the opening auction (see the print check below). Errors found and corrected are listed below |
| Blended histories: identical return series | No two companies share 20 or more identical member-day bars. But Alpaca's own files splice securities that used one symbol at different times, so member-day returns use each ticker only inside the dates the identity table gives it, and the stock-picking preview ranks each company on its own bars (below) |
| Is the S&P 500 list complete up to 2026? | Yes. The fja05680 file stops at 2026-08-18; Wikipedia's change log extends it, and the result ends with the 503 members on Wikipedia's list today ([membership.md](membership.md)). Company by company, no member is missing against Wikipedia's monthly lists, and none is extra ([identity.md](identity.md)) |

### What the identity table fixed

The membership file labels early periods with later tickers (Yahoo as AABA, Priceline as BKNG), joins companies that
shared a ticker (Chubb Corp then ACE as CB; Trane then the former Gardner Denver as IR; Johnson Controls then Tyco as
JCI), and leaves out ACE (2015), Tyco (2015 to 2016) and Actavis (early 2015). It also lists Michael Kors twice
(KORS and CPRI, 2016 to 2018) and Coca-Cola Enterprises twice (CCE and CCEP), makes Trane's rename and the Cimarex
removal a day late (Trane drops out for 2020-03-02), and keeps Four Corners Property Trust for a week when S&P added
it for one day. It gives Bemis's two S&P 500 sessions (2019-06-07 and 2019-06-10, before the merger with Amcor) to
Amcor, whose first trading day was 2019-06-11. It ends 21st Century Fox a day early: the company was still a member
on 2019-03-19, its last session, trading as TFCFA and TFCF. And it leaves out MasterBrand, a member on 2022-12-15 and
2022-12-16 after its spin-off from Fortune Brands. Wikipedia's CIK column lags events by months or years.

`reference/identity.csv` covers 746 companies with 814 ticker rows, each dated exactly or by a membership day, and
seven companies listing two share classes. Every member day since 2015-01-01 has a ticker row, Four Corners' one day
(2015-11-10) included. `reference/identity_fixes.csv` holds the 97 hand-checked corrections, each with its evidence:
renames, share classes, CIKs, boundaries and membership dates. The evidence for the 35 renames varies. 14 are dated by
a filing (5), Alpaca's as-of lookups (7) or Alpaca's name-change records (2). 9 rest on Benzinga headlines or news
tags, 5 on the membership file's switch date and a Benzinga headline, and 7 on the membership file's switch date alone
(DD, GL, BKR, PEAK, VIAC, TFC and BBWI). Every row the last session marked unchecked or from memory now has a source;
the check moved IQV's start from 2017-11-14 to 2017-11-15. Two hand-written rows end Fortune Brands' FBHS ticker on
2022-12-14 and give it FBIN for its last member days (2022-12-15 and 2022-12-16, after the MasterBrand spin-off),
which Wikipedia's monthly lists never showed.

A news tag for another share class of a member listed under the plain root (LEN.B for Lennar's LEN) maps through its
root only if it is one of the six tags in `CLASS_TAGS` (`data_pipeline/identity.py`): BIO.B, CBS.A, LEN.B, STZ.B,
TAP.A and UA.C. The list is explicit because a foreign class can share a member's root: CCL.A is CCL Industries on the
TSX, not Carnival. A company counts once in a story however many of its class tags the story carries, so FOXA and FOX
on one story are one company. `python -m pytest tests` passes (131 tests).

### Alpaca's histories follow a symbol

A history fetched with `asof` can splice in another security under the same symbol. The FOXA file is 21st Century Fox
until 2019-03-18 and Fox Corporation after. The DWDP file is Dow Chemical's before 2017-09-01. Under Armour's UA file
is class A until 2016-12-06 and class C after, because the classes swapped tickers. ARNC continues into the 2020
Arconic spin-off, DLPH into Delphi Technologies, P into a 2026 company. XL Group's 2016 move from Ireland to Bermuda
is two securities to Alpaca, so the table gives XL two rows. The download plan therefore fetches each ticker as of a
date inside its own row (787 plan rows for 719 companies), and member-day returns use only that row's days.

A company changes rows 56 times while a member; at 11 of them the new file has another security's bar, or none, for
the previous session, so the audit stitches that day's return from the previous row's close. A company's first member
day, or a return after a gap in its membership, has no previous row to stitch from (208 days). At 195 of them the
file's previous bar can't be shown to be the company's own, so that day's return is left undefined, raw and adjusted
alike. That also blanks some genuine first-day returns (SEDG 2021-12-20, IR 2020-03-02). It is kept on purpose: a
wrong return is worse than a missing one.

The stock-picking preview ranks each company on its own bars: its member days under any of its rows, and its file's
other days unless the bar is another security's member bar that day or a zero-volume fill. Incomplete bars are left
out. Before this fix the 2018 preview ranked DowDuPont on Dow Chemical's 2017 bars and left it out. On its own bars it
ranks 40th, and General Motors, 50th before, drops out of the 2018 list (`universe_preview.csv`).

### Incomplete bars (`research/audit/incomplete_bars.csv`)

1,035 member bars hold only part of the day's trades: a trade count below 5% of the median of the file's previous 20
bars (`prices.incomplete`). They fall on four dates: 2018-03-26 (1, Kellogg), 2021-04-19 (356), 2021-10-25 (326) and
2022-03-08 (352), in the raw and adjusted files alike. 83 of them are in that year's stock-picking preview. Their
volume,
high, low and VWAP aren't the day's, and their open may not be either, so features must treat them as missing.

### Price corrections (`reference/price_events.csv`)

122 rows, each with its evidence:

- **Opens on chaotic days (54).** Alpaca's daily open is the day's first trade on any exchange. A market-on-open
  order fills in the listing exchange's opening auction, which can come minutes later at a very different price.
  Each of these rows replaces Alpaca's open with the listing exchange's opening auction print. On 2023-01-24, the NYSE
  opening glitch, the NYSE opened 15 stocks between 09:35 and 09:46, and Alpaca's opens were 8% to 24% away from those
  prints (Norwegian Cruise Line's the furthest, 24% above). Most of the rest are March 2020 and 2020-11-09. The other
  opens that miss the auction are not corrected one at a time (see the print check below).
- **Closes (7).** CHK 2016-02-08, MRO and PXD 2020-03-09, LYV 2020-03-12, NTRS 2020-03-13, and HLT and OKE 2020-03-18
  close at the listing exchange's closing auction, not at Alpaca's close. The new print check found OKE and NTRS
  (rows 121 and 122).
- **Nordstrom (1).** Its bar on 2018-03-26 is rebuilt from clean trades.
- **Distributions (37).** `adjustment_events.csv` holds 77 splits and 73 distributions (spin-offs, special
  dividends, one warrant dividend), and all 73 are checked against the true total return on the ex-date: the terms
  from the company's filing or press release, and the closing price of every piece, with these exceptions. Ford's
  2023 terms and Franklin's 2018 record date rest on secondary sources only. Aimco's 2020-11-03 ex-date is inferred
  from the prices, and its stock part is valued at the stated $8.20 without a price check. BD's 2026-02-10 ex-date is
  taken from the prices. And 30 of the 60 rows in `checked.csv` record that their source was found through a search
  result; 28 of those cite the company's own release or an SEC filing, Progressive's 2021-01-07 row cites a Benzinga
  copy of the release, and Ford's cites none. Alpaca's adjusted return is off by more than 1 percentage point at 31 of
  the 73, by 1.1
  to 88 points. WestRock, TEGNA, Aptiv and RTX get the ratio applied as a split (WestRock: -84.5% adjusted against
  +3.6% true). Western Digital's Sandisk spin-off is adjusted to +4.7% against -5.1% true, and TransDigm's 2025
  special dividend as if $174 a share were paid instead of $90. GE's 2019 Wabtec distribution is applied on
  2019-02-25, a day before GE went ex, so both days get a row. Xerox, DuPont, 3M, Fortive (2020 and 2025), Honeywell
  (2026), Trane, Aimco, Danaher (2016 and 2023), Air Products, Dover, DowDuPont, NortonLifeLock, SL Green, DTE,
  Labcorp, BorgWarner, BD, Aptiv (2026), FedEx and Skydance are adjusted, but by the wrong amount. Gardner Denver's
  history is adjusted for Ingersoll-Rand's distribution although its holders received nothing. Under Armour's class C
  dividend isn't adjusted at all, and four more distributions happen where a company changes rows (Alcoa to Arconic,
  Tyco to Johnson Controls, Arconic to Howmet, L Brands to Bath & Body Works). Every close behind the 19 rows added on
  31 Oct matches the listing exchange's closing auction print in the new print check.
- **Distributions Alpaca never applies (18).** `adjustment_events.csv` lists only days where the adjusted and raw moves
  differ, so a distribution Alpaca leaves out never shows there. Alpaca's own spin-off records (from 2019), Benzinga
  headlines about completed spin-offs, the S&P 500 change log and Alpaca's dividend records turned up 16 on member days
  with no adjustment at all, every one more than 1 point off: the spin-offs of Starwood (Vistana into ILG, 2016),
  Johnson Controls (Adient), Yum (Yum China: -29.7% left as a real loss against +0.7% true), Citrix (LogMeIn), Biogen
  (Bioverativ), Pentair (nVent: -33.4% against +0.4%), Pfizer (Viatris), Merck (Organon), International Paper
  (Sylvamo), IBM (Kyndryl), Realty Income (Orion), Zimmer Biomet (ZimVie), BD (Embecta, 2022), Fortune Brands
  (MasterBrand) and Corteva (Vylor: -83.8% against +4.1%), and Occidental's 2020 warrant dividend. Aimco's 2019
  special dividend in cash and stock gets only its offsetting reverse split (-2.2% adjusted against +1.8% true). Of
  the 17,461 dividends Alpaca records on member days, its adjusted bars match the record within 1 point at all but
  three: Occidental's on 2020-03-09, the day the stock halved; Aimco's special dividend on 2020-11-03, which Alpaca
  records twice; and NortonLifeLock's on 2020-02-03. Each has a row (116, 79 and 87). Honeywell's Garrett and Resideo
  spin-offs (2018) and Jacobs' 2025 dividend of its last Amentum shares are within 1 point. Occidental's warrants had
  no price on the ex-date, so they are valued at their first close, an estimate, and Starwood's ex-date comes from the
  prices. Every close behind these 18 rows matches the listing exchange's closing auction print in the new print
  check.
- **Halts (2).** Biogen's two FDA-panel halts, zero-volume days that the simulator must not trade.
- **Failures (3).** SVB Financial, First Republic and Signature Bank (rows 118 to 120): their shares stopped trading
  after the banks failed, so an exit can't use the last close.

The other 42 distributions in `adjustment_events.csv` are within 1 point of the true total return and need no row:
the spin-offs from HCP, Conagra, Varian, HPE (twice in 2017), Vornado, MetLife, DXC, Henry Schein, FMC, VF, Exelon,
AT&T, GE (2023 and 2024), Kellogg, Jacobs, Lennar, Honeywell (2025), DuPont (2025), Comcast and S&P Global; the
special dividends of Symantec, Equity Residential (twice), TransDigm (five, 2016 to 2024), Costco, Franklin,
TripAdvisor, LyondellBasell, Public Storage, Ford, Arch Capital and Progressive (twice); and regular dividends of
Frontier, Macy's and Helmerich & Payne that topped 4% of a fallen price. Lennar's check is approximate: Millrose had no
price on Lennar's ex-date (2025-01-21; when-issued trading began on 2025-02-05), but any value between Millrose's
first regular-way open and close leaves Alpaca within 1 point. The checks are in `D:\chrono-data\audit\distributions\`
(prices, so kept out of git). `checked.csv` holds the terms, source and closes of the 60 checked on 31 Oct. For the 18
distributions Alpaca never applies, the terms and sources are in each row's evidence in `price_events.csv`.
`unadjusted_results.csv` holds the calculation, without a source column, for 15 of those 18 (not FBIN 2022-12-15,
AIV 2019-02-21 or OXY 2020-03-09) and for the Garrett, Resideo and Amentum checks. Those three have no
`price_events.csv` row, so their ratios have no recorded source.

### The print check (`research/verify_prints.py`)

The check was redone with a stricter method (run and installed on 4 Nov). For each side it takes the largest auction
print on the
listing exchange (open: trade condition O or Q; close: 6 or M). It looks for the close from 5 seconds before the
calendar's close (13:00 on an early close) to 30 minutes after. A bar matches when it is within the larger of one
cent and 0.2% of that print, and a side with no print found is not judged. The first check took the largest print on
any exchange, assumed a 16:00 close (so it missed early closes at 13:00), and passed gaps of up to 2%.

It covers 787 stock-days on 436 dates (`D:\chrono-data\audit\official_prints.csv`; the 31 Oct file is kept as
`official_prints_2026-10-31.csv`): the large moves, screens for suspicious opens and closes, and 300 random member
days. 522 match, 255 miss on the open only, 4 on the close only and 4 on both. Two (LLTC 2016-07-26 and RCL 2020-03-13)
match on
the open and have no closing print. Of the 723 stock-days the first check passed, 198 now miss the open and 2 the
close (OKE 2020-03-18, Alpaca's close 1.95% below the auction, and NTRS 2020-03-13, 0.34% above). The distribution
checks, rerun the same way (`distributions/prints*_v2.csv`, 125 stock-days; the old `prints*.csv` stay), find every
close at the listing exchange's closing auction and 38 opens off. The distribution rows use closes only. All 62 print
overrides in `price_events.csv` agree with the new check's prints.

- **Closes.** All 8 close misses have a row: the 7 closes above and Nordstrom's bar.
- **Opens.** 259 stock-days miss the open, by a median 0.64%. 55 of them have a row (the 54 opens and Nordstrom's
  bar) and 204 don't. On the 300 random days, 23 miss the open.

prices.md now shows 141 of the 265 large moves failing the print check, where the first check failed 31 of the 262 it
judged. 138 of them
fail on the open, 80 of those by less than 1% (median 0.84%). Only 6 fail on the close, and all 6 have a row. The new
failures come from the stricter check: Alpaca's daily open is the day's first trade on any exchange, which the 2%
tolerance let pass. On a day with a big move the first trade lands away from the opening auction more often: 138 of
the 265 large moves miss the open, against 23 of the 300 random days.

The owner's decision of 4 Nov: Alpaca's daily open is the first trade, not the opening auction, so the open misses are
not corrected one at a time. M1 fetches the official opening auction for every stock-day the simulator trades. The
two close misses got overrides (rows 121 and 122).

## The split

`reference/split.json` (`python -m data_pipeline.split 2026-10-28`) confirms PLAN.md 5.5 with counts only; nothing
in it reads a price or a return. It no longer counts stories about the picked companies, because the picks are ranked
on price times volume (`news_reading_load.csv` has those counts by year). Stories are counted by New York date from
each period's first session to its last, from `research/audit/news_by_day.csv`.

| Period | Dates | Sessions | Company member days | Picked stock-days | Benzinga stories | Single-firm stories about members |
|---|---|---|---|---|---|---|
| Warm-up | 2016-01-04 to 2016-12-30 (picks on 2016-04-01) | 252 | 125,987 | 9,550 | 139,239 | 33,291 |
| Dev | 2017-01-03 to 2019-12-31 | 754 | 376,972 | 37,700 | 354,552 | 79,000 |
| Sealed | 2020-01-02 to the last trading day before the seal (data now runs to 2026-10-28) | 1,715 | 857,512 | 85,750 | 1,609,374 | 387,796 |

## Not done, and known limits

- The search for distributions Alpaca never applies rests on Alpaca's spin-off records (which start in 2019 and miss
  some, Kyndryl and Organon among them), Benzinga headlines, the S&P 500 change log and Alpaca's dividend records, so a
  distribution none of them names can still be missing. The dividend check compares Alpaca's adjusted bars with
  Alpaca's own dividend records, so a dividend recorded on the wrong date, or not recorded at all, isn't caught.
- Bars from the first download end on 2026-10-28. The 86 files fetched on 31 Oct (43 tickers, raw and adjusted,
  FBHS and FBIN among them) run to 2026-10-30 where the security still trades. Of the 8 fetched on 4 Nov (BMS, TFCFA,
  TFCF and MBC), MBC's run to
  2026-10-30 and the others end with their securities.
- News summaries and content were not measured by year (headlines only).
- Alpaca's open is the day's first trade. Outside the 54 corrected opens, it stands until M1 fetches the official
  opening auction; it missed the auction on 23 of the 300 random days checked.
- The print check can't see a bar that blends two securities when each side matches its own print. ARNC on
  2020-04-01 matches both NYSE prints, but its open is at the old Arconic's level and its close at the new company's.
  The tables use Howmet's HWM file from that day.
