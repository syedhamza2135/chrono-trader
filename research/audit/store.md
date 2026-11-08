# The event store (M1)

Written by `python -m data_pipeline.store`. Counts only: the tables are raw data in `D:\chrono-data\store`.

- Data through 2026-10-28.
- Bars: 1,420,646, of which 1,371,711 on member days and 48,935 on the companies' own days outside membership.
- Member bars without a return (the previous bar isn't the company's own): 717.
- Member bars with an official open: 1,371,192. The simulator doesn't trade a stock on a day without one.
- Labels: 1,419,403. 222 end at a last traded close: 103 where the company stopped trading (an acquisition or a failure), and 119 where the store stops keeping a removed company's bars, 14 days after its removal, while its file trades on. Failed companies: 3, and their 3 exit labels are -1, a total loss.
- The 54 opens that `reference/price_events.csv` overrides, equal to the auctions' official opens: 54 of 54.
- `reference/price_events.csv`, by action and result:
  - total_return: applied, 58
  - override_open: checked against the opens, 54
  - override_close: applied, 7
  - stopped_trading: no bar to fix, 3
  - no_trade: applied, 2
  - override_bar: applied, 1
- Stories (Benzinga, edited at most 3 days after publishing): 2,239,859. Kept by the single-firm filter and naming a company in the identity table: 534,619, in 559,526 (story, company) pairs.
- Membership rows: 799. Identity rows: 814.
