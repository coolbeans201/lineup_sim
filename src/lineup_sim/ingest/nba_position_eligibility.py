"""Derive BRef-style multi-position eligibility from per-game data."""

from __future__ import annotations

from collections import defaultdict

from lineup_sim.core.names import normalize_player_name
from lineup_sim.sports.nba.positions import SLOT_ORDER, eligible_lineup_positions, primary_position

__all__ = [
    "SLOT_ORDER",
    "apply_career_position",
    "build_career_position_map",
    "combo_from_slots",
    "load_career_position_overrides",
    "merge_career_position_maps",
    "slots_from_pos_label",
]


def slots_from_pos_label(pos_raw: str | None) -> set[str]:
    if not pos_raw:
        return set()
    return eligible_lineup_positions(str(pos_raw).strip())


def combo_from_slots(slots: set[str]) -> str:
    ordered = [slot for slot in SLOT_ORDER if slot in slots]
    if not ordered:
        return "G"
    return "-".join(ordered)


def build_career_position_map(records: list[dict]) -> dict[str, str]:
    """
    Union every BRef ``pos`` / ``position_raw`` label a player appears under.

    Matches 82-0-style versatility: LeBron listed as SF, PG, C, PF, SG across
    his career → ``PG-SG-SF-PF-C``.
    """
    accum: dict[str, set[str]] = defaultdict(set)
    for record in records:
        name = normalize_player_name(record.get("player_name") or record.get("player", ""))
        if not name:
            continue
        pos_raw = record.get("position_raw") or record.get("pos") or record.get("position")
        if pos_raw is None:
            continue
        text = str(pos_raw).strip()
        if not text or text.lower() == "nan":
            continue
        accum[name] |= slots_from_pos_label(text.upper())

    return {name: combo_from_slots(slots) for name, slots in accum.items() if slots}


def merge_career_position_maps(*maps: dict[str, str]) -> dict[str, str]:
    merged: dict[str, set[str]] = defaultdict(set)
    for career_map in maps:
        for name, combo in career_map.items():
            merged[name] |= slots_from_pos_label(combo)
    return {name: combo_from_slots(slots) for name, slots in merged.items() if slots}


def load_career_position_overrides() -> dict[str, str]:
    """Fixture rows with richer BRef combo labels (e.g. Oscar PG-SG)."""
    from lineup_sim.ingest.nba_bref import load_historical_fixtures

    return build_career_position_map(load_historical_fixtures())


def apply_career_position(row: dict, career_map: dict[str, str]) -> dict:
    name = normalize_player_name(row.get("player_name", ""))
    combo = career_map.get(name)
    if not combo:
        return row
    out = dict(row)
    out["position_raw"] = combo
    out["position"] = primary_position(combo)
    return out
