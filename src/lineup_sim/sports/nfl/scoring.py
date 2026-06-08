"""NFL offense scoring — fantasy-style per-game weights by yard/TD type."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason, Preset
from lineup_sim.ingest.nfl_positions import DEFENSE_POSITIONS, OFFENSE_POSITIONS

# Standard fantasy points per game (passing de-emphasized vs rush/rec).
_PASS_YDS_PG = 0.04
_RUSH_REC_YDS_PG = 0.1
_PASS_TD_PG = 4.0
_RUSH_REC_TD_PG = 6.0

# Legacy combined totals when split stats are unavailable.
_QB_YARDS_PG = 0.04
_SKILL_YARDS_PG = 0.1
_QB_TD_PG = 4.0
_SKILL_TD_PG = 6.0


def _games_played(player: PlayerSeason) -> float:
    return max(player.stats.get("games", 17.0), 1.0)


def _per_game(total: float, games: float) -> float:
    return total / games


def _has_split_offense_stats(player: PlayerSeason) -> bool:
    keys = ("pass_yds", "rush_yds", "rec_yds", "pass_td", "rush_td", "rec_td")
    return any(key in player.stats for key in keys)


def offense_stat_composite(player: PlayerSeason) -> float:
    """Per-game fantasy composite; QBs scaled on passing, skill on rush/rec."""
    if player.position not in OFFENSE_POSITIONS:
        return 0.0

    games = _games_played(player)

    if _has_split_offense_stats(player):
        pass_yds = _per_game(player.stats.get("pass_yds", 0), games)
        rush_yds = _per_game(player.stats.get("rush_yds", 0), games)
        rec_yds = _per_game(player.stats.get("rec_yds", 0), games)
        pass_td = _per_game(player.stats.get("pass_td", 0), games)
        rush_td = _per_game(player.stats.get("rush_td", 0), games)
        rec_td = _per_game(player.stats.get("rec_td", 0), games)
        return (
            pass_yds * _PASS_YDS_PG
            + rush_yds * _RUSH_REC_YDS_PG
            + rec_yds * _RUSH_REC_YDS_PG
            + pass_td * _PASS_TD_PG
            + rush_td * _RUSH_REC_TD_PG
            + rec_td * _RUSH_REC_TD_PG
        )

    yards_pg = _per_game(player.stats.get("yards", 0), games)
    td_pg = _per_game(player.stats.get("td", 0), games)
    if player.position == "QB":
        return yards_pg * _QB_YARDS_PG + td_pg * _QB_TD_PG
    return yards_pg * _SKILL_YARDS_PG + td_pg * _SKILL_TD_PG


def nfl_stat_composite(player: PlayerSeason, preset: Preset) -> float:
    """Defense uses preset weights; offense uses fantasy per-game scaling."""
    if player.position in DEFENSE_POSITIONS:
        from lineup_sim.core.presets import get_preset
        from lineup_sim.core.scoring import preset_weighted_composite

        defense_preset = (
            preset
            if preset.stat_weights.keys() >= {"sacks", "tackles"}
            else get_preset("nfl_two_way")
        )
        return preset_weighted_composite(player, defense_preset)
    return offense_stat_composite(player)
