"""The seal (PLAN 5.5 item 4 and 9.12): the runner refuses any date in the sealed years unless `seal.lock` matches the
run's settings, `PREREG.md` and the git commit, and the working tree is clean. The sealed years start on
reference/split.json's sealed start (2020-01-02).

`seal.lock` is JSON: {"settings": {part: sha256 of that part's settings}, "prereg": sha256 of PREREG.md, "commit":
the sealed commit, plus the sealed dates and when it was written}. `settings` may also be a single hash, for a lock
with one part.

The lock and git (M4 step 1). The lock records the commit it seals, so it can't be part of that commit. It is
committed alone, straight after: the check accepts HEAD only when HEAD's one parent is the sealed commit, HEAD
changes `seal.lock` and nothing else, and `seal.lock` is tracked. With the clean tree, the lock read is the one in
git. Any other commit after the seal breaks the match, and an uncommitted lock is refused, even one git ignores
(M4 judge J4-2).

The dates. A sealed run's settings carry its first and last sessions, and the runner refuses a run whose arguments
differ (J4-4), so the lock fixes the sealed window.

The parts (M4 decision 2). The sealed event has named parts (PARTS): "main" (the live agent, its twins, the placebo
and the baselines) and "older_vintage" (the live agent on the older table, research/audit/cutoff.md 10.1). A run in
the sealed years names its part in its settings as "sealed_part", and the lock holds one settings hash per part.

Once (PLAN 9.12). `begin` writes each sealed run's start to the run log before any sealed view opens:
DATA_DIR/sealed/runs.jsonl, shared by every checkout and outside git. A part that has started before is refused, even
if that run crashed, unless the caller passes again=True. Such a run is logged with again true, and the sealed runner
records it as another trial. `replay` in the sealed years needs a logged start with the same settings (J4-3). The
Simulator itself is not guarded: the guard is on sim.simulator's run, run_many and replay."""
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARTS = ("main", "older_vintage")
LOCK = "seal.lock"
RUNS_LOG = None  # the run log's path; None means DATA_DIR/sealed/runs.jsonl (tests point it elsewhere)


class SealError(RuntimeError):
    pass


def _root(root):
    return Path(root) if root is not None else ROOT


def _split(root=None):
    return json.loads((_root(root) / "reference" / "split.json").read_text(encoding="utf-8"))["periods"]["sealed"]


def sealed_start(root=None):
    return pd.Timestamp(_split(root)["start"])


