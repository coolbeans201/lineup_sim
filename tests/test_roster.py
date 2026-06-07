"""Roster assignment rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import assign_player, assigned_identities, empty_lineup, player_identity


def _player(name: str, season: int, *, player_id: str | None = None) -> PlayerSeason:
    return PlayerSeason(
        player_id=player_id or f"{name.lower().replace(' ', '_')}_{season}",
        player_name=name,
        team="Test Team",
        team_abbr="TST",
        season=season,
        position="PG",
        position_raw="PG",
        stats={"PTS": season, "REB": 5, "AST": 5, "STL": 1, "BLK": 0},
        decade="2000s",
    )


def test_player_identity_ignores_season():
    a = _player("Allen Iverson", 2001)
    b = _player("Allen Iverson", 2006, player_id="other")
    assert player_identity(a) == player_identity(b)


def test_assign_player_clears_same_player_from_other_slots():
    preset = get_preset("nba_all_eras")
    lineup = empty_lineup(preset)
    first = _player("Allen Iverson", 2001)
    second = _player("Allen Iverson", 2006, player_id="ai2006")
    combo = PlayerSeason(
        player_id="oscar",
        player_name="Oscar Robertson",
        team="Royals",
        team_abbr="SAC",
        season=1965,
        position="PG",
        position_raw="PG-SG",
        stats={"PTS": 30, "REB": 10, "AST": 11, "STL": 0, "BLK": 0},
        decade="1960s",
    )

    lineup = assign_player(lineup, preset, "pg", combo)
    lineup = assign_player(lineup, preset, "sg", combo)

    by_slot = {a.slot_id: a.player for a in lineup.assignments}
    assert by_slot["pg"] is None
    assert by_slot["sg"] is not None

    lineup = assign_player(lineup, preset, "pg", first)
    lineup = assign_player(lineup, preset, "pg", second)

    by_slot = {a.slot_id: a.player for a in lineup.assignments}
    assert by_slot["pg"] is not None
    assert by_slot["pg"].season == 2006
    assert sum(1 for a in lineup.assignments if a.player and player_identity(a.player) == player_identity(first)) == 1


def test_assigned_identities_excludes_current_slot():
    preset = get_preset("nba_all_eras")
    lineup = assign_player(empty_lineup(preset), preset, "pg", _player("Allen Iverson", 2001))
    taken = assigned_identities(lineup, exclude_slot_id="pg")
    assert taken == set()
    taken_all = assigned_identities(lineup)
    assert player_identity(_player("Allen Iverson", 2001)) in taken_all
