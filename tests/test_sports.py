"""Multi-sport scoring and leaderboard tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import assign_player, empty_lineup
from lineup_sim.core.scoring import score_lineup
from lineup_sim.daily.leaderboard import entries_for_day, submit_entry
from lineup_sim.sports.mlb.plugin import MLBPlugin
from lineup_sim.sports.nfl.plugin import NFLPlugin


def test_nfl_lineup_scores():
    preset = get_preset("nfl_two_way")
    pool = {p.player_name: p for p in NFLPlugin().load_player_pool()}
    lineup = empty_lineup(preset)
    lineup = assign_player(lineup, preset, "qb", pool["Patrick Mahomes"])
    lineup = assign_player(lineup, preset, "edge", pool["T.J. Watt"])
    score = score_lineup(lineup, NFLPlugin().load_player_pool())
    assert score.team_rating != 0
    assert score.max_games == 17


def test_mlb_lineup_scores():
    preset = get_preset("mlb_battery")
    pool = {p.player_name: p for p in MLBPlugin().load_player_pool()}
    lineup = empty_lineup(preset)
    lineup = assign_player(lineup, preset, "h1", pool["Aaron Judge"])
    lineup = assign_player(lineup, preset, "sp", pool["Clayton Kershaw"])
    score = score_lineup(lineup, MLBPlugin().load_player_pool())
    assert score.team_rating != 0
    assert score.max_games == 162


def test_leaderboard_submit_and_list():
    entry = submit_entry(
        date="2099-01-01",
        sport="nba",
        preset_slug="nba_all_eras",
        player_name="Test User",
        team_rating=1.5,
        projected_wins=70.0,
        grade="A+",
        lineup_summary="Test lineup",
    )
    rows = entries_for_day("2099-01-01", "nba", "nba_all_eras")
    assert any(r.share_code == entry.share_code for r in rows)
