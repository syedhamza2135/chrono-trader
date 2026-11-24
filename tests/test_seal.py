"""The seal on a real git repo (M4 step 1, PLAN 9.12): seal.lock committed alone after the sealed commit, the writer,
the once-per-part guard with its again flag, and sealed runs through sim.simulator with both parts. Each test builds
its own temporary repo and run log; nothing reads the real store or the real sealed years. The made-up world's
sealed start is moved into its own dates (2017-03-01), so its sealed sessions are made up too."""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
from reader import vintage as V  # noqa: E402
from sim import seal, simulator  # noqa: E402
from world.clock import Clock  # noqa: E402
from world.world import World  # noqa: E402

START, END = "2017-03-01", "2017-06-30"  # the made-up world's "sealed years"
MAIN = {"sealed_part": "main", "agent": "toy"}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                           "-c", "commit.gpgsign=false", *args], capture_output=True, text=True, check=True).stdout


def make_repo(tmp_path, start=START, end=END):
    repo = tmp_path / "repo"
    (repo / "reference").mkdir(parents=True)
    (repo / "reference" / "split.json").write_text(json.dumps({"periods": {"sealed": {"start": start, "end": end}}}))
    (repo / "PREREG.md").write_text("H1, H2, H3\n")
    (repo / "code.py").write_text("x = 1\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the code and PREREG")
    return repo


def commit_lock(repo):
    git(repo, "add", "seal.lock")
    git(repo, "commit", "-q", "-m", "the seal")


def test_the_lock_committed_alone_after_the_sealed_commit_passes(tmp_path):
    repo = make_repo(tmp_path)
    sealed = git(repo, "rev-parse", "HEAD").strip()
    lock = seal.write({"main": MAIN}, root=repo)
    assert lock["commit"] == sealed and lock["sealed_start"] == START and lock["sealed_end"] == END
    with pytest.raises(seal.SealError, match="commit"):  # written but not committed
        seal.check(START, END, MAIN, root=repo)
    commit_lock(repo)
    seal.check(START, END, MAIN, root=repo)  # HEAD is the lock's commit, whose parent is the sealed one
    with pytest.raises(seal.SealError, match="settings"):
        seal.check(START, END, {**MAIN, "agent": "other"}, root=repo)
    with pytest.raises(seal.SealError, match="settings"):
        seal.check(START, END, {**MAIN, "sealed_part": "older_vintage"}, root=repo)  # a part the lock lacks
    seal.check("2016-01-04", "2017-02-28", None, root=repo)  # before the sealed start: no seal needed


def test_any_other_commit_after_the_seal_breaks_it(tmp_path):
    repo = make_repo(tmp_path)
    seal.write({"main": MAIN}, root=repo)
    commit_lock(repo)
    (repo / "code.py").write_text("x = 2\n")
    with pytest.raises(seal.SealError, match="clean"):
        seal.check(START, END, MAIN, root=repo)
    git(repo, "commit", "-q", "-am", "a change after the seal")
    with pytest.raises(seal.SealError, match="commit"):
        seal.check(START, END, MAIN, root=repo)


def test_the_lock_committed_with_anything_else_breaks_it(tmp_path):
    repo = make_repo(tmp_path)
    seal.write({"main": MAIN}, root=repo)
    (repo / "code.py").write_text("x = 2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the seal and a change")
    with pytest.raises(seal.SealError, match="commit"):
        seal.check(START, END, MAIN, root=repo)


def test_an_empty_commit_after_the_lock_breaks_it(tmp_path):
    repo = make_repo(tmp_path)
    seal.write({"main": MAIN}, root=repo)
    commit_lock(repo)
    git(repo, "commit", "-q", "--allow-empty", "-m", "nothing")
    with pytest.raises(seal.SealError, match="commit"):
        seal.check(START, END, MAIN, root=repo)


def test_a_changed_prereg_breaks_it(tmp_path):
    repo = make_repo(tmp_path)
    seal.write({"main": MAIN}, root=repo)
    (repo / "PREREG.md").write_text("H1 only\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the seal, and PREREG edited")
    with pytest.raises(seal.SealError, match="prereg, commit"):
        seal.check(START, END, MAIN, root=repo)


