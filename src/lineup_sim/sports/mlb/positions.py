"""MLB position eligibility for lineup slots."""

from __future__ import annotations

FIELD_POSITIONS = frozenset({"C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "OF", "DH"})
PITCH_POSITIONS = frozenset({"SP", "RP", "P"})


def parse_positions(position_raw: str) -> set[str]:
    return {part.strip().upper() for part in position_raw.split("/") if part.strip()}


def position_matches(player_pos: str, slot_pos: str) -> bool:
    slot = slot_pos.upper()
    positions = parse_positions(player_pos)
    if not positions:
        positions = {player_pos.upper()}

    if slot == "DH":
        return bool(positions & (FIELD_POSITIONS - {"DH"})) or "DH" in positions

    if slot == "CL":
        return "RP" in positions or "CL" in positions or "P" in positions

    if slot in {"LF", "CF", "RF"}:
        return slot in positions or "OF" in positions

    return slot in positions


def side_matches(player_pos: str, side: str) -> bool:
    positions = parse_positions(player_pos)
    if not positions:
        positions = {player_pos.upper()}
    if side == "batting":
        return bool(positions & FIELD_POSITIONS) and not positions <= PITCH_POSITIONS
    if side == "pitching":
        return bool(positions & PITCH_POSITIONS)
    return True
