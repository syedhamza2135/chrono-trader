# M0 data audit: answers

The answer to each question in PLAN.md section 9.3, as of 31 Oct 2026. The detail is in the generated reports:
[membership.md](membership.md), [identity.md](identity.md), [prices.md](prices.md) and [news.md](news.md). The
hand-checked tables are in `reference/`, each row with its evidence. Every number below comes from those reports or
from a command named next to it.

## News

| Question | Answer |
|---|---|
| Is news on the free plan, and at what rate limit? | Yes, at 200 requests a minute (`research/alpaca_check.py`, `research/alpaca_news_probe.py`). The full download took about 4.5 hours |
| Stories per S&P 500 member per year, 2015 to 2026. Does 2016 work as the warm-up? | Yes. Benzinga stories a year run from 107,848 (2017) to 261,736 (2024). Single-firm stories naming a member company: 33,296 in 2016, 23,843 in 2017, then rising to 65,553 in 2023 (table below). The median picked stock has 177 single-firm stories on 96 days in 2016, and the thinnest pick, Berkshire Hathaway, has 48 |
| Share of stories with a summary or content, by year | Not measured by year. The full download keeps headlines and metadata only (`include_content=false`), because the reader reads headlines. The samples showed an empty summary on every 2015 to 2020 story sampled, a summary on 186 of 306 stories in Sep 2026, and content on 34% to 76% of stories depending on the sample |
| How are symbols per story distributed? (sets the single-firm filter) | Each year, 80% to 88% of Benzinga stories name 1 or 2 companies once each tag is mapped to a company on the story's date, and 2% to 10% carry no symbol. The filter keeps stories naming at most 2 companies |
| Do session recaps land in their New York windows? | 12,231 recap headlines checked: 11,841 inside their window, 385 late, 5 early. Four of the early ones fit the session on the day they were stamped and name the next weekday, so they're typos. One, a mid-day list stamped 08:03 on 2018-07-13, is unexplained. A late stamp only delays a story |
| Gap between `created_at` and `updated_at` | Edited more than 15 minutes after publishing: 0.0% to 2.5% of stories a year. More than 3 days: at most 0.5% in any year (2021). Availability uses `updated_at` plus the 15-minute delay, so a late edit only delays a story |

Single-firm stories per year (`research/audit/news_reading_load.csv`):

| Year | About member companies | About that year's 50 picked companies | Median per picked company | Fewest (company) |
|---|---|---|---|---|
| 2016 | 33,296 | 11,788 | 177 | 48 (BRK.B) |
| 2017 | 23,843 | 8,209 | 124 | 28 (SLB) |
| 2018 | 26,899 | 8,548 | 133 | 35 (CHTR) |
| 2019 | 28,262 | 9,560 | 121 | 40 (PG) |
| 2020 | 36,108 | 10,957 | 146 | 58 (BRK.B) |
| 2021 | 47,382 | 18,223 | 222 | 52 (BRK.B) |
| 2022 | 58,105 | 21,584 | 278 | 84 (BRK.B) |
| 2023 | 65,553 | 22,547 | 292 | 109 (BRK.B) |
| 2024 | 64,943 | 21,754 | 319 | 113 (KO) |
| 2025 | 63,375 | 21,346 | 271 | 126 (PG) |
| 2026 (to 29 Oct) | 52,974 | 17,794 | 247 | 77 (PG) |

Reading load: 500,740 headlines about member companies, about 21 hours on the laptop's CPU and 1.5 GB of embeddings;
172,310 about picked companies, about 7 hours.

## Prices

