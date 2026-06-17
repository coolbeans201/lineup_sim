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


def era_column_label(*, sport: str | None = None) -> str:
    """Table column for when a player played (season year or franchise decade)."""
    return "Decade" if sport == "mlb" else "Season"


def player_era_display(player, *, sport: str | None = None) -> str | int:
    """Value for the era column in player tables."""
    if sport == "mlb":
        return player.decade or "—"
    return player.season


def stat_display_label(stat: str, *, sport: str | None = None) -> str:
    """Human-readable column label for a preset stat key."""
    del sport  # reserved for sport-specific overrides later
    if stat in _STAT_LABELS:
        return _STAT_LABELS[stat]
    if stat.isupper() or len(stat) <= 4:
        return stat
    return stat.replace("_", " ").title()


_MLB_RATE_DECIMALS: dict[str, int] = {
    "AVG": 3,
    "OPS": 3,
    "OBP": 3,
    "SLG": 3,
    "ERA": 2,
    "WHIP": 2,
}


def format_stat_display_value(value: float, stat: str, *, sport: str | None = None) -> int | float:
    """Numeric value for table cells — counting stats as integers, rates with fixed decimals."""
    if sport == "mlb":
        if stat in _MLB_RATE_DECIMALS:
            return round(value, _MLB_RATE_DECIMALS[stat])
        return int(round(value))
    if sport == "nfl":
        return int(round(value))
    return round(value, 1)


def format_stat_display_string(value: float, stat: str, *, sport: str | None = None) -> str:
    """Text value for inline stat summaries."""
    formatted = format_stat_display_value(value, stat, sport=sport)
    if isinstance(formatted, int):
        return str(formatted)
    if sport == "mlb" and stat in _MLB_RATE_DECIMALS:
        return f"{formatted:.{_MLB_RATE_DECIMALS[stat]}f}"
    return f"{formatted:.1f}"


def stat_accumulates_in_lineup_total(stat: str, *, sport: str | None = None) -> bool:
    """Whether a stat should appear summed in the team totals row."""
    if sport == "mlb" and stat in _MLB_RATE_DECIMALS:
        return False
    return True


def lineup_breakdown_caption(preset) -> str:
    """Sport-aware caption for locked-in and score breakdown tables."""
    if preset.sport == "mlb":
        return (
            "Franchise-decade tenure totals for each pick, weighted stat score, and slot rating "
            "(how much that player pulls team rating up or down)."
        )
    if preset.sport == "nfl":
        return (
            "Season stat totals for each pick; slot rating uses per-game fantasy points × position weight. "
            "Composite Z is era-relative vs position/season peers — use it with the stats to judge each pick."
        )
    return (
        "Per-game stats for each pick, weighted stat score, and slot rating "
        "(how much that player pulls team rating up or down)."
    )


def empty_lineup_formula_notes(preset) -> list[str]:
    if preset.sport == "mlb":
        stat_note = "Slot rating = weighted franchise-decade tenure stats × slot/position weight."
    elif preset.sport == "nfl":
        stat_note = "Slot rating = per-game fantasy composite × slot/position weight."
    else:
        stat_note = "Slot rating = weighted per-game stats × slot/position weight."
    return [
        stat_note,
        "Composite Z = era-relative context vs position/season peers (display only).",
        "Team rating = weighted mean slot ratings minus balance penalty for weak slot.",
    ]


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
