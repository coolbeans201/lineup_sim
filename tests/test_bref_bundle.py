"""Bundled BRef per-game import tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.bref_bundle import (
    import_csv_to_bundle,
    load_bundled_season,
    row_from_csv_record,
)
from lineup_sim.sports.nba.positions import position_matches


def test_row_from_csv_record_maps_positions_and_stats():
    row = row_from_csv_record(
        {
            "lg": "NBA",
            "season": 1988,
            "player": "Larry Bird",
            "player_id": "birdla01",
            "team": "BOS",
            "pos": "SF",
            "g": 76,
            "pts_per_game": 25.8,
            "trb_per_game": 9.8,
            "ast_per_game": 6.8,
            "stl_per_game": 1.6,
            "blk_per_game": 0.6,
        }
    )
    assert row is not None
    assert row["position_raw"] == "SF"
    assert row["team_abbr"] == "BOS"
    assert row["stats"]["PTS"] == 25.8
    assert position_matches(row["position_raw"], "SF")
    assert not position_matches(row["position_raw"], "C")


def test_import_csv_to_bundle_writes_season_file(tmp_path, monkeypatch):
    import lineup_sim.ingest.bref_bundle as bundle

    monkeypatch.setattr(bundle, "BUNDLE_DIR", tmp_path)
    csv_path = tmp_path / "sample.csv"
    pd.DataFrame(
        [
            {
                "season": 1970,
                "lg": "NBA",
                "player": "Bob Lanier",
                "player_id": "lanier01",
                "team": "DET",
                "pos": "C",
                "g": 82,
                "pts_per_game": 26.1,
                "trb_per_game": 11.5,
                "ast_per_game": 3.0,
                "stl_per_game": 1.0,
                "blk_per_game": 2.0,
            },
            {
                "season": 1970,
                "lg": "NBA",
                "player": "Bench Guy",
                "player_id": "bench01",
                "team": "DET",
                "pos": "SG",
                "g": 10,
                "pts_per_game": 3.0,
                "trb_per_game": 1.0,
                "ast_per_game": 0.5,
                "stl_per_game": 0.1,
                "blk_per_game": 0.0,
            },
        ]
    ).to_csv(csv_path, index=False)

    counts = import_csv_to_bundle(csv_path, start_year=1970, end_year=1970, min_games=20)
    assert counts == {1970: 1}

    rows = json.loads((tmp_path / "1970.json").read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["player_name"] == "Bob Lanier"
