"""Player identity helpers for roster uniqueness rules."""

from __future__ import annotations

from lineup_sim.core.models import Lineup, PlayerSeason


def player_identity(player: PlayerSeason) -> str:
    """Stable identity for roster uniqueness (same person across seasons)."""
    from lineup_sim.core.names import normalize_player_name

    return normalize_player_name(player.player_name)


def assigned_identities(lineup: Lineup, *, exclude_slot_id: str | None = None) -> set[str]:
    identities: set[str] = set()
    for assignment in lineup.assignments:
        if assignment.player is None:
            continue
        if exclude_slot_id and assignment.slot_id == exclude_slot_id:
            continue
        identities.add(player_identity(assignment.player))
    return identities
