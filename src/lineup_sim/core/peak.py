"""Collapse player rows to peak season per team and timeframe."""

from __future__ import annotations

from typing import Iterable

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.names import normalize_player_name


def pick_peak_seasons(players: Iterable[PlayerSeason], sport: str) -> list[PlayerSeason]:
    """Keep each player's best season on a team within the filtered timeframe."""
    from lineup_sim.sports.registry import get_sport_plugin

    plugin = get_sport_plugin(sport)
    grouped: dict[tuple[str, str, str], PlayerSeason] = {}
    for p in players:
        key = (normalize_player_name(p.player_name), p.team_abbr.upper(), p.decade)
        existing = grouped.get(key)
        if existing is None or plugin.season_value(p) > plugin.season_value(existing):
            grouped[key] = p
    return list(grouped.values())
