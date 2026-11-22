# Judge: the M3 dev report's statistics and the switch-day check (23 Nov)

Scope: the uncommitted step 5 code on `claude/m3-kickoff-56264f`. Read: `eval/stats.py`, `eval/switch_day.py`,
`eval/metrics.py`, `replay` and `Simulator.step` in `sim/simulator.py`, the calls in `eval/report.py`,
`tests/test_report.py`, `cutoff.md` 10.2, the kickoff's step 5 and decision 2, and PLAN through
`docs/digests/plan_rules.md` (L330, L345-349, L575-600). No run, store table or `.env` was read. Every number below
is from made-up data, in the scratchpad script `judge_checks.py` (rerun it with the venv's python).

Result: 0 must-change, 3 should-change, 8 nits.

## Should-change

1. **The deflated Sharpe's N can count runs, not trials.** `report.py:161-163`, PLAN L596 and L575. `eval/trials.py`
   logs one row per run, and one `run_many` call holds many agents. If step 6 runs the variants in one call, N is 1
   or 2 while 10 variants were tried, and the bar `sr0` is too low, so the DSR is too high. Also, with N > 1 but one
   Sharpe in `srs`, V is 0 and the DSR silently equals the PSR. Fix: log one ledger row per variant (the kickoff's
   open question), and until then use `max(len(trials), len(srs))` and print a warning when `len(srs) < 2`.
2. **The switch-day years come from the report's first date.** `report.py:188` uses `range(first.year, last.year + 1)`.
   Decision 2 and `switch_day.py:46` say 2017 to 2019. With `first` in 2016 (the runs start on 2016-04-01), 2016's
   October to December days join the pooled "other" mean, though 2016 has no first-20 days with predictions. On made-up
   data this moved the pooled difference from 0.0197 to 0.0220 (check 6). Fix: pass `years=[2017, 2018, 2019]` from
   the settings, or assert `first.year == 2017`.
3. **The frozen-twin replay test has no frozen twin.** `tests/test_report.py:162-171` calls `run_many` without
   `freeze`, and the second part checks only the first date. Fix: run with `freeze=("rev",)` over a year end and
   `assert_frame_equal` each twin's replay at its run cost against its own equity rows.

## Nits

4. Regimes, vol: the high/low line is the median over the whole report period (`metrics.py:211`), so a day's label
   moves when later closes change (check 5). Trend and shock do not. Say so in the report, or use an expanding median.
5. Regimes, shock: the peak starts at the window's first session (`metrics.py:214`), so a window that opens inside a
   drawdown never flags it (check 5b). Fix: seed `peak` with the highest close before the window.
6. Regimes, trend: a NaN prior close with a valid mean gives "down" (`metrics.py:210`). Fix: test `p.isna()` too.
7. Sector tilt is reported for the long-short book only (`report.py:154-157`); PLAN L595 lists tilt for both books.
8. p-values use the normal (`stats.py:72`, `switch_day.py:42`); fine for 754 days, slightly liberal for a 63-day
   quarter. Say so in the report, as the kickoff does.
9. `test_no_switch_effect_gives_no_warning` (`test_report.py:288-293`) gives all three years the same noise, since
   `noise[i]` restarts each year. Draw it per day.
10. The vol test (`test_report.py:241`) checks only labels and NaNs, not the median line.
11. The pooled HAC lag (6) is shorter than a 20-day first-20 block and the 5-session news half-life, so its errors may
    be low. Not a departure from 10.2 or PLAN; worth a line in the report's limits.

## Checked and right

- Newey-West (`stats.py:25-40`): S = sum g g' plus Bartlett weights 1 - k/(L + 1) on Gamma_k + Gamma_k', sandwiched by
  (X'X)^-1, no small-sample factor (the textbook form). It matches an independent double loop to 2e-16 on an AR(1)
  case with 3 regressors (check 1). The lag rule gives 0, 1, 4, 6 for 0, 4, 100, 754 days.
- A difference of means is exactly the slope on a dummy with an intercept (check 2). HAC errors over the pooled days
  in date order are a correct reading of "Newey-West standard errors over the pooled days".
- PSR (`stats.py:109-113`): sqrt(T - 1), 1 - skew SR + (kurt - 1)/4 SR^2 with kurtosis not excess, as in Bailey and
  Lopez de Prado (2012). The expected maximum (`stats.py:116-123`) is their 2014 form with Euler's constant. Daily
  Sharpe ratios are used on both sides, so the units agree. Against Monte Carlo: 1.575 vs 1.539 (N = 10), 2.531 vs
  2.508 (N = 100); 0.520 vs 0.563 at N = 2, the approximation's known weakness at small N (check 3).
- Book statistics: geometric annual return, ddof 1 volatility, Sharpe over zero, drawdown from 1.0. Returns use the
  previous row's equity, so a window starting in 2017 keeps 2016-12-30 as its base. Turnover's pre-trade equity is
  equity + cost, which holds because trades move value between cash and holdings and the exit sale is in `traded`.
- Beta: row k's return is holdings from open k-1 to open k (`Simulator.step` marks at the open, then trades), and
  `spy_open_returns` is adj_open k over adj_open k-1, indexed at k. No one-day shift.
- Sector tilt: net target weight per sector, zero-filled on days a sector is absent, over days with any target.
- `replay` is exact: `step` is deterministic in (day, targets, book); replay walks the run's own equity dates, so a
  twin starts fresh at 1.0 on its join session, as in `run_many`. A None or empty decision is not in `decisions`, and
  `targets.get(day)` gives None, which `step` treats as empty, as the run did. Opens and labels do not depend on
  `allow_sealed`, so sealed runs replay too.
- Switch day against 10.2, line by line: calendar first 20 per year; effect is live IC minus price-only IC on days
  with both; pooled difference of pooled means; HAC over pooled days; (a) p < 0.05 one-sided; (b) per-year d > 2 se,
  strict, "at least half" as 2 x count >= years counted. The four open readings are reasonable. On "its standard
  errors": the literal subject is the first-20 mean, but on iid noise the difference's HAC error and the first-20
  mean's error differ by under 1% (median ratio 0.999, check 7), so the reading does not matter.
- Coefficient life and twin gaps start on 1 January after the snapshot; quarters count from 1. No look-ahead.
- Hand-worked tests: NW mean (S 6.25, se 0.625), dummy fit (V entries), lag rule, PSR 0.840742, moments (kurtosis
  1.64), rank IC -0.5, quarters, twin gaps, sector tilt, seed spread (sd 0.2/sqrt 3) and the regimes' shock path all
  recompute by hand to the values asserted.
