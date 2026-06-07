"""NBA spin draft rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.constraints import eligible_for_slot, pool_for_spin
from lineup_sim.core.spin_options import spin_options_for_slot
from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import assign_player, eligible_open_slots, empty_lineup
from lineup_sim.sports.nba.plugin import NBAPlugin


def test_nba_spin_pool_is_not_position_filtered():
    preset = get_preset("nba_all_eras")
    pool = NBAPlugin().load_player_pool()
    slot = preset.slots[0]

    lal_1960s = next(
        spin
        for spin in spin_options_for_slot(preset, slot, pool)
        if spin.team_abbr == "LAL" and spin.era_label == "1960s"
    )
    spin_pool = pool_for_spin(pool, lal_1960s, sport="nba")
    positions = {p.position for p in spin_pool}
    assert len(spin_pool) > 1
    assert positions != {"PG"}


def test_nba_spin_assignment_requires_valid_position():
    preset = get_preset("nba_all_eras")
    pg_slot = preset.slots[0]
    c_slot = next(s for s in preset.slots if s.position == "C")
    wilt = PlayerSeason(
        player_id="wilt62",
        player_name="Wilt Chamberlain",
        team="Philadelphia Warriors",
        team_abbr="PHI",
        season=1962,
        position="C",
        position_raw="C",
        stats={"PTS": 50.4, "REB": 25.7, "AST": 2.4, "STL": 0.0, "BLK": 0.0},
        decade="1960s",
    )
    assert not eligible_for_slot(wilt, pg_slot, "nba")
    assert eligible_for_slot(wilt, c_slot, "nba")

    lineup = empty_lineup(preset)
    assert eligible_open_slots(wilt, lineup, preset, "nba") == [c_slot]
    lineup = assign_player(lineup, preset, c_slot.slot_id, wilt)
    assert next(a.player for a in lineup.assignments if a.slot_id == c_slot.slot_id) is wilt


def test_open_slots_shrink_as_lineup_fills():
    preset = get_preset("nba_all_eras")
    lineup = empty_lineup(preset)
    from lineup_sim.core.roster import open_slots

    assert len(open_slots(lineup, preset)) == 5
    lineup = assign_player(lineup, preset, "pg", _sample_player("Oscar Robertson", "PG", "PG-SG"))
    assert len(open_slots(lineup, preset)) == 4


def test_dual_position_player_has_multiple_open_slots():
    preset = get_preset("nba_all_eras")
    lineup = empty_lineup(preset)
    oscar = _sample_player("Oscar Robertson", "PG", "PG-SG")
    eligible = eligible_open_slots(oscar, lineup, preset, "nba")
    positions = {slot.position for slot in eligible}
    assert positions == {"PG", "SG"}


def _sample_player(name: str, position: str, position_raw: str) -> PlayerSeason:
    return PlayerSeason(
        player_id=name.lower().replace(" ", "_"),
        player_name=name,
        team="Test Team",
        team_abbr="TST",
        season=1965,
        position=position,
        position_raw=position_raw,
        stats={"PTS": 25, "REB": 5, "AST": 8, "STL": 1, "BLK": 0},
        decade="1960s",
    )
