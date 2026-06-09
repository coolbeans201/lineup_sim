"""MLB sport plugin."""

from __future__ import annotations

import random
from collections import defaultdict

import pandas as pd

from lineup_sim.core.models import PlayerSeason, Preset
from lineup_sim.ingest.mlb import build_pool
from lineup_sim.sports.base import SportPlugin
from lineup_sim.sports.mlb.positions import (
    PITCH_POSITIONS,
    position_matches as mlb_position_matches,
    side_matches as mlb_side_matches,
)
from lineup_sim.sports.mlb.scoring import mlb_stat_composite

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
    _spin_index: dict[tuple[str, str], list[PlayerSeason]] | None = None
    _cohort_df: pd.DataFrame | None = None
    _cohort_slices: dict[tuple[str, str], pd.DataFrame] | None = None
    _viable_spin_cache: dict[str, set[tuple[str, str]]] | None = None
    _composite_cache: dict[tuple[str, int, str, str], float] | None = None

    def teams(self) -> list[dict[str, str]]:
        return MLB_TEAMS

    def _clear_indexes(self) -> None:
        self._spin_index = None
        self._cohort_df = None
        self._cohort_slices = None
        self._viable_spin_cache = None
        self._composite_cache = None

    def _build_indexes(self, pool: list[PlayerSeason]) -> None:
        from lineup_sim.core.scoring import _cohort_frame

        spin_index: dict[tuple[str, str], list[PlayerSeason]] = defaultdict(list)
        for player in pool:
            if not player.decade:
                continue
            spin_index[(player.team_abbr.upper(), player.decade)].append(player)

        self._spin_index = dict(spin_index)
        self._cohort_df = _cohort_frame(pool, self.sport_id)
        slices: dict[tuple[str, str], pd.DataFrame] = {}
        if not self._cohort_df.empty:
            for (decade, position), group in self._cohort_df.groupby(["decade", "position"], sort=False):
                slices[(str(decade), str(position))] = group
        self._cohort_slices = slices
        self._viable_spin_cache = {}
        self._composite_cache = {}

    def load_player_pool(self) -> list[PlayerSeason]:
        if self._pool_cache is None:
            self._pool_cache = build_pool()
            self._build_indexes(self._pool_cache)
        return self._pool_cache

    def reload_pool(self) -> list[PlayerSeason]:
        self._pool_cache = None
        self._clear_indexes()
        return self.load_player_pool()

    def spin_pool(self, team_abbr: str, decade: str) -> list[PlayerSeason]:
        pool = self.load_player_pool()
        if self._spin_index is None:
            return pool
        return list(self._spin_index.get((team_abbr.upper(), decade), ()))

    def viable_spin_keys(self, preset: Preset) -> set[tuple[str, str]]:
        from lineup_sim.core.constraints import _spin_covers_slots
        from lineup_sim.core.spin_options import decades_for_preset

        self.load_player_pool()
        if self._spin_index is None or self._viable_spin_cache is None:
            return set()
        cached = self._viable_spin_cache.get(preset.slug)
        if cached is not None:
            return cached
        allowed_decades = set(decades_for_preset(preset))
        viable: set[tuple[str, str]] = set()
        for (team_abbr, decade), players in self._spin_index.items():
            if decade not in allowed_decades:
                continue
            if _spin_covers_slots(players, preset.slots, self.sport_id):
                viable.add((team_abbr, decade))
        self._viable_spin_cache[preset.slug] = viable
        return viable

    def cohort_dataframe(self) -> pd.DataFrame:
        self.load_player_pool()
        return self._cohort_df if self._cohort_df is not None else pd.DataFrame()

    def cohort_slice(self, cohort: pd.DataFrame, player: PlayerSeason) -> pd.DataFrame:
        del cohort
        if self._cohort_slices is not None:
            sliced = self._cohort_slices.get((player.decade, player.position))
            if sliced is not None and not sliced.empty:
                return sliced
        return super().cohort_slice(self.cohort_dataframe(), player)

    def position_matches(self, player_pos: str, slot_pos: str) -> bool:
        return mlb_position_matches(player_pos, slot_pos)

    def side_matches(self, player_pos: str, side: str) -> bool:
        return mlb_side_matches(player_pos, side)

    def random_era_window(self, rng: random.Random) -> tuple[int, int]:
        start = rng.choice(list(range(1980, 2021, 10)))
        return start, start + 9

    def stat_composite(self, player: PlayerSeason, preset: Preset) -> float | None:
        if self._composite_cache is None:
            return mlb_stat_composite(player, preset)
        key = (player.player_id, player.season, player.team_abbr, player.role or "bat")
        cached = self._composite_cache.get(key)
        if cached is not None:
            return cached
        value = mlb_stat_composite(player, preset)
        self._composite_cache[key] = value
        return value

    def stat_tracking_factor(self, player: PlayerSeason, stat: str) -> float:
        positions = (player.position_raw or player.position).upper()
        is_pitcher = player.role == "pitch" or any(
            token in positions for token in PITCH_POSITIONS
        )
        if is_pitcher:
            return 1.0 if stat in {"W", "K", "SV", "ERA", "WHIP", "IP"} else 0.0
        return 1.0 if stat in {"AVG", "HR", "RBI", "SB", "OPS"} else 0.0

    def season_value(self, player: PlayerSeason) -> float:
        from lineup_sim.sports.mlb.scoring import (
            batting_tenure_composite,
            pitching_tenure_composite,
        )

        if player.role == "pitch":
            return pitching_tenure_composite(player)
        return batting_tenure_composite(player)
