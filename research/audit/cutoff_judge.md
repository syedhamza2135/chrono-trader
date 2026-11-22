# Judge: the cutoff check (21 Nov 2026)

Question: does `reader/cutoff.py` implement `research/m2_kickoff.md` section 5 (lines 212 to 247) and the rules in
`research/audit/cutoff.md` section 1 (lines 7 to 53), and would a vintage that had learned the year it reads end as
"fail"?

Read: those two sections, `reader/cutoff.py`, `tests/test_cutoff.py` lines 100 to 165, and `reader/download.py`
lines 1 to 12 and 40 to 57 (to see how the tokenizer is pinned). No real cell was computed. The synthetic checks are
in the scratchpad scripts `judge_cutoff.py` and `judge_cutoff2.py` (made-up losses only, no headlines); the model is
loss(v, y) = base(y) - 0.05 (v - 2014) - 0.3 k(v, y) + noise 0.5, N = 1,000, 2,000 resamples.

## What is right

- Cells: years V-1 to V+2 for vintages 2014 to 2024, inside 2015 to 2026, give 41 (`cutoff.py:70-72`). Every cell
  that checks A and B need is in the set, including (2014, 2015), (2014, 2016) and (2023, 2025).
- Check A is G(V+1, V+1) - G(V+1, V) gated on G(V+1, V+1); check B is G(V, V) - G(V, V+1) gated on G(V, V)
  (`cutoff.py:234-241`). Both match the spec lines 219 to 224 and `cutoff.md` lines 23 and 24.
- Masks depend only on story_id and the token count, never touch [CLS] or [SEP], and give at least one
  (`cutoff.py:75-87`). I checked story ids 1 to 2,999 at 3, 4, 12, 40 and 256 tokens. Half-up rounding holds at
  x.5 values (30 inner tokens give 5, 50 give 8). Every vintage uses one tokenizer, and `download.py:52-57` checks
  `tokenizer.json` and the other small files against one set of git object ids for all 11 vintages. So the masks
  are the same for every vintage.
- Padding: pads get label -100 and attention 0. Losses are means over masked tokens only, so special tokens and pads
  never enter the loss (`cutoff.py:129-144`). Batch order comes from the token counts, which are the same for every
  vintage.
- The sample does not depend on row order. Shuffling a 50,000-row made-up frame gave the same `sample_hash`. It
  reads only story_id, created_at and headline (`cutoff.py:176-186`). No price, return or label.
- Bootstrap: within a year, one shared index matrix for every vintage (`cutoff.py:209-220`), so gains stay paired.
  Years use independent streams. That is right: the two terms of A and of B come from different years' headlines,
  so they cannot be paired, and independence is the right model for them.
- Outcomes match `cutoff.md` lines 30 to 35 exactly (`cutoff.py:245-262`). 16 tests pass in about 10 s.
- A complete leak fails. Vintage 2018 knowing all of 2019 ends "fail" (B fails). If every vintage is off by one
  year, B's interval falls below zero and every vintage fails, gate or no gate.
- Gate design: reasonable. A leak in V shrinks A's gate, so A alone would only say "too weak". B's gate G(V, V) is
  untouched by a leak in V, so B fails such a vintage with its gate open. If V-1 leaked too, G(V, V) shrinks, but
  B then goes below zero and fails anyway. The 2024 vintage rests on B alone, as the spec says.
- Probe rule: coherent. The flag sits halfway between the 2014 vintage and the median of the vintages that could
  know. "Uninformative" covers probes where no vintage learned anything. The 2025 rule is a fair fallback.

## Findings

### 1. High (spec level, not a code bug): a partial leak passes

- Where: `cutoff.py:10-12` and `235-241`; spec `m2_kickoff.md:219-222` ("If V already knew year V+1, the two gains
  would be equal"). That holds only if V knew all of V+1.
- Evidence (`judge_cutoff2.py`, spillover s = 0.4, 2018 learns a share f of 2019): f = 0.25 gives B
  0.109 [0.050, 0.170], so 2018 passes. f = 0.5 gives 0.064 [0.005, 0.125], so it passes. f = 0.75 fails, and so
  does f = 1. In practice the likely failure is a cutoff a few months late, or a few documents with the wrong date.
  That is a small f, and the check passes it.
- Fix: keep the frozen rule. Add two numbers to the report, marked as added after the rules: the ratio
  G(V, V+1) / G(V, V) for each vintage next to the others (a leaker stands out), and G(V, V+1) split into January
  to March versus the rest of V+1 (a late cutoff puts the gain in the early months). The owner reads them as he
  reads probe flags.

### 2. Medium: "too weak" leaves a leaky vintage in use

- Where: `cutoff.py:254-255` and `261`; `cutoff.md:38-39`.
- Evidence: when a vintage leaked fully but its yearly gain is too small to measure (q = 0, small g), B's interval
  holds zero and its gate is shut, so the outcome is "too weak". That is the M-4 default. `cutoff.md` says such a
  vintage is not replaced, so the long reader run would use it.
- Fix: the owner rules on M-4 before the reader run. Until then, treat "too weak" as not cleared: the reader run
  waits for the owner, as for a fail.

### 3. Medium: the N rule sizes power on G, not on B, so honest vintages can fail

- Where: `cutoff.py:265-274`; `cutoff.md:41-44`.
- Evidence: `pick_n` asks for half-width at most G(2016, 2016) / 2. But B's true value is G(V, V) - G(V, V+1),
  which is smaller than G(V, V) whenever there is spillover. If spillover is half of G, B's true value equals the
  half-width, and an honest vintage's B interval holds zero about half the time. With its gate open, that is a
  "fail". In the s = 0.4 run with f = 0, the honest vintages 2016 and 2020 failed this way. A false fail costs a
  replacement, and 2015 has none.
- Fix: in the pilot, also print B(2016)'s point value and require half-width at most B / 2. If that is not met at
  2,000, report the expected power before the run.

### 4. Low: probes for 2015 events can never flag

- Where: `cutoff.py:336-343`. For E = 2015 the only earlier vintage is 2014, which is lo itself. It would be
  flagged only if lo >= hi, and then the probe is uninformative. This is harmless, since 2014 reads no news.
- Fix: say so in the report, or label 2015 probes as sanity checks.

### 5. Low: no check covers 2026, which the 2024 vintage also reads

- Where: `cutoff.py:51-54`; `m2_kickoff.md:172`. B(2024) covers 2025 only. A leak into 2026 could only happen if
  that vintage was trained in 2026.
- Fix: cite the 2024 vintage's publish date as evidence in the report.

### 6. Low: dedup depends on input order if a story_id repeats

- Where: `cutoff.py:96-97` (`drop_duplicates` keeps the first row after a sort on story_id). `eligible_by_year`
  (`cutoff.py:373`) counts before dedup.
- Fix: assert that story_id is unique in `headlines()`.

## Verdict

The code implements the spec and the frozen rules correctly, and a vintage that fully learned its reading year
ends "fail". A partial leak (about half or less of the year) passes, and "too weak" leaves a vintage in use. Both
need the owner's ruling or an added diagnostic before the long reader run.