def test_the_writer_refuses_what_it_should(tmp_path):
    repo = make_repo(tmp_path)
    with pytest.raises(seal.SealError, match="main among them"):
        seal.write({"older_vintage": {"sealed_part": "older_vintage"}}, root=repo)
    with pytest.raises(seal.SealError, match="main among them"):
        seal.write({"main": MAIN, "extra": {"sealed_part": "extra"}}, root=repo)
    with pytest.raises(seal.SealError, match="name the part"):
        seal.write({"main": {"sealed_part": "older_vintage"}}, root=repo)
    (repo / "code.py").write_text("x = 2\n")
    with pytest.raises(seal.SealError, match="clean"):
        seal.write({"main": MAIN}, root=repo)
    git(repo, "commit", "-q", "-am", "x = 2")
    seal.write({"main": MAIN}, root=repo)
    with pytest.raises(seal.SealError, match="exists already"):
        seal.write({"main": MAIN}, root=repo)
    other = tmp_path / "other"
    other.mkdir()
    (other / "x").write_text("x")
    git(other, "init", "-q")
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "no PREREG")
    with pytest.raises(seal.SealError, match="no PREREG.md"):
        seal.write({"main": MAIN}, root=other)


def test_each_part_starts_once_unless_again(tmp_path):
    repo = make_repo(tmp_path)
    log = tmp_path / "log" / "runs.jsonl"
    first = seal.begin(MAIN, root=repo, log=log)
    assert first["n"] == 1 and first["again"] is False and first["part"] == "main"
    with pytest.raises(seal.SealError, match="started already.*again=True"):
        seal.begin(MAIN, root=repo, log=log)
    second = seal.begin(MAIN, again=True, root=repo, log=log)
    assert second["n"] == 2 and second["again"] is True
    older = {"sealed_part": "older_vintage"}
    with pytest.raises(seal.SealError, match="never started"):
        seal.begin(older, again=True, root=repo, log=log)
    assert seal.begin(older, root=repo, log=log)["n"] == 1
    with pytest.raises(seal.SealError, match="names its part"):
        seal.begin({"agent": "toy"}, root=repo, log=log)
    assert [e["part"] for e in seal.started(log)] == ["main", "main", "older_vintage"]


class Idle:
    params = {}

    def decide(self, view):
        return None

    def freeze(self):
        return Idle()


class Looks:
    """Takes a view each day and keeps its time, so the test sees which sessions were opened."""
    params = {"looks": True}

    def __init__(self):
        self.seen = []

    def decide(self, view):
        self.seen.append(view.t)
        return None


def older(tables):
    emb = synthetic.make_embeddings(tables)
    created = emb.story_id.map(tables["stories"].set_index("story_id").created_at)
    return emb.assign(vintage_year=V.vintage_for(created, 1).to_numpy())


FIRST, LAST = "2017-02-27", "2017-03-02"  # four sessions, the last two "sealed"


def part(name, first=FIRST, last=LAST):
    """A sealed run's caller settings: its part and its dates (sim.simulator refuses dates that differ, J4-4)."""
    return {"sealed_part": name, "first": first, "last": last}


@pytest.fixture
def sealed_repo(tmp_path, monkeypatch):
    """A real repo whose split puts the sealed start on 2017-03-01, with seal.ROOT and the run log pointed at it."""
    repo = make_repo(tmp_path)
    monkeypatch.setattr(seal, "ROOT", repo)
    monkeypatch.setattr(seal, "RUNS_LOG", tmp_path / "log" / "runs.jsonl")
    return repo


def worlds():
    tables = synthetic.make_tables(0)
    main = World(**tables, embeddings=synthetic.make_embeddings(tables))
    off = World(**tables, embeddings=older(tables), vintage_offset=1)
    for w in (main, off):
        w._sealed = pd.Timestamp(START)  # the World's own sealed start, moved with the split's
    return main, off


