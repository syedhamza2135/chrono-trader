# Skeptic: the simulator's accounting and the label rules

This skeptic ran on Opus at high effort. It tried to refute each finding in `judge_sim_labels.md`. No code was
changed. Every store check prints counts, ids, dates and return differences in percentage points, never a price.

How to run (PowerShell, worktree root):
`$env:CHRONO_ENV_FILE = "C:\Users\syedh\dev\chrono-trader\.env"`, then
`D:\venvs\chrono-trader\Scripts\python.exe <script>`.

New scripts, in `research/review_2026-11-21/scripts/skeptic_sim_labels/`:

- `check_m1.py`: a new synthetic spin-off through `store.labels`, then the 58 `total_return` rows against the store,
  with the error measured where the truth is known without a spin-off price.
- `check_l2.py`: the at_close labels on non-member days against the last member day.

I also reran all three judge scripts. They print the same numbers as the judge reports.

| id | verdict | severity (judge) | severity (skeptic) |
|----|---------|------------------|--------------------|
| M1 | CONFIRMED (one side claim is wrong) | medium | medium |
| L1 | PARTLY | low | low |
| L2 | CONFIRMED | low | low |
| L3 | CONFIRMED | low | low |
| L4 | CONFIRMED | low | low |

PLAN line numbers. Near the top, the judge's PLAN lines are one too high, as the digest warns. "Closes cancel" is
PLAN L26, not L27. "Trades only at its official open" is PLAN L25, not L26. The later lines it cites (L221, L229,
L230, L555, L570, L589, L612, L618) say what the judge says.

## M1. On a distribution's ex-date at a label's end, the closes don't cancel

- Verdict: CONFIRMED. One side claim is wrong (see the last point below).
- Reason. On the ex-date j, `ret_j` is the csv's close-based total return, (close_j + D_close) / close_{j-1}. The
  label's end piece is (1 + ret_j) * open_j / close_j (store.py:188). So close_j enters as a sum, not a ratio, and
  doesn't cancel. The piece equals open_j / close_{j-1} * (1 + D_close / close_j). The open-to-open truth is
  open_j / close_{j-1} * (1 + D_open / open_j).
- Does PLAN or price_events.csv intend closes at the ex-date? No. PLAN L26 says the label chains corrected
  close-to-close returns "so the closes cancel and a wrong close can't move a label". store.py:19 says the same.
  The EQT row (csv line 124, 0-based index 122) works out its total return from the two closes. It also notes that
  2018-11-12 is EQT's last member day, "so its label ends here", and that the opening prints agree with the ratio.
  But it stores only the close-based return. Nothing in PLAN or the csv asks for the ex-date's closes at a label's
  end.
- Do the 58 really fall on label end days? Yes, all 58. Every ex-date has an official open, so the label from the
  previous open always ends there, and a label passes through a day only when that day has no open.
- Evidence (`check_m1.py`):
  - Synthetic. Parent and spin-off are each worth 50 at day 1's open, so the truth is 0. With closes 50 and 50, the
    label is +0.00 pp. With 55 and 55 it is +0.00. With 50 and 60 it is +10.00. With 45 and 50 it is +5.56. Only the
    split between the two closes moves the label, which is the effect the judge describes.
  - Store. 58 of the 58 total_return rows match a store bar. The store's `ret` equals the csv value on all 58, and
    all 58 have an official open. 58 open-to-open labels end on an ex-date (58 distinct events). 56 of them start on
    a member day, and 55 ex-date bars are member days. 0 at_close labels end on one.
  - Size where the truth needs no spin-off price. The 7 cash rows (6 special_dividend, 1 dividend) have a fixed D,
    so the truth is (open_j + D) / close_{j-1}. Their errors: DPS 2018-07-10 -6.39 pp (non-member day), AIV
    2020-11-03 -2.09 pp, NLOK 2020-02-03 -1.11 pp, OXY 2020-03-09 +0.73 pp, SLG 2020-12-14 +0.14 pp, AIV 2019-02-21
    -0.01 pp, TDG 2025-09-02 -0.00 pp. 3 of the 7 are over 1 pp, and 2 of those are member days. This assumes the
    special dividends were all cash, which is what their kind says.
  - EQT 2018-11-13. Using the opening value stated in the evidence, the end piece is +3.20 pp above the open-based
    one. The judge's Q9 gives +3.21 pp (piece) and +3.07 pp (whole label). Only this row states an opening value in
    a form the script could parse, so most of the 46 spin-offs are not measured.
  - Distribution share d: under 2% on 6, 2-10% on 15, 10-30% on 25, 30% or more on 12. This matches the judge.
