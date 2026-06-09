"""MLB tenure-decade scoring — rewards total franchise production in a decade."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason, Preset
from lineup_sim.sports.mlb.positions import PITCH_POSITIONS, parse_positions


def _games_played(player: PlayerSeason) -> float:
    return max(player.stats.get("G", 1.0), 1.0)


def _innings_pitched(player: PlayerSeason) -> float:
    if "IP" in player.stats:
        return max(player.stats["IP"], 1.0)
    return max(player.stats.get("IPouts", 3.0) / 3.0, 1.0)


def batting_tenure_composite(player: PlayerSeason) -> float:
    """Rate + counting stats scaled to a per-100-games decade line."""
    games = _games_played(player)
    scale = 100.0 / games
    hr = player.stats.get("HR", 0.0) * scale
    rbi = player.stats.get("RBI", 0.0) * scale
    sb = player.stats.get("SB", 0.0) * scale
    ops = player.stats.get("OPS", 0.0)
    avg = player.stats.get("AVG", 0.0)
    return hr * 0.4 + rbi * 0.15 + sb * 0.2 + ops * 2.0 + avg * 1.5


def pitching_tenure_composite(player: PlayerSeason) -> float:
    ip = _innings_pitched(player)
    k9 = player.stats.get("K", 0.0) / ip * 9.0
    return (
        player.stats.get("W", 0.0) * 0.35
        + k9 * 0.12
        + player.stats.get("SV", 0.0) * 0.5
        - player.stats.get("ERA", 0.0) * 0.15
        - player.stats.get("WHIP", 0.0) * 0.35
    )


def mlb_stat_composite(player: PlayerSeason, preset: Preset) -> float:
    del preset
    positions = parse_positions(player.position_raw or player.position)
    if player.role == "pitch" or positions & PITCH_POSITIONS:
        return pitching_tenure_composite(player)
    return batting_tenure_composite(player)
