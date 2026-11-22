"""Tests for reader/cutoff.py, on synthetic data and a tiny random ModernBERT (no store, no real weights), except one
tokenizer test that runs only when the pinned tokenizer is on D:."""
import numpy as np
import pandas as pd
import pytest

from reader import cutoff as C


def test_cells_are_v_minus_1_to_v_plus_2_inside_the_years():
    cells = C.cells()
    assert len(cells) == 41 and len(set(cells)) == 41
    for v, y in cells:
        assert v - 1 <= y <= v + 2 and 2015 <= y <= 2026
    assert {y for v, y in cells if v == 2014} == {2015, 2016}
    assert {y for v, y in cells if v == 2024} == {2023, 2024, 2025, 2026}
    # every cell the checks need is measured
    need = set()
    for V in C.CHECK_A:
        need |= {(V, V + 1), (V + 1, V + 1), (V, V), (V + 1, V)}
    for V in C.CHECK_B:
        need |= {(V - 1, V), (V, V), (V - 1, V + 1), (V, V + 1)}
    assert need <= set(cells)


def test_mask_count_is_15_percent_of_inner_tokens_at_least_one():
    assert C.n_masked(3) == 1  # one inner token
    assert C.n_masked(12) == 2  # 10 inner: 1.5 rounds up
    assert C.n_masked(22) == 3  # 20 inner: 3.0
    assert C.n_masked(9) == 1  # 7 inner: 1.05
    with pytest.raises(ValueError):
        C.n_masked(2)


def test_masks_come_from_the_story_id_alone():
    a = C.mask_positions(123456, 30)
    C.mask_positions(999, 30)  # another call in between changes nothing
    assert np.array_equal(a, C.mask_positions(123456, 30))
    assert len(a) == C.n_masked(30) and len(set(a)) == len(a)
    assert a.min() >= 1 and a.max() <= 28  # never [CLS] (0) or [SEP] (29)
    picks = {tuple(C.mask_positions(s, 30)) for s in range(200)}
    assert len(picks) > 150  # different stories get different masks


def _frame(n=60):
    rng = np.random.default_rng(0)
    rows = [(int(sid), y, int(rng.integers(2, 40))) for y in C.YEARS for sid in rng.choice(10**8, n, replace=False)]
    return pd.DataFrame(rows, columns=["story_id", "year", "n_tokens"])


def test_sample_is_seeded_per_year_and_nested():
    f = _frame()
    big = C.draw_sample(f, n_max=20)
    again = C.draw_sample(f.sample(frac=1, random_state=3), n_max=20)  # row order doesn't matter
    pd.testing.assert_frame_equal(big.reset_index(drop=True), again.reset_index(drop=True))
    assert C.sample_hash(big) == C.sample_hash(again)
    small = C.draw_sample(f, n_max=8)
    for y in C.YEARS:
        b = big[big.year == y].sort_values("rank")
        s = small[small.year == y].sort_values("rank")
        assert b.story_id.tolist()[:8] == s.story_id.tolist()  # a smaller sample is the start of a larger one
        assert len(b) == 20
    assert (big.n_tokens >= 3).all()
    assert C.draw_sample(f, n_max=20, seed=1).story_id.tolist() != big.story_id.tolist()


def _tiny_mlm():
    torch = pytest.importorskip("torch")
    from transformers import ModernBertConfig, ModernBertForMaskedLM
    torch.manual_seed(0)
    cfg = ModernBertConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                           num_attention_heads=2, pad_token_id=0, bos_token_id=1, eos_token_id=2, cls_token_id=1,
                           sep_token_id=2, max_position_embeddings=64)
    return ModernBertForMaskedLM(cfg).eval()


def _headlines(n=9, seed=1):
    rng = np.random.default_rng(seed)
    return [[1, *rng.integers(4, 64, size=int(rng.integers(1, 20))).tolist(), 2] for _ in range(n)]


