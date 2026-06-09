"""NFL ingest: PFR bundle (1970-1998) + nflverse bundle (1999+) with live fallback."""

from __future__ import annotations

import json
from pathlib import Path

from lineup_sim.core.models import PlayerSeason, decade_label
from lineup_sim.ingest.cache import read_cache, write_cache
from lineup_sim.ingest.nfl_bundle import (
    MIN_GAMES,
    NFLVERSE_END,
    NFLVERSE_START,
    has_nflverse_bundled_data,
    load_bundled_rows,
)
from lineup_sim.ingest.nfl_positions import normalize_nfl_position
from lineup_sim.ingest.pfr_bundle import (
    PFR_END,
    PFR_START,
    has_pfr_bundled_data,
    load_all_pfr_bundled,
)

SAMPLE_PATH = Path(__file__).resolve().parents[3] / "data" / "sample" / "nfl_players.json"


def _num(value) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _row_from_dict(raw: dict) -> PlayerSeason | None:
    pos = normalize_nfl_position(
        str(raw.get("position", "")),
        str(raw.get("position_group", "")),
    )
    if pos is None:
        pos = normalize_nfl_position(str(raw.get("position", "")))
    if pos is None:
        return None

    return PlayerSeason(
        player_id=str(raw["player_id"]),
        player_name=raw["player_name"],
        team=raw.get("team") or raw.get("team_name", ""),
        team_abbr=str(raw.get("team_abbr", "")).upper(),
        season=int(raw["season"]),
        position=pos,
        position_raw=str(raw.get("position_raw") or raw.get("position", pos)),
        stats={k: float(v) for k, v in raw["stats"].items()},
        decade=raw.get("decade") or decade_label(int(raw["season"])),
    )


def _stats_from_nflverse_row(row) -> dict[str, float]:
    pass_yds = _num(row.get("passing_yards"))
    rush_yds = _num(row.get("rushing_yards"))
    rec_yds = _num(row.get("receiving_yards"))
    pass_td = _num(row.get("passing_tds"))
    rush_td = _num(row.get("rushing_tds"))
    rec_td = _num(row.get("receiving_tds"))
    yards = pass_yds + rush_yds + rec_yds
    td = pass_td + rush_td + rec_td
    tackles = (
        _num(row.get("def_tackles_solo"))
        + _num(row.get("def_tackle_assists"))
        + _num(row.get("tackles"))
        + _num(row.get("tackles_solo"))
    )
    return {
        "games": _num(row.get("games")),
        "pass_yds": pass_yds,
        "rush_yds": rush_yds,
        "rec_yds": rec_yds,
        "pass_td": pass_td,
        "rush_td": rush_td,
        "rec_td": rec_td,
        "yards": yards,
        "td": td,
        "sacks": _num(row.get("def_sacks") or row.get("sacks")),
        "tackles": tackles,
        "interceptions": _num(row.get("def_interceptions") or row.get("interceptions")),
    }


def _dict_from_nflverse_row(row, *, season: int) -> dict | None:
    raw_pos = str(row.get("position", "") or "")
    group = str(row.get("position_group", "") or "")
    pos = normalize_nfl_position(raw_pos, group)
    if pos is None:
        return None

    games = int(_num(row.get("games")))
    if games < MIN_GAMES:
        return None

    team_abbr = str(row.get("recent_team") or row.get("team") or "").upper()
    if not team_abbr:
        return None

    player_id = str(row.get("player_id") or row.get("gsis_id") or "")
    if not player_id:
        return None

    return {
        "player_id": player_id,
        "player_name": row.get("player_display_name") or row.get("player_name", ""),
        "team": team_abbr,
        "team_abbr": team_abbr,
        "season": season,
        "position": pos,
        "position_raw": raw_pos,
        "position_group": group,
        "stats": _stats_from_nflverse_row(row),
    }


def load_sample_pool() -> list[PlayerSeason]:
    if not SAMPLE_PATH.exists():
        return []
    with SAMPLE_PATH.open(encoding="utf-8") as f:
        rows = json.load(f)
    pool: list[PlayerSeason] = []
    for raw in rows:
        player = _row_from_dict(raw)
        if player is not None:
            pool.append(player)
    return pool


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
            record = _dict_from_nflverse_row(row, season=season)
            if record is not None:
                rows.append(record)
        write_cache("nfl", f"season_{season}", rows)
        return rows
    except Exception:
        return []


def _append_rows(pool: list[PlayerSeason], seen: set[tuple], rows: list[dict]) -> None:
    for raw in rows:
        key = (raw["player_id"], raw["season"], str(raw["team_abbr"]).upper())
        if key in seen:
            continue
        player = _row_from_dict(raw)
        if player is None:
            continue
        seen.add(key)
        pool.append(player)


def build_pool(seasons: list[int] | None = None) -> list[PlayerSeason]:
    pool = load_sample_pool()
    seen = {(p.player_id, p.season, p.team_abbr) for p in pool}

    if has_pfr_bundled_data():
        _append_rows(pool, seen, load_all_pfr_bundled(start_year=PFR_START, end_year=PFR_END))

    if has_nflverse_bundled_data():
        _append_rows(pool, seen, load_bundled_rows())
        return pool

    seasons = seasons or list(range(NFLVERSE_START, NFLVERSE_END + 1))
    for season in seasons:
        for raw in fetch_season_stats(season):
            _append_rows(pool, seen, [raw])

    return pool
