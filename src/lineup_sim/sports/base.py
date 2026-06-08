"""Sport plugin interface."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from lineup_sim.core.models import PlayerSeason, Preset


class SportPlugin(ABC):
    sport_id: str
    display_name: str

    @abstractmethod
    def teams(self) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def load_player_pool(self) -> list[PlayerSeason]:
        raise NotImplementedError

    def position_matches(self, player_pos: str, slot_pos: str) -> bool:
        return player_pos.upper() == slot_pos.upper()

    def side_matches(self, player_pos: str, side: str) -> bool:
        return True

    def season_value(self, player: PlayerSeason) -> float:
        return sum(player.stats.values())

    def stat_composite(self, player: PlayerSeason, preset: Preset) -> float | None:
        """Optional sport-specific stat score; None falls back to preset stat_weights."""
        return None

    def stat_direction(self, stat: str) -> float:
        if stat.upper() in {"ERA", "WHIP", "INT", "TOV", "TURNOVERS"}:
            return -1.0
        return 1.0

    def stat_tracking_factor(self, player: PlayerSeason, stat: str) -> float:
        """1.0 when the stat was reliably tracked; 0.0 to drop it from scoring."""
        return 1.0

    def cohort_slice(self, cohort: pd.DataFrame, player: PlayerSeason) -> pd.DataFrame:
        if cohort.empty:
            return cohort
        mask = (cohort["season"] == player.season) & (cohort["position"] == player.position)
        sliced = cohort.loc[mask]
        if len(sliced) >= 5:
            return sliced
        decade_mask = (cohort["decade"] == player.decade) & (cohort["position"] == player.position)
        return cohort.loc[decade_mask]

    def random_era_window(self, rng: random.Random) -> tuple[int, int]:
        start = rng.choice(range(1999, 2021, 5))
        return start, start + 4

    def search_players(
        self,
        query: str,
        *,
        decade: str | None = None,
        position: str | None = None,
        limit: int = 25,
    ) -> list[PlayerSeason]:
        pool = self.load_player_pool()
        q = query.lower().strip()
        out: list[PlayerSeason] = []
        for p in pool:
            if q and q not in p.player_name.lower() and q not in p.team.lower():
                continue
            if decade and p.decade != decade:
                continue
            if position and not self.position_matches(p.position, position):
                continue
            out.append(p)
            if len(out) >= limit:
                break
        return out
