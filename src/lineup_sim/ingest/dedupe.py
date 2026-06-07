"""Deduplicate player-season rows for draft UI and scoring pools."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.names import normalize_player_name

__all__ = ["dedupe_player_seasons", "normalize_player_name"]


def dedupe_player_seasons(players: list[PlayerSeason], sport: str) -> list[PlayerSeason]:
    """
    One row per player per season (best stint by sport season_value).

    Removes duplicate ingest rows (sample + fixtures + API) and collapses
    multi-team seasons to the strongest statistical line.
    """
    from lineup_sim.sports.registry import get_sport_plugin

    plugin = get_sport_plugin(sport)
    best: dict[tuple[str, int], PlayerSeason] = {}

    for p in players:
        key = (normalize_player_name(p.player_name), p.season)
        existing = best.get(key)
        if existing is None or plugin.season_value(p) > plugin.season_value(existing):
            best[key] = p

    return list(best.values())
