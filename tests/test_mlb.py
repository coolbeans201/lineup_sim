"""MLB tenure pool, positions, and scoring tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.constraints import pool_for_spin
from lineup_sim.core.models import SpinConstraint
from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import assign_player, empty_lineup, find_player_in_pool
from lineup_sim.core.scoring import score_lineup
from lineup_sim.core.constraints import eligible_for_slot
from lineup_sim.sports.mlb.plugin import MLBPlugin
from lineup_sim.sports.mlb.positions import position_matches, side_matches


def _pool():
    return MLBPlugin().load_player_pool()


def test_mlb_modern_lineup_scores():
    preset = get_preset("mlb_modern")
    pool = _pool()
    jeter = find_player_in_pool(
        pool,
        player_id="jeterde01",
        season=1999,
        team_abbr="NYY",
        role="bat",
    )
    rivera = find_player_in_pool(
        pool,
        player_id="riverma01",
        season=1999,
        team_abbr="NYY",
        role="pitch",
    )
    assert jeter is not None
    assert rivera is not None

    lineup = empty_lineup(preset)
    lineup = assign_player(lineup, preset, "ss", jeter)
    lineup = assign_player(lineup, preset, "cl", rivera)
    score = score_lineup(lineup, pool)
    assert score.team_rating != 0
    assert score.max_games == 162


def test_mlb_position_matching():
    assert position_matches("SS/DH", "SS")
    assert position_matches("SS/DH", "DH")
    assert position_matches("CF/OF/DH", "LF")
    assert position_matches("SP/RP", "CL")
    assert not position_matches("SS/DH", "SP")
    assert side_matches("SS/DH", "batting")
    assert side_matches("SP/RP", "pitching")
    assert not side_matches("SP/RP", "batting")


def test_mlb_pool_for_spin_keeps_tenure_rows():
    pool = _pool()
    spin = SpinConstraint(
        round_index=1,
        team_abbr="NYY",
        team_name="New York Yankees",
        era_label="1990s",
        season_start=1990,
        season_end=1999,
    )
    spin_pool = pool_for_spin(pool, spin, sport="mlb")
    jeters = [p for p in spin_pool if p.player_id == "jeterde01" and p.role == "bat"]
    assert len(jeters) == 1
    assert jeters[0].stats["PA"] > 2000


def test_mlb_spin_index_matches_filter_pool():
    from lineup_sim.core.constraints import filter_pool
    from lineup_sim.sports.mlb.plugin import MLBPlugin

    pool = _pool()
    plugin = MLBPlugin()
    plugin.reload_pool()
    spin = SpinConstraint(
        round_index=1,
        team_abbr="ATL",
        team_name="Braves",
        era_label="2000s",
        season_start=2000,
        season_end=2009,
    )
    indexed = plugin.spin_pool("ATL", "2000s")
    filtered = filter_pool(pool, team_abbr="ATL", decade="2000s", sport="mlb")
    assert len(indexed) == len(filtered)
    assert {p.player_id for p in indexed} == {p.player_id for p in filtered}


def test_mlb_viable_spin_keys_prefilter_modern_preset():
    from lineup_sim.sports.mlb.plugin import MLBPlugin

    if not _pool():
        return
    preset = get_preset("mlb_modern")
    plugin = MLBPlugin()
    plugin.reload_pool()
    viable = plugin.viable_spin_keys(preset)
    assert viable
    assert ("NYY", "1990s") in viable


def test_mlb_typical_lineup_projects_near_500_record():
    from lineup_sim.core.roster_identity import player_identity
    from lineup_sim.core.scoring import _pool_rating_baseline, player_stat_composite

    preset = get_preset("mlb_modern")
    pool = _pool()
    baseline = _pool_rating_baseline(pool, preset)
    assert baseline > 2.0

    lineup = empty_lineup(preset)
    used: set[str] = set()
    for slot in preset.slots:
        slot_vals = [
            (player_stat_composite(p, preset), p)
            for p in pool
            if player_identity(p) not in used and eligible_for_slot(p, slot, "mlb")
        ]
        assert slot_vals, f"No eligible players for {slot.slot_id}"
        _, player = min(slot_vals, key=lambda item: abs(item[0] - baseline))
        used.add(player_identity(player))
        lineup = assign_player(lineup, preset, slot.slot_id, player)

    score = score_lineup(lineup, pool)
    assert 75 <= score.projected_wins <= 88
    assert 0.46 <= score.win_pct <= 0.55


def test_mlb_solid_lineup_does_not_project_historic_pace():
    """A good-but-not-all-time spin draft should land around 100 wins, not 160."""
    preset = get_preset("mlb_modern")
    pool = _pool()
    lineup = empty_lineup(preset)
    picks = [
        ("b1", "karroer01", 1999, "LAD", "bat"),
        ("b2", "phillbr01", 2016, "CIN", "bat"),
        ("b3", "delacel01", 2025, "CIN", "bat"),
        ("ss", "yountro01", 1989, "MIL", "bat"),
        ("cf", "crowape01", 2025, "CHC", "bat"),
        ("rf", "rodriju01", 2025, "SEA", "bat"),
        ("dh", "croncj01", 2023, "COL", "bat"),
        ("sp", "maddugr01", 2003, "ATL", "pitch"),
    ]
    for slot_id, player_id, season, team_abbr, role in picks:
        player = find_player_in_pool(
            pool,
            player_id=player_id,
            season=season,
            team_abbr=team_abbr,
            role=role,
        )
        assert player is not None, f"missing {player_id}"
        lineup = assign_player(lineup, preset, slot_id, player)

    score = score_lineup(lineup, pool)
    assert score.grade in {"A", "A+", "B"}
    assert score.projected_wins < 120
    assert score.win_pct < 0.72


def test_mlb_team_totals_sum_counting_stats_only():
    preset = get_preset("mlb_modern")
    pool = _pool()
    jeter = find_player_in_pool(
        pool,
        player_id="jeterde01",
        season=1999,
        team_abbr="NYY",
        role="bat",
    )
    rivera = find_player_in_pool(
        pool,
        player_id="riverma01",
        season=1999,
        team_abbr="NYY",
        role="pitch",
    )
    if jeter is None or rivera is None:
        return
    lineup = empty_lineup(preset)
    lineup = assign_player(lineup, preset, "ss", jeter)
    lineup = assign_player(lineup, preset, "cl", rivera)
    score = score_lineup(lineup, pool)
    assert "HR" in score.category_totals
    assert "OPS" not in score.category_totals
    assert "AVG" not in score.category_totals
    assert "ERA" not in score.category_totals
    assert "WHIP" not in score.category_totals
