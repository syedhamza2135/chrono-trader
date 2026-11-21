# Judge: the simulator's accounting and the label rules

This judge ran on Opus at high effort, because Fable hit its monthly spend limit.

Read: sim/simulator.py, sim/seal.py, world/rules.py, data_pipeline/store.py lines 1-60, 60-92 (series) and 93-194
(`apply_events`, `failures`, `labels`) and 222-240 (`main`), the three digests, and row 124 of
reference/price_events.csv (EQT). No code was changed. Store checks print counts, ids, dates and return differences,
never a price.

Check scripts, all in research/review_2026-11-21/scripts/judge_sim_labels/ (run from the worktree root with
`$env:CHRONO_ENV_FILE = "C:\Users\syedh\dev\chrono-trader\.env"` and D:\venvs\chrono-trader\Scripts\python.exe):

- `check_synthetic.py`: `store.labels` and `Simulator` on made-up frames. 12 checks pass; checks 5 and 10 fail on
  purpose (findings M1 and L1).
- `check_store.py`: the store's labels and opens (Q1 to Q10), including a full rebuild of the labels from the stored
  bars and opens.
- `check_store_more.py`: at_close labels by kind, opens with no label, and the size of the 58 corrected distributions.

## Answers in short

1. The daily accounting is right on every case checked: fill and mark at the official open, 5 bps per side on traded
   value, signed values for longs and shorts, compounding through equity, a missing open waits, failed banks lose
   everything (a short gains it), acquisitions sell at the last traded close on the next session. Two small gaps: the
   exit sale is left out of `traded` (L1), and a stock still trading after its 14-day window is sold at a close (L2).
2. The labels follow PLAN's rule (open to next official open, corrected close-to-close in between, last traded close
   at a stop, -1 for the three failures, `end_open_time` the printed time of the end open). One exception: on a
   distribution's ex-date that is a label's end day, the closes do not cancel, so the label carries day j's closing
   prices and is off by up to a few points (M1).
3. Yes. The simulator books exactly the label, at the label's end, for the position set at the label's start. A
   rebuild of all 1,419,403 labels from the stored tables matches every row.
4. No off-by-one found. Every label spans 0, 1 or 2 sessions; the 525 two-session labels match the 525 opens with no
   print; at_close labels are marked and shown on the next session.

One medium, three low.

## M1 (medium). On a distribution's ex-date at a label's end, the closes don't cancel

- Where: data_pipeline/store.py:173 and 188 (the end piece `exp(growth[j] - growth[i]) * oo[j] / close[j]`), with
  store.py:128-129 (`total_return` replaces `ret` on the ex-date). The claim "The closes cancel, so a wrong close
  can't move a label" is at store.py:19.
- Evidence. The end piece is `(1 + ret_j) * open_j / close_j`. Where `ret_j` is a plain price ratio or a split, this
  is the overnight return and close_j cancels (synthetic check 1). Where `ret_j` holds a distribution valued at the
  close, (close_j + D_close) / close_{j-1}, the piece becomes (open_j + D_close * open_j / close_j) / close_{j-1}.
  The open-to-open truth is (open_j + D_open) / close_{j-1}. The gap is the spun-off value's weight times how far the
  spin-off and the parent moved apart between the open and the close of day j.
  - Synthetic check 5: a made-up spin-off worth half the old price; the label is 5.00 points above the truth, and
    it changes when only close_j changes.
  - Store, check_store.py Q9: EQT's label from 2018-11-12 to 2018-11-13 (the Equitrans spin-off, price_events.csv
    row 124, whose evidence gives the opening prints) is 3.07 points above the open-based label.
  - Store, check_store.py Q8 and check_store_more.py C: all 58 `total_return` events fall on the end day of an
    open-to-open label; 55 are member days. The distribution is 10% to 30% of the price on 25 of them and 30% or
    more on 12.
  - The same holds for the distributions Alpaca's adjusted bars carry uncorrected (PLAN L481: 42 within 1 point),
    and for ordinary cash dividends, where the error is the dividend yield times the overnight move, too small to
    matter.
- Leak? The label is visible at 9:30 on day j but depends on day j's closes (public at 16:00). The first 9:00
  decision that sees it is day j+1's, after that close, so no agent decision gets future data. The simulator books
  the wrong amount for those stock-days, and the label the learner trains on is wrong by the same amount.
- PLAN: plan_rules.md L33 (PLAN L27: "chaining corrected close-to-close total returns, so closes cancel"), L139
  (PLAN L221: dividends and splits inside the window are part of the label), L346 (PLAN L555: open-to-open target).
- Fix: give each `total_return` row in price_events.csv an open-based ex-date return as well, (open_j + value of the
  distribution at the open) / close_{j-1}, and use it as the end piece of the label that ends on that day. The
  `ret` used inside a window stays as it is.

## L1 (low). An exit sale at a last close is left out of `traded`, and its cost is not in the equity used to size trades

- Where: sim/simulator.py:76-79 (exit adds to `cost` and `cash`, not to `traded`), 80 (equity before the cost),
  104 (`cash -= cost` after sizing).
- Evidence: synthetic check 10. On the session after an at_close exit, the row shows cost 0.0005 and traded 0.
  Targets that day are sized on equity that still includes the exit's cost.
