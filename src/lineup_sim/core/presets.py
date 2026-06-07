"""Load constraint/scoring presets from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from lineup_sim.core.models import Preset, RosterSlot, decade_sort_key

PRESETS_DIR = Path(__file__).resolve().parents[3] / "data" / "presets"
_PRESET_CACHE: dict[str, Preset] | None = None

POSITION_ORDER = {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}


def _parse_slot(raw: dict) -> RosterSlot:
    return RosterSlot(
        slot_id=raw["slot_id"],
        label=raw["label"],
        position=raw.get("position"),
        weight=float(raw.get("weight", 1.0)),
        decade=raw.get("decade"),
        side=raw.get("side"),
    )


def _sort_slots(slots: list[RosterSlot]) -> list[RosterSlot]:
    if all(s.decade for s in slots):
        return sorted(slots, key=lambda s: decade_sort_key(s.decade))
    if all(s.position for s in slots) and not any(s.decade for s in slots):
        return sorted(slots, key=lambda s: POSITION_ORDER.get(s.position or "", 99))
    return slots


def _parse_preset(raw: dict) -> Preset:
    slots = _sort_slots([_parse_slot(s) for s in raw["slots"]])
    return Preset(
        sport=raw["sport"],
        name=raw["name"],
        slug=raw["slug"],
        description=raw.get("description", ""),
        slots=slots,
        stat_weights={k: float(v) for k, v in raw.get("stat_weights", {}).items()},
        max_games=int(raw.get("max_games", 82)),
        position_weights={k: float(v) for k, v in raw.get("position_weights", {}).items()},
        balance_penalty=float(raw.get("balance_penalty", 0.15)),
        grade_thresholds={k: float(v) for k, v in raw.get("grade_thresholds", {}).items()},
        rating_baseline=float(raw["rating_baseline"]) if raw.get("rating_baseline") is not None else None,
        win_rating_slope=float(raw.get("win_rating_slope", 0.30)),
    )


def load_presets(force: bool = False) -> dict[str, Preset]:
    global _PRESET_CACHE
    if _PRESET_CACHE is not None and not force:
        return _PRESET_CACHE

    presets: dict[str, Preset] = {}
    if PRESETS_DIR.exists():
        for path in sorted(PRESETS_DIR.glob("*.yaml")):
            with path.open(encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            preset = _parse_preset(raw)
            presets[preset.slug] = preset

    _PRESET_CACHE = presets
    return presets


def get_preset(slug: str) -> Preset:
    presets = load_presets()
    if slug not in presets:
        raise KeyError(f"Unknown preset: {slug}")
    return presets[slug]


def list_presets(sport: str | None = None) -> list[Preset]:
    presets = list(load_presets().values())
    if sport:
        presets = [p for p in presets if p.sport == sport]
    return sorted(presets, key=lambda p: p.name)
