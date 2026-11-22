# Judge: the frozen rules for the stronger cutoff probes (22 Nov 2026)

Scope: `research/audit/cutoff.md` section 8, `reader/probes2.csv`, the named parts of `reader/cutoff.py`,
`tests/test_cutoff.py` from line 226, `research/probe_margin_pilot.py`. No probe of the new set was scored and no
model was loaded. The facts about events below come from the judge's memory. Each one marked "confirm" must be checked
against its source before anyone acts on it. The ones not marked are well known, but they still need a check before a
row is changed.

## What was checked and found right

- The hashes of `reader/probes2.csv` and `reader/cutoff.py` today match the freeze in 8.7 (`5dac4506...b619`,
  `06f106d0...09e3`).
- `tests/test_cutoff.py` passes, 24 tests and no skips, so the real-tokenizer length check ran: every answer and its
  four wrong answers have the same token count, and each decodes back to itself.
- `python research/probe_margin_pilot.py` prints the counts in 8.4 exactly: margin 2, 3, 4 give 10, 7, 3 informative
  cells and 2, 2, 0 flags (p2019b on 2018, p2024a on 2023).
- `probe2_cell` (cutoff.py 366 to 378) does what 8.4 says. lo is the median of 2014 to E-1 without V (line 374). hi
  is the median of E to 2024 (line 375). Informative means a gap of at least `MARGIN` (line 376). A flag means a
  score at or above the midpoint.
- `probe2_last` (380 to 385) flags 2024 at lo + 1.5, where lo is the median of 2014 to 2023, as 8.4 says.
- `probe2_outcomes` (388 to 425) does what 8.5 says. q is taken over the probes of 2016 to 2024, each judged on
  E-1 (lines 402 and 403). A vintage fails on 2 flags whatever n is (line 415). It passes on n, or on q x 8 for 2024,
  of at least 3 (line 417). Later-year flags cover V+2 to 2024, early flags cover January to March, and neither
  decides anything.
- `run_probes` puts the answer first and `probe_score` takes element 0 as the answer, so the order is right.
- Leaving V out of lo works as meant: a leak in V cannot raise its own baseline, and hi never contains V.
- 8.5 already admits these limits: short leaks touch only early events, 2024's power is borrowed, and 2026 is not
  covered.

## Findings, ranked

### High

**1. The 2024 rule has no margin and a far baseline, so an honest 2024 can fail. A leaky one can also pass.**
`reader/cutoff.py` 380 to 385, cutoff.md 8.4 last paragraph and 8.5.
- Any 2025 probe can flag 2024. Nothing first checks that the probe can tell a vintage that knows from one that
  does not. lo is the median of ten vintages, centred on about the 2018 to 2019 vintages. So 2024 gets five to six
  years of honest growth in what it knows about the answer, for free. The doc's case for 1.5 ("the lowest halfway
  point the rule for earlier years allows") holds only for probes that pass the margin. Here no probe is screened.
- Check, on the first run's saved scores (the table in cutoff.md section 5). The script is below. Applied to the
  vintage just before each event, the 2024-style rule flags 4 of 18 probes (p2016b, p2019b, p2020a, p2024a). The
  gated rule flags 2. At 4 in 18, the chance of 2 or more flags among 8 probes is 0.56.
- The other way round: with lo above -1.5, no score can reach lo + 1.5, since scores are at most 0. Such a probe
  can never flag. A leaky 2024 can pass if most 2025 probes are like that, and q, measured on other years, would not
  show it.
- Fix (one line): take 2024's lo from its nearest vintages (median of 2021 to 2023). Count a 2025 probe only when
  that lo is -3 or lower, which is the room the margin needs since hi is at most 0. 2024 passes only when at least
  3 probes count.

**2. Several probes have answers tied to the sentence in public before 1 January of the event's year.** This breaks
8.2's rule that the answer "was not public before 1 January". An honest vintage E-1 can favour these answers.
- q2016g Wells Fargo. The Los Angeles Times reported the unwanted accounts in December 2013. The Los Angeles City
  Attorney sued Wells Fargo over them in May 2015. So 2015 already links "accounts customers never asked for" to
  Wells Fargo.
