# M3 step 7: the older-vintage rerun (dev years, 23 Nov)

**Outcome: not informative.** The rule's news effect on the dev years is not above zero at one-sided 5%, so by
`research/audit/cutoff.md` section 10.1 the check says nothing. Every number below the outcome is descriptive only,
outside the frozen rule. The check did not pass, and it did not warn.

## What ran

- **The reading.** `python -m reader.embed run-older` read every story again with the vintage a year older than the
  rule's (`reader/vintage.py`, offset 1). It ran detached from 22:57 New York on 22 Nov to 05:58 New York on 23 Nov,
  106 parts in all, into `D:\chrono-data\reader_older`. Its error log holds only the model-loading progress bars.
- **The table.** `python -m reader.embed finish-older` checked every part and wrote `embeddings.parquet` (502,712 rows)
  and its two arrays (502,712 rows of 768).
- **The count check** (`research/m3_older_vintage.py count`, saved as `D:\chrono-data\runs\m3_dev\older_count.json`):
  - rows: 502,712 in the main table and 502,712 in the older one;
  - the same story ids, and the same `available_at` for each;
  - every older row's vintage equals the rule's vintage minus one, by `vintage_for(created_at, 1)`.

  | Vintage | Main table | Older table |
  |---|---|---|
  | 2014 | | 33,251 |
  | 2015 | 33,251 | 23,910 |
  | 2016 | 23,910 | 27,013 |
  | 2017 | 27,013 | 28,807 |
  | 2018 | 28,807 | 36,455 |
  | 2019 | 36,455 | 47,607 |
  | 2020 | 47,607 | 58,380 |
  | 2021 | 58,380 | 65,544 |
  | 2022 | 65,544 | 65,110 |
  | 2023 | 65,110 | 116,635 |
  | 2024 | 116,635 | |

- **The rerun** (`research/m3_older_vintage.py run`). The chosen configuration, T09 `{"band": 15, "hold": 5}`, read
  unchanged from `stage2.json`. It used a World built with `vintage_offset=1` on the older table and ran from
  2016-01-04 to 2019-12-31. That took 12.9 minutes: 817 decision days, 39 fits, no forced sales and no unmarked
  positions. Ledger row `20261123T061536_0f452837` in `runs/trials.csv`, with no trial name, so the trial count stays
  8. Its settings (`runs/settings/0f4528...e7e8.json`) carry `vintage_offset: 1` and `embeddings_store:
  reader_older`. The row is marked dirty because `research/m3_kickoff.md` had an uncommitted edit when it ran. The
  code was commit `001d01c`.
- **The rule** (`research/m3_older_vintage.py result`, saved as `D:\chrono-data\runs\m3_dev\older_result.json`). The
  news effect on a day is the agent's daily rank IC minus the price-only twin's IC that day. The twin comes from the
  comparison pass (`m3_dev/compare/price_only`). IC days run from the start of the dev years to the last day whose
  labels end by 2019-12-31: 753 days. Newey-West, lag 6, one-sided p.

## The numbers

| Series (753 days) | Mean | NW t | One-sided p |
|---|---|---|---|
| IC, the rule's vintage (the T09 run from step 6) | 0.00763 | 1.38 | 0.084 |
| IC, the older vintage | 0.00768 | 1.35 | 0.089 |
| IC, price-only twin | 0.00076 | 0.09 | 0.46 |
| News effect, the rule's vintage | +0.00687 | 0.74 | 0.23 |
| News effect, the older vintage | +0.00692 | 0.73 | 0.23 |
| Daily IC, the rule's run minus the older run | -0.00005 | -0.01 | 0.50 |

- **The gate.** The rule's news effect is +0.00687 with p 0.23. That is not above zero at one-sided 5% (the lead's
  reading of 23 Nov, made after the dev result, recorded in `research/m3_kickoff.md` step 7). So the check says
  nothing: not informative.
- **(a) and (b), descriptive only.** (a) asks whether the older news effect is less than half the rule's. It is not:
  +0.00692 against half of +0.00687. (b) asks whether the paired difference is above zero at one-sided 5%. It is not:
  p 0.50. So neither part of the warning would hold even if the gate were read loosely, as a mean above zero.
- **What it shows, descriptively.** On the dev years, the agent ranks stocks just as well with news read by a model
  whose training ended a year earlier. The two runs differ by -0.00005 IC a day on average. That fits a news effect
  too small to tell apart from zero on dev. It says nothing either way about leakage from the vintages' training data.

## For the owner and the step 8 review

- The gate rests on the lead's reading of "above zero" (one-sided 5%). Under a loose reading (a mean above zero),
  the outcome would be "no warning", since (a) fails. So no reading gives a warning here.
- `research/m3_kickoff.md` says the older table "can serve a sealed-year repeat if M4 adds one". The World built in
  step 7 refuses the sealed years whenever the offset is set, so such a repeat would need a new, reviewed change.
