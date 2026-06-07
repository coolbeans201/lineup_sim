"""NFL ingest via nflreadpy with bundled fallback."""

from __future__ import annotations

import json
from pathlib import Path

from lineup_sim.core.models import PlayerSeason, decade_label
from lineup_sim.ingest.cache import read_cache, write_cache

SAMPLE_PATH = Path(__file__).resolve().parents[3] / "data" / "sample" / "nfl_players.json"


def _row_from_dict(raw: dict) -> PlayerSeason:
    return PlayerSeason(
        player_id=str(raw["player_id"]),
        player_name=raw["player_name"],
        team=raw["team"],
        team_abbr=raw["team_abbr"],
        season=int(raw["season"]),
        position=raw["position"],
        stats={k: float(v) for k, v in raw["stats"].items()},
        decade=raw.get("decade") or decade_label(int(raw["season"])),
    )


def load_sample_pool() -> list[PlayerSeason]:
    with SAMPLE_PATH.open(encoding="utf-8") as f:
        rows = json.load(f)
    return [_row_from_dict(r) for r in rows]


def fetch_season_stats(season: int) -> list[dict]:
    cached = read_cache("nfl", f"season_{season}")
    if cached is not None:
        return cached

    try:
        import nflreadpy as nfl

        df = nfl.load_player_stats([season], summary_level="reg")
        if hasattr(df, "to_pandas"):
            df = df.to_pandas()
        rows: list[dict] = []
        for _, row in df.iterrows():
            pos = str(row.get("position", "WR") or "WR")
            stats: dict[str, float] = {
                "yards": float(row.get("passing_yards", 0) or 0)
                + float(row.get("rushing_yards", 0) or 0)
                + float(row.get("receiving_yards", 0) or 0),
                "td": float(row.get("passing_tds", 0) or 0)
                + float(row.get("rushing_tds", 0) or 0)
                + float(row.get("receiving_tds", 0) or 0),
                "sacks": float(row.get("sacks", 0) or 0),
                "tackles": float(row.get("tackles", 0) or 0)
                + float(row.get("tackles_solo", 0) or 0),
                "interceptions": float(row.get("interceptions", 0) or 0),
            }
            rows.append(
                {
                    "player_id": str(row.get("player_id", row.get("gsis_id", ""))),
                    "player_name": row.get("player_display_name", row.get("player_name", "")),
                    "team": row.get("team", ""),
                    "team_abbr": row.get("team", ""),
                    "season": int(season),
                    "position": pos,
                    "stats": stats,
                }
            )
        write_cache("nfl", f"season_{season}", rows)
        return rows
    except Exception:
        return []


def build_pool(seasons: list[int] | None = None) -> list[PlayerSeason]:
    seasons = seasons or list(range(2018, 2025))
    pool = load_sample_pool()
    seen = {(p.player_id, p.season, p.team_abbr) for p in pool}

    for season in seasons:
        for raw in fetch_season_stats(season):
            key = (raw["player_id"], raw["season"], raw["team_abbr"])
            if key in seen:
                continue
            seen.add(key)
            pool.append(_row_from_dict(raw))

    return pool