def test_a_sealed_run_needs_the_lock_and_runs_each_part_once(sealed_repo):
    main, off = worlds()
    first, last = FIRST, LAST
    with pytest.raises(PermissionError, match="sealed years"):
        main.view(Clock().decision_time(START))  # shut by hand
    with pytest.raises(seal.SealError, match="no seal.lock"):
        simulator.run_many(main, {"live": Idle()}, first, last, settings=part("main"))
    parts = {"main": simulator.settings_many(main, {"live": Looks()}, settings=part("main")),
             "older_vintage": simulator.settings_many(off, {"live_older_vintage": Looks()},
                                                      settings=part("older_vintage"))}
    assert parts["older_vintage"]["vintage_offset"] == 1 and "vintage_offset" not in parts["main"]
    seal.write(parts)
    commit_lock(sealed_repo)
    agent = Looks()
    simulator.run_many(main, {"live": agent}, first, last, settings=part("main"))
    assert pd.Timestamp(START, tz="America/New_York").date() in {t.tz_convert("America/New_York").date()
                                                                for t in agent.seen}
    assert main.allow_sealed is False  # put back after the run
    with pytest.raises(seal.SealError, match="started already"):
        simulator.run_many(main, {"live": Looks()}, first, last, settings=part("main"))
    simulator.run_many(main, {"live": Looks()}, first, last, settings=part("main"), again=True)
    with pytest.raises(seal.SealError, match="settings"):  # another agent's settings
        simulator.run_many(main, {"live": Idle()}, first, last, settings=part("main"), again=True)
    with pytest.raises(PermissionError, match="vintage_offset"):  # the offset World as the main part
        simulator.run_many(off, {"live_older_vintage": Looks()}, first, last, settings=part("main"))
    with pytest.raises(PermissionError, match="needs a World with vintage_offset 1"):
        simulator.run_many(main, {"live_older_vintage": Looks()}, first, last,
                           settings=part("older_vintage"))
    with pytest.raises(PermissionError, match="vintage_offset"):  # the offset World with no part at all
        simulator.run(off, Looks(), first, last, settings={})
    older_agent = Looks()
    simulator.run_many(off, {"live_older_vintage": older_agent}, first, last,
                       settings=part("older_vintage"))
    assert len(older_agent.seen) == 4 and off.allow_sealed is False
    with pytest.raises(PermissionError, match="sealed years"):
        off.view(Clock().decision_time(START))  # shut again after the run
    log = seal.started()
    assert [(e["part"], e["n"], e["again"]) for e in log] == [("main", 1, False), ("main", 2, True),
                                                              ("older_vintage", 1, False)]


def test_a_refused_run_opens_nothing_and_logs_nothing(sealed_repo):
    main, _ = worlds()
    seal.write({"main": simulator.settings_many(main, {"live": Looks()}, settings=part("main"))})
    commit_lock(sealed_repo)
    (sealed_repo / "code.py").write_text("x = 3\n")  # a dirty tree
    with pytest.raises(seal.SealError, match="clean"):
        simulator.run_many(main, {"live": Looks()}, "2017-02-27", "2017-03-02", settings=part("main"))
    assert seal.started() == [] and main.allow_sealed is False


