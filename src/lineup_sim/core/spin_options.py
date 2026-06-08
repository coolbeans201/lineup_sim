"""Team-era spin options for manual constraint picking."""

from __future__ import annotations

from lineup_sim.core.models import Lineup, PlayerSeason, Preset, RosterSlot, SpinConstraint
from lineup_sim.sports.registry import get_sport_plugin

NBA_DECADES = ["1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]
OTHER_SPORT_DECADES = ["1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]
PICK_SPIN_SPORTS = frozenset({"nba", "nfl"})


def seasons_for_decade(decade: str) -> tuple[int, int]:
    mapping = {
        "1950s": (1950, 1959),
        "1960s": (1960, 1969),
        "1970s": (1970, 1979),
        "1980s": (1980, 1989),
        "1990s": (1990, 1999),
        "2000s": (2000, 2009),
        "2010s": (2010, 2019),
        "2020s": (2020, 2029),
    }
    return mapping[decade]


def era_window_label(start: int, end: int) -> str:
    if start == end:
        return str(start)
    return f"{start}-{end}"


def spin_constraint(
    *,
    round_index: int,
    team: dict[str, str],
    era_label: str,
    season_start: int,
    season_end: int,
) -> SpinConstraint:
    return SpinConstraint(
        round_index=round_index,
        team_abbr=team["abbr"],
        team_name=team["name"],
        era_label=era_label,
        season_start=season_start,
        season_end=season_end,
    )


def _spin_has_players(
    pool: list[PlayerSeason],
    preset: Preset,
    spin: SpinConstraint,
    slot: RosterSlot | None,
    *,
    min_pool_size: int,
    required_slots: list[RosterSlot] | None = None,
) -> bool:
    from lineup_sim.core.constraints import _spin_has_players as constraints_spin_has_players

    return constraints_spin_has_players(
        pool,
        preset,
        spin,
        slot,
        min_pool_size=min_pool_size,
        required_slots=required_slots,
    )


def spin_options_for_pick(
    preset: Preset,
    pool: list[PlayerSeason] | None = None,
    *,
    min_pool_size: int = 1,
    lineup: Lineup | None = None,
    pick_index: int | None = None,
) -> list[SpinConstraint]:
    """Team+era combos for pick-then-assign draft (NBA/NFL) — not filtered by slot position."""
    if preset.sport not in PICK_SPIN_SPORTS:
        raise ValueError(f"spin_options_for_pick does not support {preset.sport}")
    from lineup_sim.core.constraints import anticipated_open_slots

    plugin = get_sport_plugin(preset.sport)
    pool = pool or plugin.load_player_pool()
    teams = plugin.teams()
    decades = NBA_DECADES if preset.sport == "nba" else OTHER_SPORT_DECADES
    required_slots = None
    if lineup is not None and pick_index is not None:
        required_slots = anticipated_open_slots(preset, pick_index, lineup)
    options: list[SpinConstraint] = []

    for team in teams:
        for decade in decades:
            start, end = seasons_for_decade(decade)
            probe = spin_constraint(
                round_index=0,
                team=team,
                era_label=decade,
                season_start=start,
                season_end=end,
            )
            if _spin_has_players(
                pool,
                preset,
                probe,
                None,
                min_pool_size=min_pool_size,
                required_slots=required_slots,
            ):
                options.append(probe)

    options.sort(key=lambda spin: (spin.team_name, spin.era_label))
    return options


def spin_options_for_slot(
    preset: Preset,
    slot: RosterSlot,
    pool: list[PlayerSeason] | None = None,
    *,
    min_pool_size: int = 1,
) -> list[SpinConstraint]:
    """Team-era combos with enough players to draft from (NBA: any position)."""
    plugin = get_sport_plugin(preset.sport)
    pool = pool or plugin.load_player_pool()
    teams = plugin.teams()
    decades = NBA_DECADES if preset.sport == "nba" else OTHER_SPORT_DECADES
    options: list[SpinConstraint] = []

    for team in teams:
        for decade in decades:
            start, end = seasons_for_decade(decade)
            era_label = decade
            probe = spin_constraint(
                round_index=0,
                team=team,
                era_label=era_label,
                season_start=start,
                season_end=end,
            )
            if _spin_has_players(pool, preset, probe, slot, min_pool_size=min_pool_size):
                options.append(
                    spin_constraint(
                        round_index=0,
                        team=team,
                        era_label=era_label,
                        season_start=start,
                        season_end=end,
                    )
                )

    options.sort(key=lambda spin: (spin.team_name, spin.era_label))
    return options