- q2020f BioNTech. Pfizer and BioNTech announced an mRNA flu vaccine partnership in August 2018, and BioNTech listed
  in October 2019. "Pfizer and its German partner" points to BioNTech for the 2018 and 2019 vintages.
- q2018e Sky. 21st Century Fox agreed to buy the rest of Sky in December 2016, and the bid was in the news all
  through 2017. "won an auction for the British broadcaster" points to Sky before Comcast came in.
- q2019b SABIC. Aramco said in July 2018 that it was looking at buying a stake in SABIC (confirm). The checker could
  not rule this out (8.6).
- q2025e Scale AI. Scale AI's May 2024 round valued it at about 13.8 billion dollars, and Meta was among the
  investors (confirm Meta). "about 14 billion dollars" plus "Meta" points to Scale AI for the 2024 vintage.
- q2023d GPT-4. The name of OpenAI's next model was public before 2023, for example the 2021 Wired interview on the
  size of GPT-4 (confirm). The number after GPT-3 is the obvious guess. GPT-3 and GPT-2 also fit the sentence except
  for "in March".
- Fix: replace these six with events whose answer had no link to the sentence before that year.

### Medium

**3. More answers were predictable, or likely linked, before the year.** Each one alone is tolerated, but they
cluster by year (finding 4).
- q2016c Duterte. Cayetano, Escudero and Trillanes ran for vice president, not president (Cayetano as Duterte's
  running mate). A 2015 vintage that knows the field is left with Duterte or Roxas, and 2015's lo is the 2014 vintage
  alone.
- q2017c Macron. He declared his candidacy in November 2016, and "the 39-year-old" fits only him among the five.
- q2017b Mobileye. Intel, Mobileye and BMW announced a self-driving partnership in July 2016.
- q2018b Uber. Uber moved its self-driving cars to Arizona in December 2016, and one crashed in Tempe in March 2017.
- q2019e Boris Johnson. He was the favourite to succeed May all through 2018.
- q2022f Liz Truss. Sunak is not a candidate, and Truss led the Conservative members' polls in 2021 (confirm). Among
  the five, she was the obvious pick at the end of 2021.
- q2022c TerraUSD. UST briefly lost its peg in May 2021 (confirm).
- q2023f Splunk. A report of a Cisco offer for Splunk in 2022 (confirm).
- q2023a Adani. Gautam Adani's rise to among the world's richest was a 2022 story, so the 2022 vintage knows Adani
  better than the median older vintage.
- q2024e Wiz and q2024h Microsoft. Wiz was the best-known cloud security startup by 2023. Microsoft signed nuclear
  and fusion power deals in 2023 (Helion, and one with Constellation; confirm).
- q2025c Liberation. Trump called 5 November 2024 "Liberation Day" at rallies in October 2024 (confirm).
- q2025a Palisades. A smaller fire of that name burned near Pacific Palisades in 2021 (confirm).
- q2025d Signal. WhatsApp is missing, and Signal was the app US officials were told to use in December 2024
  (confirm).
- q2016a AlphaGo. If it is tokenized as "Alpha" and "Go", the "Go" piece copies "the game of Go", and "Alpha" gets
  help from Alphabet (August 2015). Check with
  `[tok.convert_ids_to_tokens(i) for i in C.candidate_inputs(tok, s, "AlphaGo")]`.
- Fix: replace the clearest cases (q2016c, q2017c, q2022f, q2025c, q2025d and, if confirmed, q2023f) so that no year
  keeps two of them.

**4. One flag tolerated, two fail: the doc says two flags "are not chance", but the pilot does not show it.**
cutoff.md 8.5, `FAIL_FLAGS` line 74.
- In the pilot, 2 of 7 informative cells flagged the vintage just before the event. One is put down to length and
  one to an answer public before the event (8.4). The second kind remains in the new list (findings 2 and 3).
- At 1 honest flag in 7, the chance of 2 or more among 8 informative probes is 0.32, and 0.15 among 5. Over ten
  vintages, at least one honest fail is likely. Findings 2 and 3 put two or more such probes in 2016, 2017, 2018,
  2022, 2023 and 2025.
