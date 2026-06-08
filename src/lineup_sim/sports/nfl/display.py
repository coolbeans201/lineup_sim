"""Human-readable NFL stat lines for UI dropdowns."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason
from lineup_sim.ingest.nfl_positions import DEFENSE_POSITIONS
from lineup_sim.sports.nfl.scoring import _games_played, _has_split_offense_stats, _per_game

_OFFENSE_SPLIT_STATS: tuple[tuple[str, str, bool], ...] = (
    ("pass_yds", "pass yds/g", True),
    ("rush_yds", "rush yds/g", True),
    ("rec_yds", "rec yds/g", True),
    ("pass_td", "pass TD/g", False),
    ("rush_td", "rush TD/g", False),
    ("rec_td", "rec TD/g", False),
)


def _fmt_count(value: float, *, per_game: bool = False) -> str:
    if per_game and abs(value - round(value)) < 0.05:
        return f"{value:,.0f}"
    if abs(value - round(value)) < 0.05:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def _offense_split_line(player: PlayerSeason) -> str:
    games = _games_played(player)
    parts: list[str] = []
    for key, label, is_volume in _OFFENSE_SPLIT_STATS:
        total = player.stats.get(key, 0)
        if total <= 0:
            continue
        value = _per_game(total, games)
        parts.append(f"{_fmt_count(value, per_game=True)} {label}")
    return " · ".join(parts)


def _offense_legacy_line(player: PlayerSeason) -> str:
    games = _games_played(player)
    parts: list[str] = []
    yards = player.stats.get("yards", 0)
    td = player.stats.get("td", 0)
    if yards > 0:
        parts.append(f"{_fmt_count(_per_game(yards, games), per_game=True)} yds/g")
    if td > 0:
        parts.append(f"{_fmt_count(_per_game(td, games), per_game=True)} TD/g")
    return " · ".join(parts)


def _defense_line(player: PlayerSeason) -> str:
    parts: list[str] = []
    sacks = player.stats.get("sacks", 0)
    tackles = player.stats.get("tackles", 0)
    ints = player.stats.get("interceptions", 0)
    if sacks > 0:
        parts.append(f"{_fmt_count(sacks)} sk")
    if tackles > 0:
        parts.append(f"{_fmt_count(tackles)} tkl")
    if ints > 0:
        parts.append(f"{_fmt_count(ints)} INT")
    return " · ".join(parts)


def format_player_dropdown_stats(player: PlayerSeason) -> str:
    """Compact, position-aware stat summary for player pickers."""
    if player.position in DEFENSE_POSITIONS:
        return _defense_line(player) or "—"
    if _has_split_offense_stats(player):
        return _offense_split_line(player) or "—"
    return _offense_legacy_line(player) or "—"
