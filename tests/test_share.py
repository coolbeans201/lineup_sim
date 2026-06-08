"""Share and leaderboard tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import assign_player, empty_lineup, lineup_from_dict
from lineup_sim.core.scoring import score_lineup
from lineup_sim.daily.share import (
    decode_share_payload,
    encode_share_payload,
    lineup_summary,
    share_full_url,
    share_url,
)
from lineup_sim.sports.nba.plugin import NBAPlugin


def test_share_roundtrip():
    preset = get_preset("nba_all_eras")
    pool = {p.player_name: p for p in NBAPlugin().load_player_pool()}
    lineup = empty_lineup(preset)
    lineup = assign_player(lineup, preset, "c", pool["Wilt Chamberlain"])
    score = score_lineup(lineup, NBAPlugin().load_player_pool())
    token = encode_share_payload(lineup, score, date="2026-06-05")
    payload = decode_share_payload(token)
    restored = lineup_from_dict(preset, payload["lineup"])
    filled = [a for a in restored.assignments if a.player is not None]
    assert filled
    assert filled[0].player.player_name == "Wilt Chamberlain"
    assert payload["score"]["grade"] == score.grade
    assert "Wilt" in lineup_summary(lineup)


def test_share_url_formats_query_string():
    token = "abc123"
    assert share_url(token) == "?share=abc123"


def test_share_full_url_falls_back_without_streamlit_context():
    assert share_full_url("abc123") == "?share=abc123"
