"""The simulator (sim/), the seal (sim/seal.py) and the daily rank IC (eval/metrics.py), on made-up records.

Run with: python -m pytest tests
"""
import json

import pandas as pd
import pytest

from eval.metrics import daily_rank_ic
from sim import seal
from sim.simulator import Simulator

D = pd.to_datetime(["2021-03-15", "2021-03-16", "2021-03-17", "2021-03-18"]).astype("datetime64[ns]")


class FakeWorld:
    """Just what the simulator reads: official opens and the labels between them."""

    def __init__(self, opens, labels):
        self.opens = pd.DataFrame(opens, columns=["entity_id", "share_class", "date", "open"])

        class T:
            pass
        self.labels = T()
        self.labels.df = pd.DataFrame(labels, columns=["entity_id", "share_class", "date", "end", "label", "at_close"])


def targets(*rows):
    return pd.DataFrame(rows, columns=["entity_id", "share_class", "position"])


def test_a_holding_grows_by_its_label_and_costs_are_5_bps_a_side():
    w = FakeWorld([("A", "", d, 10.0) for d in D], [("A", "", D[0], D[1], 0.10, False), ("A", "", D[1], D[2], 0.0, False)])
    sim = Simulator(w)
    sim.step(D[0], targets(("A", "", 0.5)))
    assert sim.values[("A", "")] == pytest.approx(0.5)
    assert sim.rows[-1]["cost"] == pytest.approx(0.5 * 5e-4)
    sim.step(D[1], targets(("A", "", 0.5)))
    equity_before_trade = 1 - 0.5 * 5e-4 + 0.5 * 0.10
    assert sim.rows[-1]["equity"] == pytest.approx(equity_before_trade - abs(0.5 * equity_before_trade - 0.55) * 5e-4)


def test_no_trade_without_an_official_open_and_the_holding_waits_for_the_next_one():
    """Day 2 has no official open (a halt): the target can't be traded, and the label from day 1 runs to day 3."""
    w = FakeWorld([("A", "", D[0], 10.0), ("A", "", D[2], 11.0)], [("A", "", D[0], D[2], 0.10, False)])
    sim = Simulator(w)
    sim.step(D[0], targets(("A", "", 0.5)))
    sim.step(D[1], targets(("A", "", 0.0)))  # wants out, but there is no open to sell at
    assert sim.values[("A", "")] == pytest.approx(0.5) and sim.rows[-1]["traded"] == 0
    sim.step(D[2], targets(("A", "", 0.0)))
    assert ("A", "") not in sim.values
    assert sim.cash == pytest.approx(1 - 0.5 * 5e-4 + 0.05 - 0.55 * 5e-4)


def test_a_company_that_stops_trading_is_sold_at_its_last_close():
    w = FakeWorld([("A", "", D[0], 10.0)], [("A", "", D[0], D[0], -0.20, True)])
    sim = Simulator(w)
    sim.step(D[0], targets(("A", "", 0.5)))
    sim.step(D[1], targets(("A", "", 0.5)))  # the next session: the exit is settled, and there's no open to buy at
    assert ("A", "") not in sim.values
    assert sim.cash == pytest.approx(1 - 0.5 - 0.5 * 5e-4 + 0.4 - 0.4 * 5e-4)  # bought for 0.5, sold at 0.4


def test_a_holding_with_no_label_from_todays_open_is_sold_there_not_frozen():
    """D1 has an official open but no label from it (the next open lies across a day without a return): the holding
    is sold at D1's open, where its last label ended, and counted."""
    w = FakeWorld([("A", "", d, 10.0) for d in D], [("A", "", D[0], D[1], 0.10, False), ("A", "", D[2], D[3], 0.0, False)])
    sim = Simulator(w, cost_bps=0)
    sim.step(D[0], targets(("A", "", 0.5)))
    sim.step(D[1], targets(("A", "", 0.5)))
    assert ("A", "") not in sim.values and sim.forced_sales == 1
    assert sim.cash == pytest.approx(1.05)


def test_a_short_loses_when_the_stock_rises():
    w = FakeWorld([("A", "", d, 10.0) for d in D[:2]], [("A", "", D[0], D[1], 0.10, False)])
    sim = Simulator(w, cost_bps=0)
    sim.step(D[0], targets(("A", "", -0.5)))
    sim.step(D[1], targets(("A", "", -0.5)))
    assert sim.rows[-1]["equity"] == pytest.approx(1 - 0.05)


def test_rank_ic_is_one_for_a_perfect_ranking_and_minus_one_reversed():
    lab = pd.DataFrame({"entity_id": list("ABCDEFGHIJ"), "share_class": "", "date": D[0], "label": range(10)})
    good = lab.rename(columns={"label": "prediction"})
    assert daily_rank_ic(good, lab).iloc[0] == pytest.approx(1.0)
    assert daily_rank_ic(good.assign(prediction=-good.prediction), lab).iloc[0] == pytest.approx(-1.0)
    assert daily_rank_ic(good.head(5), lab).empty  # fewer than 10 stocks that day


def write_seal(root, settings, commit):
    (root / "reference").mkdir()
    (root / "reference" / "split.json").write_text(json.dumps({"periods": {"sealed": {"start": "2020-01-02"}}}))
    (root / "PREREG.md").write_text("hypotheses")
    import hashlib
    lock = {"settings": seal.settings_hash(settings), "prereg": hashlib.sha256(b"hypotheses").hexdigest(),
            "commit": commit}
    (root / "seal.lock").write_text(json.dumps(lock))


class FakeGit:
    def __init__(self, commit="abc", dirty=False):
        self.commit, self.is_dirty = commit, dirty

    def head(self):
        return self.commit

    def dirty(self):
        return self.is_dirty


def test_dev_dates_need_no_seal(tmp_path):
    (tmp_path / "reference").mkdir()
    (tmp_path / "reference" / "split.json").write_text(json.dumps({"periods": {"sealed": {"start": "2020-01-02"}}}))
    seal.check("2017-01-03", "2019-12-31", None, root=tmp_path, git=FakeGit())


def test_the_runner_refuses_sealed_dates_without_a_matching_seal_and_a_clean_tree(tmp_path):
    settings = {"agent": "toy", "cost_bps": 5}
    with pytest.raises(seal.SealError, match="no seal.lock"):
        (tmp_path / "reference").mkdir()
        (tmp_path / "reference" / "split.json").write_text(json.dumps({"periods": {"sealed": {"start": "2020-01-02"}}}))
        seal.check("2019-06-03", "2020-01-02", settings, root=tmp_path, git=FakeGit())
    (tmp_path / "reference" / "split.json").unlink()
    (tmp_path / "reference").rmdir()
    write_seal(tmp_path, settings, "abc")
    seal.check("2020-01-02", "2026-10-28", settings, root=tmp_path, git=FakeGit())  # all match, clean tree
    with pytest.raises(seal.SealError, match="settings"):
        seal.check("2020-01-02", "2026-10-28", {**settings, "cost_bps": 10}, root=tmp_path, git=FakeGit())
    with pytest.raises(seal.SealError, match="commit"):
        seal.check("2020-01-02", "2026-10-28", settings, root=tmp_path, git=FakeGit(commit="def"))
    with pytest.raises(seal.SealError, match="clean"):
        seal.check("2020-01-02", "2026-10-28", settings, root=tmp_path, git=FakeGit(dirty=True))
    (tmp_path / "PREREG.md").write_text("changed hypotheses")
    with pytest.raises(seal.SealError, match="prereg"):
        seal.check("2020-01-02", "2026-10-28", settings, root=tmp_path, git=FakeGit())