| Question | Answer |
|---|---|
| Survivorship: does every member have bars around each January? | Yes. Every member company has bars on every picking date, 2016-04-01 and the first trading day of each year from 2017 to 2026. Across all 1,371,715 company member days, 68 sessions have no bar: 66 come after a company's last trade (an acquisition closes a few days before the index removal), and 2 before Amcor's first NYSE trade (2019-06-07 and 2019-06-10). The gaps the first audit found (10 names in 2016) were labelling problems that the identity table fixes |
| Identity: every rename and reused ticker among companies that ever rank in the top 50 | 93 companies rank in the top 50 at least once. Renames: UTX to RTX (2020-04-03), PCLN to BKNG (2018-02-27), FB to META (2022-06-09), ACT to AGN (Actavis became Allergan plc, 2015-06-15), DWDP to DD (2019-06-03). Two share classes: Alphabet (GOOGL class A, GOOG class C) and Comcast (CMCSA, and CMCSK until 2015-12-13). Reused tickers: AGN (Allergan Inc until 2015-03-22, then Allergan plc from 2015-06-15) and DD (E.I. du Pont until 2017-08-31, then DuPont de Nemours from 2019-06-03). In the news only, META meant Roundhill's Metaverse ETF from 2021-06-30 until Facebook took it in June 2022 |
| Corporate actions: raw to adjusted ratios, and every one-day move above 25% in a big stock | 150 member days where the adjusted and raw moves differ by more than 4%: splits, special dividends and spin-offs. 265 adjusted moves above 25% on member days, 14 of them reversed by more than 20% the next day. In the picked stocks' own years there are 10 such moves (Salesforce 2020-08-26, Meta 2022-02-03, Twitter 2022-04-04, Netflix 2022-04-20, Palo Alto Networks 2024-02-21, Intel 2024-08-02, Oracle 2025-09-10, Supermicro 2026-03-20 and 2026-06-10, Palantir 2026-08-04), and all ten match the exchanges' official auction prints. Errors found and corrected are listed below |
| Blended histories: identical return series | No two companies share 20 or more identical member-day bars. But Alpaca's own files splice securities that used one symbol at different times, so each ticker is used only inside the dates the identity table gives it (below) |
| Is the S&P 500 list complete up to 2026? | Yes. The fja05680 file stops at 2026-08-18; Wikipedia's change log extends it, and the result ends with the 503 members on Wikipedia's list today ([membership.md](membership.md)). Company by company, no member is missing against Wikipedia's monthly lists, and none is extra ([identity.md](identity.md)) |

### What the identity table fixed

The membership file labels early periods with later tickers (Yahoo as AABA, Priceline as BKNG), joins companies that
shared a ticker (Chubb Corp then ACE as CB; Trane then the former Gardner Denver as IR; Johnson Controls then Tyco as
JCI), and leaves out ACE (2015), Tyco (2015 to 2016) and Actavis (early 2015). It also lists Michael Kors twice
(KORS and CPRI, 2016 to 2018) and Coca-Cola Enterprises twice (CCE and CCEP), makes Trane's rename and the Cimarex
removal a day late (Trane drops out for 2020-03-02), and keeps Four Corners Property Trust for a week when S&P added
it for one day. Wikipedia's CIK column lags events by months or years.

`reference/identity.csv` covers 744 companies with 807 ticker rows, each dated exactly or by a membership day, and
seven companies listing two share classes. `reference/identity_fixes.csv` holds the 86 hand-checked corrections, each
with its evidence: renames dated by filings or by Alpaca's as-of lookups, share classes, CIKs, boundaries, and
membership dates. Every row the last session marked unchecked or from memory now has a source; the check moved
IQV's start from 2017-11-14 to 2017-11-15. `python -m pytest tests` passes (53 tests).

### Alpaca's histories follow a symbol

A history fetched with `asof` can splice in another security under the same symbol. The FOXA file is 21st Century Fox
until 2019-03-18 and Fox Corporation after. Under Armour's UA file is class A until 2016-12-06 and class C after,
because the classes swapped tickers. ARNC continues into the 2020 Arconic spin-off, DLPH into Delphi Technologies, P
into a 2026 company. XL Group's 2016 move from Ireland to Bermuda is two securities to Alpaca, so the table gives XL two
rows. The download plan therefore fetches each ticker as of a date inside its own row and uses only that row's days.
A company changes rows 53 times while a member; at 9 of them the new file has another security's bar, or none, for the
previous session, so the audit stitches that day's return from the previous row's close.

