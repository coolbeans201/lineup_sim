"""NFL pick-then-assign spin draft rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.core.constraints import (
    generate_spins,
    players_fitting_open_slots,
    pool_for_spin,
    resolve_spin_for_pick,
    used_spin_keys,
)
from lineup_sim.core.models import SpinConstraint
from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import assign_player, empty_lineup, find_player_in_pool
from lineup_sim.core.spin_options import spin_options_for_pick
from lineup_sim.sports.nfl.plugin import NFLPlugin


def test_nfl_spin_pool_is_not_position_filtered():
    preset = get_preset("nfl_two_way")
    pool = NFLPlugin().load_player_pool()
    options = spin_options_for_pick(preset, pool)
    assert options

    sf_1990s = next(
        spin for spin in options if spin.team_abbr == "SF" and spin.era_label == "1990s"
    )
    spin_pool = pool_for_spin(pool, sf_1990s, sport="nfl")
    positions = {p.position for p in spin_pool}
    assert len(spin_pool) > 1
    assert "QB" in positions
    assert positions != {"QB"}


def test_nfl_spin_pick_resolves_team_season_not_first_player_id_match():
    """Peak pool keeps one row per player/team/decade — same player_id can repeat."""
    pool = NFLPlugin().load_player_pool()
    spin = SpinConstraint(
        round_index=1,
        team_abbr="CLE",
        team_name="Cleveland Browns",
        era_label="2010s",
        season_start=2010,
        season_end=2019,
    )
    spin_pool = pool_for_spin(pool, spin, sport="nfl")
    barnidge = next(p for p in spin_pool if p.player_name == "Gary Barnidge")

    assert barnidge.team_abbr == "CLE"
    assert barnidge.season == 2015

    wrong = find_player_in_pool(pool, player_id=barnidge.player_id)
    assert wrong is not None
    assert wrong.team_abbr == "CAR"
    assert wrong.season == 2009

    resolved = find_player_in_pool(
        pool,
        player_id=barnidge.player_id,
        season=barnidge.season,
        team_abbr=barnidge.team_abbr,
    )
    assert resolved == barnidge


def test_nfl_spin_rerolls_when_seeded_pool_does_not_fit_open_slots():
    preset = get_preset("nfl_offense")
    pool = NFLPlugin().load_player_pool()
    buf_2020s = SpinConstraint(
        round_index=2,
        team_abbr="BUF",
        team_name="Buffalo Bills",
        era_label="2020s",
        season_start=2020,
        season_end=2029,
    )
    lineup = empty_lineup(preset)
    qb = next(p for p in pool if p.position == "QB")
    lineup = assign_player(lineup, preset, "qb", qb)

    spin_pool = pool_for_spin(pool, buf_2020s, sport="nfl")
    assert len(spin_pool) >= 1
    assert not players_fitting_open_slots(spin_pool, lineup, preset, "nfl")

    spins = [buf_2020s] + generate_spins(preset, seed=99)[1:]
    resolved = resolve_spin_for_pick(
        pool=pool,
        preset=preset,
        lineup=lineup,
        sport="nfl",
        pick_index=2,
        spin=spins[1],
        spins=spins,
        used=used_spin_keys(spins, 2),
        seed=99,
    )
    assert resolved is not None
    assert (resolved.team_abbr, resolved.era_label) != ("BUF", "2020s")
    pick_pool = players_fitting_open_slots(
        pool_for_spin(pool, resolved, sport="nfl"),
        lineup,
        preset,
        "nfl",
    )
    assert pick_pool


def test_nfl_spin_options_respect_current_open_slots():
    preset = get_preset("nfl_offense")
    pool = NFLPlugin().load_player_pool()
    lineup = empty_lineup(preset)
    qb = next(p for p in pool if p.position == "QB")
    lineup = assign_player(lineup, preset, "qb", qb)

    options = spin_options_for_pick(preset, pool, lineup=lineup, pick_index=2)
    assert options
    for spin in options:
        spin_pool = pool_for_spin(pool, spin, sport="nfl")
        assert players_fitting_open_slots(spin_pool, lineup, preset, "nfl")


def test_nfl_generate_spins_uses_team_era_not_slot_position():
    preset = get_preset("nfl_offense")
    spins = generate_spins(preset, seed=42)
    assert len(spins) == preset.slot_count
    plugin = NFLPlugin()
    pool = plugin.load_player_pool()
    for spin in spins:
        candidates = pool_for_spin(pool, spin, sport="nfl")
        assert len(candidates) >= 1
        assert len({p.position for p in candidates}) > 1
