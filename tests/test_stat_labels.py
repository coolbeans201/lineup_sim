"""Stat display labels and projected record formatting."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.stat_labels import (
    era_column_label,
    format_projected_record,
    format_stat_display_string,
    format_stat_display_value,
    integer_record,
    player_era_display,
    stat_accumulates_in_lineup_total,
    stat_display_label,
)


def test_nfl_stat_display_labels_match_fantasy_tracker_style():
    assert stat_display_label("yards", sport="nfl") == "Yds"
    assert stat_display_label("td", sport="nfl") == "TD"
    assert stat_display_label("sacks", sport="nfl") == "Sk"
    assert stat_display_label("tackles", sport="nfl") == "Tkl"
    assert stat_display_label("interceptions", sport="nfl") == "INT"
    assert stat_display_label("PTS", sport="nba") == "PTS"


def test_era_column_uses_decade_for_mlb():
    assert era_column_label(sport="mlb") == "Decade"
    assert era_column_label(sport="nba") == "Season"

    player = PlayerSeason(
        player_id="jeterde01",
        player_name="Derek Jeter",
        team="New York Yankees",
        team_abbr="NYY",
        season=1999,
        position="SS",
        decade="1990s",
        stats={},
    )
    assert player_era_display(player, sport="mlb") == "1990s"
    assert player_era_display(player, sport="nba") == 1999


def test_counting_stats_display_without_decimals():
    assert format_stat_display_value(211.0, "HR", sport="mlb") == 211
    assert format_stat_display_value(734.4, "RBI", sport="mlb") == 734
    assert format_stat_display_value(0.248, "AVG", sport="mlb") == 0.248
    assert format_stat_display_value(3.16, "ERA", sport="mlb") == 3.16
    assert format_stat_display_value(4823.0, "yards", sport="nfl") == 4823
    assert format_stat_display_value(41.0, "td", sport="nfl") == 41
    assert format_stat_display_value(30.4, "PTS", sport="nba") == 30.4
    assert format_stat_display_string(211.0, "HR", sport="mlb") == "211"
    assert format_stat_display_string(0.248, "AVG", sport="mlb") == "0.248"
    assert stat_accumulates_in_lineup_total("HR", sport="mlb") is True
    assert stat_accumulates_in_lineup_total("OPS", sport="mlb") is False


def test_integer_record_always_sums_to_max_games():
    assert integer_record(13.5, 17) == (14, 3)
    assert integer_record(14.0, 17) == (14, 3)
    assert integer_record(16.6, 17) == (17, 0)
    assert format_projected_record(13.5, max_games=17) == "14-3"
    assert format_projected_record(14.0, max_games=17) == "14-3"
