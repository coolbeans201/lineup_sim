"""MLB sport plugin."""

from __future__ import annotations

import random

from lineup_sim.core.models import PlayerSeason
from lineup_sim.ingest.mlb import build_pool
from lineup_sim.sports.base import SportPlugin

MLB_TEAMS = [
    {"abbr": "ARI", "name": "Arizona Diamondbacks"},
    {"abbr": "ATL", "name": "Atlanta Braves"},
    {"abbr": "BAL", "name": "Baltimore Orioles"},
    {"abbr": "BOS", "name": "Boston Red Sox"},
    {"abbr": "CHC", "name": "Chicago Cubs"},
    {"abbr": "CWS", "name": "Chicago White Sox"},
    {"abbr": "CIN", "name": "Cincinnati Reds"},
    {"abbr": "CLE", "name": "Cleveland Guardians"},
    {"abbr": "COL", "name": "Colorado Rockies"},
    {"abbr": "DET", "name": "Detroit Tigers"},
    {"abbr": "HOU", "name": "Houston Astros"},
    {"abbr": "KC", "name": "Kansas City Royals"},
    {"abbr": "LAA", "name": "Los Angeles Angels"},
    {"abbr": "LAD", "name": "Los Angeles Dodgers"},
    {"abbr": "MIA", "name": "Miami Marlins"},
    {"abbr": "MIL", "name": "Milwaukee Brewers"},
    {"abbr": "MIN", "name": "Minnesota Twins"},
    {"abbr": "NYM", "name": "New York Mets"},
    {"abbr": "NYY", "name": "New York Yankees"},
    {"abbr": "OAK", "name": "Oakland Athletics"},
    {"abbr": "PHI", "name": "Philadelphia Phillies"},
    {"abbr": "PIT", "name": "Pittsburgh Pirates"},
    {"abbr": "SD", "name": "San Diego Padres"},
    {"abbr": "SEA", "name": "Seattle Mariners"},
    {"abbr": "SF", "name": "San Francisco Giants"},
    {"abbr": "STL", "name": "St. Louis Cardinals"},
    {"abbr": "TB", "name": "Tampa Bay Rays"},
    {"abbr": "TEX", "name": "Texas Rangers"},
    {"abbr": "TOR", "name": "Toronto Blue Jays"},
    {"abbr": "WSH", "name": "Washington Nationals"},
]


class MLBPlugin(SportPlugin):
    sport_id = "mlb"
    display_name = "MLB"

    _pool_cache: list[PlayerSeason] | None = None

    def teams(self) -> list[dict[str, str]]:
        return MLB_TEAMS

    def load_player_pool(self) -> list[PlayerSeason]:
        if self._pool_cache is None:
            self._pool_cache = build_pool()
        return self._pool_cache

    def position_matches(self, player_pos: str, slot_pos: str) -> bool:
        pos = player_pos.upper()
        slot = slot_pos.upper()
        if slot == "H":
            return pos in {"H", "OF", "1B", "2B", "3B", "SS", "C", "DH"}
        if slot == "P":
            return pos in {"P", "SP", "RP"}
        return pos == slot

    def side_matches(self, player_pos: str, side: str) -> bool:
        pos = player_pos.upper()
        if side == "batting":
            return pos in {"H", "OF", "1B", "2B", "3B", "SS", "C", "DH"}
        if side == "pitching":
            return pos in {"P", "SP", "RP"}
        return True

    def random_era_window(self, rng: random.Random) -> tuple[int, int]:
        start = rng.choice(list(range(2008, 2021, 4)))
        return start, start + 3

    def season_value(self, player: PlayerSeason) -> float:
        if player.position.upper() in {"P", "SP", "RP"}:
            return player.stats.get("K", 0) - player.stats.get("ERA", 0) * 10
        return player.stats.get("OPS", 0) * 100 + player.stats.get("HR", 0) * 2
