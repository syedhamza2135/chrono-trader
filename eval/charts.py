"""The dev report's charts (PLAN 9.10) as plain SVG line charts, since the venv has no plotting library: IC over
time, the frozen-twin gaps, equity curves against the matched baselines, and cost sensitivity."""
import math
from html import escape

import numpy as np
import pandas as pd

COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2", "#7f7f7f", "#17becf",
          "#bcbd22"]
W, H, LEFT, RIGHT, TOP, BOTTOM = 900, 420, 70, 190, 40, 50


def lines(series, title, path, ylabel="", zero=True):
    """Writes an SVG chart of {name: Series by date} to `path` and returns the path. Gaps (NaN) break a line."""
    series = {k: v.dropna().sort_index() for k, v in series.items() if v is not None and len(v.dropna())}
    xs = [s.index for s in series.values()]
    if not xs:
        raise ValueError("nothing to draw")
    x0 = min(x.min() for x in xs).value
    x1 = max(x.max() for x in xs).value
    vals = np.concatenate([s.to_numpy(dtype=float) for s in series.values()] + ([np.zeros(1)] if zero else []))
    y0, y1 = float(np.nanmin(vals)), float(np.nanmax(vals))
    if y1 == y0:
        y0, y1 = y0 - 1.0, y1 + 1.0
    pad = (y1 - y0) * 0.05
    y0, y1 = y0 - pad, y1 + pad
    pw, ph = W - LEFT - RIGHT, H - TOP - BOTTOM

    def px(t):
        return LEFT + (t - x0) / max(x1 - x0, 1) * pw

    def py(v):
        return TOP + (y1 - v) / (y1 - y0) * ph

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           'font-family="sans-serif" font-size="12">', f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{LEFT}" y="24" font-size="15">{escape(title)}</text>']
    for k in range(6):  # y grid and labels
        v = y0 + (y1 - y0) * k / 5
        out.append(f'<line x1="{LEFT}" x2="{LEFT + pw}" y1="{py(v):.1f}" y2="{py(v):.1f}" stroke="#e5e5e5"/>')
        out.append(f'<text x="{LEFT - 6}" y="{py(v) + 4:.1f}" text-anchor="end">{v:.3g}</text>')
    if zero and y0 < 0 < y1:
        out.append(f'<line x1="{LEFT}" x2="{LEFT + pw}" y1="{py(0):.1f}" y2="{py(0):.1f}" stroke="#999"/>')
    for y in range(pd.Timestamp(x0).year, pd.Timestamp(x1).year + 1):  # each year at its start, or the left edge
        t = max(pd.Timestamp(y, 1, 1).value, x0)
        out.append(f'<line x1="{px(t):.1f}" x2="{px(t):.1f}" y1="{TOP}" y2="{TOP + ph}" stroke="#e5e5e5"/>')
        out.append(f'<text x="{px(t):.1f}" y="{TOP + ph + 18}" text-anchor="start">{y}</text>')
    out.append(f'<rect x="{LEFT}" y="{TOP}" width="{pw}" height="{ph}" fill="none" stroke="#333"/>')
    if ylabel:
        out.append(f'<text x="16" y="{TOP + ph / 2:.0f}" transform="rotate(-90 16 {TOP + ph / 2:.0f})" '
                   f'text-anchor="middle">{escape(ylabel)}</text>')
    for i, (name, s) in enumerate(series.items()):
        col = COLORS[i % len(COLORS)]
        pts, segs = [], []
        for t, v in zip(s.index, s.to_numpy(dtype=float)):
            if math.isnan(v):
                if pts:
                    segs.append(pts)
                pts = []
                continue
            pts.append(f"{px(t.value):.1f},{py(v):.1f}")
        if pts:
            segs.append(pts)
        for seg in segs:
            out.append(f'<polyline fill="none" stroke="{col}" stroke-width="1.5" points="{" ".join(seg)}"/>')
        ly = TOP + 14 + 18 * i
        out.append(f'<line x1="{LEFT + pw + 12}" x2="{LEFT + pw + 32}" y1="{ly - 4}" y2="{ly - 4}" stroke="{col}" '
                   'stroke-width="2"/>')
        out.append(f'<text x="{LEFT + pw + 38}" y="{ly}">{escape(str(name))}</text>')
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return path


def wealth(r):
    """The wealth path of daily returns, starting at 1 before the first."""
    return (1.0 + r.fillna(0.0)).cumprod()