def settings_hash(settings):
    return hashlib.sha256(json.dumps(settings, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def prereg_hash(root=None):
    p = _root(root) / "PREREG.md"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def runs_log():
    if RUNS_LOG is not None:
        return Path(RUNS_LOG)
    from data_pipeline.settings import DATA_DIR
    return DATA_DIR / "sealed" / "runs.jsonl"


class Git:
    def __init__(self, root=None):
        self.root = _root(root)

    def _git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True,
                              check=True).stdout

    def head(self):
        return self._git("rev-parse", "HEAD").strip()

    def dirty(self):
        return bool(self._git("status", "--porcelain").strip())

    def parents(self, rev):
        return self._git("rev-list", "--parents", "-n", "1", rev).split()[1:]

    def tracked(self, path):
        return subprocess.run(["git", "-C", str(self.root), "ls-files", "--error-unmatch", "--", path],
                              capture_output=True, text=True).returncode == 0

    def changed(self, rev):
        """The paths `rev` changes against its first parent."""
        return sorted(self._git("diff-tree", "--no-commit-id", "--name-only", "-r", rev).split())


def _now(now=None):
    return (now or datetime.now(ZoneInfo("America/New_York"))).strftime("%Y-%m-%dT%H:%M:%S")


def _commit_matches(sealed, git):
    """HEAD is the lock's own commit: its one parent is the sealed commit, it changes seal.lock alone, and seal.lock
    is tracked (so not deleted at HEAD and kept as an ignored file)."""
    head = git.head()
    return bool(sealed) and git.parents(head) == [sealed] and git.changed(head) == [LOCK] and git.tracked(LOCK)


def _part_hash(lock, settings):
    s = lock.get("settings")
    return s.get(settings.get("sealed_part")) if isinstance(s, dict) else s


def check(first, last, settings, root=None, git=None):
    """Return quietly if the dates stay before the sealed years or the seal holds; raise SealError otherwise."""
    root = _root(root)
    if pd.Timestamp(last) < sealed_start(root):
        return
    lock_path = root / LOCK
    if not lock_path.exists():
        raise SealError(f"{first} to {last} reaches the sealed years, and there is no seal.lock")
    if settings is None:
        raise SealError("a run in the sealed years needs its settings, to check them against seal.lock")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    git = git or Git(root)
    wrong = [k for k, ok in (("settings", _part_hash(lock, settings) == settings_hash(settings)),
                             ("prereg", lock.get("prereg") == prereg_hash(root)),
                             ("commit", _commit_matches(lock.get("commit"), git))) if not ok]
    if wrong:
        raise SealError(f"seal.lock doesn't match: {', '.join(wrong)}")
    if git.dirty():
        raise SealError("the working tree isn't clean")


def write(parts, root=None, git=None, now=None):
    """Write seal.lock for the sealed commit (HEAD) from {part: that part's full run settings}, as
    sim.simulator.settings_many gives them. Refuses a lock that exists, a missing PREREG.md, a dirty tree, an unknown
    part, a part whose settings name another part, and a lock without "main". Commit the lock alone straight after."""
    root = _root(root)
    git = git or Git(root)
    if (root / LOCK).exists():
        raise SealError("seal.lock exists already: the seal is written once")
    if prereg_hash(root) is None:
        raise SealError("there is no PREREG.md to seal")
    if git.dirty():
        raise SealError("the working tree isn't clean: commit the code and PREREG.md first")
    if "main" not in parts or set(parts) - set(PARTS):
        raise SealError(f"the parts are {PARTS}, with main among them; got {sorted(parts)}")
    for name, s in parts.items():
        if s.get("sealed_part") != name:
            raise SealError(f"the {name} part's settings name the part {s.get('sealed_part')!r}")
    split = _split(root)
    lock = {"settings": {name: settings_hash(s) for name, s in parts.items()}, "prereg": prereg_hash(root),
            "commit": git.head(), "sealed_start": split["start"], "sealed_end": split.get("end"),
            "written_at": _now(now)}
    (root / LOCK).write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return lock


def started(log=None):
    """The run log's entries, oldest first."""
    path = Path(log) if log is not None else runs_log()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require_started(settings, log=None):
    """For replay in the sealed years (J4-3): the run log must hold a start of the settings' part with the same
    settings hash."""
    part, h = (settings or {}).get("sealed_part"), settings_hash(settings)
    if not any(e.get("part") == part and e.get("settings_hash") == h for e in started(log)):
        raise SealError(f"no sealed {part!r} run with these settings has started: a replay in the sealed years "
                        "replays a sealed run")


def begin(settings, again=False, root=None, git=None, log=None, now=None):
    """Record the start of a sealed run in the run log, after `check` has passed and before any sealed view opens.
    Refuses a part that started before unless again=True, and again=True for a part that never started. Returns the
    entry."""
    part = (settings or {}).get("sealed_part")
    if part not in PARTS:
        raise SealError(f"a run in the sealed years names its part, one of {PARTS}, as sealed_part; got {part!r}")
    path = Path(log) if log is not None else runs_log()
    earlier = [e for e in started(path) if e.get("part") == part]
    if earlier and not again:
        raise SealError(f"the sealed {part} run started already, on {earlier[0]['started_at']}: a second run needs "
                        "again=True and counts as another trial (PLAN 9.12)")
    if again and not earlier:
        raise SealError(f"again=True, but the sealed {part} run has never started")
    git = git or Git(root)
    entry = {"part": part, "n": len(earlier) + 1, "again": bool(again), "started_at": _now(now),
             "commit": git.head(), "settings_hash": settings_hash(settings)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry
