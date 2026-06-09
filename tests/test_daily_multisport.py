"""Daily puzzle tests across sports (require local bundles when marked)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.constraints import pool_for_spin
from lineup_sim.core.presets import get_preset
from lineup_sim.daily.seed import daily_puzzle
from lineup_sim.ingest.mlb import has_bundled_tenures
from lineup_sim.ingest.nfl_bundle import has_nflverse_bundled_data
from lineup_sim.sports.mlb.plugin import MLBPlugin
from lineup_sim.sports.nfl.plugin import NFLPlugin


@pytest.mark.parametrize("preset_slug", ["nba_all_eras", "nfl_offense", "mlb_modern", "mlb_classic"])
def test_daily_puzzle_spin_count_matches_slots(preset_slug: str):
    preset = get_preset(preset_slug)
    if preset.sport == "mlb" and not has_bundled_tenures():
        pytest.skip("MLB Lahman bundle not imported")
    if preset.sport == "nfl" and not has_nflverse_bundled_data():
        pytest.skip("NFL nflverse bundle not imported")
    puzzle = daily_puzzle(preset.sport, preset_slug, day="2026-06-05")
    assert len(puzzle.spins) == preset.slot_count


def test_mlb_classic_daily_spins_have_players_when_bundle_present():
    if not has_bundled_tenures():
        pytest.skip("MLB Lahman bundle not imported")
    preset = get_preset("mlb_classic")
    pool = MLBPlugin().load_player_pool()
    puzzle = daily_puzzle("mlb", "mlb_classic", day="2026-06-08")
    for slot, spin in zip(preset.slots, puzzle.spins):
        candidates = pool_for_spin(pool, spin, sport="mlb")
        assert candidates, f"{spin.team_abbr} {spin.era_label} empty for {slot.slot_id}"


def test_nfl_daily_spins_have_players_when_bundle_present():
    if not has_nflverse_bundled_data():
        pytest.skip("NFL nflverse bundle not imported")
    preset = get_preset("nfl_offense")
    pool = NFLPlugin().load_player_pool()
    puzzle = daily_puzzle("nfl", "nfl_offense", day="2026-06-09")
    for slot, spin in zip(preset.slots, puzzle.spins):
        candidates = pool_for_spin(pool, spin, sport="nfl")
        assert candidates, f"{spin.team_abbr} {spin.era_label} empty for {slot.slot_id}"