- Fix: do findings 1 to 3. Then either keep the rule and write down this honest-fail rate, or take lo from the
  three vintages before V (V-3 to V-1), which removes most of the slow growth in what vintages know about an answer.

**5. Wrong answers that are also true, or nearly true.** This breaks 8.2. They lower hi, so probes lose power, but
they do not by themselves make an honest vintage fail.
- q2020d Lordstown. Hindenburg Research accused Lordstown Motors in March 2021.
- q2020c ten. On 20 April 2020 WTI also fell below 10 dollars, which may have been a first for the contract
  (confirm).
- q2019f Monarch. It collapsed in October 2017 and stranded about 110,000 people.
- q2023h Sumitomo Metal. The buyer was called Nippon Steel and Sumitomo Metal from 2012 to 2019.
- q2020b America. Saudi Arabia's 2014 price war was against US shale. The sentence is false only because of
  "In March".
- Fix: swap each one, then rerun the token-count test.

### Low

**6. Wordings that give the answer to every vintage.** These probes are dead: they cannot be informative, and they
push vintages toward "too weak".
- q2016d "professional networking site".
- q2018g "open-source software company".
- q2020g "workplace messaging company".
- q2021e "carries fuel along the US East Coast".
- q2023e "seized ... and sold to", the Washington Mutual and JPMorgan pattern of 2008.
- q2021a. Texas also lost power in a February 2011 winter storm.
- q2019d. Actavis bought Allergan in 2014, and Pfizer agreed to buy it in 2015.
- q2018c. Flipkart is the dominant Indian online retailer.
- These are worth noting. Replacing them adds power.

**7. Small code gaps.**
- `cmd_report_probes2` (line 559) prints the hash taken at the run and the hash now, but does not stop when they
  differ.
- `cmd_probes2` (line 551) reuses an existing folder and silently overwrites `scores.parquet`.
- `run_probes` (line 546) records the hash of `probes2.csv` only, not the hash of `cutoff.py`.
- `probe2_outcomes` builds q and each year's probes from the keys of the score table, so a missing probe shrinks
  them without warning.
- Fix: stop on a hash mismatch or an existing scores file, record both hashes, and assert 80 probes with 11
  vintages each.

**8. Tests.** `test_probe2_cell` line 275 does not really test leaving V out: lo would be -3 with V in or out. Add a
case where V's own score would move the median.

**9. Worth noting.**
- n = 3 with f = 1 passes, with one in three informative probes flagged.
- In the pilot, q at margin 3 was about 7 in 18 (0.39), just above the 0.375 that 2024 needs. So 2024's pass or
  "too weak" may turn on one probe.
- The same token count does not mean the same make-up. "Scale AI" is two words, while "Appen" may split into pieces.
  This leaves a smaller form of the length effect in 8.1.

## The check for findings 1 and 4 (run from the repo root; it reads the section 5 table only)

```python
import re, numpy as np
V = list(range(2014, 2025)); rows = []
for line in open("research/audit/cutoff.md", encoding="utf-8"):
    m = re.match(r"\| (p20\d\d[a-z]) \| (\d{4}) \| (.*?) \| (?:informative|uninformative|no later)", line)
    if m and 2016 <= int(m[2]) <= 2024:
        rows.append((m[1], int(m[2]), dict(zip(V, map(float, m[3].split(" | "))))))
f = [pid for pid, E, s in rows if s[E-1] >= np.median([s[v] for v in V if v < E-1]) + 1.5]
print(len(rows), "probes; the 2024-style rule flags V = E-1 on", f)
for p, n in ((1/7, 8), (1/7, 5), (4/18, 8)):
    print(p, n, 1 - (1-p)**n - n*p*(1-p)**(n-1))
```

Output: 18 probes, with flags on p2016b, p2019b, p2020a and p2024a. P(2 or more) is 0.32, 0.15 and 0.56. The first
set had unequal lengths, so these rates are a guide, not a measurement.

## Verdict

Do not run as frozen. These must change first:
- finding 1, the 2024 rule;
- finding 2, six probes;
- the clearest cases of finding 3;
- finding 5, five wrong answers.

Then rerun the token-count test and record the new hashes in 8.8. Findings 4 and 6 to 9 are worth doing but need not
hold up the run. No score has been seen, so these changes are still made blind.
