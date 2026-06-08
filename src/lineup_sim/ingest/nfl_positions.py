"""Normalize nflverse positions to Lineup Sim roster slots."""

from __future__ import annotations

OFFENSE_POSITIONS = frozenset({"QB", "RB", "WR", "TE", "FB"})
OFFENSE_FLEX_POSITIONS = frozenset({"RB", "WR", "TE", "FB"})
DEFENSE_POSITIONS = frozenset({"EDGE", "DT", "LB", "CB", "S"})

# Raw codes that still appear in bundled rows or legacy data.
_EDGE_ALIASES = frozenset({"EDGE", "DE", "OLB"})
_LB_ALIASES = frozenset({"LB", "ILB", "MLB"})
_S_ALIASES = frozenset({"S", "SAF", "SS", "FS", "DB"})
_DT_ALIASES = frozenset({"DT", "NT", "DL"})


def normalize_nfl_position(position: str, position_group: str = "") -> str | None:
    """Map nflverse position codes to a fantasy roster position, or None to skip."""
    pos = (position or "").strip().upper()
    group = (position_group or "").strip().upper()

    if not pos and not group:
        return None

    if pos == "QB" or group == "QB":
        return "QB"
    if pos in {"RB", "FB"} or group == "RB":
        return "RB"
    if pos == "WR" or group == "WR":
        return "WR"
    if pos == "TE" or group == "TE":
        return "TE"

    if pos in _EDGE_ALIASES or (group == "DL" and pos in {"DE", "EDGE"}):
        return "EDGE"
    if pos in _DT_ALIASES or (group == "DL" and pos in {"DT", "NT"}):
        return "DT"
    if group == "LB":
        return "EDGE" if pos in {"DE", "OLB", "EDGE"} else "LB"
    if pos in _LB_ALIASES:
        return "LB"

    if pos == "CB" or (group == "DB" and pos == "CB"):
        return "CB"
    if pos in _S_ALIASES or group == "DB":
        return "S"

    return None


def offense_position(position: str) -> bool:
    return position.upper() in OFFENSE_POSITIONS


def offense_flex_position(position: str) -> bool:
    return position.upper() in OFFENSE_FLEX_POSITIONS


def defense_position(position: str) -> bool:
    return position.upper() in DEFENSE_POSITIONS
