"""Roster assignment rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import (
    assign_player,
    assigned_identities,
    eligible_reassign_slots,
    empty_lineup,
    player_identity,
    reassign_player,
    swap_plans_for_new_pick,
)


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


def test_reassign_multi_position_player_frees_slot():
    preset = get_preset("nba_all_eras")
    lebron = PlayerSeason(
        player_id="lebron",
        player_name="LeBron James",
        team="Lakers",
        team_abbr="LAL",
        season=2020,
        position="SF",
        position_raw="PG-SG-SF-PF-C",
        stats={"PTS": 25, "REB": 7, "AST": 10, "STL": 1, "BLK": 1},
        decade="2020s",
    )
    wilt = PlayerSeason(
        player_id="wilt",
        player_name="Wilt Chamberlain",
        team="Warriors",
        team_abbr="GSW",
        season=1962,
        position="C",
        position_raw="C",
        stats={"PTS": 50, "REB": 25, "AST": 2, "STL": 0, "BLK": 0},
        decade="1960s",
    )
    lineup = empty_lineup(preset)
    lineup = assign_player(lineup, preset, "sf", lebron)
    lineup = assign_player(lineup, preset, "c", wilt)

    targets = eligible_reassign_slots(lebron, lineup, preset, "nba", from_slot_id="sf")
    assert {slot.slot_id for slot in targets} == {"pg", "sg", "pf"}

    lineup = reassign_player(lineup, preset, from_slot_id="sf", to_slot_id="pg")
    by_slot = {a.slot_id: a.player for a in lineup.assignments}
    assert by_slot["sf"] is None
    assert by_slot["pg"].player_name == "LeBron James"
    assert by_slot["c"].player_name == "Wilt Chamberlain"


def test_swap_plans_for_new_pick_when_only_occupied_slot_fits():
    preset = get_preset("nba_all_eras")
    lebron = PlayerSeason(
        player_id="lebron",
        player_name="LeBron James",
        team="Lakers",
        team_abbr="LAL",
        season=2020,
        position="SF",
        position_raw="PG-SG-SF-PF-C",
        stats={"PTS": 25, "REB": 7, "AST": 10, "STL": 1, "BLK": 1},
        decade="2020s",
    )
    sf_only = PlayerSeason(
        player_id="kawhi",
        player_name="Kawhi Leonard",
        team="Clippers",
        team_abbr="LAC",
        season=2021,
        position="SF",
        position_raw="SF",
        stats={"PTS": 24, "REB": 6, "AST": 5, "STL": 1, "BLK": 1},
        decade="2020s",
    )
    lineup = empty_lineup(preset)
    lineup = assign_player(lineup, preset, "sf", lebron)

    plans = swap_plans_for_new_pick(sf_only, lineup, preset, "nba")
    assert len(plans) >= 1
    plan = next(p for p in plans if p.assign_slot_id == "sf")
    assert plan.occupant.player_name == "LeBron James"
    assert plan.move_to_slot_id in {"pg", "sg", "pf", "c"}


def test_assigned_identities_excludes_current_slot():
    preset = get_preset("nba_all_eras")
    lineup = assign_player(empty_lineup(preset), preset, "pg", _player("Allen Iverson", 2001))
    taken = assigned_identities(lineup, exclude_slot_id="pg")
    assert taken == set()
    taken_all = assigned_identities(lineup)
    assert player_identity(_player("Allen Iverson", 2001)) in taken_all
