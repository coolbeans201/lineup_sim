"""Roster construction helpers."""

from __future__ import annotations

from dataclasses import dataclass

from lineup_sim.core.models import Lineup, PlayerSeason, Preset, RosterSlot, SlotAssignment
from lineup_sim.core.constraints import eligible_for_slot
from lineup_sim.core.roster_identity import assigned_identities, player_identity

__all__ = [
    "assign_player",
    "assigned_identities",
    "completion_ratio",
    "eligible_open_slots",
    "eligible_reassign_slots",
    "empty_lineup",
    "find_player_in_pool",
    "lineup_from_dict",
    "lineup_to_dict",
    "open_slots",
    "player_identity",
    "player_pool_key",
    "reassign_player",
    "swap_plans_for_new_pick",
    "swappable_assignments",
    "PickSwapPlan",
]


@dataclass(frozen=True)
class PickSwapPlan:
    """Move an occupant off a slot so a new pick can take that position."""

    assign_slot_id: str
    move_to_slot_id: str
    occupant: PlayerSeason


def player_pool_key(player: PlayerSeason) -> tuple[str, ...]:
    """Disambiguate pool rows that share a player_id across teams/seasons/roles."""
    key: tuple[str, ...] = (player.player_id, player.season, player.team_abbr.upper())
    if player.role:
        return key + (player.role,)
    return key


def find_player_in_pool(
    pool: Iterable[PlayerSeason],
    *,
    player_id: str,
    season: int | None = None,
    team_abbr: str | None = None,
    role: str | None = None,
) -> PlayerSeason | None:
    if season is not None and team_abbr:
        target: tuple[str, ...] = (player_id, season, team_abbr.upper())
        if role:
            target = target + (role,)
        for player in pool:
            if player_pool_key(player) == target:
                return player
        return None
    return next((player for player in pool if player.player_id == player_id), None)


def empty_lineup(preset: Preset, label: str = "Lineup A") -> Lineup:
    return Lineup(
        preset_slug=preset.slug,
        sport=preset.sport,
        label=label,
        assignments=[SlotAssignment(slot_id=s.slot_id) for s in preset.slots],
    )


def offense_first_draft(preset: Preset) -> bool:
    """NFL offense/defense presets: fill all offense slots before defense opens."""
    if preset.sport != "nfl":
        return False
    sides = {s.side for s in preset.slots if s.side}
    return "offense" in sides and "defense" in sides


def open_slots(lineup: Lineup, preset: Preset) -> list[RosterSlot]:
    filled = {a.slot_id for a in lineup.assignments if a.player is not None}
    empty = [s for s in preset.slots if s.slot_id not in filled]
    if offense_first_draft(preset):
        offense_empty = [s for s in empty if s.side == "offense"]
        if offense_empty:
            return offense_empty
        return [s for s in empty if s.side == "defense"]
    return empty


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


def eligible_reassign_slots(
    player: PlayerSeason,
    lineup: Lineup,
    preset: Preset,
    sport: str,
    *,
    from_slot_id: str,
) -> list[RosterSlot]:
    """Empty slots a locked-in player can move to (freeing their current slot)."""
    return [
        slot
        for slot in eligible_open_slots(player, lineup, preset, sport)
        if slot.slot_id != from_slot_id
    ]


def swap_plans_for_new_pick(
    player: PlayerSeason,
    lineup: Lineup,
    preset: Preset,
    sport: str,
) -> list[PickSwapPlan]:
    """Ways to free an occupied slot the new pick qualifies for by moving someone else."""
    slot_map = {s.slot_id: s for s in preset.slots}
    plans: list[PickSwapPlan] = []
    seen: set[tuple[str, str, str]] = set()

    for assignment in lineup.assignments:
        if assignment.player is None:
            continue
        slot = slot_map[assignment.slot_id]
        if not eligible_for_slot(player, slot, sport, enforce_position=True):
            continue
        for target in eligible_reassign_slots(
            assignment.player,
            lineup,
            preset,
            sport,
            from_slot_id=assignment.slot_id,
        ):
            key = (assignment.slot_id, target.slot_id, player.player_id)
            if key in seen:
                continue
            seen.add(key)
            plans.append(
                PickSwapPlan(
                    assign_slot_id=assignment.slot_id,
                    move_to_slot_id=target.slot_id,
                    occupant=assignment.player,
                )
            )
    return plans


def swappable_assignments(
    lineup: Lineup,
    preset: Preset,
    sport: str,
) -> list[tuple[SlotAssignment, list[RosterSlot]]]:
    """Locked-in players who can move to at least one other open eligible slot."""
    out: list[tuple[SlotAssignment, list[RosterSlot]]] = []
    for assignment in lineup.assignments:
        if assignment.player is None:
            continue
        targets = eligible_reassign_slots(
            assignment.player,
            lineup,
            preset,
            sport,
            from_slot_id=assignment.slot_id,
        )
        if targets:
            out.append((assignment, targets))
    return out


def reassign_player(
    lineup: Lineup,
    preset: Preset,
    from_slot_id: str,
    to_slot_id: str,
) -> Lineup:
    """Move a locked-in player to another empty slot they qualify for."""
    if from_slot_id == to_slot_id:
        raise ValueError("Cannot reassign a player to the same slot")

    slot_map = {s.slot_id: s for s in preset.slots}
    if from_slot_id not in slot_map or to_slot_id not in slot_map:
        raise ValueError("Unknown slot")

    from_assignment = next(a for a in lineup.assignments if a.slot_id == from_slot_id)
    if from_assignment.player is None:
        raise ValueError(f"No player assigned to slot {from_slot_id}")

    to_assignment = next(a for a in lineup.assignments if a.slot_id == to_slot_id)
    if to_assignment.player is not None:
        raise ValueError(f"Slot {to_slot_id} is not empty")

    player = from_assignment.player
    targets = eligible_reassign_slots(
        player,
        lineup,
        preset,
        preset.sport,
        from_slot_id=from_slot_id,
    )
    if not any(slot.slot_id == to_slot_id for slot in targets):
        raise ValueError(
            f"{player.player_name} cannot move from {from_slot_id} to {to_slot_id}"
        )

    new_assignments: list[SlotAssignment] = []
    for assignment in lineup.assignments:
        if assignment.slot_id == from_slot_id:
            new_assignments.append(SlotAssignment(slot_id=from_slot_id, player=None))
        elif assignment.slot_id == to_slot_id:
            new_assignments.append(SlotAssignment(slot_id=to_slot_id, player=player))
        else:
            new_assignments.append(assignment)

    return Lineup(
        preset_slug=lineup.preset_slug,
        sport=lineup.sport,
        label=lineup.label,
        assignments=new_assignments,
        metadata=dict(lineup.metadata),
    )


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
                role=raw.get("role", ""),
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
            "role": p.role,
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
