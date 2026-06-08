"""Display labels for stat keys — aligned with Fantasy Tracker casing."""

from __future__ import annotations

_STAT_LABELS: dict[str, str] = {
    # NFL offense
    "yards": "Yds",
    "td": "TD",
    "pass_yds": "Pass Yds",
    "rush_yds": "Rush Yds",
    "rec_yds": "Rec Yds",
    "pass_td": "Pass TD",
    "rush_td": "Rush TD",
    "rec_td": "Rec TD",
    # NFL defense
    "sacks": "Sk",
    "tackles": "Tkl",
    "interceptions": "INT",
}


def stat_display_label(stat: str, *, sport: str | None = None) -> str:
    """Human-readable column label for a preset stat key."""
    del sport  # reserved for sport-specific overrides later
    if stat in _STAT_LABELS:
        return _STAT_LABELS[stat]
    if stat.isupper() or len(stat) <= 4:
        return stat
    return stat.replace("_", " ").title()


def integer_record(wins: float, max_games: int) -> tuple[int, int]:
    """Whole-number W-L that always sums to max_games."""
    wins_int = max(0, min(max_games, int(round(wins))))
    return wins_int, max_games - wins_int


def format_projected_record(
    projected_wins: float,
    *,
    max_games: int,
    projected_losses: float | None = None,
) -> str:
    wins_int, losses_int = integer_record(projected_wins, max_games)
    return f"{wins_int}-{losses_int}"
