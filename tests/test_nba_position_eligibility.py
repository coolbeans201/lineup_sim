"""Career position eligibility from BRef per-game rows."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.nba_position_eligibility import (
    apply_career_position,
    build_career_position_map,
    combo_from_slots,
    load_career_position_overrides,
    merge_career_position_maps,
    slots_from_pos_label,
)
from lineup_sim.sports.nba.plugin import NBAPlugin
from lineup_sim.sports.nba.positions import eligible_lineup_positions


def test_combo_from_slots_orders_canonical():
    assert combo_from_slots({"C", "PG", "SF"}) == "PG-SF-C"


def test_build_career_position_map_unions_season_labels():
    records = [
        {"player_name": "LeBron James", "pos": "SF", "season": 2004},
        {"player_name": "LeBron James", "pos": "PG", "season": 2020},
        {"player_name": "LeBron James", "pos": "C", "season": 2022},
        {"player_name": "LeBron James", "pos": "PF", "season": 2023},
        {"player_name": "LeBron James", "pos": "SG", "season": 2005},
    ]
    career = build_career_position_map(records)
    assert career["lebron james"] == "PG-SG-SF-PF-C"
    assert eligible_lineup_positions(career["lebron james"]) == {
        "PG",
        "SG",
        "SF",
        "PF",
        "C",
    }


def test_fixture_override_adds_oscar_pg_sg():
    records = [{"player_name": "Oscar Robertson", "pos": "PG", "season": 1964}]
    career = merge_career_position_maps(
        build_career_position_map(records),
        load_career_position_overrides(),
    )
    assert eligible_lineup_positions(career["oscar robertson"]) == {"PG", "SG"}


def test_apply_career_position_updates_row():
    row = apply_career_position(
        {"player_name": "Jerry West", "position_raw": "PG", "position": "PG"},
        {"jerry west": "PG-SG"},
    )
    assert row["position_raw"] == "PG-SG"
    assert row["position"] == "PG"


def test_live_pool_has_multi_position_players():
    plugin = NBAPlugin()
    plugin.reload_pool()
    pool = plugin.load_player_pool()
    multi = [
        p
        for p in pool
        if len(eligible_lineup_positions(p.position_raw or p.position)) > 1
    ]
    assert len(multi) > 100

    lebron = next(p for p in pool if p.player_name == "LeBron James" and p.season == 2012)
    assert eligible_lineup_positions(lebron.position_raw) == {"PG", "SG", "SF", "PF", "C"}

    jerry = next(p for p in pool if p.player_name == "Jerry West")
    assert eligible_lineup_positions(jerry.position_raw) == {"PG", "SG"}

    oscar = next(p for p in pool if p.player_name == "Oscar Robertson")
    assert eligible_lineup_positions(oscar.position_raw) == {"PG", "SG"}