- PLAN: plan_rules.md L359 (PLAN L570: costs on traded value), L369 (PLAN L589: turnover is reported).
- Fix: add `abs(v)` to `traded` at the exit, and subtract the exit cost from cash before line 80.

## L2 (low). A company still trading when its 14-day window ends is treated as stopped and sold at a close

- Where: data_pipeline/store.py:175-183 (`stopped` is true for any series whose last kept bar is before the data
  end), and sim/simulator.py:73-79, which books such a label as a sale at that close.
- Evidence: check_store_more.py A. Of the 222 at_close labels, 103 end on a member day (companies that stopped
  trading while members) and 119 end on a non-member day, where the series was cut by the store's 14-day window
  (counts.json `exits_window_cut` 119). One of them, CTVA ending 2026-10-19, is in the last 10 sessions. All 119
  start on a non-member day, so the simulator meets them only if it holds a stock more than two weeks after it left
  the index. Inside a series the same situation ends with no label and a forced sale at the open (L3), so the two
  cases are treated differently.
- PLAN: plan_rules.md L29 (PLAN L26: the simulator trades a stock only at its official open), L34 (PLAN L27: a
  company that stops trading exits at its last traded close).
- Fix: set `at_close` only where the company really stopped (no later bar in its raw files, or a
  `stopped_trading` or failure event), and leave window-cut series without a last label, so the simulator sells at
  the last official open inside the window.

## L3 (low). A forced sale is decided from whether a later label exists

- Where: sim/simulator.py:84-88. Whether `_label_from(key, day)` finds a label depends on later data: the next
  official open and a defined return on every day up to it.
- Evidence: check_store.py Q1 and check_store_more.py B. 698 official opens have no label: 503 on the data's last
  day (exempt, line 84) and 195 with a later open, none of them on a member day; 188 of those reach the next open
  within 7 calendar days. Synthetic check 9 shows the sale. The agent never sees this; only the booked P&L can use
  it, and today on no member day.
- PLAN: plan_rules.md L29 (PLAN L26), L144 (PLAN L229: a decision uses only what was public).
- Fix: none needed now. If agents start holding non-members, decide the forced sale from facts known at the open
  (the store window's end date) rather than from the label table.

## L4 (low). The seal does not limit a second sealed run, and `run` leaves the World open to the sealed years

- Where: sim/seal.py:43-61 (no record of an earlier sealed run, no flag), sim/simulator.py:124-125
  (`world.allow_sealed = True` stays on the World after `run` returns).
- Evidence: read of the lines. A later `world.view` on the same object can open sealed dates without a seal check.
- PLAN: plan_rules.md L393 (PLAN L618: one sealed run; a second needs an explicit flag and is logged as another
  trial), L388 (PLAN L612).
- Fix: in M4, record each sealed run in `runs/trials.csv` and refuse a second without a flag; reset
  `allow_sealed` in a `finally` at the end of `run`.

## Checked and found sound

- Fill price: the simulator trades only where `opens.open` is not null (simulator.py:40-42, 91-92), and the labels
  start at the same official opens (store.py:165, 174). Q2: every open-to-open label ends at the next official open
  of the same listing (0 of 1,419,181 differ).
- Labels in the store: the rebuild with `store.labels` from the stored bars and opens matches all 1,419,403 rows
  (end, at_close, label within 1e-9; Q10). `end_open_time` equals the end open's print time on every row (Q3).
- Splits: a split on any day of the window, the end day included, gives the split-adjusted open-to-open return
  exactly (synthetic check 1). Only ratios of adjusted bars are used; raw levels appear only as same-day ratios
  (close_i / open_i, open_j / close_j), as PLAN L231 asks.
- Days with no return: a label never crosses one (store.py:172, 186; synthetic check 3).
- Days with no official open: the label runs to the next one and the holding keeps its value and is not traded
  (synthetic checks 2 and 8). The 525 two-session labels match the 525 opens with no print (Q4). No label spans more
  than 7 calendar days.
- Costs: 5 bps per side on the absolute change in value, both buys and sells, longs and shorts (simulator.py:93-98);
  a one-stock book over four sessions matches a hand ledger (synthetic check 6).
- Position sizing and compounding: targets are weights of equity after marking; equity is cash plus signed values;
  each day's equity row carries the compounded result (simulator.py:80-114).
- Failed banks: exactly three -1 labels, all at_close, ending on the last traded bar: entities 0000719739
  (2023-03-09), 0001288784 (2023-03-10) and 0001132979 (2023-04-28) (Q5). The simulator books them on the next
  session, after the 9:00 decision, a long losing all and a short gaining all (synthetic check 7).
- Acquisitions: all 222 at_close labels end on the series' last traded bar (Q5), and are visible at 9:30 on the
  next session, matching the day the simulator books the sale (rules.py:43-55, simulator.py:73).
- Halts and empty bars: the 2 `no_trade` bars and the 8 zero-volume bars have no official open and start no label
  (Q6, Q7).
- Dates: labels are keyed by New York session dates; the at_close visibility uses the next NYSE session; at 9:00 on
  day k the newest visible label starts on day k-2 (rules.py:43-55, PLAN L230).
- Days outside membership: labels exist there too, and the simulator trades any stock with an official open and a
  label. Membership is the agent's concern, not the simulator's; PLAN sets no simulator rule on it.
