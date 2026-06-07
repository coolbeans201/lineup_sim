"""Sport plugin registry."""

from __future__ import annotations

from lineup_sim.sports.base import SportPlugin
from lineup_sim.sports.mlb.plugin import MLBPlugin
from lineup_sim.sports.nba.plugin import NBAPlugin
from lineup_sim.sports.nfl.plugin import NFLPlugin

_PLUGINS: dict[str, SportPlugin] = {
    "nba": NBAPlugin(),
    "nfl": NFLPlugin(),
    "mlb": MLBPlugin(),
}


def get_sport_plugin(sport: str) -> SportPlugin:
    if sport not in _PLUGINS:
        raise KeyError(f"Unknown sport: {sport}")
    return _PLUGINS[sport]


def list_sports() -> list[dict[str, str]]:
    return [{"id": p.sport_id, "name": p.display_name} for p in _PLUGINS.values()]
