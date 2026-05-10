"""Feedback loop: adjust category weights from observed performance.

You can drop a CSV at data/performance.csv with columns:
    category,clicks,conversions

Either fill it manually from your affiliate dashboard, or upload via a
GitHub Actions workflow that pulls reports. Without it, weights drift toward
1.0 (uniform) over time, which is a safe default.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .config import DATA_DIR


PERF_FILE = DATA_DIR / "performance.csv"


def update_weights(state: dict[str, Any]) -> dict[str, Any]:
    weights: dict[str, float] = dict(state.get("category_weights", {}))
    if not PERF_FILE.exists():
        # Soft decay toward 1.0 each run so weights don't get stuck.
        for k, v in list(weights.items()):
            weights[k] = round(v + (1.0 - v) * 0.1, 4)
        state["category_weights"] = weights
        return state

    totals: dict[str, dict[str, float]] = {}
    with PERF_FILE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row.get("category", "").strip()
            if not cat:
                continue
            try:
                clicks = float(row.get("clicks", 0) or 0)
                conv = float(row.get("conversions", 0) or 0)
            except ValueError:
                continue
            t = totals.setdefault(cat, {"clicks": 0.0, "conv": 0.0})
            t["clicks"] += clicks
            t["conv"] += conv

    if not totals:
        return state

    # Score = conversions weighted higher than clicks. Normalize so the mean
    # is 1.0, with clamps to keep the optimizer from collapsing the variety.
    raw: dict[str, float] = {}
    for cat, t in totals.items():
        raw[cat] = t["clicks"] * 1.0 + t["conv"] * 10.0

    mean = sum(raw.values()) / max(len(raw), 1)
    if mean > 0:
        for cat, score in raw.items():
            normalized = score / mean
            normalized = max(0.4, min(2.0, normalized))
            # Blend with previous weight so changes are gradual.
            prev = weights.get(cat, 1.0)
            weights[cat] = round(prev * 0.6 + normalized * 0.4, 4)

    state["category_weights"] = weights
    return state