### Price corrections (`reference/price_events.csv`)

116 rows, each with its evidence:

- **Opens on chaotic days (54).** Alpaca's daily open is the day's first trade on any exchange. A market-on-open
  order fills in the listing exchange's opening auction, which can come minutes later at a very different price. The
  re-check took the largest opening print as the listing exchange's auction. On 2023-01-24, the NYSE opening glitch,
  it opened 15 stocks between 09:35 and 09:45, 8% to 15% away from Alpaca's opens (LLY 340.00 against 384.44). Most
  of the rest are March 2020 and 2020-11-09.
- **Closes (5).** CHK 2016-02-08, MRO and PXD 2020-03-09, LYV 2020-03-12 and HLT 2020-03-18 close at the official
  closing auction, not at Alpaca's close. Nordstrom on 2018-03-26 is rebuilt from clean trades.
- **Distributions (37).** `adjustment_events.csv` holds 77 splits and 73 distributions (spin-offs, special
  dividends, one warrant dividend), and all 73 are checked against the true total return on the ex-date: the terms
  from the company's filing or press release, and the closing price of every piece. Alpaca's adjusted return is off
  by more than 1 percentage point at 31 of them, by 1.1 to 88 points. WestRock, TEGNA, Aptiv and RTX get the ratio
  applied as a split (WestRock: -84.5% adjusted against +3.6% true). Western Digital's Sandisk spin-off is adjusted
  to +4.7% against -5.1% true, and TransDigm's 2025 special dividend as if $174 a share were paid instead of $90. GE's
  2019 Wabtec distribution is applied on 2019-02-25, a day before GE went ex, so both days get a row. Xerox, DuPont,
  3M, Fortive (2020 and 2025), Honeywell (2026), Trane, Aimco, Danaher (2016 and 2023), Air Products, Dover,
  DowDuPont, NortonLifeLock, SL Green, DTE, Labcorp, BorgWarner, BD, Aptiv (2026), FedEx and Skydance are adjusted,
  but by the wrong amount. Gardner Denver's history is adjusted for Ingersoll-Rand's distribution although its holders
  received nothing. Under Armour's class C dividend isn't adjusted at all, and four more distributions happen where a
  company changes rows (Alcoa to Arconic, Tyco to Johnson Controls, Arconic to Howmet, L Brands to Bath & Body Works).
  Every close behind the 19 rows added on 31 Oct matches the listing exchange's closing auction print.
- **Distributions Alpaca never applies (17).** `adjustment_events.csv` lists only days where the adjusted and raw moves
  differ, so a distribution Alpaca leaves out never shows there. Alpaca's own spin-off records (from 2019), Benzinga
  headlines about completed spin-offs, the S&P 500 change log and Alpaca's dividend records turned up 15 on member days
  with no adjustment at all, every one more than 1 point off: the spin-offs of Starwood (Vistana into ILG, 2016),
  Johnson Controls (Adient), Yum (Yum China: -29.7% left as a real loss against +0.7% true), Citrix (LogMeIn), Biogen
  (Bioverativ), Pentair (nVent: -33.4% against +0.4%), Pfizer (Viatris), Merck (Organon), International Paper
  (Sylvamo), IBM (Kyndryl), Realty Income (Orion), Zimmer Biomet (ZimVie), BD (Embecta, 2022) and Corteva (Vylor:
  -83.8% against +4.1%), and Occidental's 2020 warrant dividend. Aimco's 2019 special dividend in cash and stock gets
  only its offsetting reverse split (-2.2% adjusted against +1.8% true). Of the 17,461 dividends Alpaca records on
  member days, its adjusted bars match the record within 1 point at all but Occidental's on 2020-03-09, the day the
  stock halved. Honeywell's Garrett and Resideo spin-offs (2018) and Jacobs' 2025 dividend of its last Amentum shares
  are within 1 point. Occidental's warrants had no price on the ex-date, so they are valued at their first close, an
  estimate, and Starwood's ex-date comes from the prices. Every close behind these 17 rows matches the listing
  exchange's closing auction print.
