"""NFL sport plugin."""

from __future__ import annotations

import random

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.peak import pick_peak_seasons
from lineup_sim.ingest.nfl import build_pool
from lineup_sim.ingest.nfl_positions import (
    DEFENSE_POSITIONS,
    OFFENSE_FLEX_POSITIONS,
    OFFENSE_POSITIONS,
)
from lineup_sim.sports.base import SportPlugin
from lineup_sim.sports.nfl.scoring import nfl_stat_composite

_OFFENSE_STATS = frozenset({"yards", "td", "pass_yds", "rush_yds", "rec_yds", "pass_td", "rush_td", "rec_td"})
_DEFENSE_STATS = frozenset({"sacks", "tackles", "interceptions"})

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

class NFLPlugin(SportPlugin):
    sport_id = "nfl"
    display_name = "NFL"

    _pool_cache: list[PlayerSeason] | None = None

    def teams(self) -> list[dict[str, str]]:
        return NFL_TEAMS

    def load_player_pool(self) -> list[PlayerSeason]:
        if self._pool_cache is None:
            self._pool_cache = pick_peak_seasons(build_pool(), self.sport_id)
        return self._pool_cache

    def reload_pool(self) -> list[PlayerSeason]:
        self._pool_cache = None
        return self.load_player_pool()

    def position_matches(self, player_pos: str, slot_pos: str) -> bool:
        pos = player_pos.upper()
        slot = slot_pos.upper()
        if slot == "FLEX":
            return pos in OFFENSE_FLEX_POSITIONS
        if slot == "D-FLEX":
            return pos in DEFENSE_POSITIONS
        if slot == "EDGE":
            return pos in {"EDGE", "DE", "OLB"}
        if slot == "S":
            return pos in {"S", "SAF", "SS", "FS", "DB"}
        if slot == "LB":
            return pos in {"LB", "ILB", "MLB"}
        if slot == "DT":
            return pos in {"DT", "NT", "DL"}
        return pos == slot

    def side_matches(self, player_pos: str, side: str) -> bool:
        pos = player_pos.upper()
        if side == "offense":
            return pos in OFFENSE_POSITIONS
        if side == "defense":
            return pos in DEFENSE_POSITIONS
        return True

    def random_era_window(self, rng: random.Random) -> tuple[int, int]:
        start = rng.choice(list(range(1970, 2021, 5)))
        return start, min(start + 4, 2024)

    def stat_tracking_factor(self, player: PlayerSeason, stat: str) -> float:
        pos = player.position
        if pos in DEFENSE_POSITIONS:
            return 1.0 if stat in _DEFENSE_STATS else 0.0
        if pos in OFFENSE_POSITIONS:
            return 1.0 if stat in _OFFENSE_STATS else 0.0
        return 1.0

    def stat_composite(self, player: PlayerSeason, preset) -> float | None:
        return nfl_stat_composite(player, preset)

    def season_value(self, player: PlayerSeason) -> float:
        """Peak-season tiebreaker — mirrors position-aware NFL scoring."""
        from lineup_sim.core.presets import get_preset

        preset_slug = "nfl_two_way" if player.position in DEFENSE_POSITIONS else "nfl_offense"
        return nfl_stat_composite(player, get_preset(preset_slug))
