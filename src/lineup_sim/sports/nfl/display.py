"""Human-readable NFL stat lines for UI dropdowns and tables."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason
from lineup_sim.ingest.nfl_positions import DEFENSE_POSITIONS
from lineup_sim.sports.nfl.scoring import _has_split_offense_stats

_OFFENSE_SPLIT_STATS: tuple[tuple[str, str], ...] = (
    ("pass_yds", "pass yds"),
    ("rush_yds", "rush yds"),
    ("rec_yds", "rec yds"),
    ("pass_td", "pass TD"),
    ("rush_td", "rush TD"),
    ("rec_td", "rec TD"),
)


def _fmt_count(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def _offense_split_line(player: PlayerSeason) -> str:
    parts: list[str] = []
    for key, label in _OFFENSE_SPLIT_STATS:
        total = player.stats.get(key, 0)
        if total <= 0:
            continue
        parts.append(f"{_fmt_count(total)} {label}")
    return " · ".join(parts)


def _offense_legacy_line(player: PlayerSeason) -> str:
    parts: list[str] = []
    yards = player.stats.get("yards", 0)
    td = player.stats.get("td", 0)
    if yards > 0:
        parts.append(f"{_fmt_count(yards)} yds")
    if td > 0:
        parts.append(f"{_fmt_count(td)} TD")
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
    """Season-total stat summary for player pickers (matches lineup tables)."""
    if player.position in DEFENSE_POSITIONS:
        return _defense_line(player) or "—"
    if _has_split_offense_stats(player):
        return _offense_split_line(player) or "—"
    return _offense_legacy_line(player) or "—"
