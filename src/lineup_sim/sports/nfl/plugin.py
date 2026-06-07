"""NFL sport plugin."""

from __future__ import annotations

import random

from lineup_sim.core.models import PlayerSeason
from lineup_sim.ingest.nfl import build_pool
from lineup_sim.sports.base import SportPlugin

NFL_TEAMS = [
    {"abbr": "ARI", "name": "Arizona Cardinals"},
    {"abbr": "ATL", "name": "Atlanta Falcons"},
    {"abbr": "BAL", "name": "Baltimore Ravens"},
    {"abbr": "BUF", "name": "Buffalo Bills"},
    {"abbr": "CAR", "name": "Carolina Panthers"},
    {"abbr": "CHI", "name": "Chicago Bears"},
    {"abbr": "CIN", "name": "Cincinnati Bengals"},
    {"abbr": "CLE", "name": "Cleveland Browns"},
    {"abbr": "DAL", "name": "Dallas Cowboys"},
    {"abbr": "DEN", "name": "Denver Broncos"},
    {"abbr": "DET", "name": "Detroit Lions"},
    {"abbr": "GB", "name": "Green Bay Packers"},
    {"abbr": "HOU", "name": "Houston Texans"},
    {"abbr": "IND", "name": "Indianapolis Colts"},
    {"abbr": "JAX", "name": "Jacksonville Jaguars"},
    {"abbr": "KC", "name": "Kansas City Chiefs"},
    {"abbr": "LV", "name": "Las Vegas Raiders"},
    {"abbr": "LAC", "name": "Los Angeles Chargers"},
    {"abbr": "LAR", "name": "Los Angeles Rams"},
    {"abbr": "MIA", "name": "Miami Dolphins"},
    {"abbr": "MIN", "name": "Minnesota Vikings"},
    {"abbr": "NE", "name": "New England Patriots"},
    {"abbr": "NO", "name": "New Orleans Saints"},
    {"abbr": "NYG", "name": "New York Giants"},
    {"abbr": "NYJ", "name": "New York Jets"},
    {"abbr": "PHI", "name": "Philadelphia Eagles"},
    {"abbr": "PIT", "name": "Pittsburgh Steelers"},
    {"abbr": "SEA", "name": "Seattle Seahawks"},
    {"abbr": "SF", "name": "San Francisco 49ers"},
    {"abbr": "TB", "name": "Tampa Bay Buccaneers"},
    {"abbr": "TEN", "name": "Tennessee Titans"},
    {"abbr": "WAS", "name": "Washington Commanders"},
]

OFFENSE = {"QB", "RB", "WR", "TE", "FB"}
DEFENSE = {"EDGE", "DE", "DT", "LB", "OLB", "ILB", "MLB", "CB", "S", "DB", "DL", "NT"}


class NFLPlugin(SportPlugin):
    sport_id = "nfl"
    display_name = "NFL"

    _pool_cache: list[PlayerSeason] | None = None

    def teams(self) -> list[dict[str, str]]:
        return NFL_TEAMS

    def load_player_pool(self) -> list[PlayerSeason]:
        if self._pool_cache is None:
            self._pool_cache = build_pool()
        return self._pool_cache

    def position_matches(self, player_pos: str, slot_pos: str) -> bool:
        pos = player_pos.upper()
        slot = slot_pos.upper()
        if slot == "FLEX":
            return pos in OFFENSE
        if slot == "D-FLEX":
            return pos in DEFENSE
        if slot == "EDGE":
            return pos in {"EDGE", "DE", "OLB", "LB"}
        return pos == slot or (slot == "S" and pos in {"S", "DB"})

    def side_matches(self, player_pos: str, side: str) -> bool:
        pos = player_pos.upper()
        if side == "offense":
            return pos in OFFENSE
        if side == "defense":
            return pos in DEFENSE
        return True

    def random_era_window(self, rng: random.Random) -> tuple[int, int]:
        start = rng.choice(list(range(1999, 2021, 5)))
        return start, start + 4

    def season_value(self, player: PlayerSeason) -> float:
        return player.stats.get("yards", 0) + player.stats.get("td", 0) * 12
