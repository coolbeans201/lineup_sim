"""Era rules, spin logic, and player pool filtering."""

from __future__ import annotations

import random
from typing import Iterable

from lineup_sim.core.models import Lineup, PlayerSeason, Preset, RosterSlot, SpinConstraint
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
    if sport == "mlb" and team_abbr and decade and position is None and side is None:
        from lineup_sim.sports.mlb.plugin import MLBPlugin

        plugin = get_sport_plugin("mlb")
        if isinstance(plugin, MLBPlugin):
            return plugin.spin_pool(team_abbr, decade)

    plugin = get_sport_plugin(sport)
    out: list[PlayerSeason] = []

    for p in players:
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


def anticipated_open_slots(
    preset: Preset,
    pick_index: int,
    lineup: Lineup | None = None,
) -> list[RosterSlot]:
    """Open slots for spin validation — uses live lineup when drafting, else pick phase."""
    from lineup_sim.core.roster import offense_first_draft, open_slots

    if lineup is not None and any(a.player is not None for a in lineup.assignments):
        return open_slots(lineup, preset)
    if offense_first_draft(preset):
        offense_slots = [s for s in preset.slots if s.side == "offense"]
        defense_slots = [s for s in preset.slots if s.side == "defense"]
        if pick_index <= len(offense_slots):
            return offense_slots
        return defense_slots
    return list(preset.slots)


def players_fitting_open_slots(
    player_pool: Iterable[PlayerSeason],
    lineup: Lineup,
    preset: Preset,
    sport: str,
) -> list[PlayerSeason]:
    """Players from a pool who can fill at least one currently open slot."""
    from lineup_sim.core.roster import open_slots, player_pool_key

    slots = open_slots(lineup, preset)
    if not slots:
        return []

    out: list[PlayerSeason] = []
    seen: set[tuple[str, int, str]] = set()
    for player in player_pool:
        key = player_pool_key(player)
        if key in seen:
            continue
        if any(eligible_for_slot(player, slot, sport) for slot in slots):
            out.append(player)
            seen.add(key)
    return out


def _count_players_fitting_slots(
    player_pool: Iterable[PlayerSeason],
    slots: Iterable[RosterSlot],
    sport: str,
) -> int:
    slot_list = list(slots)
    if not slot_list:
        return 0
    return sum(
        1
        for player in player_pool
        if any(eligible_for_slot(player, slot, sport) for slot in slot_list)
    )


def _spin_covers_slots(
    player_pool: Iterable[PlayerSeason],
    slots: Iterable[RosterSlot],
    sport: str,
) -> bool:
    """True when the pool can fill every required slot (MLB lineup viability)."""
    slot_list = list(slots)
    if not slot_list:
        return False
    pool = list(player_pool)
    if not pool:
        return False
    return all(
        any(eligible_for_slot(player, slot, sport) for player in pool)
        for slot in slot_list
    )


def used_spin_keys(spins: list[SpinConstraint] | None, pick_index: int) -> set[tuple[str, str]]:
    if not spins or pick_index <= 1:
        return set()
    return {(spin.team_abbr, spin.era_label) for spin in spins[: pick_index - 1]}


def choose_spin_for_lineup(
    *,
    pool: list[PlayerSeason],
    preset: Preset,
    lineup: Lineup,
    sport: str,
    used: set[tuple[str, str]],
    pick_index: int,
    seed: int | None = None,
) -> SpinConstraint | None:
    from lineup_sim.core.spin_options import spin_options_for_pick

    options = spin_options_for_pick(preset, pool, lineup=lineup, pick_index=pick_index)
    options = [spin for spin in options if (spin.team_abbr, spin.era_label) not in used]
    if not options:
        return None
    options.sort(key=lambda spin: (spin.team_abbr, spin.era_label))
    if seed is not None:
        rng = random.Random(seed + pick_index * 9973)
        return rng.choice(options)
    return options[0]


def resolve_spin_for_pick(
    *,
    pool: list[PlayerSeason],
    preset: Preset,
    lineup: Lineup,
    sport: str,
    pick_index: int,
    spin: SpinConstraint | None,
    spins: list[SpinConstraint] | None,
    used: set[tuple[str, str]],
    seed: int | None = None,
) -> SpinConstraint | None:
    """Pick a team+era whose pool includes someone for the current open slots."""

    def spin_works(candidate: SpinConstraint | None) -> bool:
        if candidate is None:
            return False
        spin_pool = pool_for_spin(pool, candidate, sport=sport)
        return len(players_fitting_open_slots(spin_pool, lineup, preset, sport)) > 0

    if spin_works(spin):
        return spin

    return choose_spin_for_lineup(
        pool=pool,
        preset=preset,
        lineup=lineup,
        sport=sport,
        used=used,
        pick_index=pick_index,
        seed=seed,
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
    if preset.sport in PICK_SPIN_SPORTS:
        spin_pool = pool_for_spin(pool, spin, sport=preset.sport)
        if len(spin_pool) < min_pool_size:
            return False
        if required_slots:
            if preset.sport == "mlb":
                return _spin_covers_slots(spin_pool, required_slots, preset.sport)
            return (
                _count_players_fitting_slots(spin_pool, required_slots, preset.sport)
                >= min_pool_size
            )
        return True
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


from lineup_sim.core.spin_options import (
    PICK_SPIN_SPORTS,
    TENURE_SPORTS,
    decades_for_preset,
)


def _pick_spin_candidates(
    pool: list[PlayerSeason],
    preset: Preset,
    teams: list[dict[str, str]],
    used: set[tuple[str, str]],
    decades: list[str],
    *,
    min_pool_size: int,
    required_slots: list[RosterSlot] | None = None,
) -> list[tuple[dict[str, str], str, int, int]]:
    candidates: list[tuple[dict[str, str], str, int, int]] = []
    mlb_viable: set[tuple[str, str]] | None = None
    if preset.sport == "mlb":
        from lineup_sim.sports.mlb.plugin import MLBPlugin

        plugin = get_sport_plugin("mlb")
        if isinstance(plugin, MLBPlugin):
            mlb_viable = plugin.viable_spin_keys(preset)

    for team in teams:
        for decade in decades:
            key = (team["abbr"], decade)
            if key in used:
                continue
            start, end = seasons_for_decade(decade)
            if mlb_viable is not None:
                if key in mlb_viable:
                    candidates.append((team, decade, start, end))
                continue
            probe = SpinConstraint(
                round_index=0,
                team_abbr=team["abbr"],
                team_name=team["name"],
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

        if preset.sport in PICK_SPIN_SPORTS:
            decades = decades_for_preset(preset)
            required_slots = anticipated_open_slots(preset, i + 1, None)
            candidates = _pick_spin_candidates(
                pool,
                preset,
                teams,
                used,
                decades,
                min_pool_size=min_pool_size,
                required_slots=required_slots,
            )
            if not candidates:
                hint = ""
                if preset.sport == "mlb" and len(pool) < 500:
                    hint = (
                        " Import the Lahman tenure bundle first: "
                        "`.venv\\Scripts\\python.exe scripts\\import_lahman_bundle.py`"
                    )
                raise ValueError(
                    f"No valid {preset.sport.upper()} team+era spin with enough players "
                    f"to fill all lineup slots (round {i + 1}).{hint}"
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
    # NBA/NFL pick spins expose the full roster — position is chosen at draft time.
    if sport in PICK_SPIN_SPORTS:
        position = None
        side = None
    if sport in {"nba", "mlb"}:
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
    if sport in TENURE_SPORTS:
        return pool
    return pick_peak_seasons(pool, sport)
