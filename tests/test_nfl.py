"""NFL presets, positions, and spin options."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.peak import pick_peak_seasons
from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import assign_player, empty_lineup, open_slots
from lineup_sim.core.scoring import player_stat_composite, score_lineup
from lineup_sim.core.spin_options import spin_options_for_slot
from lineup_sim.ingest.nfl_positions import normalize_nfl_position
from lineup_sim.sports.nfl.plugin import NFLPlugin


def test_nfl_offense_preset_slots():
    preset = get_preset("nfl_offense")
    assert preset.slot_count == 6
    positions = [s.position for s in preset.slots]
    assert positions == ["QB", "RB", "WR", "TE", "FLEX", "FLEX"]
    assert all(s.side == "offense" for s in preset.slots)


def test_nfl_two_way_preset_slots():
    preset = get_preset("nfl_two_way")
    assert preset.slot_count == 12
    offense = [s for s in preset.slots if s.side == "offense"]
    defense = [s for s in preset.slots if s.side == "defense"]
    assert len(offense) == 6
    assert len(defense) == 6
    assert [s.position for s in defense] == ["EDGE", "DT", "LB", "CB", "S", "D-FLEX"]


def test_normalize_nfl_positions():
    assert normalize_nfl_position("DE", "DL") == "EDGE"
    assert normalize_nfl_position("OLB", "LB") == "EDGE"
    assert normalize_nfl_position("ILB", "LB") == "LB"
    assert normalize_nfl_position("SAF", "DB") == "S"
    assert normalize_nfl_position("CB", "DB") == "CB"
    assert normalize_nfl_position("OT", "OL") is None


def test_nfl_position_matching_no_lb_at_edge():
    plugin = NFLPlugin()
    assert plugin.position_matches("EDGE", "EDGE")
    assert plugin.position_matches("DE", "EDGE")
    assert not plugin.position_matches("LB", "EDGE")
    assert plugin.position_matches("RB", "FLEX")
    assert plugin.position_matches("WR", "FLEX")
    assert not plugin.position_matches("QB", "FLEX")
    assert plugin.position_matches("CB", "D-FLEX")
    assert not plugin.position_matches("QB", "D-FLEX")


def test_nfl_spin_options_for_first_slot():
    preset = get_preset("nfl_two_way")
    slot = preset.slots[0]
    plugin = NFLPlugin()
    options = spin_options_for_slot(preset, slot, pool=plugin.load_player_pool())
    assert options
    assert all(opt.team_abbr for opt in options)


def test_nfl_pick_peak_uses_defensive_stats_for_linebackers():
    rows = [
        PlayerSeason(
            player_id="lt85",
            player_name="Lawrence Taylor",
            team="Giants",
            team_abbr="NYG",
            season=1985,
            position="LB",
            stats={"yards": 0, "td": 0, "sacks": 17.5, "tackles": 70, "interceptions": 0},
            decade="1980s",
        ),
        PlayerSeason(
            player_id="lt86",
            player_name="Lawrence Taylor",
            team="Giants",
            team_abbr="NYG",
            season=1986,
            position="LB",
            stats={"yards": 0, "td": 0, "sacks": 21.0, "tackles": 75, "interceptions": 0},
            decade="1980s",
        ),
    ]
    plugin = NFLPlugin()
    assert plugin.season_value(rows[1]) > plugin.season_value(rows[0])
    peak = pick_peak_seasons(rows, "nfl")
    assert len(peak) == 1
    assert peak[0].season == 1986


def test_nfl_two_way_opens_offense_before_defense():
    preset = get_preset("nfl_two_way")
    lineup = empty_lineup(preset)
    open_ids = {s.slot_id for s in open_slots(lineup, preset)}
    assert open_ids == {"qb", "rb", "wr", "te", "flex1", "flex2"}

    pool = {p.player_name: p for p in NFLPlugin().load_player_pool()}
    lineup = assign_player(lineup, preset, "qb", pool["Patrick Mahomes"])
    lineup = assign_player(lineup, preset, "rb", pool["Derrick Henry"])
    open_ids = {s.slot_id for s in open_slots(lineup, preset)}
    assert "edge" not in open_ids
    assert open_ids <= {"wr", "te", "flex1", "flex2"}

    extras = [
        ("wr", "Justin Jefferson", "WR"),
        ("te", "Travis Kelce", "TE"),
        ("flex1", "Saquon Barkley", "RB"),
        ("flex2", "Tyreek Hill", "WR"),
    ]
    for slot_id, name, _ in extras:
        lineup = assign_player(lineup, preset, slot_id, pool[name])
    open_ids = {s.slot_id for s in open_slots(lineup, preset)}
    assert "qb" not in open_ids
    assert open_ids == {"edge", "dt", "lb", "cb", "s", "dflex"}


def test_nfl_dropdown_stats_hide_irrelevant_zeros():
    from app.components import player_option_label
    from lineup_sim.sports.nfl.display import format_player_dropdown_stats

    pool = NFLPlugin().load_player_pool()
    by_name = {p.player_name: p for p in pool}
    mahomes = by_name["Patrick Mahomes"]
    watt = next(p for p in pool if p.player_name == "T.J. Watt" and p.stats.get("sacks", 0) > 0)

    offense_line = format_player_dropdown_stats(mahomes)
    assert "sk" not in offense_line
    assert "tkl" not in offense_line
    assert "yds/g" in offense_line
    assert "TD/g" in offense_line

    defense_line = format_player_dropdown_stats(watt)
    assert "sk" in defense_line
    assert "tkl" in defense_line
    assert "yds" not in defense_line

    label = player_option_label(mahomes, sport="nfl")
    assert "sacks" not in label
    assert "Patrick Mahomes" in label
    assert "QB" in label


def test_nfl_stat_tracking_factor_by_side():
    plugin = NFLPlugin()
    qb = PlayerSeason(
        player_id="qb1",
        player_name="QB",
        team="Team",
        team_abbr="TM",
        season=2020,
        position="QB",
        stats={"yards": 4000, "td": 30, "sacks": 0, "tackles": 0, "interceptions": 0},
    )
    edge = PlayerSeason(
        player_id="ed1",
        player_name="EDGE",
        team="Team",
        team_abbr="TM",
        season=2020,
        position="EDGE",
        stats={"yards": 0, "td": 0, "sacks": 12, "tackles": 40, "interceptions": 1},
    )
    assert plugin.stat_tracking_factor(qb, "yards") == 1.0
    assert plugin.stat_tracking_factor(qb, "sacks") == 0.0
    assert plugin.stat_tracking_factor(edge, "sacks") == 1.0
    assert plugin.stat_tracking_factor(edge, "yards") == 0.0


def test_nfl_typical_lineup_projects_near_500_record():
    from lineup_sim.core.constraints import eligible_for_slot
    from lineup_sim.core.scoring import _pool_rating_baseline, score_lineup

    preset = get_preset("nfl_offense")
    pool = NFLPlugin().load_player_pool()
    baseline = _pool_rating_baseline(pool, preset)
    assert baseline > 2.0

    lineup = empty_lineup(preset)
    used: set[str] = set()
    for slot in preset.slots:
        slot_vals = [
            (player_stat_composite(p, preset), p)
            for p in pool
            if p.player_id not in used and eligible_for_slot(p, slot, "nfl")
        ]
        _, player = min(slot_vals, key=lambda item: abs(item[0] - baseline))
        used.add(player.player_id)
        lineup = assign_player(lineup, preset, slot.slot_id, player)

    score = score_lineup(lineup, pool)
    assert 6.5 <= score.projected_wins <= 10.5
    assert 0.38 <= score.win_pct <= 0.62


def test_nfl_elite_offense_does_not_project_undefeated():
    from lineup_sim.sports.nfl.scoring import offense_stat_composite

    preset = get_preset("nfl_offense")
    pool = NFLPlugin().load_player_pool()
    top = sorted(pool, key=offense_stat_composite, reverse=True)
    by_pos: dict[str, PlayerSeason] = {}
    for player in top:
        if player.position not in by_pos and player.position in {"QB", "RB", "WR", "TE"}:
            by_pos[player.position] = player

    lineup = empty_lineup(preset)
    for slot_id, pos in [("qb", "QB"), ("rb", "RB"), ("wr", "WR"), ("te", "TE")]:
        lineup = assign_player(lineup, preset, slot_id, by_pos[pos])
    used = {a.player.player_id for a in lineup.assignments if a.player}
    flex = [p for p in top if p.position in {"RB", "WR", "TE"} and p.player_id not in used]
    lineup = assign_player(lineup, preset, "flex1", flex[0])
    lineup = assign_player(lineup, preset, "flex2", flex[1])

    score = score_lineup(lineup, pool)
    assert score.projected_wins < 17.0
    assert score.win_pct < 0.99
    assert score.projected_wins >= 14.0


def test_nfl_offense_fantasy_scaling_balances_qb_and_skill_positions():
    from lineup_sim.sports.nfl.scoring import offense_stat_composite

    mahomes = PlayerSeason(
        player_id="pm18",
        player_name="Patrick Mahomes",
        team="Chiefs",
        team_abbr="KC",
        season=2018,
        position="QB",
        stats={
            "games": 16,
            "pass_yds": 5097,
            "rush_yds": 272,
            "rec_yds": 0,
            "pass_td": 50,
            "rush_td": 2,
            "rec_td": 0,
            "yards": 5369,
            "td": 52,
        },
        decade="2010s",
    )
    henry = PlayerSeason(
        player_id="dh24",
        player_name="Derrick Henry",
        team="Titans",
        team_abbr="TEN",
        season=2024,
        position="RB",
        stats={
            "games": 17,
            "pass_yds": 0,
            "rush_yds": 1921,
            "rec_yds": 193,
            "pass_td": 0,
            "rush_td": 16,
            "rec_td": 2,
            "yards": 2114,
            "td": 18,
        },
        decade="2020s",
    )
    qb_score = offense_stat_composite(mahomes)
    rb_score = offense_stat_composite(henry)
    assert 18 <= qb_score <= 32
    assert 15 <= rb_score <= 28
    assert qb_score < rb_score * 2


def test_nfl_pick_peak_uses_offensive_stats_for_quarterbacks():
    rows = [
        PlayerSeason(
            player_id="mont90",
            player_name="Joe Montana",
            team="49ers",
            team_abbr="SF",
            season=1990,
            position="QB",
            stats={"yards": 4106, "td": 27, "sacks": 0, "tackles": 0, "interceptions": 0},
            decade="1990s",
        ),
        PlayerSeason(
            player_id="mont88",
            player_name="Joe Montana",
            team="49ers",
            team_abbr="SF",
            season=1988,
            position="QB",
            stats={"yards": 2981, "td": 18, "sacks": 0, "tackles": 0, "interceptions": 0},
            decade="1980s",
        ),
    ]
    peak = pick_peak_seasons(rows, "nfl")
    assert len(peak) == 2
    assert {p.season for p in peak} == {1988, 1990}


def test_nfl_offense_lineup_scores():
    preset = get_preset("nfl_offense")
    pool = {p.player_name: p for p in NFLPlugin().load_player_pool()}
    lineup = empty_lineup(preset)
    lineup = assign_player(lineup, preset, "qb", pool["Patrick Mahomes"])
    lineup = assign_player(lineup, preset, "rb", pool["Derrick Henry"])
    score = score_lineup(lineup, NFLPlugin().load_player_pool())
    assert score.team_rating != 0
    assert score.max_games == 17
