"""Share roundtrip tests for NFL and MLB."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import assign_player, empty_lineup, lineup_from_dict
from lineup_sim.core.scoring import score_lineup
from lineup_sim.daily.share import decode_share_payload, encode_share_payload, lineup_summary
from lineup_sim.ingest.mlb import has_bundled_tenures
from lineup_sim.ingest.nfl_bundle import has_nflverse_bundled_data
from lineup_sim.sports.mlb.plugin import MLBPlugin
from lineup_sim.sports.nfl.plugin import NFLPlugin


@pytest.mark.skipif(not has_nflverse_bundled_data(), reason="NFL nflverse bundle not imported")
def test_nfl_share_roundtrip():
    preset = get_preset("nfl_offense")
    pool = {p.player_name: p for p in NFLPlugin().load_player_pool()}
    mahomes = pool.get("Patrick Mahomes")
    if mahomes is None:
        pytest.skip("Patrick Mahomes not in NFL pool")
    lineup = assign_player(empty_lineup(preset), preset, "qb", mahomes)
    score = score_lineup(lineup, NFLPlugin().load_player_pool())
    token = encode_share_payload(lineup, score)
    payload = decode_share_payload(token)
    restored = lineup_from_dict(preset, payload["lineup"])
    assert restored.assignments[0].player.player_name == "Patrick Mahomes"


@pytest.mark.skipif(not has_bundled_tenures(), reason="MLB Lahman bundle not imported")
def test_mlb_share_roundtrip_and_summary_uses_decade():
    preset = get_preset("mlb_modern")
    pool = MLBPlugin().load_player_pool()
    jeter = next(
        (p for p in pool if p.player_id == "jeterde01" and p.decade == "1990s" and p.role == "bat"),
        None,
    )
    if jeter is None:
        pytest.skip("Derek Jeter 1990s tenure not in pool")
    lineup = assign_player(empty_lineup(preset), preset, "ss", jeter)
    score = score_lineup(lineup, pool)
    token = encode_share_payload(lineup, score)
    payload = decode_share_payload(token)
    restored = lineup_from_dict(preset, payload["lineup"])
    filled = [a.player for a in restored.assignments if a.player is not None]
    assert filled and filled[0].player_name == "Derek Jeter"
    assert "1990s" in lineup_summary(lineup)
