"""MLB dropdown stat formatting for tenure rows."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason
from lineup_sim.sports.mlb.positions import PITCH_POSITIONS, parse_positions


def format_player_dropdown_stats(player: PlayerSeason) -> str:
    if player.role == "pitch":
        ip = player.stats.get("IP", player.stats.get("IPouts", 0) / 3)
        return (
            f"{player.stats.get('W', 0):.0f} W · "
            f"{player.stats.get('SV', 0):.0f} SV · "
            f"{player.stats.get('ERA', 0):.2f} ERA · "
            f"{ip:.0f} IP"
        )
    positions = parse_positions(player.position_raw or player.position)
    if positions & PITCH_POSITIONS:
        ip = player.stats.get("IP", player.stats.get("IPouts", 0) / 3)
        return (
            f"{player.stats.get('W', 0):.0f} W · "
            f"{player.stats.get('SV', 0):.0f} SV · "
            f"{player.stats.get('ERA', 0):.2f} ERA · "
            f"{ip:.0f} IP"
        )
    return (
        f"{player.stats.get('AVG', 0):.3f} AVG · "
        f"{player.stats.get('HR', 0):.0f} HR · "
        f"{player.stats.get('RBI', 0):.0f} RBI · "
        f"{player.stats.get('OPS', 0):.3f} OPS"
    )
