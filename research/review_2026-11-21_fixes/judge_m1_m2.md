# Judge: the M-1 and M-2 fixes (review of 21 Nov 2026)

The question: are the M-1 and M-2 fixes correct and complete for what they claim, and do they add a new defect or
leak? Read: the diff of the eight files, `research/ex_date_opens.py`, the fixes note (sections "The store is not
rebuilt" and "Medium"), the review's M-1 and M-2, `store.apply_events` and `store.labels`, the `total_return` rows of
`reference/price_events.csv`, and `world/rules.py` `label`. No repo file was changed. The scripts are in
`research/review_2026-11-21_fixes/judge_scripts/`.

The short answer: M-2's fix is right in its arithmetic and its data, with three low points. M-1's fix catches the
review's five snippets, but the twin of a trick already on the list still gets past it.

## Findings

**J-1 (medium). The name check can still be passed by `pd.__dict__` and by strings run as code.**
- Where: `tests/test_boundaries.py:67` (the `forbidden` helper exempts `__dict__`) and `FORBIDDEN` at line 24.
- Evidence: `vars` is forbidden because `vars(pd)['read_parquet']` got past the first review. `pd.__dict__['read_' +
  'parquet'](path)` does the same thing and passes both checks, because `__dict__` is exempt and strings are not
  names. Two more pass because the code is in a string: `DataFrame.query('a > @pd.read_csv(@p)...',
  engine='python')`, and a function with a string annotation read back by `typing.get_type_hints` (both `pandas`
  and `typing` are allowed libraries). Each of the three reads a made-up file when run.
- Check: `judge_scripts/m1_bypass.py` puts each snippet through `agent_import_problems` and `agent_name_problems`
  (the five review snippets: CAUGHT; these three: PASSES), then runs the three on a temp file.
- PLAN: L210, L426, L609 (digest 133, 253, 385): agents import nothing but `world.view`.
- Fix: drop `__dict__` from the exemptions and add `query`, `get_type_hints`, `ForwardRef`, `_evaluate` and
  `singledispatch` to `FORBIDDEN` (no file in `agent/` uses any of them, by grep); add the three to `LEAKY_AGENT`.
  It stays a name check; only the separate process the docstring names closes the class.

**J-2 (low). `from scipy.sparse import load_npz` passes.**
- Where: `tests/test_boundaries.py:24-30`. `load` is forbidden only as an exact name, and `scipy` is allowed.
- Evidence: `m1_bypass.py`, snippet "scipy.sparse.load_npz": PASSES. It reads `.npz` files. Nothing in the store is
  `.npz` today, but M2's embeddings may be stored as arrays.
- Fix: add the prefix `load_` to `FORBIDDEN_PREFIXES` (no agent file uses it).

**J-3 (low). A label ending on an ex-date is visible before every open it uses has printed.**
- Where: `data_pipeline/store.py:197-204`. `end_open_time` is the parent's open print (`printed[j]`), and
  `world/rules.py:43-54` makes the label visible then. The new last piece also uses the other securities' opens.
- Evidence: on 36 of the 55 rows, another security's official open printed after the parent's. The latest: ARNC on
  2020-04-01, 37.1 minutes after HWM's; then ADNT 2016-10-31 at 12.6, MBC 2022-12-15 at 10.7, DTM 2021-07-01 at 9.6.
  As with L-S5, only a view after 9:30 on the ex-date could see it; the simulator asks only for 9:00 views. So the
  fixes note's "L-S5 is fixed" holds for the close, not for these opens.
- Check: `judge_scripts/m2_recompute.py` (calls Alpaca's auctions endpoint; set `CHRONO_ENV_FILE`).
- Fix: have `research/ex_date_opens.py` write the latest open time it used to a new column, and in `labels` set
  `end_open_time` to the later of that and `printed[j]`.

**J-4 (low, the owner's call). Thin first-day opens now set some labels.**
- Where: `research/ex_date_opens.py:74-81` uses the official open whatever its size and only prints a note.
- Evidence: 15 rows rest on a print under 10,000 shares (the fixes note's count). HWM 2020-04-01 shows the cost:
  `total_return` -0.0704, `open_return` +0.1924, from ARNC's 4,398-share open. That open printed 37.1 minutes after
  HWM's (J-3). The fixes note already flags this.
- Fix: decide a rule for thin opens, for example a size floor below which the row says what it uses instead. Any
  later price moves the label's visible time with it (J-3).

**J-5 (low). `open_return` is frozen against today's store close, with no check that it still matches.**
- Where: `research/ex_date_opens.py:121` divides by the store's previous close; `store.py:134-135` applies the
  number as it stands.
- Evidence: the closes cancel only while `close[j-1]` in the series equals the close the script used. A later
  `override_close` on the day before an ex-date, or a series change, would break that silently. `store.main`
  checks nothing about it, and no test compares stored labels with a rebuild (the fixes note says so).
- Fix: write the previous close used to the csv and have `store.main` assert it equals `close[j-1]`; or store the
  distribution's value at the open and let `labels` divide by `close[j-1]` itself.

**J-6 (info, older than this fix). OXY 2020-07-02 values its warrants at the close of 2020-08-04.**
- Where: `reference/price_events.csv`, the OXY 2020-07-02 row. The row says it is an estimate.
- Evidence: the fixed term 0.125 x 4.78 enters both `total_return` (a bar visible at that day's close) and now
  `open_return` (a label visible on 2020-07-02). The price is from a month later. Not part of M-2; noted only.

## Checked and found right

- **M-2 (a), the formula.** `before` is the log return up to the close before day j, so the label is
  close_i / open_i x (the total return to close_j-1) x (parent open_j + distribution at open) / close_j-1, the
  open-to-open truth. `judge_scripts/m2_label_cases.py` builds made-up frames and compares with the truth to 1e-12:
  a label that crosses a day with no official open and a cash dividend, then ends on a spin-off ex-date; j = i + 1;
  a label that starts on the ex-date; an `at_close` label ending on an ex-date (it keeps the close-based piece,
  right for a sale at the close); a day without a return (no label crosses it). It also reads the csv as
  `store.main` does (`dtype=str`, so a blank `open_return` is NaN and is skipped). All pass.
- **The pos map.** Each of the 55 rows matches exactly one store bar by symbol and date, so `apply_events` and the
  script pick the same bar (`m2_recompute.py` prints no clash).
- **M-2 (b), the script.** All 55 `open_return` values recompute exactly (largest difference 0.0000) from the
  store's parent open and previous close, the same numbers `labels` uses (`bars.parquet` is the series `labels`
  reads), and Alpaca's official opens asof the ex-date. `judge_scripts/m2_terms.py` shows how each term is read:
  46 rows use another security's open and 9 use a fixed amount (AIV twice, NLOK, SLG, TDG, OXY twice, DPS, CCE),
  each a cash amount or the warrant value the row fixes. The two-class row (UA 2016-04-08) values UA.C at its open.
  The "Per old share" rows divide both the parent and the new share by the row's ratio (DD by 3, HON by 2) over the
  pre-split previous close, as their formulas do. TT 2020-03-02 values 0.8824 of the new IR.
- **The 3 blank rows.** JCI 2016-09-06 (0.955 x), IR 2020-03-02 and GE 2019-02-25 have no sum. There the old end
  piece cancels the ex-date close if (1 + ret) equals ratio x close / previous close in the store. The gaps are
  -0.0036, -0.0005 and -0.0013 points, the csv's four-decimal rounding (`judge_scripts/m2_blank_rows.py`).
- **M-2 (c).** Beyond J-3 and J-6, no label uses data after its visible time: the new piece uses the closes up to
  day j-1 and the opens on day j only.
- **M-1.** The five review snippets are caught at the import line. The exemption for `from world.view import View`
  covers only the module's path: the imported names and aliases are still checked (`World` is caught), `import
  world.view` is still caught, and `from ..world.view import View` reaches the same module. No hole there.
- **The simulator.** `traded` now includes the exit sale; it is only reported in `rows`, and no file in `eval/`,
  `sim/`, `agent/` or `world/` reads it. Cost and cash are unchanged: the exit was already charged
  (`sim/simulator.py:78-80`). A failed company's exit adds 0. `allow_sealed` is restored in `finally` (lines
  124-136), including when the agent raises, and a run that started with it True leaves it True.