- **Halts (2).** Biogen's two FDA-panel halts, zero-volume days that the simulator must not trade.

The other 42 distributions in `adjustment_events.csv` are within 1 point of the true total return and need no row:
the spin-offs from HCP, Conagra, Varian, HPE (twice in 2017), Vornado, MetLife, DXC, Henry Schein, FMC, VF, Exelon,
AT&T, GE (2023 and 2024), Kellogg, Jacobs, Lennar, Honeywell (2025), DuPont (2025), Comcast and S&P Global; the
special dividends of Symantec, Equity Residential (twice), TransDigm (five, 2016 to 2024), Costco, Franklin,
TripAdvisor, LyondellBasell, Public Storage, Ford, Arch Capital and Progressive (twice); and regular dividends of
Frontier, Macy's and Helmerich & Payne that topped 4% of a fallen price. Lennar's check is approximate: Millrose had no
price on Lennar's ex-date (2025-01-21; when-issued trading began on 2025-02-05), but any value between Millrose's
first regular-way open and close leaves Alpaca within 1 point. The terms, sources and closes are in
`D:\chrono-data\audit\distributions\` (prices, so kept out of git): `checked.csv` for the 60 checked on 31 Oct and
`unadjusted_results.csv` for the distributions Alpaca never applies.

The official prints were checked on 784 days: the large moves, screens for suspicious opens and closes, and 300
random days. Opens on chaotic days outside that sample are not checked.

## The split

`reference/split.json` (`python -m data_pipeline.split 2026-10-28`) confirms PLAN.md 5.5 with counts only; nothing
in it reads a price or a return.

| Period | Dates | Sessions | Company member days | Picked stock-days | Single-firm stories about members | About picked companies |
|---|---|---|---|---|---|---|
| Warm-up | 2016-01-04 to 2016-12-30 (picks on 2016-04-01) | 252 | 125,987 | 9,550 | 33,296 | 11,788 |
| Dev | 2017-01-03 to 2019-12-31 | 754 | 376,971 | 37,700 | 79,004 | 26,317 |
| Sealed | 2020-01-02 to the last trading day before the seal (data now runs to 2026-10-28) | 1,715 | 857,510 | 85,750 | 388,440 | 134,205 |

## Not done, and known limits

- The search for distributions Alpaca never applies rests on Alpaca's spin-off records (which start in 2019 and miss
  some, Kyndryl and Organon among them), Benzinga headlines, the S&P 500 change log and Alpaca's dividend records, so a
  distribution none of them names can still be missing. The dividend check compares Alpaca's adjusted bars with
  Alpaca's own dividend records, so a dividend recorded on the wrong date, or not recorded at all, isn't caught.
- Fortune Brands has no bar on 2022-12-15 and 2022-12-16, its last member days and the MasterBrand spin-off's first:
  its ticker changed from FBHS to FBIN on 2022-12-15 (Alpaca's name-change record), and the identity table has no FBIN
  row, so the audit counts the two days as coming after a last trade.
- Bars from the first download end on 2026-10-28; the 82 files fetched on 31 Oct (41 tickers, raw and adjusted) run
  to 2026-10-30.
- News summaries and content were not measured by year (headlines only).
- The re-check of official prints covers 68 of the 69 days that failed the first pass (the 69th, ARNC on 2020-04-01,
  is Howmet's HWM in the new tables). The 715 that matched were judged by the first and last print, not the largest.
