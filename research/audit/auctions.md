# Official auction prints (M1)

Written by `python -m data_pipeline.auctions`. Counts only: the prints themselves are raw market data
and stay in `D:\chrono-data\auctions`.

- Bar files fetched: 787, one per file of the bar plan.
- Stock-days with a bar: 1,877,968. With an auction record on an NYSE session: 1,873,240.
- Auction records on days with no NYSE session, left out: 680, on 1 dates (2024-07-20).
- Member stock-days with a bar (inside a plan row's own dates): 1,371,723. Without an official
  open on the listing exchange: 519 (listed in `research/audit/auctions_missing_opens.csv`).
- Official opens more than an hour after the session's open: 218.

- The print check judged the open on 785 plan stock-days. The auctions agree on 785.
- The print check judged the close on 783 plan stock-days. The auctions agree on 783.
- Print-check stock-days that no plan row serves, so not compared: 2 (ARNC 2020-04-01, ARNC 2020-04-03).
- Disagreements are in `D:\chrono-data\audit\auctions_check.csv`.