def test_the_sealed_runner_seals_each_part_on_what_run_many_will_check(monkeypatch):
    """research/m4_sealed_run.py, with the chosen configuration and the data fingerprint stubbed (no data is read):
    each part's sealed settings name the part and its dates, and equal what run_many computes from a real World with
    the default window, without and with the offset (M4 judge J4-5)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
    import m4_sealed_run as R
    monkeypatch.setattr(R, "chosen", lambda: ("T09", {"band": 15, "hold": 5}))
    monkeypatch.setattr(R, "fingerprint", lambda store: {"store": Path(store).name})
    main_s, older_s = R.full_settings("main"), R.full_settings("older_vintage")
    assert main_s["sealed_part"] == "main" and older_s["sealed_part"] == "older_vintage"
    assert main_s["first"] == "2016-01-04" and main_s["last"] == older_s["last"] == R.sealed_end()
    assert "vintage_offset" not in main_s and older_s["vintage_offset"] == 1
    assert older_s["data"] == {"store": "reader_older"} and main_s["data"] == {"store": "store"}
    assert list(older_s["agents"]) == ["live_older_vintage"] and older_s["freeze"] == []
    assert main_s["freeze"] == ["live"] and {"live", "price_only", "placebo_1", "random_5"} <= set(main_s["agents"])
    main, off = worlds()  # real Worlds, built with the default window
    for name, world, want in (("main", main, main_s), ("older_vintage", off, older_s)):
        agents, freeze = R.agents_of(name, {"band": 15, "hold": 5})
        assert simulator.settings_many(world, agents, R.dev.COST, R.caller_settings(name), freeze) == want
    assert "sealed_part" not in R.caller_settings("main", last="2019-12-31", data={})  # the dev check: no part


def test_a_lock_git_ignores_or_drops_is_refused(tmp_path):
    """M4 judge J4-2: the lock must be tracked in HEAD, the commit that adds it alone."""
    repo = make_repo(tmp_path)
    seal.write({"main": MAIN}, root=repo)
    (repo / ".git" / "info").mkdir(exist_ok=True)
    with open(repo / ".git" / "info" / "exclude", "a") as f:
        f.write("seal.lock\n")
    assert not seal.Git(repo).dirty()  # ignored, so the tree looks clean
    with pytest.raises(seal.SealError, match="commit"):
        seal.check(START, END, MAIN, root=repo)
    git(repo, "add", "-f", "seal.lock")
    git(repo, "commit", "-q", "-m", "the seal")
    seal.check(START, END, MAIN, root=repo)
    git(repo, "rm", "-q", "--cached", "seal.lock")
    git(repo, "commit", "-q", "-m", "drop the lock from git, keep the file")
    with pytest.raises(seal.SealError, match="commit"):
        seal.check(START, END, MAIN, root=repo)


def test_a_sealed_run_must_run_the_dates_its_settings_name(sealed_repo):
    """M4 judge J4-4."""
    main, _ = worlds()
    s = part("main", "2016-01-04", END)
    seal.write({"main": simulator.settings_many(main, {"live": Looks()}, settings=s)})
    commit_lock(sealed_repo)
    with pytest.raises(seal.SealError, match="name its dates"):
        simulator.run_many(main, {"live": Looks()}, START, "2017-03-03", settings=s)
    assert seal.started() == [] and main.allow_sealed is False


def test_a_sealed_replay_needs_a_started_run_with_its_settings(sealed_repo):
    """M4 judge J4-3."""
    main, _ = worlds()
    full = simulator.settings_many(main, {"live": Looks()}, settings=part("main"))
    seal.write({"main": full})
    commit_lock(sealed_repo)
    days = Clock().between(FIRST, LAST)
    fake = simulator.Run(pd.DataFrame(columns=["date", "entity_id", "share_class", "prediction", "position"]),
                         pd.DataFrame({"date": days}), {})
    with pytest.raises(seal.SealError, match="has started"):
        simulator.replay(main, fake, costs=(0.0,), settings=full)
    simulator.run_many(main, {"live": Looks()}, FIRST, LAST, settings=part("main"))
    assert len(simulator.replay(main, fake, costs=(0.0,), settings=full)[0.0]) == len(days)


def test_the_sealed_ledger_stays_out_of_git_until_it_is_copied(sealed_repo, tmp_path, monkeypatch):
    """M4 judge J4-1: a ledger row in the repo would dirty the tree and stop the next part, so the sealed runs write
    theirs outside git and `ledger` copies them in at the end."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
    import m4_sealed_run as R
    from eval import trials
    main, off = worlds()
    parts = {"main": simulator.settings_many(main, {"live": Looks()}, settings=part("main")),
             "older_vintage": simulator.settings_many(off, {"live_older_vintage": Looks()},
                                                      settings=part("older_vintage"))}
    (sealed_repo / "runs").mkdir()
    (sealed_repo / "runs" / "trials.csv").write_text(",".join(trials.COLUMNS) + "\n")
    git(sealed_repo, "add", "-A")
    git(sealed_repo, "commit", "-q", "-m", "the ledger")
    seal.write(parts)
    commit_lock(sealed_repo)
    ledger = tmp_path / "ledger"
    g = seal.Git(sealed_repo)
    simulator.run_many(main, {"live": Looks()}, FIRST, LAST, settings=part("main"))
    trials.record(parts["main"], FIRST, LAST, ["live"], tmp_path / "out", runs=ledger, git=g)
    simulator.run_many(off, {"live_older_vintage": Looks()}, FIRST, LAST, settings=part("older_vintage"))
    trials.record(parts["older_vintage"], FIRST, LAST, ["live_older_vintage"], tmp_path / "out", runs=ledger, git=g)
    assert not g.dirty()
    added = R.ledger_step(ledger, sealed_repo / "runs")
    assert len(added) == 2 and len(trials.rows(sealed_repo / "runs")) == 2
    assert R.ledger_step(ledger, sealed_repo / "runs") == []  # copied once
    assert {f.name for f in (sealed_repo / "runs" / "settings").iterdir()} == {
        f"{seal.settings_hash(s)}.json" for s in parts.values()}
