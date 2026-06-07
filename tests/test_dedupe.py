"""Player pool deduplication tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.models import PlayerSeason
from lineup_sim.ingest.dedupe import dedupe_player_seasons


def _p(name: str, season: int, team: str, pts: float, pid: str = "a") -> PlayerSeason:
    return PlayerSeason(
        player_id=pid,
        player_name=name,
        team=team,
        team_abbr=team,
        season=season,
        position="C",
        stats={"PTS": pts, "REB": 10, "AST": 2, "STL": 1, "BLK": 1},
    )


def test_dedupe_same_player_same_season_different_sources():
    rows = [
        _p("Wilt Chamberlain", 1962, "GSW", 50.4, pid="sample"),
        _p("Wilt Chamberlain", 1962, "GSW", 50.4, pid="bref_wilt_1962_GSW"),
    ]
    out = dedupe_player_seasons(rows, "nba")
    assert len(out) == 1
    assert out[0].player_name == "Wilt Chamberlain"


def test_dedupe_same_player_same_season_keeps_best_stint():
    rows = [
        _p("Karl Malone", 1997, "UTA", 27.0, pid="1"),
        _p("Karl Malone", 1997, "UTA", 27.4, pid="2"),
    ]
    rows[1].stats["PTS"] = 27.4
    out = dedupe_player_seasons(rows, "nba")
    assert len(out) == 1
    assert out[0].stats["PTS"] == 27.4