def test_loss_does_not_depend_on_the_batch_and_matches_full_logits():
    torch = pytest.importorskip("torch")
    mlm = _tiny_mlm()
    enc, ids = _headlines(), np.arange(100, 109)
    together = C.headline_losses(mlm, enc, ids, batch=64, pad_id=0, mask_id=3)
    alone = np.array([C.headline_losses(mlm, [e], [i], batch=1, pad_id=0, mask_id=3)[0] for e, i in zip(enc, ids)])
    assert np.allclose(together, alone, atol=1e-5)
    for e, i, got in zip(enc, ids, together):
        x = torch.tensor([e])
        pos = C.mask_positions(i, len(e))
        y = x[0, pos].clone()
        x[0, pos] = 3
        with torch.inference_mode():
            logits = mlm(input_ids=x, attention_mask=torch.ones_like(x)).logits[0, pos]
        want = torch.nn.functional.cross_entropy(logits, y).item()
        assert abs(got - want) < 1e-5


def _synthetic(knows, n=400, gain=0.3, noise=0.05, seed=0):
    """Losses where vintage v has learned year y when knows(v, y): base difficulty per headline, minus gain for
    each learned year up to y, plus noise."""
    rng = np.random.default_rng(seed)
    base = {y: rng.normal(4.0, 1.0, n) for y in C.YEARS}
    return {(v, y): base[y] - gain * knows(v, y) + rng.normal(0, noise, n) for v, y in C.cells()}


def test_honest_vintages_pass():
    losses = _synthetic(lambda v, y: float(y <= v))
    G, checks = C.statistics(losses, boot=2000)
    status, result = C.outcomes(G, checks)
    assert set(result) == set(C.CHECK_B) and set(result.values()) == {"pass"}
    assert len(checks) == len(C.CHECK_A) + len(C.CHECK_B)
    for c in checks.values():
        assert c["ci"][0] <= c["value"] <= c["ci"][1]


def test_a_vintage_that_knows_its_reading_year_fails():
    # the 2018 vintage has also learned 2019
    losses = _synthetic(lambda v, y: float(y <= v or (v == 2018 and y == 2019)))
    G, checks = C.statistics(losses, boot=2000)
    status, result = C.outcomes(G, checks)
    # check B fails it; check A's gate G(2019, 2019) is what the leak shrinks, so A is too weak
    assert status[("B", 2018)] == "fail" and status[("A", 2018)] == "too weak"
    assert result[2018] == "fail"
    assert result[2019] == "too weak"  # 2019 adds nothing measurable on its own year, since 2018 knew it
    assert all(o == "pass" for V, o in result.items() if V not in (2018, 2019))


def test_no_measurable_yearly_gain_is_too_weak_not_a_pass():
    losses = _synthetic(lambda v, y: 0.0)
    G, checks = C.statistics(losses, boot=2000)
    status, result = C.outcomes(G, checks)
    # pure noise: no vintage passes. Most are too weak; by chance a gate opens or an interval falls below zero
    # (about 1 in 40 each, over 19 checks), and those read as fails
    assert "pass" not in result.values()
    assert sum(o == "too weak" for o in result.values()) >= 5


def test_outcome_precedence():
    open_, shut = {"value": 1, "ci": (0.5, 1.5)}, {"value": 0, "ci": (-0.1, 0.1)}
    G = {(2016, 2016): open_, (2017, 2017): shut, (2018, 2018): shut, (2019, 2019): open_}
    checks = {("A", 2016): {"value": 0.2, "ci": (0.1, 0.3), "gate": (2017, 2017)},  # passes behind a shut gate
              ("B", 2016): {"value": -0.1, "ci": (-0.3, 0.1), "gate": (2016, 2016)},  # holds zero, gate open
              ("B", 2017): {"value": 0.0, "ci": (-0.1, 0.1), "gate": (2017, 2017)},  # holds zero, gate shut
              ("B", 2018): {"value": -0.5, "ci": (-0.7, -0.3), "gate": (2018, 2018)},  # below zero, gate shut
              ("B", 2019): {"value": 0.5, "ci": (0.3, 0.7), "gate": (2019, 2019)}}  # passes
    status, result = C.outcomes(G, checks)
    assert status == {("A", 2016): "too weak", ("B", 2016): "fail", ("B", 2017): "too weak", ("B", 2018): "fail",
                      ("B", 2019): "pass"}
    assert result == {2016: "fail", 2017: "too weak", 2018: "fail", 2019: "pass"}  # a fail beats too weak


