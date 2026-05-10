"""Persistent state store - tracks topics covered, performance hints, etc."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR


STATE_FILE = DATA_DIR / "state.json"


def _default_state() -> dict[str, Any]:
    return {
        "covered_topics": [],
        "topic_performance": {},  # topic -> {"clicks": int, "score": float}
        "last_run": None,
        "post_count": 0,
        "category_weights": {
            "ガジェット": 1.0,
            "キッチン用品": 1.0,
            "美容・健康": 1.0,
            "本・学習": 1.0,
            "在宅ワーク": 1.0,
            "アウトドア": 1.0,
        },
    }


def load() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return _default_state()
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults so newly added keys don't break old state.
        merged = _default_state()
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return _default_state()


def save(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(STATE_FILE)
