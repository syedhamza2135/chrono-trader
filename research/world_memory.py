"""What World.load costs with the embeddings (judge J-3): the time to load, the process's private memory, and the
time and size of a view in each period. Also checks the .npy arrays against embeddings.parquet on three row groups.
Prints counts, times and sizes only. Windows only (it reads the memory through psapi).
Usage: python research/world_memory.py [DAYS | all]
DAYS is the World's embedding window (M3 decision 1; the World's default, 90, when left out). `all` serves every
visible row, as M2 measured (research/audit/reader.md).
"""
import ctypes
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from data_pipeline.settings import DATA_DIR  # noqa: E402
from world.world import EMBEDDING_WINDOW_DAYS, World  # noqa: E402


class _Counters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


def memory():
    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    c = _Counters()
    c.cb = ctypes.sizeof(c)
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return f"private memory {c.PagefileUsage / 2**30:.2f} GB (peak {c.PeakPagefileUsage / 2**30:.2f})"


def main():
    store = DATA_DIR / "store"
    f = pq.ParquetFile(store / "embeddings.parquet")
    arrays = {c: np.load(store / n, mmap_mode="r") for c, n in (("emb_last", "embeddings_last.npy"),
                                                                ("emb_avg", "embeddings_avg.npy"))}
    start, same, groups = 0, True, f.num_row_groups
    for g in range(groups):
        n = f.metadata.row_group(g).num_rows
        if g in (0, groups // 2, groups - 1):
            t = f.read_row_group(g, columns=list(arrays))
            for c, a in arrays.items():
                x = t.column(c).combine_chunks().flatten().to_numpy(zero_copy_only=False).reshape(n, -1)
                same &= bool(np.array_equal(x, a[start:start + n]))
        start += n
    print(f"arrays equal embeddings.parquet on its first, middle and last of {groups} row groups: {same}")
    del arrays
    t0 = time.time()
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    window = None if arg == "all" else (int(arg) if arg else EMBEDDING_WINDOW_DAYS)
    w = World.load(allow_sealed=True, embedding_window_days=window)
    print(f"World.load with embeddings (window: {window if window else 'every row'}): {time.time() - t0:.0f} s, "
          f"{memory()}")
    split = json.loads((ROOT / "reference" / "split.json").read_text(encoding="utf-8"))["periods"]
    for name in ("warm_up", "dev", "sealed"):
        day = w.clock.between(split[name]["start"], split[name]["end"])[-1]
        t0 = time.time()
        v = w.view(w.clock.decision_time(day))
        print(f"view on {pd.Timestamp(day).date()} (last session of {name}): {time.time() - t0:.1f} s, {memory()},"
              f" {len(v.embeddings)} embeddings, {v.embeddings.last.nbytes + v.embeddings.avg.nbytes:,} bytes of vectors")
        del v


if __name__ == "__main__":
    main()
