"""The cutoff check (M2 step 2; research/m2_kickoff.md section 5): does each ChronoBERT vintage stop learning at its
cutoff? A pipeline job, like data_pipeline: it may read the whole store, but it reads headlines as text only (no
price, return or label) and never prints or saves one. Outputs go to DATA_DIR/reader/cutoff; results are numbers.

The measure. A sample of N headlines per New York year from 2015 to 2026, drawn once with a fixed seed from the
stories in story_entities. Each headline gets fixed masks: 15% of its tokens other than [CLS] and [SEP], at least one,
chosen from its story_id. Every vintage sees the same headlines with the same masks (the 11 vintages share one
tokenizer). L(v, y) is vintage v's mean masked-word loss on year y's sample, and G(v, y) = L(v-1, y) - L(v, y).

The checks, for each vintage V that reads news (2015 to 2024):
- check A (V from 2015 to 2023): G(V+1, V+1) - G(V+1, V) > 0. Its power gate is G(V+1, V+1).
- check B (V from 2015 to 2024): G(V, V) - G(V, V+1) > 0. Its power gate is G(V, V), V's gain on its own year.
Each number gets a 95% percentile interval from 10,000 bootstrap resamples of the headlines, one resample per year
shared by every vintage, so the differences stay paired.

The outcomes, fixed before the run (review finding M-4; written into research/audit/cutoff.md before any result):
- a check's power gate is open when the gate's interval lies above zero. A check whose interval lies above zero
  passes if its gate is open, and is too weak if not. A check whose interval lies below zero fails, gate or no gate.
  A check whose interval holds zero fails if its gate is open, and is too weak if not. (A leak in V shrinks
  G(V+1, V+1), check A's gate, but not G(V, V), check B's, so check B still fails a vintage that knew its year.)
- a vintage fails when any of its checks fails; otherwise it is too weak when any check is too weak; otherwise it
  passes. The 2014 vintage reads no news and only serves as 2015's predecessor, so it has no outcome.
- named-event probes (reader/probes.csv) can flag a vintage, but a flag alone fails nothing.

Usage (python -m reader.cutoff ...):
  sample          draw the sample (story ids, years, token counts and mask counts only)
  pilot           the 2015 and 2016 vintages on the first 300 headlines of 2015 to 2017; prints the paired spread
                  and the N the rule picks
  run N           every (vintage, year) cell at N headlines a year, then the probes; finished cells are skipped
  report N        every number of research/audit/cutoff.md, from the saved cells (no model is loaded)
  probes2         score the stronger probes (reader/probes2.csv) with every vintage
  report-probes2  the stronger probes' tables and each vintage's outcome (cutoff.md section 8; no model is loaded)

On 21 Nov 2026 the owner chose to settle the cutoff on stronger probes ("Stronger probes"). The loss check and the
first probe set stay as the record and decide nothing; the rules that decide are probe2_lo, probe2_threshold,
probe2_cell, probe2_last and probe2_outcomes below, written into research/audit/cutoff.md section 8 before any score
of reader/probes2.csv.
"""
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_pipeline.settings import DATA_DIR  # noqa: E402

