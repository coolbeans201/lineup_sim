"""Core scoring and compare tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.presets import get_preset, load_presets
from lineup_sim.core.roster import assign_player, empty_lineup
from lineup_sim.core.scoring import player_stat_composite, score_lineup
from lineup_sim.core.compare import compare_lineups
from lineup_sim.daily.seed import daily_puzzle, _seed_from_date


def test_presets_load():
    presets = load_presets(force=True)
    assert "nba_all_eras" in presets
    assert "nfl_two_way" in presets
    assert "mlb_battery" in presets


def test_pre_1974_omits_stl_blk_from_stat_score():
    preset = get_preset("nba_all_eras")
    wilt = PlayerSeason(
        player_id="wilt66",
        player_name="Wilt Chamberlain",
        team="Philadelphia Warriors",
        team_abbr="GSW",
        season=1962,
        position="C",
        decade="1960s",
        stats={"PTS": 50.4, "REB": 25.7, "AST": 2.4, "STL": 0.0, "BLK": 0.0},
    )
    expected = (50.4 * 1.0 + 25.7 * 0.9 + 2.4 * 0.85) / (1.0 + 0.9 + 0.85)
    assert player_stat_composite(wilt, preset) == pytest.approx(expected, rel=1e-6)

    jordan = PlayerSeason(
        player_id="mj96",
        player_name="Michael Jordan",
        team="Chicago Bulls",
        team_abbr="CHI",
        season=1996,
        position="SG",
        decade="1990s",
        stats={"PTS": 30.4, "REB": 6.6, "AST": 4.3, "STL": 2.2, "BLK": 0.5},
    )
    jordan_expected = (
        30.4 * 1.0 + 6.6 * 0.9 + 4.3 * 0.85 + 2.2 * 0.75 + 0.5 * 0.75
    ) / (1.0 + 0.9 + 0.85 + 0.75 + 0.75)
    assert player_stat_composite(jordan, preset) == pytest.approx(jordan_expected, rel=1e-6)


def test_nba_lineup_scores():
    preset = get_preset("nba_all_eras")
    lineup = empty_lineup(preset)
    wilt = PlayerSeason(
        player_id="wilt66",
        player_name="Wilt Chamberlain",
        team="Philadelphia Warriors",
        team_abbr="GSW",
        season=1962,
        position="C",
        decade="1960s",
        stats={"PTS": 50.4, "REB": 25.7, "AST": 2.4, "STL": 0.0, "BLK": 0.0},
    )
    lineup = assign_player(lineup, preset, "c", wilt)
    from lineup_sim.sports.nba.plugin import NBAPlugin

    score = score_lineup(lineup, NBAPlugin().load_player_pool())
    assert score.team_rating != 0
    assert score.projected_wins > 0
    assert score.grade in {"S+", "A+", "A", "B", "C", "D", "F"}


def test_slot_rating_uses_raw_stats_not_z_scores():
    preset = get_preset("nba_all_eras")
    from lineup_sim.sports.nba.plugin import NBAPlugin

    pool = NBAPlugin().load_player_pool()
    wilt = next(p for p in pool if p.player_name == "Wilt Chamberlain" and p.season == 1962)
    score = score_lineup(
        assign_player(empty_lineup(preset), preset, "c", wilt),
        pool,
    )
    rating = score.player_ratings[0]
    assert rating.slot_rating == pytest.approx(player_stat_composite(wilt, preset), rel=1e-6)
    assert rating.slot_rating > rating.composite_z


def test_elite_nba_lineup_projects_dominant_record():
    preset = get_preset("nba_all_eras")
    from lineup_sim.sports.nba.plugin import NBAPlugin

    pool = NBAPlugin().load_player_pool()

    def find(name: str, season: int):
        return next(p for p in pool if p.player_name == name and p.season == season)

    lineup = empty_lineup(preset)
    for slot_id, player in [
        ("pg", find("James Harden", 2019)),
        ("sg", find("Kobe Bryant", 2006)),
        ("sf", find("Elgin Baylor", 1962)),
        ("pf", find("Giannis Antetokounmpo", 2023)),
        ("c", find("Wilt Chamberlain", 1962)),
    ]:
        lineup = assign_player(lineup, preset, slot_id, player)

    score = score_lineup(lineup, pool)
    assert score.grade == "S+"
    assert score.projected_wins >= 75
    wilt = next(r for r in score.player_ratings if r.player.player_name == "Wilt Chamberlain")
    assert wilt.slot_rating >= 17.0


def test_record_notes_explain_projected_losses():
    preset = get_preset("nba_all_eras")
    from lineup_sim.sports.nba.plugin import NBAPlugin

    pool = NBAPlugin().load_player_pool()

    def find(name: str, season: int):
        return next(p for p in pool if p.player_name == name and p.season == season)

    lineup = empty_lineup(preset)
    for slot_id, player in [
        ("pg", find("James Harden", 2019)),
        ("sg", find("Kobe Bryant", 2006)),
        ("sf", find("Elgin Baylor", 1962)),
        ("pf", find("Giannis Antetokounmpo", 2023)),
        ("c", find("Wilt Chamberlain", 1962)),
    ]:
        lineup = assign_player(lineup, preset, slot_id, player)

    score = score_lineup(lineup, pool)
    assert score.record_notes
    assert any("82-0" in note for note in score.record_notes)
    assert score.win_pct > 0.9


def test_compare_lineups():
    preset = get_preset("nba_all_eras")
    from lineup_sim.sports.nba.plugin import NBAPlugin

    pool = NBAPlugin().load_player_pool()
    by_name = {p.player_name: p for p in pool}

    lineup_a = empty_lineup(preset, label="A")
    lineup_b = empty_lineup(preset, label="B")
    lineup_a = assign_player(lineup_a, preset, "c", by_name["Wilt Chamberlain"])
    lineup_b = assign_player(lineup_b, preset, "c", by_name["Bill Russell"])

    result = compare_lineups(lineup_a, lineup_b)
    assert result.winner in {"A", "B", "Tie"}
    assert len(result.rows) == preset.slot_count


def test_daily_seed_is_deterministic():
    a = _seed_from_date("nba", "2026-06-05", "nba_all_eras")
    b = _seed_from_date("nba", "2026-06-05", "nba_all_eras")
    c = _seed_from_date("nba", "2026-06-06", "nba_all_eras")
    assert a == b
    assert a != c


def test_daily_puzzle_spins_match_slots():
    puzzle = daily_puzzle("nba", "nba_all_eras", day="2026-06-05")
    preset = get_preset("nba_all_eras")
    assert len(puzzle.spins) == preset.slot_count


def test_daily_puzzle_spins_have_players_for_each_slot():
    from lineup_sim.core.constraints import pool_for_spin
    from lineup_sim.sports.nba.plugin import NBAPlugin

    preset = get_preset("nba_all_eras")
    plugin = NBAPlugin()
    plugin.reload_pool()
    pool = plugin.load_player_pool()

    for day in ("2026-06-05", "2026-06-07"):
        puzzle = daily_puzzle("nba", "nba_all_eras", day=day)
        for i, (slot, spin) in enumerate(zip(preset.slots, puzzle.spins)):
            candidates = pool_for_spin(
                pool,
                spin,
                sport="nba",
            )
            assert candidates, f"{day} pick {i + 1} {spin.team_abbr} {spin.era_label} has no players"
