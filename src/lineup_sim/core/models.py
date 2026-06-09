"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlayerSeason:
    """One player-season row used for drafting and scoring."""

    player_id: str
    player_name: str
    team: str
    team_abbr: str
    season: int
    position: str
    stats: dict[str, float]
    decade: str = ""
    position_raw: str = ""
    role: str = ""  # mlb: "bat" | "pitch"

    def __post_init__(self) -> None:
        if not self.decade:
            self.decade = decade_label(self.season)
        if not self.position_raw:
            self.position_raw = self.position


@dataclass
class RosterSlot:
    slot_id: str
    label: str
    position: str | None = None
    weight: float = 1.0
    decade: str | None = None
    side: str | None = None  # offense / defense / batting / pitching


@dataclass
class Preset:
    sport: str
    name: str
    slug: str
    description: str
    slots: list[RosterSlot]
    stat_weights: dict[str, float]
    max_games: int
    position_weights: dict[str, float] = field(default_factory=dict)
    balance_penalty: float = 0.15
    grade_thresholds: dict[str, float] = field(default_factory=dict)
    rating_baseline: float | None = None
    win_rating_slope: float = 0.30
    era_decades: list[str] = field(default_factory=list)

    @property
    def slot_count(self) -> int:
        return len(self.slots)


@dataclass
class SlotAssignment:
    slot_id: str
    player: PlayerSeason | None = None


@dataclass
class Lineup:
    preset_slug: str
    sport: str
    assignments: list[SlotAssignment]
    label: str = "Lineup A"
    metadata: dict[str, Any] = field(default_factory=dict)

    def filled_players(self) -> list[tuple[RosterSlot, PlayerSeason]]:
        from lineup_sim.core.presets import get_preset

        preset = get_preset(self.preset_slug)
        slot_map = {s.slot_id: s for s in preset.slots}
        out: list[tuple[RosterSlot, PlayerSeason]] = []
        for a in self.assignments:
            if a.player is not None:
                out.append((slot_map[a.slot_id], a.player))
        return out


@dataclass
class PlayerRating:
    player: PlayerSeason
    slot_id: str
    composite_z: float
    slot_rating: float
    stat_zs: dict[str, float]


@dataclass
class ScoreResult:
    team_rating: float
    projected_wins: float
    projected_losses: float
    max_games: int
    grade: str
    player_ratings: list[PlayerRating]
    category_totals: dict[str, float]
    weakest_slot_id: str | None
    balance_adjustment: float
    formula_notes: list[str]
    win_pct: float = 0.0
    record_notes: list[str] = field(default_factory=list)


@dataclass
class SpinConstraint:
    """One random draft round: team + era window."""

    round_index: int
    team_abbr: str
    team_name: str
    era_label: str
    season_start: int
    season_end: int


@dataclass
class DailyPuzzle:
    sport: str
    date: str
    preset_slug: str
    seed: int
    spins: list[SpinConstraint]


@dataclass
class LeaderboardEntry:
    date: str
    sport: str
    preset_slug: str
    player_name: str
    team_rating: float
    projected_wins: float
    grade: str
    share_code: str
    lineup_summary: str
    projected_losses: float | None = None
    share_token: str | None = None


def decade_label(season: int) -> str:
    if season < 1960:
        return "1950s"
    if season < 1970:
        return "1960s"
    if season < 1980:
        return "1970s"
    if season < 1990:
        return "1980s"
    if season < 2000:
        return "1990s"
    if season < 2010:
        return "2000s"
    if season < 2020:
        return "2010s"
    return "2020s"


DECADE_ORDER: dict[str, int] = {
    "1950s": 1950,
    "1960s": 1960,
    "1970s": 1970,
    "1980s": 1980,
    "1990s": 1990,
    "2000s": 2000,
    "2010s": 2010,
    "2020s": 2020,
}


def decade_sort_key(decade: str | None) -> int:
    if not decade:
        return 9999
    return DECADE_ORDER.get(decade, 9999)
