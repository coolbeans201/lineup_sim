"""Spin constraint tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.constraints import pool_for_spin
from lineup_sim.core.spin_options import spin_options_for_slot
from lineup_sim.core.presets import get_preset
from lineup_sim.sports.nba.plugin import NBAPlugin


def test_spin_options_for_slot_lists_players():
    preset = get_preset("nba_all_eras")
    pool = NBAPlugin().load_player_pool()
    slot = preset.slots[0]

    options = spin_options_for_slot(preset, slot, pool)
    assert options
    assert all(
        pool_for_spin(pool, spin, sport="nba")
        for spin in options[:5]
    )
