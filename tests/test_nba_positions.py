"""Position normalization tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.peak import pick_peak_seasons
from lineup_sim.sports.nba.positions import (
    eligible_lineup_positions,
    parse_position_tokens,
    position_matches,
    primary_position,
)


def test_primary_position_from_bref_style():
    assert primary_position("PG-SG") == "PG"
    assert primary_position("F-C") == "PF"
    assert primary_position("C") == "C"


def test_position_matching_multi():
    assert position_matches("PG-SG", "SG")
    assert position_matches("PG-SG", "PG")
    assert position_matches("F-C", "PF")
    assert position_matches("F-C", "C")
    assert not position_matches("PG", "C")


def test_pure_pg_only_matches_pg():
    assert position_matches("PG", "PG")
    assert not position_matches("PG", "SG")
    assert not position_matches("PG", "SF")
    assert not position_matches("PG", "PF")


def test_guard_forward_combo():
    assert eligible_lineup_positions("G-F") == {"SG", "SF"}
    assert position_matches("G-F", "SF")
    assert not position_matches("G-F", "PG")


def test_parse_position_tokens():
    assert parse_position_tokens("G-F") == {"G", "F"}
    assert parse_position_tokens("PG-SG") == {"PG", "SG"}


def test_pick_peak_seasons_keeps_best_on_team_in_decade():
    rows = [
        PlayerSeason(
            player_id="a1",
            player_name="Allen Iverson",
            team="76ers",
            team_abbr="PHI",
            season=2001,
            position="PG",
            position_raw="SG",
            stats={"PTS": 31.1, "REB": 3.8, "AST": 4.6, "STL": 2.5, "BLK": 0.3},
            decade="2000s",
        ),
        PlayerSeason(
            player_id="a2",
            player_name="Allen Iverson",
            team="76ers",
            team_abbr="PHI",
            season=2002,
            position="PG",
            position_raw="SG",
            stats={"PTS": 27.6, "REB": 4.2, "AST": 5.5, "STL": 2.7, "BLK": 0.2},
            decade="2000s",
        ),
    ]
    peak = pick_peak_seasons(rows, "nba")
    assert len(peak) == 1
    assert peak[0].season == 2001


def test_load_pool_keeps_one_peak_per_player_team_decade():
    from lineup_sim.sports.nba.plugin import NBAPlugin

    plugin = NBAPlugin()
    plugin.reload_pool()
    pool = plugin.load_player_pool()
    wilts = [
        p
        for p in pool
        if p.player_name == "Wilt Chamberlain" and p.team_abbr == "GSW" and p.decade == "1960s"
    ]
    assert len(wilts) == 1
    assert wilts[0].season == 1962
