"""NBA sport plugin."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason
from lineup_sim.core.peak import pick_peak_seasons
from lineup_sim.ingest.nba import STL_BLK_FIRST_SEASON, build_pool
from lineup_sim.sports.base import SportPlugin
from lineup_sim.sports.nba.positions import position_matches as nba_position_matches

NBA_TEAMS = [
    {"abbr": "ATL", "name": "Atlanta Hawks"},
    {"abbr": "BOS", "name": "Boston Celtics"},
    {"abbr": "BKN", "name": "Brooklyn Nets"},
    {"abbr": "CHA", "name": "Charlotte Hornets"},
    {"abbr": "CHI", "name": "Chicago Bulls"},
    {"abbr": "CLE", "name": "Cleveland Cavaliers"},
    {"abbr": "DAL", "name": "Dallas Mavericks"},
    {"abbr": "DEN", "name": "Denver Nuggets"},
    {"abbr": "DET", "name": "Detroit Pistons"},
    {"abbr": "GSW", "name": "Golden State Warriors"},
    {"abbr": "HOU", "name": "Houston Rockets"},
    {"abbr": "IND", "name": "Indiana Pacers"},
    {"abbr": "LAC", "name": "LA Clippers"},
    {"abbr": "LAL", "name": "Los Angeles Lakers"},
    {"abbr": "MEM", "name": "Memphis Grizzlies"},
    {"abbr": "MIA", "name": "Miami Heat"},
    {"abbr": "MIL", "name": "Milwaukee Bucks"},
    {"abbr": "MIN", "name": "Minnesota Timberwolves"},
    {"abbr": "NOP", "name": "New Orleans Pelicans"},
    {"abbr": "NYK", "name": "New York Knicks"},
    {"abbr": "OKC", "name": "Oklahoma City Thunder"},
    {"abbr": "ORL", "name": "Orlando Magic"},
    {"abbr": "PHI", "name": "Philadelphia 76ers"},
    {"abbr": "PHX", "name": "Phoenix Suns"},
    {"abbr": "POR", "name": "Portland Trail Blazers"},
    {"abbr": "SAC", "name": "Sacramento Kings"},
    {"abbr": "SAS", "name": "San Antonio Spurs"},
    {"abbr": "TOR", "name": "Toronto Raptors"},
    {"abbr": "UTA", "name": "Utah Jazz"},
    {"abbr": "WAS", "name": "Washington Wizards"},
]


class NBAPlugin(SportPlugin):
    sport_id = "nba"
    display_name = "NBA"

    _pool_cache: list[PlayerSeason] | None = None

    def teams(self) -> list[dict[str, str]]:
        return NBA_TEAMS

    def load_player_pool(self) -> list[PlayerSeason]:
        if self._pool_cache is None:
            self._pool_cache = pick_peak_seasons(build_pool(), self.sport_id)
        return self._pool_cache

    def reload_pool(self) -> list[PlayerSeason]:
        self._pool_cache = None
        return self.load_player_pool()

    def position_matches(self, player_pos: str, slot_pos: str) -> bool:
        return nba_position_matches(player_pos, slot_pos)

    def season_value(self, player: PlayerSeason) -> float:
        return player.stats.get("PTS", 0) * 1.0 + player.stats.get("REB", 0) * 0.8

    def stat_tracking_factor(self, player: PlayerSeason, stat: str) -> float:
        if stat in {"STL", "BLK"} and player.season < STL_BLK_FIRST_SEASON:
            return 0.0
        return 1.0