def test_bootstrap_is_reproducible_and_paired_within_a_year():
    rng = np.random.default_rng(5)
    x = rng.normal(0, 1, 300)
    d = {(2016, 2016): x, (2017, 2016): x + 1.0, (2017, 2017): rng.normal(0, 1, 250)}
    p1, m1 = C.boot_means(d, boot=1000)
    p2, m2 = C.boot_means(d, boot=1000)
    assert np.array_equal(m1[(2017, 2016)], m2[(2017, 2016)])
    # the same resample for every vector of a year: the difference of two vectors that differ by a constant is that
    # constant in every resample
    assert np.allclose(m1[(2017, 2016)] - m1[(2016, 2016)], 1.0)
    assert abs(p1[(2016, 2016)] - x.mean()) < 1e-12


def test_pick_n():
    rng = np.random.default_rng(0)
    assert C.pick_n(rng.normal(0.3, 0.5, 300), rng.normal(0.0, 0.5, 300)) == 1000
    assert C.pick_n(rng.normal(0.03, 0.5, 300), rng.normal(0.0, 0.5, 300)) == 2000
    assert C.pick_n(rng.normal(-0.1, 0.5, 300), rng.normal(0.0, 0.5, 300)) == 2000


def test_probe_score_and_flags():
    assert abs(C.probe_score([0.0, 0.0]) + np.log(2)) < 1e-12
    assert C.probe_score([-1.0, -5.0, -6.0]) < 0
    scores = {v: -3.0 for v in C.VINTAGES}
    for v in range(2020, 2025):
        scores[v] = -0.2
    kind, flags = C.probe_flags(scores, 2020)
    assert kind == "informative" and flags == []
    scores[2019] = -0.5  # the vintage before the event already scores like those after it
    assert C.probe_flags(scores, 2020) == ("informative", [2019])
    assert C.probe_flags({v: -2.0 for v in C.VINTAGES}, 2020) == ("uninformative", [])
    late = {v: -2.0 for v in C.VINTAGES}
    late[2024] = -0.1
    assert C.probe_flags(late, 2025) == ("no later vintage", [2024])


def test_span_tokens():
    offsets = [(0, 0), (0, 6), (6, 8), (8, 12), (12, 15), (15, 21), (21, 22), (0, 0)]
    assert C.span_tokens(offsets, 13, 21) == [4, 5]
    assert C.span_tokens(offsets, 0, 6) == [1]


def test_probes_file_is_well_formed():
    probes = C.load_probes()
    ids = [p["probe_id"] for p in probes]
    assert len(ids) == len(set(ids)) >= 20
    years = [p["event_year"] for p in probes]
    assert set(years) == set(range(2015, 2026))
    for p in probes:
        assert p["sentence"].count("{}") == 1
        assert 1 <= p["event_month"] <= 12
        assert len(p["wrong"]) >= 3 and p["answer"] not in p["wrong"] and len(set(p["wrong"])) == len(p["wrong"])
        assert p["source"]


def test_candidate_logprob_on_the_tiny_model():
    mlm = _tiny_mlm()
    ids = [1, 10, 11, 12, 13, 2]
    lp = C.candidate_logprob(mlm, ids, [2, 3], mask_id=3)
    assert np.isfinite(lp) and lp < 0


@pytest.mark.skipif(not C.snapshot(2014).exists(), reason="the pinned tokenizer is not on D:")
def test_candidates_fill_their_own_tokens_with_the_real_tokenizer():
    tok = C.tokenizer()
    for p in C.load_probes():
        for cand in [p["answer"], *p["wrong"]]:
            ids, pos = C.candidate_inputs(tok, p["sentence"], cand)
            text = tok.decode([ids[i] for i in pos]).strip()
            assert text == cand, (p["probe_id"], cand, text)