os.environ.setdefault("HF_HOME", str(DATA_DIR / "hf"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

YEARS = tuple(range(2015, 2027))
VINTAGES = tuple(range(2014, 2025))
CHECK_A = tuple(range(2015, 2024))
CHECK_B = tuple(range(2015, 2025))
MASK_RATE = 0.15
SAMPLE_SEED, MASK_SEED, BOOT_SEED = 20151231, 15, 10_000
N_MAX = 2000  # the sample is a seeded order of each year's stories; a run uses its first N
N_PILOT, PILOT_VINTAGES, PILOT_YEARS = 300, (2015, 2016), (2015, 2016, 2017)
N_CHOICES = (1000, 2000)
BOOT = 10_000
CAP, BATCH, THREADS = 256, 64, 4
OUT = DATA_DIR / "reader" / "cutoff"
STORE = DATA_DIR / "store"
PROBES = ROOT / "reader" / "probes.csv"  # the first set (21 Nov 2026), kept as the record
PROBES2 = ROOT / "reader" / "probes2.csv"  # the stronger set (21 Nov 2026), which decides
MARGIN = 3.0  # an informative probe: the later vintages' median log share at least this far above the earlier ones'
MIN_INFORMATIVE = 3  # a vintage passes only with at least this many informative probes of the year it reads
FAIL_FLAGS = 2  # a vintage fails with this many flags among the probes of the year it reads
PINS = json.loads((ROOT / "reader" / "vintages.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the design

def cells():
    """The (vintage, year) cells the check measures: years V-1 to V+2 for each vintage, inside 2015 to 2026."""
    return [(v, y) for v in VINTAGES for y in range(v - 1, v + 3) if y in YEARS]


def n_masked(n_tokens):
    """How many tokens a headline of n_tokens (with [CLS] and [SEP]) gets masked: 15% of the inner ones, rounded
    half up, at least one."""
    inner = n_tokens - 2
    if inner < 1:
        raise ValueError("a headline needs at least one token besides [CLS] and [SEP]")
    return max(1, int(np.floor(MASK_RATE * inner + 0.5)))


def mask_positions(story_id, n_tokens):
    """The fixed mask positions of one headline, from its story_id alone (never position 0 or the last, [SEP])."""
    rng = np.random.default_rng([MASK_SEED, int(story_id)])
    return np.sort(rng.choice(np.arange(1, n_tokens - 1), size=n_masked(n_tokens), replace=False))


def draw_sample(frame, n_max=N_MAX, seed=SAMPLE_SEED):
    """frame has story_id, year and n_tokens. For each year in YEARS: the stories with at least one inner token, in
    story_id order, then put in a seeded random order; the first n_max are kept, with their rank in that order. A run
    at N uses ranks below N, so a smaller sample is always the start of a larger one."""
    out = []
    for y in YEARS:
        f = frame[(frame.year == y) & (frame.n_tokens >= 3)].sort_values("story_id", kind="stable")
        if f.story_id.duplicated().any():
            raise ValueError(f"year {y}: duplicate story ids")
        order = np.random.default_rng([seed, y]).permutation(len(f))[:n_max]
        g = f.iloc[order][["story_id", "year", "n_tokens"]].copy()
        g["rank"] = np.arange(len(g))
        out.append(g)
    s = pd.concat(out, ignore_index=True)
    s["n_masked"] = [n_masked(n) for n in s.n_tokens]
    return s.astype({"story_id": "int64", "year": "int64", "n_tokens": "int64", "rank": "int64",
                     "n_masked": "int64"})


def sample_hash(sample):
    """A SHA-256 over (year, rank, story_id, n_tokens), to tie saved cells to one sample."""
    s = sample.sort_values(["year", "rank"])
    h = hashlib.sha256()
    for row in s[["year", "rank", "story_id", "n_tokens"]].itertuples(index=False):
        h.update(("%d,%d,%d,%d\n" % tuple(row)).encode())
    return h.hexdigest()


# ---------------------------------------------------------------- the model's part

def headline_losses(mlm, encoded, story_ids, batch=BATCH, pad_id=0, mask_id=None):
    """Each headline's mean cross-entropy over its fixed masked tokens. encoded is a list of token-id lists, each
    starting with [CLS] and ending with [SEP]. Batches are sorted by length; padding is masked out of attention."""
    import torch
    losses = np.empty(len(encoded))
    order = np.argsort([len(e) for e in encoded], kind="stable")
    with torch.inference_mode():
        for i in range(0, len(encoded), batch):
            idx = order[i:i + batch]
            width = max(len(encoded[j]) for j in idx)
            ids = torch.full((len(idx), width), pad_id, dtype=torch.long)
            att = torch.zeros((len(idx), width), dtype=torch.long)
            labels = torch.full((len(idx), width), -100, dtype=torch.long)
            for r, j in enumerate(idx):
                e = torch.tensor(encoded[j], dtype=torch.long)
                ids[r, :len(e)] = e
                att[r, :len(e)] = 1
                pick = torch.from_numpy(mask_positions(story_ids[j], len(e)))
                labels[r, pick] = e[pick]
                ids[r, pick] = mask_id
            h = mlm.model(input_ids=ids, attention_mask=att).last_hidden_state
            sel = labels != -100
            logits = mlm.decoder(mlm.head(h[sel]))
            ce = torch.nn.functional.cross_entropy(logits.float(), labels[sel], reduction="none")
            rows = sel.nonzero()[:, 0]
            per = torch.zeros(len(idx), dtype=ce.dtype).index_add_(0, rows, ce) / sel.sum(1)
            losses[idx] = per.numpy()
    return losses


def snapshot(vintage):
    pin = PINS["vintages"][str(vintage)]
    return DATA_DIR / "hf" / "hub" / ("models--" + pin["repo"].replace("/", "--")) / "snapshots" / pin["commit"]


def load_vintage(vintage):
    """One vintage's masked-word model, from its pinned snapshot on D:, offline, after checking every file against
    reader/vintages.json (the weights by size and SHA-256). Stops if anything differs."""
    from reader.download import problems
    folder = snapshot(vintage)
    found = problems(folder, PINS["vintages"][str(vintage)])
    if found:
        raise SystemExit(f"vintage {vintage}: {'; '.join(found)}")
    import torch
    from transformers import AutoModelForMaskedLM
    torch.set_num_threads(THREADS)
    return AutoModelForMaskedLM.from_pretrained(str(folder), attn_implementation="sdpa").eval()


def tokenizer():
    """The one tokenizer every vintage shares (the small files match one set of git object ids)."""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(str(snapshot(VINTAGES[0])))


# ---------------------------------------------------------------- the store's part

def headlines():
    """story_id, year (New York, from created_at) and headline of every story in story_entities. Kept in memory
    only; nothing here prints or saves a headline."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    ids = pq.read_table(STORE / "story_entities.parquet", columns=["story_id"]).column("story_id").unique()
    t = pq.read_table(STORE / "stories.parquet", columns=["story_id", "created_at", "headline"])
    t = t.filter(pc.is_in(t["story_id"], value_set=ids))
    df = t.to_pandas()
    df["year"] = df.created_at.dt.tz_convert("America/New_York").dt.year
    return df[["story_id", "year", "headline"]]


def encode(tok, texts, chunk=50_000):
    out = []
    for i in range(0, len(texts), chunk):
        out.extend(tok(texts[i:i + chunk], truncation=True, max_length=CAP)["input_ids"])
    return out


# ---------------------------------------------------------------- the statistics

def gains(losses):
    """Per-headline gains d(v, y) = loss(v-1, y) - loss(v, y), for every cell whose predecessor cell exists."""
    return {(v, y): losses[(v - 1, y)] - losses[(v, y)] for (v, y) in losses if (v - 1, y) in losses}


def boot_means(d, boot=BOOT, seed=BOOT_SEED, chunk=500):
    """Point means and bootstrap means of each per-headline vector in d (keyed by (v, y)). Each year has one set of
    resamples, shared by every vector of that year, so differences within a year stay paired; years are resampled
    independently."""
    point = {k: float(np.mean(x)) for k, x in d.items()}
    means = {k: np.empty(boot) for k in d}
    for y in sorted({y for _, y in d}):
        keys = [k for k in d if k[1] == y]
        n = len(d[keys[0]])
        if any(len(d[k]) != n for k in keys):
            raise ValueError(f"year {y}: the vectors differ in length")
        mat = np.stack([d[k] for k in keys])
        rng = np.random.default_rng([seed, y])
        for s in range(0, boot, chunk):
            idx = rng.integers(0, n, size=(min(chunk, boot - s), n))
            m = mat[:, idx].mean(axis=2)
            for r, k in enumerate(keys):
                means[k][s:s + len(idx)] = m[r]
    return point, means


def interval(x):
    lo, hi = np.percentile(x, [2.5, 97.5])
    return float(lo), float(hi)


def statistics(losses, boot=BOOT, seed=BOOT_SEED):
    """Every gain G(v, y) and every check, each with its point value and 95% interval."""
    point, means = boot_means(gains(losses), boot, seed)
    G = {k: {"value": point[k], "ci": interval(means[k])} for k in point}
    checks = {}
    for V in CHECK_A:
        a, b, gate = (V + 1, V + 1), (V + 1, V), (V + 1, V + 1)
        if a in point and b in point:
            checks[("A", V)] = {"value": point[a] - point[b], "ci": interval(means[a] - means[b]), "gate": gate}
    for V in CHECK_B:
        a, b, gate = (V, V), (V, V + 1), (V, V)
        if a in point and b in point:
            checks[("B", V)] = {"value": point[a] - point[b], "ci": interval(means[a] - means[b]), "gate": gate}
    return G, checks


def outcomes(G, checks):
    """Each check's status and each reading vintage's outcome, by the rules in this module's docstring."""
    status = {}
    for key, c in checks.items():
        gate_open = G[c["gate"]]["ci"][0] > 0
        if c["ci"][0] > 0:
            status[key] = "pass" if gate_open else "too weak"
        elif c["ci"][1] < 0:
            status[key] = "fail"
        else:
            status[key] = "fail" if gate_open else "too weak"
    result = {}
    for V in CHECK_B:
        mine = [status[k] for k in (("A", V), ("B", V)) if k in status]
        if not mine:
            continue
        result[V] = "fail" if "fail" in mine else "too weak" if "too weak" in mine else "pass"
    return status, result


def pick_n(d_own, d_next):
    """The pilot's rule for N: d_own and d_next are the 2016 vintage's per-headline gains on 2016 and 2017. Predict
    check B's 95% half-width at N from their spread; take the smallest N in N_CHOICES whose half-width is at most
    half the own-year gain, else the largest."""
    g = float(np.mean(d_own))
    for n in N_CHOICES:
        hw = 1.96 * np.sqrt(np.var(d_own, ddof=1) / n + np.var(d_next, ddof=1) / n)
        if g > 0 and hw <= g / 2:
            return n
    return N_CHOICES[-1]


# ---------------------------------------------------------------- the probes

def load_probes(path=PROBES):
    """reader/probes.csv: probe_id, event_year, event_month, sentence (one {} where the answer goes), answer, wrong
    (wrong answers separated by |), source. reader/probes2.csv has event_date (YYYY-MM-DD, New York) in place of
    event_year and event_month; both are derived from it."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if "event_date" in r:
            y, m, _ = (int(x) for x in r["event_date"].split("-"))
            r["event_year"], r["event_month"] = y, m
        r["event_year"], r["event_month"] = int(r["event_year"]), int(r["event_month"])
        r["wrong"] = r["wrong"].split("|")
    return rows


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def span_tokens(offsets, start, end):
    """Positions of the tokens whose character span overlaps [start, end) (special tokens have empty spans)."""
    return [i for i, (a, b) in enumerate(offsets) if b > a and a < end and b > start]


def candidate_inputs(tok, sentence, candidate):
    """The sentence with one candidate in place, its token ids, and the positions the candidate fills."""
    start = sentence.index("{}")
    text = sentence.replace("{}", candidate, 1)
    enc = tok(text, return_offsets_mapping=True)
    pos = span_tokens(enc["offset_mapping"], start, start + len(candidate))
    if not pos:
        raise ValueError("a candidate fills no token")
    return enc["input_ids"], pos


def candidate_logprob(mlm, ids, pos, mask_id):
    """The log-probability of a candidate's tokens with all of them masked at once (summed over its tokens)."""
    import torch
    x = torch.tensor([ids])
    y = x[0, pos].clone()
    x[0, pos] = mask_id
    with torch.inference_mode():
        h = mlm.model(input_ids=x, attention_mask=torch.ones_like(x)).last_hidden_state
        lp = torch.log_softmax(mlm.decoder(mlm.head(h[0, pos])).float(), dim=-1)
    return float(lp[torch.arange(len(pos)), y].sum())


def probe_score(logps):
    """The answer's share among the candidates, as a log: logps[0] is the answer's, the rest the wrong answers'."""
    a = np.asarray(logps, dtype=float)
    return float(a[0] - (a.max() + np.log(np.exp(a - a.max()).sum())))


def probe_flags(scores, event_year):
    """scores maps each vintage to one probe's score. For an event in year E, the vintages from E on could know the
    answer. lo is the oldest vintage's score, hi the median score of the vintages from E on. A vintage before E is
    flagged when its score is at least halfway from lo to hi. If hi <= lo the probe is uninformative (no flags). If
    no vintage is from E on (E = 2025), a vintage is flagged when its score is above lo and the answer's share is
    above one half (more likely than all the wrong answers together)."""
    vs = sorted(scores)
    lo = scores[vs[0]]
    after = [scores[v] for v in vs if v >= event_year]
    before = [v for v in vs if v < event_year]
    if after:
        hi = float(np.median(after))
        if hi <= lo:
            return "uninformative", []
        mid = (lo + hi) / 2
        return "informative", [v for v in before if scores[v] >= mid]
    return "no later vintage", [v for v in before if scores[v] > lo and scores[v] > np.log(0.5)]


# ---------------------------------------------------------------- the stronger probes (research/audit/cutoff.md s. 8)
# The rules the owner chose on 21 Nov 2026 ("Stronger probes"). They decide each vintage's cutoff; the loss check and
# the first probe set above stay as the record and decide nothing.

BASE = 3  # lo is the median of the BASE vintages just before the vintage judged (judge finding 4, 21 Nov 2026)


def probe2_lo(scores, V):
    """The baseline for vintage V: the median score of the vintages from max(2014, V - BASE) to V - 1. It leaves V
    out (a leak in V can't raise its own baseline) and uses only V's nearest predecessors, so slow honest growth in
    what vintages know about an answer over the years doesn't count as a leak."""
    return float(np.median([scores[v] for v in VINTAGES if V - BASE <= v < V]))


def probe2_threshold(table, probes):
    """T, the least rise over lo that can flag a vintage: the 95th percentile of score - probe2_lo over every honest
    cell, never below MARGIN / 2. An honest cell is a probe of year E (2016 to 2025) and a vintage V from 2015 to
    E-2, a full year or more before the event, so the rise is the vintage-to-vintage drift of a vintage that can't
    know the answer. An honest vintage then clears T on about 1 probe in 20."""
    year = {p["probe_id"]: p["event_year"] for p in probes}
    rises = [table[pid][V] - probe2_lo(table[pid], V) for pid in table for V in range(VINTAGES[1], year[pid] - 1)]
    return max(MARGIN / 2, float(np.percentile(rises, 95)))


def probe2_cell(scores, event_year, V, t=MARGIN / 2):
    """One probe of an event in year E (2016 to 2024) and one vintage V from 2015 to E-1. lo is probe2_lo(V); hi is
    the median score of the vintages from E to 2024. The probe is informative for V when hi - lo >= MARGIN, and V is
    flagged when the probe is informative for V and V's score is at least both (lo + hi) / 2 and lo + t, where t is
    probe2_threshold. Returns (informative, flagged, lo, hi)."""
    E = event_year
    if not (VINTAGES[0] < V < E <= VINTAGES[-1]):
        raise ValueError("probe2_cell needs 2014 < V < E <= 2024")
    lo = probe2_lo(scores, V)
    hi = float(np.median([scores[v] for v in VINTAGES if v >= E]))
    informative = hi - lo >= MARGIN
    return informative, bool(informative and scores[V] >= max((lo + hi) / 2, lo + t)), lo, hi


def probe2_last(scores, t=MARGIN / 2):
    """A 2025 probe and the 2024 vintage (no vintage comes after 2025's events, so hi can't be measured). lo is
    probe2_lo(2024), the median of 2021 to 2023. The probe is usable when lo <= -MARGIN, the room a gap of MARGIN
    needs, since a score is at most 0. The 2024 vintage is flagged when the probe is usable and its score is at least
    lo + t, where t is probe2_threshold. Returns (usable, flagged, lo)."""
    lo = probe2_lo(scores, VINTAGES[-1])
    usable = lo <= -MARGIN
    return usable, bool(usable and scores[VINTAGES[-1]] >= lo + t), lo


def probe2_outcomes(table, probes):
    """table maps probe_id to {vintage: score} for every probe in probes (load_probes(PROBES2)) and every vintage.
    Each vintage V from 2015 to 2024 is judged on the probes of year V+1, the year it reads first, and f is the number
    of those that flag V. For V from 2015 to 2023, n is the number informative for V. For V = 2024 a probe's
    informativeness can't be measured, so n is q times the number of usable 2025 probes, where q is the share of the
    2016 to 2024 probes informative for the vintage just before their event: the power is borrowed from the other
    years. V fails when f >= FAIL_FLAGS; otherwise it passes when n >= MIN_INFORMATIVE; otherwise it is too weak.
    Flags on the probes of later years (V+2 to 2024), and which flags fall on events from January to March, are
    reported for the owner and decide nothing. Returns (outcomes, q, T)."""
    if set(table) != {p["probe_id"] for p in probes} or any(set(s) != set(VINTAGES) for s in table.values()):
        raise ValueError("the score table must hold every probe and every vintage")
    year = {p["probe_id"]: p["event_year"] for p in probes}
    month = {p["probe_id"]: p["event_month"] for p in probes}
    last = VINTAGES[-1]
    before = [pid for pid in table if year[pid] <= last]
    T = probe2_threshold(table, probes)
    q = float(np.mean([probe2_cell(table[pid], year[pid], year[pid] - 1, T)[0] for pid in before]))
    out = {}
    for V in VINTAGES[1:]:
        nxt = sorted(pid for pid in table if year[pid] == V + 1)
        if V < last:
            cells = {pid: probe2_cell(table[pid], V + 1, V, T)[:2] for pid in nxt}
        else:
            cells = {pid: probe2_last(table[pid], T)[:2] for pid in nxt}
        n = sum(c[0] for c in cells.values())
        if V == last:
            n = q * n
        flags = [pid for pid, c in cells.items() if c[1]]
        if len(flags) >= FAIL_FLAGS:
            outcome = "fail"
        elif n >= MIN_INFORMATIVE:
            outcome = "pass"
        else:
            outcome = "too weak"
        later = sorted(pid for pid in table if V + 2 <= year[pid] <= last and probe2_cell(table[pid], year[pid], V, T)[1])
        out[V] = {"probes": len(nxt), "informative": n, "flags": flags,
                  "early flags": [pid for pid in flags if month[pid] <= 3], "later flags": later, "outcome": outcome}
    return out, q, T


# ---------------------------------------------------------------- the jobs

def cell_path(v, y, folder=None):
    return Path(folder or OUT) / f"loss_v{v}_y{y}.parquet"


def load_sample():
    s = pd.read_parquet(OUT / "sample.parquet")
    manifest = json.loads((OUT / "sample.json").read_text(encoding="utf-8"))
    if sample_hash(s) != manifest["sample_sha256"]:
        raise SystemExit("the saved sample does not match its manifest")
    return s


def cmd_sample():
    import transformers
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    df = headlines()
    tok = tokenizer()
    df["n_tokens"] = [len(e) for e in encode(tok, df.headline.tolist())]
    s = draw_sample(df[["story_id", "year", "n_tokens"]])
    s.to_parquet(OUT / "sample.parquet", index=False)
    manifest = {"sample_sha256": sample_hash(s), "n_max": N_MAX, "seed": SAMPLE_SEED, "mask_seed": MASK_SEED,
                "mask_rate": MASK_RATE, "cap": CAP, "transformers": transformers.__version__,
                "stories_in_story_entities": int(len(df)),
                "eligible_by_year": {int(y): int(((df.year == y) & (df.n_tokens >= 3)).sum()) for y in YEARS}}
    (OUT / "sample.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"{len(df):,} stories in story_entities; sample of up to {N_MAX} a year in {time.perf_counter() - t0:.0f}s")
    for y in YEARS:
        print(f"  {y}: {manifest['eligible_by_year'][y]:,} eligible, {int((s.year == y).sum())} drawn")
    print("sample SHA-256", manifest["sample_sha256"])


def measure(todo, n, folder):
    """Compute the cells in todo (a list of (vintage, year)) at n headlines a year, one vintage at a time. Each cell
    is saved as story_id and loss; a cell already saved for the same story ids is skipped."""
    folder.mkdir(parents=True, exist_ok=True)
    s = load_sample()
    s = s[s["rank"] < n]
    by_year = {y: g.sort_values("rank") for y, g in s.groupby("year")}
    need = [(v, y) for v, y in todo
            if not (cell_path(v, y, folder).exists()
                    and pd.read_parquet(cell_path(v, y, folder)).story_id.tolist() == by_year[y].story_id.tolist())]
    if not need:
        print("every cell is done")
        return
    df = headlines()
    df = df[df.story_id.isin(s.story_id)].set_index("story_id")
    tok = tokenizer()
    enc = {y: encode(tok, df.loc[g.story_id, "headline"].tolist()) for y, g in by_year.items()}
    for y, g in by_year.items():
        if [len(e) for e in enc[y]] != g.n_tokens.tolist():
            raise SystemExit(f"year {y}: token counts differ from the sample's")
    del df
    for v in sorted({v for v, _ in need}):
        t0 = time.perf_counter()
        mlm = load_vintage(v)
        print(f"vintage {v} loaded and checked in {time.perf_counter() - t0:.0f}s", flush=True)
        for (vv, y) in need:
            if vv != v:
                continue
            t1 = time.perf_counter()
            ids = by_year[y].story_id.to_numpy()
            loss = headline_losses(mlm, enc[y], ids, pad_id=tok.pad_token_id, mask_id=tok.mask_token_id)
            out = pd.DataFrame({"story_id": ids, "loss": loss})
            tmp = cell_path(v, y, folder).with_suffix(".tmp")
            out.to_parquet(tmp, index=False)
            os.replace(tmp, cell_path(v, y, folder))
            secs = time.perf_counter() - t1
            print(f"  cell ({v}, {y}): L {loss.mean():.4f}, {len(ids)} headlines, {len(ids) / secs:.1f} a second",
                  flush=True)
        del mlm


def read_cells(todo, n, folder):
    s = load_sample()
    s = s[s["rank"] < n]
    want = {y: g.sort_values("rank").story_id.tolist() for y, g in s.groupby("year")}
    losses = {}
    for v, y in todo:
        c = pd.read_parquet(cell_path(v, y, folder))
        if c.story_id.tolist() != want[y]:
            raise SystemExit(f"cell ({v}, {y}) is for other headlines")
        losses[(v, y)] = c.loss.to_numpy()
    return losses


def cmd_pilot():
    folder = OUT / "pilot"
    todo = [(v, y) for v in PILOT_VINTAGES for y in PILOT_YEARS]
    measure(todo, N_PILOT, folder)
    losses = read_cells(todo, N_PILOT, folder)
    d = gains(losses)
    for y in PILOT_YEARS:
        x = d[(2016, y)]
        print(f"pilot G(2016, {y}) = {x.mean():.4f}, per-headline sd {x.std(ddof=1):.4f}, n {len(x)}, standard "
              f"error {x.std(ddof=1) / np.sqrt(len(x)):.4f}")
    n = pick_n(d[(2016, 2016)], d[(2016, 2017)])
    print(f"the rule picks N = {n}")


def run_probes(folder, path=PROBES, name="probes"):
    probes = load_probes(path)
    tok = tokenizer()
    rows = []
    for v in VINTAGES:
        mlm = load_vintage(v)
        for p in probes:
            lps = []
            for cand in [p["answer"], *p["wrong"]]:
                ids, pos = candidate_inputs(tok, p["sentence"], cand)
                lps.append(candidate_logprob(mlm, ids, pos, tok.mask_token_id))
            rows.append({"probe_id": p["probe_id"], "vintage": v, "score": probe_score(lps)})
        del mlm
        print(f"probes scored for vintage {v}", flush=True)
    out = pd.DataFrame(rows)
    out.to_parquet(folder / f"{name}.parquet", index=False)
    (folder / f"{name}.json").write_text(json.dumps({"probes_sha256": file_sha256(path)}), encoding="utf-8")


def cmd_probes2():
    folder = OUT / "probes2"
    if (folder / "scores.parquet").exists():
        raise SystemExit(f"{folder / 'scores.parquet'} exists; the probes are scored once (move it away to rerun)")
    folder.mkdir(parents=True, exist_ok=True)
    shas = {"probes_sha256": file_sha256(PROBES2), "cutoff_sha256": file_sha256(__file__)}
    print(f"probes2.csv SHA-256 {shas['probes_sha256']}, cutoff.py SHA-256 {shas['cutoff_sha256']}", flush=True)
    run_probes(folder, PROBES2, "scores")
    (folder / "scores.json").write_text(json.dumps(shas), encoding="utf-8")


def cmd_report_probes2():
    folder = OUT / "probes2"
    shas = json.loads((folder / "scores.json").read_text(encoding="utf-8"))
    if shas["probes_sha256"] != file_sha256(PROBES2):
        raise SystemExit("reader/probes2.csv changed since the probes were scored")
    print(f"probes2.csv SHA-256 {shas['probes_sha256']} (unchanged since the run); cutoff.py SHA-256 at the run "
          f"{shas['cutoff_sha256']} (now {file_sha256(__file__)})\n")
    probes = load_probes(PROBES2)
    sc = pd.read_parquet(folder / "scores.parquet")
    table = {pid: dict(zip(g.vintage, g.score)) for pid, g in sc.groupby("probe_id", sort=True)}
    print("| Probe | Event | " + " | ".join(str(v) for v in VINTAGES) + " | lo | hi | Informative | Flags V = E-1 |")
    print("|---|---|" + "---|" * len(VINTAGES) + "---|---|---|---|")
    T = probe2_threshold(table, probes)
    for p in probes:
        pid, E, s = p["probe_id"], p["event_year"], table[p["probe_id"]]
        if E <= VINTAGES[-1]:
            inf, fl, lo, hi = probe2_cell(s, E, E - 1, T)
            tail = f"{lo:.2f} | {hi:.2f} | {'yes' if inf else 'no'} | {'yes' if fl else 'no'}"
        else:
            us, fl, lo = probe2_last(s, T)
            tail = f"{lo:.2f} | none | {'usable' if us else 'not usable'} | {'yes' if fl else 'no'}"
        print(f"| {pid} | {p['event_date']} | " + " | ".join(f"{s[v]:.2f}" for v in VINTAGES) + f" | {tail} |")
    res, q, T = probe2_outcomes(table, probes)
    print(f"\nT, the least rise over lo that flags (95th percentile of honest cells, at least 1.5): {T:.3f}")
    print(f"q, the share of the 2016 to 2024 probes informative for the vintage just before their event: {q:.3f}")
    print("\n| Vintage | Reads | Probes | Informative (2024: q x usable) | Flags | Of them January to March |"
          " Later-year flags | Outcome |\n|---|---|---|---|---|---|---|---|")
    for V, r in res.items():
        print(f"| {V} | {V + 1} | {r['probes']} | {r['informative']:.3g} | {', '.join(r['flags']) or 'none'} | "
              f"{', '.join(r['early flags']) or 'none'} | {', '.join(r['later flags']) or 'none'} | {r['outcome']} |")
    (folder / "report.json").write_text(json.dumps({"q": q, "T": T, "outcomes": {str(k): v for k, v in res.items()}},
                                                   indent=1), encoding="utf-8")


def cmd_run(n):
    measure(cells(), n, OUT / f"n{n}")
    run_probes(OUT / f"n{n}")
    print("done; now: python -m reader.cutoff report", n)


def fmt_ci(c):
    return f"{c['value']:+.4f} [{c['ci'][0]:+.4f}, {c['ci'][1]:+.4f}]"


def cmd_report(n):
    folder = OUT / f"n{n}"
    losses = read_cells(cells(), n, folder)
    G, checks = statistics(losses)
    status, result = outcomes(G, checks)
    print(f"sample SHA-256 {json.loads((OUT / 'sample.json').read_text(encoding='utf-8'))['sample_sha256']}, "
          f"N {n}, cells {len(losses)}, bootstrap {BOOT} resamples (seed {BOOT_SEED})\n")
    print("| Vintage | " + " | ".join(str(y) for y in YEARS) + " |")
    print("|---|" + "---|" * len(YEARS))
    for v in VINTAGES:
        print(f"| {v} | " + " | ".join(f"{losses[(v, y)].mean():.4f}" if (v, y) in losses else "" for y in YEARS)
              + " |")
    print("\n| Vintage | Own-year gain G(V, V) | Check A | A | Check B | B | Outcome |")
    print("|---|---|---|---|---|---|---|")
    for V in CHECK_B:
        a, b = checks.get(("A", V)), checks[("B", V)]
        print(f"| {V} | {fmt_ci(G[(V, V)])} | {fmt_ci(a) if a else 'none'} | {status.get(('A', V), '')} | "
              f"{fmt_ci(b)} | {status[('B', V)]} | {result[V]} |")
    # added after the rules (judge finding 1), outside the outcomes: how much of V's own-year gain it also shows on
    # the year it reads. Near 0 is honest; near 1 is a full leak; a partial leak sits between and can still pass.
    print("\n| Vintage | Spillover G(V, V+1) / G(V, V) |\n|---|---|")
    for V in CHECK_B:
        g = G[(V, V)]["value"]
        print(f"| {V} | {G[(V, V + 1)]['value'] / g:+.2f} |" if g > 0 else f"| {V} | none (G(V, V) not above 0) |")
    print("\n| G(v, y) | value [95% interval] |\n|---|---|")
    for k in sorted(G):
        print(f"| G({k[0]}, {k[1]}) | {fmt_ci(G[k])} |")
    pj = folder / "probes.parquet"
    if pj.exists():
        sha = json.loads((folder / "probes.json").read_text(encoding="utf-8"))["probes_sha256"]
        print(f"\nprobes.csv SHA-256 at the run {sha} (now {file_sha256(PROBES)})\n")
        sc = pd.read_parquet(pj)
        years = {p["probe_id"]: p["event_year"] for p in load_probes()}
        print("| Probe | Event year | " + " | ".join(str(v) for v in VINTAGES) + " | Kind | Flagged |")
        print("|---|---|" + "---|" * len(VINTAGES) + "---|---|")
        reading = []
        for pid, g in sc.groupby("probe_id", sort=False):
            s = dict(zip(g.vintage, g.score))
            kind, flags = probe_flags(s, years[pid])
            print(f"| {pid} | {years[pid]} | " + " | ".join(f"{s[v]:.2f}" for v in VINTAGES)
                  + f" | {kind} | {', '.join(map(str, flags)) or 'none'} |")
            after = [s[v] for v in VINTAGES if v >= years[pid]]
            gap = f"{np.median(after) - s[VINTAGES[0]]:+.2f}" if after else "none"
            steps = [f"{v} ({s[v] - s[v - 1]:+.2f})" for v in VINTAGES[1:] if s[v] - s[v - 1] > 3]
            reading.append(f"| {pid} | {gap} | {', '.join(steps) or 'none'} |")
        # added after the run, outside the rules: the gap behind each flag rule, and every rise of more than 3
        print("\n| Probe | hi - lo | Rises of more than 3 (vintage, rise) |\n|---|---|---|")
        print("\n".join(reading))
    report = {"n": n, "losses": {f"{v},{y}": float(x.mean()) for (v, y), x in losses.items()},
              "gains": {f"{v},{y}": G[(v, y)] for (v, y) in G},
              "checks": {f"{k[0]},{k[1]}": {**c, "gate": list(c["gate"]), "status": status[k]}
                         for k, c in checks.items()},
              "outcomes": {str(V): o for V, o in result.items()}}
    (folder / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


def main(argv):
    if not argv or argv[0] not in ("sample", "pilot", "run", "report", "probes2", "report-probes2"):
        print(__doc__)
        return 2
    if argv[0] == "probes2":
        cmd_probes2()
    elif argv[0] == "report-probes2":
        cmd_report_probes2()
    elif argv[0] == "sample":
        cmd_sample()
    elif argv[0] == "pilot":
        cmd_pilot()
    elif argv[0] == "run":
        cmd_run(int(argv[1]))
    else:
        cmd_report(int(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
