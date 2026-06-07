"""Team-era spin options for manual constraint picking."""

from __future__ import annotations

from lineup_sim.core.models import PlayerSeason, Preset, RosterSlot, SpinConstraint
from lineup_sim.sports.registry import get_sport_plugin

NBA_DECADES = ["1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]
OTHER_SPORT_DECADES = ["1990s", "2000s", "2010s", "2020s"]


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
) -> bool:
    from lineup_sim.core.constraints import pool_for_spin

    if preset.sport == "nba":
        return len(pool_for_spin(pool, spin, sport="nba")) >= min_pool_size
    assert slot is not None
    return (
        len(
            pool_for_spin(
                pool,
                spin,
                sport=preset.sport,
                position=slot.position,
                side=slot.side,
            )
        )
        >= min_pool_size
    )


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
            era_label = decade if preset.sport == "nba" else era_window_label(start, end)
            probe = spin_constraint(
                round_index=0,
                team=team,
                era_label=era_label,
                season_start=start,
                season_end=end,
            )
            if _spin_has_players(pool, preset, probe, None, min_pool_size=min_pool_size):
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
