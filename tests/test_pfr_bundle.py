"""PFR historical bundle parsing and pool merge."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.spin_options import OTHER_SPORT_DECADES, spin_options_for_slot
from lineup_sim.core.presets import get_preset
from lineup_sim.ingest.pfr_bundle import (
    row_from_defense_record,
    row_from_offense_record,
)
from lineup_sim.sports.nfl.plugin import NFLPlugin


def test_pfr_offense_row_parses_rice_1987():
    row = row_from_offense_record(
        {
            "Player": "Jerry Rice*+",
            "Tm": "SFO",
            "Pos": "WR",
            "G": 16,
            "PassingYds": 0,
            "RushingYds": 8,
            "ReceivingYds": 1578,
            "PassingTD": 0,
            "RushingTD": 0,
            "ReceivingTD": 15,
        },
        season=1987,
    )
    assert row is not None
    assert row["player_name"] == "Jerry Rice"
    assert row["team_abbr"] == "SF"
    assert row["position"] == "WR"
    assert row["stats"]["yards"] == 1586
    assert row["stats"]["td"] == 15


def test_pfr_offense_skips_multi_team_and_qb_flex_irrelevant():
    assert row_from_offense_record({"Player": "X", "Tm": "2TM", "Pos": "RB", "G": 16}, season=1990) is None
    row = row_from_offense_record({"Player": "Y", "Tm": "DAL", "Pos": "QB", "G": 16}, season=1990)
    assert row is not None
    plugin = NFLPlugin()
    assert plugin.position_matches(row["position"], "QB")
    assert not plugin.position_matches(row["position"], "FLEX")


def test_pfr_defense_row_parses_lawrence_taylor():
    row = row_from_defense_record(
        {
            "Player": "Lawrence Taylor*+",
            "Tm": "NYG",
            "Pos": "LB",
            "G": 16,
            "Sk": 21.0,
            "Comb": 75,
            "Int": 0,
            "TD": 0,
        },
        season=1986,
    )
    assert row is not None
    assert row["player_name"] == "Lawrence Taylor"
    assert row["position"] == "LB"
    assert row["stats"]["sacks"] == 21.0
    assert row["stats"]["tackles"] == 75


def test_nfl_spin_options_include_1970s_when_pool_has_history():
    preset = get_preset("nfl_offense")
    slot = preset.slots[0]
    plugin = NFLPlugin()
    pool = plugin.load_player_pool()
    decades = {p.decade for p in pool}
    if "1970s" not in decades and "1980s" not in decades:
        return
    options = spin_options_for_slot(preset, slot, pool=pool)
    era_labels = {opt.era_label for opt in options}
    assert "1970s" in OTHER_SPORT_DECADES
    assert any(label.startswith("197") for label in era_labels) or "1970s" in era_labels
