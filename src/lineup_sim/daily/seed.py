"""Deterministic daily puzzle generation."""

from __future__ import annotations

import hashlib
from datetime import date

from lineup_sim.core.constraints import generate_spins
from lineup_sim.core.models import DailyPuzzle
from lineup_sim.core.presets import get_preset


def _seed_from_date(sport: str, day: str, preset_slug: str) -> int:
    raw = f"{sport}:{preset_slug}:{day}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16)


def daily_puzzle(
    sport: str,
    preset_slug: str,
    *,
    day: str | None = None,
) -> DailyPuzzle:
    preset = get_preset(preset_slug)
    if preset.sport != sport:
        raise ValueError(f"Preset {preset_slug} is for {preset.sport}, not {sport}")

    day = day or date.today().isoformat()
    seed = _seed_from_date(sport, day, preset_slug)
    spins = generate_spins(preset, seed=seed)

    return DailyPuzzle(
        sport=sport,
        date=day,
        preset_slug=preset_slug,
        seed=seed,
        spins=spins,
    )
