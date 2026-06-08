"""Stat display labels and projected record formatting."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.stat_labels import (
    format_projected_record,
    integer_record,
    stat_display_label,
)


def test_nfl_stat_display_labels_match_fantasy_tracker_style():
    assert stat_display_label("yards", sport="nfl") == "Yds"
    assert stat_display_label("td", sport="nfl") == "TD"
    assert stat_display_label("sacks", sport="nfl") == "Sk"
    assert stat_display_label("tackles", sport="nfl") == "Tkl"
    assert stat_display_label("interceptions", sport="nfl") == "INT"
    assert stat_display_label("PTS", sport="nba") == "PTS"


def test_integer_record_always_sums_to_max_games():
    assert integer_record(13.5, 17) == (14, 3)
    assert integer_record(14.0, 17) == (14, 3)
    assert integer_record(16.6, 17) == (17, 0)
    assert format_projected_record(13.5, max_games=17) == "14-3"
    assert format_projected_record(14.0, max_games=17) == "14-3"