# ---------------------------------------------------------------- the stronger probes (cutoff.md section 8)

def _table(knows, flat=-4.0, known=-0.3, noise=0.0, seed=0):
    """A synthetic score table for reader/probes2.csv: vintage v scores `known` on a probe of year E when
    knows(v, E), else `flat`, plus optional noise."""
    rng = np.random.default_rng(seed)
    probes = C.load_probes(C.PROBES2)
    table = {p["probe_id"]: {v: (known if knows(v, p["event_year"]) else flat) + rng.normal(0, noise)
                             for v in C.VINTAGES} for p in probes}
    return table, probes


def test_probes2_file_is_well_formed():
    probes = C.load_probes(C.PROBES2)
    ids = [p["probe_id"] for p in probes]
    assert len(ids) == len(set(ids)) == 80
    for y in range(2016, 2026):
        assert sum(p["event_year"] == y for p in probes) == 8
    for p in probes:
        assert p["event_date"].startswith(str(p["event_year"])) and 1 <= p["event_month"] <= 12
        assert p["sentence"].count("{}") == 1
        assert len(p["wrong"]) == 4 and len(set(p["wrong"])) == 4 and p["answer"] not in p["wrong"]
        assert p["source"]
    # no event of the first set is reused: its scores were seen before these rules were written
    assert not {p["answer"] for p in probes} & {"Alphabet", "EMC", "Whole Foods", "GitHub", "Aramco", "COVID-19",
                                                "GameStop", "Meta", "Twitter", "ChatGPT", "Credit Suisse", "Threads",
                                                "Harris", "Leo", "DeepSeek"}


@pytest.mark.skipif(not C.snapshot(2014).exists(), reason="the pinned tokenizer is not on D:")
def test_probes2_candidates_have_the_answers_token_count():
    tok = C.tokenizer()
    for p in C.load_probes(C.PROBES2):
        n = [len(C.candidate_inputs(tok, p["sentence"], c)[1]) for c in [p["answer"], *p["wrong"]]]
        assert len(set(n)) == 1, (p["probe_id"], n)
        for c in [p["answer"], *p["wrong"]]:
            ids, pos = C.candidate_inputs(tok, p["sentence"], c)
            assert tok.decode([ids[i] for i in pos]).strip() == c, (p["probe_id"], c)


def test_probe2_cell():
    s = {v: -3.0 for v in C.VINTAGES}
    assert C.probe2_cell(s, 2019, 2018)[:2] == (False, False)  # flat: not informative
    for v in range(2019, 2025):
        s[v] = 0.0  # a gap of exactly the margin
    inf, fl, lo, hi = C.probe2_cell(s, 2019, 2018)
    assert (inf, fl, lo, hi) == (True, False, -3.0, 0.0)
    s[2018] = -1.5  # V scores at the halfway point
    assert C.probe2_cell(s, 2019, 2018)[:2] == (True, True)
    s2 = {**s, **{v: -1.0 for v in range(2019, 2025)}}  # a gap of 2 is under the margin of 3
    s2[2018] = -3.0
    assert C.probe2_cell(s2, 2019, 2018)[0] is False
    with pytest.raises(ValueError):
        C.probe2_cell(s, 2025, 2024)


def test_probe2_lo_uses_the_three_vintages_before_v_and_leaves_v_out():
    s = {v: -3.0 for v in C.VINTAGES}
    s[2014] = s[2015] = -20.0  # far vintages: a median over 2014 to 2017 would be -11.5
    s[2018] = 0.0  # the vintage judged
    assert C.probe2_lo(s, 2018) == -3.0  # median of 2015, 2016, 2017
    assert C.probe2_lo(s, 2019) == -3.0  # median of 2016, 2017, 2018: 2018 counts once it is not the one judged
    assert C.probe2_lo(s, 2016) == -20.0  # 2014 and 2015 only
    assert C.probe2_lo(s, 2015) == -20.0  # 2014 alone


