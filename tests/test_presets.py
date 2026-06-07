"""Preset slot ordering and position pool tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.presets import get_preset, load_presets
from lineup_sim.sports.nba.plugin import NBAPlugin
from lineup_sim.sports.nba.positions import eligible_lineup_positions, position_matches


def test_nba_all_eras_five_position_slots():
    load_presets(force=True)
    preset = get_preset("nba_all_eras")
    assert preset.slot_count == 5
    positions = [s.position for s in preset.slots]
    assert positions == ["PG", "SG", "SF", "PF", "C"]


def test_multi_position_player_fits_multiple_slots():
    oscar = PlayerSeason(
        player_id="oscar",
        player_name="Oscar Robertson",
        team="Royals",
        team_abbr="SAC",
        season=1965,
        position="PG",
        position_raw="PG-SG",
        stats={"PTS": 30, "REB": 10, "AST": 11, "STL": 0, "BLK": 0},
    )
    assert position_matches(oscar.position_raw, "PG")
    assert position_matches(oscar.position_raw, "SG")
    assert not position_matches(oscar.position_raw, "C")
    assert eligible_lineup_positions(oscar.position_raw) >= {"PG", "SG"}


def test_each_position_slot_has_pool():
    load_presets(force=True)
    preset = get_preset("nba_all_eras")
    plugin = NBAPlugin()
    plugin.reload_pool()
    pool = plugin.load_player_pool()

    for slot in preset.slots:
        count = sum(
            1
            for p in pool
            if slot.position
            and plugin.position_matches(p.position_raw or p.position, slot.position)
        )
        assert count >= 3, f"{slot.label} only has {count} eligible players"