- Severity: medium, kept. The error is on 56 member-start labels out of about 1.37 million, so its effect on P&L is
  tiny. But it breaks a rule stated in PLAN L26 and store.py:19. It also passes the project's own bar: PLAN L481
  corrected every distribution off by more than 1 point, and here at least 3 member events are (NLOK, AIV 2020,
  EQT).
- Side claim refuted. The judge says "the same holds" for distributions that Alpaca's adjusted bars carry. That is
  not the same mechanism. There `ret_j` = close_j / (f * close_{j-1}), so the end piece is open_j / (f *
  close_{j-1}) and close_j cancels. What's left is the accuracy of the vendor's factor, the known PLAN L481 issue
  (42 within 1 point). For cash dividends in this table, the error comes from the day's open-to-close move, not the
  overnight move.
- Leak. I agree there is no leak for 9:00 decisions: day j's close is public before day j+1's 9:00. I did not test a
  view taken between 9:30 and 16:00 on day j (I didn't read world/rules.py). Such a view would show a label that
  depends on day j's close.
- Cited lines checked: store.py:19, 112-133 (128-129), 162-194 (173, 188); PLAN L26, L221, L481, L555;
  price_events.csv line 124 (evidence read with every number masked).

## L1. An exit sale at a last close is left out of `traded`, and its cost is not in the equity used to size trades

- Verdict: PARTLY.
- Confirmed part: `traded`. At simulator.py:76-79 the exit adds `abs(v) * cost` to `cost` and `v` to `cash`, but
  not to `traded`. Rerunning the judge's `check_synthetic.py` prints check 10 with cost 0.000500 and traded
  0.000000. A search finds no code that reads `traded` yet (only tests/test_sim.py:50), so turnover (PLAN L589) is
  not wrong in any output today.
- Part that is not a defect: the sizing. `equity` at line 80 leaves out the exit's cost. But it also leaves out the
  cost of every trade made that day, which is taken off cash at line 104 after sizing (lines 93-104). So the exit is
  handled like any other trade. The cost is still taken off the same day, and equity is never overstated after line
  112. The only effect is that the targets are about 5 bps of the exit's value too large.
- Severity: low, kept. It matters only once M4 reports turnover.
- Cited lines checked: simulator.py:61-114.

## L2. A company still trading when its 14-day window ends is treated as stopped and sold at a close

- Verdict: CONFIRMED.
- Reason. store.py:177 sets `stopped` whenever the series' last traded bar is before `data_end`. The store's window
  keeps only 14 days after membership (PLAN L28), so a series cut by the window counts as stopped. Lines 182-183
  then give it an at_close label, and simulator.py:73-79 sells it at that close.
- Evidence (`check_l2.py`). counts.json gives labels_at_close 222, exits_stopped_trading 103, exits_window_cut 119
  and exits_failed 3. All 119 non-member at_close labels end on the series' last bar, start and end on the same day,
  and start on a non-member day (0 member). Calendar days from the last member day to the end: 14 on 98, 13 on 16,
  11 on 2, 15 on 1, 17 on 2. They bunch at the window's edge, which is what a cut by the window looks like, not a
  company that stopped trading. The judge's script also finds CTVA ending 2026-10-19 on a non-member day.
- Severity: low, kept. Only a holding kept more than about two weeks after removal reaches it.
- Cited lines checked: store.py:175-185; simulator.py:73-79; PLAN L25 to L28.

## L3. A forced sale is decided from whether a later label exists

- Verdict: CONFIRMED.
- Reason. simulator.py:84-88 sells when `_label_from(key, day)` is None. Whether a label exists depends on the next
  official open and on defined returns up to it (store.py:180-187), which are later data. The agent never sees it.
  Only the booked P&L does.
- Evidence (judge's `check_store.py` Q1 and `check_store_more.py` B, rerun). 698 official opens have no label: 503 on
  data_end and 195 with a later open, 0 of them on member days. 188 of the 195 reach the next open within 7
  calendar days.
- Severity: low, kept. No member day is affected today.
- Cited lines checked: simulator.py:52-59, 84-88; store.py:179-187.

## L4. The seal does not limit a second sealed run, and `run` leaves the World open to the sealed years

- Verdict: CONFIRMED.
- Reason. seal.py:43-62 checks the lock, the settings, PREREG, the commit and a clean tree. It keeps no record of
  earlier sealed runs and takes no flag for a second one (PLAN L618). simulator.py:124-125 sets
  `world.allow_sealed = True` and never resets it. A search for `allow_sealed` shows world/world.py:170 checks only
  that attribute, so a later `world.view` on the same object can open sealed dates with no seal check.
- Severity: low, kept. The sealed run is M4 work, and nothing reuses a World after `run` today.
- Cited lines checked: seal.py:1-62; simulator.py:117-135; PLAN L612, L618; `grep allow_sealed` over world/, sim/
  and eval/.
