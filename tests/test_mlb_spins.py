"""MLB spin generation tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.constraints import generate_spins
from lineup_sim.core.presets import get_preset
from lineup_sim.ingest.mlb import has_bundled_tenures


@pytest.mark.skipif(not has_bundled_tenures(), reason="MLB Lahman bundle not imported")
def test_mlb_generate_spins_with_bundled_pool():
    preset = get_preset("mlb_modern")
    spins = generate_spins(preset, seed=42)
    assert len(spins) == preset.slot_count
    assert len({(s.team_abbr, s.era_label) for s in spins}) == preset.slot_count