def test_probe2_last():
    s = {v: -3.0 for v in C.VINTAGES}
    assert C.probe2_last(s) == (True, False, -3.0)  # lo of -3 leaves room for the margin
    s[2024] = -1.5  # exactly lo + 1.5
    assert C.probe2_last(s)[:2] == (True, True)
    s = {v: -2.0 for v in C.VINTAGES}
    s[2024] = 0.0
    assert C.probe2_last(s)[:2] == (False, False)  # lo above -3: not usable, so it can't flag
    s[2021] = s[2022] = -9.0  # lo is the median of 2021 to 2023 only
    assert C.probe2_last(s) == (True, True, -9.0)


def test_probe2_outcomes_needs_the_full_table():
    table, probes = _table(lambda v, E: v >= E)
    del table["q2019a"]
    with pytest.raises(ValueError):
        C.probe2_outcomes(table, probes)
    table, probes = _table(lambda v, E: v >= E)
    del table["q2019a"][2014]
    with pytest.raises(ValueError):
        C.probe2_outcomes(table, probes)


def test_probe2_honest_vintages_pass_and_q_is_one():
    table, probes = _table(lambda v, E: v >= E)
    res, q, _ = C.probe2_outcomes(table, probes)
    assert q == 1.0
    assert {V: r["outcome"] for V, r in res.items()} == {V: "pass" for V in range(2015, 2025)}
    assert all(r["flags"] == [] and r["later flags"] == [] for r in res.values())
    assert res[2018]["informative"] == 8 and res[2024]["informative"] == 8.0


def test_probe2_a_leaky_vintage_fails_and_its_neighbours_do_not():
    table, probes = _table(lambda v, E: v >= E or (v == 2018 and E == 2019))
    res, _, _ = C.probe2_outcomes(table, probes)
    assert res[2018]["outcome"] == "fail" and len(res[2018]["flags"]) == 8
    assert all(r["outcome"] == "pass" for V, r in res.items() if V != 2018)
    table, probes = _table(lambda v, E: v >= E or v == 2024)  # 2024 knows 2025
    res, _, _ = C.probe2_outcomes(table, probes)
    assert res[2024]["outcome"] == "fail" and all(r["outcome"] == "pass" for V, r in res.items() if V != 2024)


def test_probe2_one_flag_is_tolerated_and_no_signal_is_too_weak():
    table, probes = _table(lambda v, E: v >= E)
    table["q2019a"][2018] = -0.3  # one probe of 2019 flags 2018
    res, _, _ = C.probe2_outcomes(table, probes)
    assert res[2018]["flags"] == ["q2019a"] and res[2018]["early flags"] == ["q2019a"]
    assert res[2018]["outcome"] == "pass"
    table, probes = _table(lambda v, E: False, noise=0.3)  # nothing is ever learned
    res, q, _ = C.probe2_outcomes(table, probes)
    assert q == 0.0 and all(r["outcome"] == "too weak" for r in res.values())


def test_probe2_later_year_flags_are_reported_but_do_not_decide():
    table, probes = _table(lambda v, E: v >= E or (v == 2016 and E == 2021))
    res, _, _ = C.probe2_outcomes(table, probes)
    assert res[2016]["outcome"] == "pass" and len(res[2016]["later flags"]) == 8


def test_probe2_threshold_follows_the_honest_drift():
    table, probes = _table(lambda v, E: v >= E)
    assert C.probe2_threshold(table, probes) == 1.5  # no drift: the floor
    table, probes = _table(lambda v, E: v >= E, noise=1.5, seed=3)
    assert C.probe2_threshold(table, probes) > 1.5
    s = {v: -4.0 for v in C.VINTAGES}
    s.update({v: -0.5 for v in range(2019, 2025)})
    s[2018] = -2.0  # past the halfway point (-2.25), but under lo + t for t = 2.5
    assert C.probe2_cell(s, 2019, 2018)[1] is True
    assert C.probe2_cell(s, 2019, 2018, t=2.5)[1] is False
