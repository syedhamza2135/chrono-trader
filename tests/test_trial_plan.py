"""M3 step 6, phase 1: the frozen trial plan's hash and its planned ledger rows (research/m3_trial_plan.py)."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import m3_trial_plan as plan  # noqa: E402


def test_the_hash_covers_the_block_only_and_ignores_line_endings(tmp_path):
    text = f"before\n{plan.START}\nline one\nline two\n{plan.END}\nafter\n"
    want = hashlib.sha256(f"{plan.START}\nline one\nline two\n{plan.END}\n".encode("utf-8")).hexdigest()
    a, b, c = tmp_path / "a.md", tmp_path / "b.md", tmp_path / "c.md"
    a.write_text(text, encoding="utf-8")
    b.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    c.write_text(text.replace("after", "changed after"), encoding="utf-8")
    assert plan.plan_hash(a) == plan.plan_hash(b) == plan.plan_hash(c) == want
    a.write_text(text.replace("line two", "line 2"), encoding="utf-8")
    assert plan.plan_hash(a) != want


def test_the_note_holds_the_plan_and_its_recorded_hash():
    text = plan.NOTE.read_text(encoding="utf-8")
    h = plan.plan_hash()
    assert text.count(plan.START) == 1 and text.count(plan.END) == 1
    assert h in text  # the recorded hash is the block's


def test_eight_trials_in_two_stages_and_t04_dropped():
    s = plan.planned_settings("h")
    assert sorted(s) == [f"T0{i}" for i in range(1, 10)]
    live = [t for t, v in s.items() if not v.get("dropped")]
    assert sorted(live) == ["T01", "T02", "T03", "T05", "T06", "T07", "T08", "T09"] and s["T04"]["dropped"]
    assert [s[t]["stage"] for t in sorted(live)] == [1] * 3 + [2] * 5
    assert s["T03"]["variant"] == {"half_life_days": 252} and s["T02"]["variant"] == {"coefficients": "averaged"}
    assert s["T01"]["variant"] == {} and s["T07"]["variant"] == {"band": 15}
    assert all(v["first"] == "2016-01-04" and v["last"] == "2019-12-31" and v["plan_sha256"] == "h"
               for v in s.values())
