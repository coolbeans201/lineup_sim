"""Bundled nflverse player-season JSON (1999+ modern era)."""

from __future__ import annotations

import json
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parents[3] / "data" / "bundled" / "nfl"
NFLVERSE_BUNDLE_PATH = BUNDLE_DIR / "nflverse" / "player_seasons.json"
LEGACY_BUNDLE_PATH = BUNDLE_DIR / "player_seasons.json"
NFLVERSE_START = 1999
NFLVERSE_END = 2024
MIN_GAMES = 8


def _bundle_path() -> Path | None:
    if NFLVERSE_BUNDLE_PATH.is_file():
        return NFLVERSE_BUNDLE_PATH
    if LEGACY_BUNDLE_PATH.is_file():
        return LEGACY_BUNDLE_PATH
    return None


def has_nflverse_bundled_data() -> bool:
    return _bundle_path() is not None


def has_bundled_data() -> bool:
    """Backward-compatible alias for nflverse bundle presence."""
    return has_nflverse_bundled_data()


def load_bundled_rows() -> list[dict]:
    path = _bundle_path()
    if path is None:
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_bundled_rows(rows: list[dict]) -> Path:
    NFLVERSE_BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NFLVERSE_BUNDLE_PATH.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    return NFLVERSE_BUNDLE_PATH
