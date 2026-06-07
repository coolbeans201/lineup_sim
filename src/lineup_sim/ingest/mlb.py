"""MLB ingest via pybaseball with bundled fallback."""

from __future__ import annotations

import json
from pathlib import Path

from lineup_sim.core.models import PlayerSeason, decade_label
from lineup_sim.ingest.cache import read_cache, write_cache

SAMPLE_PATH = Path(__file__).resolve().parents[3] / "data" / "sample" / "mlb_players.json"


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


def fetch_season_stats(year: int) -> list[dict]:
    cached = read_cache("mlb", f"season_{year}")
    if cached is not None:
        return cached

    rows: list[dict] = []
    try:
        from pybaseball import batting_stats, pitching_stats

        bat = batting_stats(year, qual=1)
        for _, row in bat.iterrows():
            rows.append(
                {
                    "player_id": str(row.get("IDfg", row.get("Name", ""))),
                    "player_name": row["Name"],
                    "team": "-".join(str(row.get("Team", "")).split("-")),
                    "team_abbr": str(row.get("Team", "")).split("-")[0],
                    "season": year,
                    "position": "H",
                    "stats": {
                        "AVG": float(row.get("AVG", 0) or 0),
                        "HR": float(row.get("HR", 0) or 0),
                        "RBI": float(row.get("RBI", 0) or 0),
                        "SB": float(row.get("SB", 0) or 0),
                        "OPS": float(row.get("OPS", 0) or 0),
                    },
                }
            )
        pitch = pitching_stats(year, qual=1)
        for _, row in pitch.iterrows():
            rows.append(
                {
                    "player_id": f"p_{row.get('IDfg', row.get('Name', ''))}",
                    "player_name": row["Name"],
                    "team": "-".join(str(row.get("Team", "")).split("-")),
                    "team_abbr": str(row.get("Team", "")).split("-")[0],
                    "season": year,
                    "position": "P",
                    "stats": {
                        "ERA": float(row.get("ERA", 5.0) or 5.0),
                        "WHIP": float(row.get("WHIP", 1.3) or 1.3),
                        "K": float(row.get("SO", 0) or 0),
                        "W": float(row.get("W", 0) or 0),
                    },
                }
            )
        write_cache("mlb", f"season_{year}", rows)
    except Exception:
        pass
    return rows


def build_pool(years: list[int] | None = None) -> list[PlayerSeason]:
    years = years or list(range(2018, 2025))
    pool = load_sample_pool()
    seen = {(p.player_id, p.season, p.team_abbr) for p in pool}

    for year in years:
        for raw in fetch_season_stats(year):
            key = (raw["player_id"], raw["season"], raw["team_abbr"])
            if key in seen:
                continue
            seen.add(key)
            pool.append(_row_from_dict(raw))

    return pool
