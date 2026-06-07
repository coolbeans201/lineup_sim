"""Roster construction helpers."""

from __future__ import annotations

from lineup_sim.core.models import Lineup, PlayerSeason, Preset, RosterSlot, SlotAssignment
from lineup_sim.core.constraints import eligible_for_slot
from lineup_sim.core.roster_identity import assigned_identities, player_identity

__all__ = [
    "assign_player",
    "assigned_identities",
    "completion_ratio",
    "eligible_open_slots",
    "empty_lineup",
    "lineup_from_dict",
    "lineup_to_dict",
    "open_slots",
    "player_identity",
]


def empty_lineup(preset: Preset, label: str = "Lineup A") -> Lineup:
    return Lineup(
        preset_slug=preset.slug,
        sport=preset.sport,
        label=label,
        assignments=[SlotAssignment(slot_id=s.slot_id) for s in preset.slots],
    )


def open_slots(lineup: Lineup, preset: Preset) -> list[RosterSlot]:
    filled = {a.slot_id for a in lineup.assignments if a.player is not None}
    return [s for s in preset.slots if s.slot_id not in filled]


def eligible_open_slots(
    player: PlayerSeason,
    lineup: Lineup,
    preset: Preset,
    sport: str,
) -> list[RosterSlot]:
    return [
        slot
        for slot in open_slots(lineup, preset)
        if eligible_for_slot(player, slot, sport, enforce_position=True)
    ]


def assign_player(
    lineup: Lineup,
    preset: Preset,
    slot_id: str,
    player: PlayerSeason | None,
    *,
    enforce_position: bool = True,
) -> Lineup:
    slot_map = {s.slot_id: s for s in preset.slots}
    if slot_id not in slot_map:
        raise ValueError(f"Unknown slot: {slot_id}")
    if player is not None and not eligible_for_slot(
        player,
        slot_map[slot_id],
        preset.sport,
        enforce_position=enforce_position,
    ):
        raise ValueError(f"{player.player_name} is not eligible for slot {slot_id}")

    new_assignments: list[SlotAssignment] = []
    for a in lineup.assignments:
        if a.slot_id == slot_id:
            new_assignments.append(SlotAssignment(slot_id=slot_id, player=player))
        elif (
            player is not None
            and a.player is not None
            and player_identity(a.player) == player_identity(player)
        ):
            new_assignments.append(SlotAssignment(slot_id=a.slot_id, player=None))
        else:
            new_assignments.append(a)

    return Lineup(
        preset_slug=lineup.preset_slug,
        sport=lineup.sport,
        label=lineup.label,
        assignments=new_assignments,
        metadata=dict(lineup.metadata),
    )


def lineup_from_dict(preset: Preset, data: dict, label: str = "Lineup A") -> Lineup:
    lineup = empty_lineup(preset, label=label)
    player_index = {p["player_id"]: p for p in data.get("players", [])}
    for slot_id, player_id in data.get("slots", {}).items():
        if player_id and player_id in player_index:
            raw = player_index[player_id]
            player = PlayerSeason(
                player_id=raw["player_id"],
                player_name=raw["player_name"],
                team=raw["team"],
                team_abbr=raw["team_abbr"],
                season=int(raw["season"]),
                position=raw["position"],
                position_raw=raw.get("position_raw", raw["position"]),
                stats={k: float(v) for k, v in raw.get("stats", {}).items()},
                decade=raw.get("decade", ""),
            )
            lineup = assign_player(lineup, preset, slot_id, player)
    return lineup


def lineup_to_dict(lineup: Lineup) -> dict:
    players: dict[str, dict] = {}
    slots: dict[str, str | None] = {}
    for a in lineup.assignments:
        slots[a.slot_id] = None
        if a.player is None:
            continue
        p = a.player
        slots[a.slot_id] = p.player_id
        players[p.player_id] = {
            "player_id": p.player_id,
            "player_name": p.player_name,
            "team": p.team,
            "team_abbr": p.team_abbr,
            "season": p.season,
            "position": p.position,
            "position_raw": p.position_raw,
            "stats": p.stats,
            "decade": p.decade,
        }
    return {
        "preset_slug": lineup.preset_slug,
        "sport": lineup.sport,
        "label": lineup.label,
        "slots": slots,
        "players": list(players.values()),
        "metadata": lineup.metadata,
    }


def completion_ratio(lineup: Lineup) -> float:
    filled = sum(1 for a in lineup.assignments if a.player is not None)
    return filled / max(len(lineup.assignments), 1)
