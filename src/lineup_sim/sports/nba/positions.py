"""Normalize Basketball Reference and API position strings to lineup slots."""

from __future__ import annotations

PRIMARY_POSITIONS = frozenset({"PG", "SG", "SF", "PF", "C"})
SLOT_ORDER = ("PG", "SG", "SF", "PF", "C")

# Whole-label combos (checked before splitting on "-")
COMPOUND_POSITION_SLOTS: dict[str, set[str]] = {
    "PG-SG": {"PG", "SG"},
    "SG-PG": {"PG", "SG"},
    "G-F": {"SG", "SF"},
    "F-G": {"SG", "SF"},
    "GF": {"SG", "SF"},
    "F-C": {"PF", "C"},
    "C-F": {"PF", "C"},
    "SF-PF": {"SF", "PF"},
    "PF-SF": {"SF", "PF"},
}

# Single tokens when a label is split (e.g. PG-SG -> PG + SG)
SINGLE_POSITION_SLOTS: dict[str, set[str]] = {
    "PG": {"PG"},
    "SG": {"SG"},
    "SF": {"SF"},
    "PF": {"PF"},
    "C": {"C"},
    "G": {"PG", "SG"},
    "F": {"SF", "PF"},
}


def _normalize_position_raw(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.upper().strip().replace("/", "-").replace(" ", "")


def eligible_lineup_positions(raw: str | None) -> set[str]:
    """Which of PG/SG/SF/PF/C can this player fill?"""
    cleaned = _normalize_position_raw(raw)
    if not cleaned:
        return set()

    if cleaned in COMPOUND_POSITION_SLOTS:
        return set(COMPOUND_POSITION_SLOTS[cleaned])

    parts = [part for part in cleaned.split("-") if part]
    if len(parts) > 1:
        eligible: set[str] = set()
        for part in parts:
            eligible |= SINGLE_POSITION_SLOTS.get(part, set())
        return eligible

    return set(SINGLE_POSITION_SLOTS.get(parts[0], set()))


def parse_position_tokens(raw: str | None) -> set[str]:
    """Literal tokens from a hyphenated BRef position label."""
    cleaned = _normalize_position_raw(raw)
    if not cleaned:
        return set()
    return {part for part in cleaned.split("-") if part}


def primary_position(raw: str | None) -> str:
    """Pick a single canonical position for storage and cohort grouping."""
    if not raw:
        return "G"
    cleaned = _normalize_position_raw(raw)
    if "F-C" in cleaned:
        return "PF"
    if "C-F" in cleaned:
        return "C"
    tokens = parse_position_tokens(raw)
    for pos in ("PG", "SG", "SF", "PF", "C"):
        if pos in tokens:
            return pos
    if "G" in tokens:
        return "SG"
    if "F" in tokens:
        return "SF"
    return "G"


def position_matches(player_pos: str, slot_pos: str) -> bool:
    """True if player can fill slot (supports multi-position labels like PG-SG)."""
    if not slot_pos:
        return True
    return slot_pos.upper() in eligible_lineup_positions(player_pos)
