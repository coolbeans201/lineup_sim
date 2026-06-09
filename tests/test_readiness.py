"""Data readiness helper tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.readiness import import_command_hint, sport_pool_ready


def test_import_command_hints_are_sport_specific():
    assert "lahman" in import_command_hint("mlb").lower()
    assert "bref" in import_command_hint("nba").lower()
    assert "bootstrap" in import_command_hint("nfl").lower()


def test_mlb_not_ready_without_bundle():
    ready, message = sport_pool_ready("mlb", pool_size=18)
    if ready:
        return
    assert message is not None
    assert "Lahman" in message
