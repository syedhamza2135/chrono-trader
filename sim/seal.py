"""The seal (PLAN 9.12): the runner refuses any date in the sealed years unless `seal.lock` matches the run's
settings, `PREREG.md` and the git commit, and the working tree is clean.

`seal.lock` is JSON: {"settings": sha256 of the settings, "prereg": sha256 of PREREG.md, "commit": the git commit}.
The sealed years start on reference/split.json's sealed start (2020-01-02)."""
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class SealError(RuntimeError):
    pass


def sealed_start(root=ROOT):
    split = json.loads((root / "reference" / "split.json").read_text(encoding="utf-8"))
    return pd.Timestamp(split["periods"]["sealed"]["start"])


def settings_hash(settings):
    return hashlib.sha256(json.dumps(settings, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class Git:
    def __init__(self, root=ROOT):
        self.root = root

    def head(self):
        return subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()

    def dirty(self):
        out = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain"], capture_output=True, text=True,
                             check=True).stdout
        return bool(out.strip())


def check(first, last, settings, root=ROOT, git=None):
    """Return quietly if the dates stay before the sealed years or the seal holds; raise SealError otherwise."""
    if pd.Timestamp(last) < sealed_start(root):
        return
    lock_path = root / "seal.lock"
    if not lock_path.exists():
        raise SealError(f"{first} to {last} reaches the sealed years, and there is no seal.lock")
    if settings is None:
        raise SealError("a run in the sealed years needs its settings, to check them against seal.lock")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    prereg = root / "PREREG.md"
    git = git or Git(root)
    found = {"settings": settings_hash(settings),
             "prereg": hashlib.sha256(prereg.read_bytes()).hexdigest() if prereg.exists() else None,
             "commit": git.head()}
    wrong = [k for k, v in found.items() if lock.get(k) != v]
    if wrong:
        raise SealError(f"seal.lock doesn't match: {', '.join(wrong)}")
    if git.dirty():
        raise SealError("the working tree isn't clean")
