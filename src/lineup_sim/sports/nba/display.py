"""NBA dropdown stat formatting."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason
from lineup_sim.ingest.nba import STL_BLK_FIRST_SEASON

_DISPLAY_STATS: tuple[str, ...] = ("PTS", "REB", "AST", "STL", "BLK")


def format_player_dropdown_stats(player: PlayerSeason) -> str:
    """Per-game stat line for player pickers (matches lineup breakdown tables)."""
    parts: list[str] = []
    for stat in _DISPLAY_STATS:
        if stat in {"STL", "BLK"} and player.season < STL_BLK_FIRST_SEASON:
            continue
        if stat not in player.stats:
            continue
        parts.append(f"{stat} {player.stats[stat]:.1f}")
    return " · ".join(parts) if parts else "—"
