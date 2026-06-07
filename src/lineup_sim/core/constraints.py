"""Era rules, spin logic, and player pool filtering."""

from __future__ import annotations

import random
from typing import Iterable

from lineup_sim.core.models import PlayerSeason, Preset, RosterSlot, SpinConstraint
from lineup_sim.core.peak import pick_peak_seasons
from lineup_sim.sports.registry import get_sport_plugin


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


def filter_pool(
    players: Iterable[PlayerSeason],
    *,
    team_abbr: str | None = None,
    decade: str | None = None,
    season_start: int | None = None,
    season_end: int | None = None,
    position: str | None = None,
    side: str | None = None,
    sport: str = "nba",
) -> list[PlayerSeason]:
    plugin = get_sport_plugin(sport)
    rows = list(players)
    out: list[PlayerSeason] = []

    for p in rows:
        if team_abbr and p.team_abbr.upper() != team_abbr.upper():
            continue
        if decade and p.decade != decade:
            continue
        if season_start is not None and p.season < season_start:
            continue
        if season_end is not None and p.season > season_end:
            continue
        if position and not plugin.position_matches(p.position_raw or p.position, position):
            continue
        if side and not plugin.side_matches(p.position, side):
            continue
        out.append(p)

    return out


def eligible_for_slot(
    player: PlayerSeason,
    slot: RosterSlot,
    sport: str,
    *,
    enforce_position: bool = True,
) -> bool:
    plugin = get_sport_plugin(sport)
    if slot.decade and player.decade != slot.decade:
        return False
    if enforce_position and slot.position and not plugin.position_matches(
        player.position_raw or player.position, slot.position
    ):
        return False
    if slot.side and not plugin.side_matches(player.position, slot.side):
        return False
    return True


def _nba_team_decade_has_players(
    pool: list[PlayerSeason],
    spin: SpinConstraint,
    *,
    min_pool_size: int,
) -> bool:
    return len(pool_for_spin(pool, spin, sport="nba")) >= min_pool_size


def _spin_has_players(
    pool: list[PlayerSeason],
    preset: Preset,
    spin: SpinConstraint,
    slot: RosterSlot,
    *,
    min_pool_size: int,
) -> bool:
    if preset.sport == "nba":
        return _nba_team_decade_has_players(pool, spin, min_pool_size=min_pool_size)
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


from lineup_sim.core.spin_options import NBA_DECADES, spin_constraint, spin_options_for_slot


def _nba_spin_candidates(
    pool: list[PlayerSeason],
    preset: Preset,
    slot: RosterSlot,
    teams: list[dict[str, str]],
    used: set[tuple[str, str]],
    *,
    min_pool_size: int,
) -> list[tuple[dict[str, str], str, int, int]]:
    decades = NBA_DECADES
    candidates: list[tuple[dict[str, str], str, int, int]] = []

    for team in teams:
        for decade in decades:
            key = (team["abbr"], decade)
            if key in used:
                continue
            start, end = seasons_for_decade(decade)
            probe = SpinConstraint(
                round_index=0,
                team_abbr=team["abbr"],
                team_name=team["name"],
                era_label=decade,
                season_start=start,
                season_end=end,
            )
            if _spin_has_players(pool, preset, probe, slot, min_pool_size=min_pool_size):
                candidates.append((team, decade, start, end))

    return candidates


def generate_spins(
    preset: Preset,
    *,
    seed: int,
    spin_count: int | None = None,
    min_pool_size: int = 1,
) -> list[SpinConstraint]:
    plugin = get_sport_plugin(preset.sport)
    pool = plugin.load_player_pool()
    teams = plugin.teams()
    rng = random.Random(seed)
    n = spin_count or preset.slot_count
    spins: list[SpinConstraint] = []
    used: set[tuple[str, str]] = set()

    for i in range(n):
        slot = preset.slots[i]

        if preset.sport == "nba":
            candidates = _nba_spin_candidates(
                pool, preset, slot, teams, used, min_pool_size=min_pool_size
            )
            if not candidates:
                raise ValueError(
                    f"No valid NBA team+decade spin with at least {min_pool_size} players "
                    f"(round {i + 1})"
                )
            candidates.sort(key=lambda item: (item[0]["abbr"], item[1]))
            team, era_label, start, end = rng.choice(candidates)
        else:
            picked = False
            for _ in range(500):
                team = rng.choice(teams)
                start, end = plugin.random_era_window(rng)
                era_label = era_window_label(start, end)
                key = (team["abbr"], era_label)
                if key in used:
                    continue
                probe = SpinConstraint(
                    round_index=i + 1,
                    team_abbr=team["abbr"],
                    team_name=team["name"],
                    era_label=era_label,
                    season_start=start,
                    season_end=end,
                )
                if not _spin_has_players(pool, preset, probe, slot, min_pool_size=min_pool_size):
                    continue
                picked = True
                break
            if not picked:
                raise ValueError(
                    f"No valid spin for slot {slot.label} ({slot.position or 'any'}) "
                    f"with at least {min_pool_size} eligible players"
                )

        used.add((team["abbr"], era_label))
        spins.append(
            SpinConstraint(
                round_index=i + 1,
                team_abbr=team["abbr"],
                team_name=team["name"],
                era_label=era_label,
                season_start=start,
                season_end=end,
            )
        )

    return spins


def pool_for_spin(
    all_players: list[PlayerSeason],
    spin: SpinConstraint,
    *,
    sport: str,
    position: str | None = None,
    side: str | None = None,
) -> list[PlayerSeason]:
    # NBA team+decade spins expose the full roster — position is chosen at draft time.
    if sport == "nba":
        position = None
        side = None
        decade = spin.era_label
        pool = filter_pool(
            all_players,
            team_abbr=spin.team_abbr,
            decade=decade,
            position=position,
            side=side,
            sport=sport,
        )
    else:
        pool = filter_pool(
            all_players,
            team_abbr=spin.team_abbr,
            season_start=spin.season_start,
            season_end=spin.season_end,
            position=position,
            side=side,
            sport=sport,
        )
    return pick_peak_seasons(pool, sport)
