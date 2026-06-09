"""MLB player pool — bundled Lahman franchise-decade tenures."""

from __future__ import annotations

import json
from pathlib import Path

from lineup_sim.core.models import PlayerSeason
from lineup_sim.ingest.lahman_common import BUNDLE_DIR

SAMPLE_PATH = Path(__file__).resolve().parents[3] / "data" / "sample" / "mlb_players.json"
TENURES_PATH = BUNDLE_DIR / "tenures.json"


def _row_from_tenure(raw: dict) -> PlayerSeason:
    return PlayerSeason(
        player_id=str(raw["player_id"]),
        player_name=raw["player_name"],
        team=raw["team"],
        team_abbr=raw["team_abbr"],
        season=int(raw["season"]),
        position=raw["position"],
        position_raw=raw.get("position_raw") or raw["position"],
        decade=raw["decade"],
        role=raw.get("role", ""),
        stats={k: float(v) for k, v in raw["stats"].items()},
    )


def _row_from_sample(raw: dict) -> PlayerSeason:
    role = raw.get("role") or (
        "pitch" if raw.get("position", "").upper() in {"P", "SP", "RP"} else "bat"
    )
    position = raw["position"]
    position_raw = raw.get("position_raw") or position
    if position.upper() == "H":
        position_raw = "RF/DH"
        position = "RF"
    return PlayerSeason(
        player_id=str(raw["player_id"]),
        player_name=raw["player_name"],
        team=raw["team"],
        team_abbr=raw["team_abbr"],
        season=int(raw["season"]),
        position=position,
        position_raw=position_raw,
        decade=raw.get("decade") or "",
        role=role,
        stats={k: float(v) for k, v in raw["stats"].items()},
    )


def load_sample_pool() -> list[PlayerSeason]:
    if not SAMPLE_PATH.exists():
        return []
    with SAMPLE_PATH.open(encoding="utf-8") as f:
        rows = json.load(f)
    return [_row_from_sample(r) for r in rows]


def has_bundled_tenures() -> bool:
    return TENURES_PATH.exists()


def load_bundled_pool() -> list[PlayerSeason]:
    with TENURES_PATH.open(encoding="utf-8") as f:
        rows = json.load(f)
    return [_row_from_tenure(r) for r in rows]


def build_pool() -> list[PlayerSeason]:
    if has_bundled_tenures():
        return load_bundled_pool()
    return load_sample_pool()
