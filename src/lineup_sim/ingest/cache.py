"""Disk cache for API responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"


def cache_path(sport: str, name: str) -> Path:
    path = CACHE_DIR / sport / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_cache(sport: str, name: str) -> Any | None:
    path = cache_path(sport, name)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_cache(sport: str, name: str, payload: Any) -> Path:
    path = cache_path(sport, name)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path
