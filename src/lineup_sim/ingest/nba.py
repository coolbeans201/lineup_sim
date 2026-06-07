"""NBA ingest: bundled Basketball Reference (1962+) + optional stats.nba.com refresh."""

from __future__ import annotations

import json
from pathlib import Path

from lineup_sim.core.models import PlayerSeason, decade_label
from lineup_sim.core.names import normalize_player_name
from lineup_sim.ingest.bref_bundle import (
    BUNDLE_END,
    BUNDLE_START,
    has_bundled_data,
    load_all_bundled,
)
from lineup_sim.ingest.cache import read_cache, write_cache
from lineup_sim.ingest.dedupe import dedupe_player_seasons
from lineup_sim.ingest.nba_position_eligibility import (
    apply_career_position,
    build_career_position_map,
    load_career_position_overrides,
    merge_career_position_maps,
)
from lineup_sim.ingest.nba_bref import fetch_bref_range, fetch_bref_season, load_historical_fixtures
from lineup_sim.sports.nba.positions import primary_position

SAMPLE_PATH = Path(__file__).resolve().parents[3] / "data" / "sample" / "nba_players.json"

# BRef per-game table exists from 1962 onward; steal/block from 1974
BREF_START = 1962
BREF_END = 1995
NBA_API_START = 1996
NBA_API_END = 2024


def _row_from_dict(raw: dict) -> PlayerSeason:
    pos_raw = raw.get("position_raw") or raw.get("position", "G")
    pos = raw.get("position") or primary_position(pos_raw)
    return PlayerSeason(
        player_id=str(raw["player_id"]),
        player_name=raw["player_name"],
        team=raw["team"],
        team_abbr=raw["team_abbr"],
        season=int(raw["season"]),
        position=pos,
        position_raw=str(pos_raw),
        stats={k: float(v) for k, v in raw["stats"].items()},
        decade=raw.get("decade") or decade_label(int(raw["season"])),
    )


def load_sample_pool() -> list[PlayerSeason]:
    with SAMPLE_PATH.open(encoding="utf-8") as f:
        rows = json.load(f)
    return [_row_from_dict(r) for r in rows]


def _season_label(year: int) -> str:
    return f"{year - 1}-{str(year)[-2:]}"


def fetch_roster_positions(season_label: str) -> dict[tuple[str, str], str]:
    """Map (player_id, team_abbr) -> BRef-style position from NBA.com rosters."""
    cached = read_cache("nba", f"roster_pos_{season_label.replace('-', '_')}")
    if cached is not None:
        return {tuple(k.split("|", 1)): v for k, v in cached.items()}

    try:
        from nba_api.stats.endpoints import commonteamroster
        from nba_api.stats.static import teams as nba_teams

        mapping: dict[tuple[str, str], str] = {}
        for team in nba_teams.get_teams():
            roster = commonteamroster.CommonTeamRoster(
                team_id=team["id"],
                season=season_label,
            ).common_team_roster.get_data_frame()
            for _, row in roster.iterrows():
                pos = str(row.get("POSITION", "") or "").strip().upper()
                if not pos:
                    continue
                mapping[(str(int(row["PLAYER_ID"])), team["abbreviation"].upper())] = pos

        write_cache(
            "nba",
            f"roster_pos_{season_label.replace('-', '_')}",
            {f"{pid}|{team}": pos for (pid, team), pos in mapping.items()},
        )
        return mapping
    except Exception:
        return {}


def fetch_season_stats(season: str) -> list[dict]:
    cached = read_cache("nba", f"api_{season}")
    if cached is not None:
        return cached

    try:
        from nba_api.stats.endpoints import leaguedashplayerstats
        from nba_api.stats.static import teams as nba_teams

        team_map = {t["id"]: t for t in nba_teams.get_teams()}
        resp = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="PerGame",
        )
        df = resp.get_data_frames()[0]
        roster_pos = fetch_roster_positions(season)
        rows: list[dict] = []
        for _, row in df.iterrows():
            if float(row.get("GP", 0) or 0) < 20:
                continue
            team = team_map.get(int(row["TEAM_ID"]), {})
            team_abbr = str(row.get("TEAM_ABBREVIATION", "") or team.get("abbreviation", "")).upper()
            player_id = str(int(row["PLAYER_ID"]))
            pos_raw = roster_pos.get((player_id, team_abbr), "G")
            rows.append(
                {
                    "player_id": player_id,
                    "player_name": row["PLAYER_NAME"],
                    "team": team.get("full_name", team_abbr),
                    "team_abbr": team_abbr,
                    "season": int(season.split("-")[0]) + 1,
                    "position": primary_position(pos_raw),
                    "position_raw": pos_raw,
                    "stats": {
                        "PTS": float(row.get("PTS", 0) or 0),
                        "REB": float(row.get("REB", 0) or 0),
                        "AST": float(row.get("AST", 0) or 0),
                        "STL": float(row.get("STL", 0) or 0),
                        "BLK": float(row.get("BLK", 0) or 0),
                    },
                }
            )
        write_cache("nba", f"api_{season}", rows)
        return rows
    except Exception:
        return []


def season_labels(start_year: int, end_year: int) -> list[str]:
    return [_season_label(y) for y in range(start_year, end_year)]


def _merge_rows(pool: list[PlayerSeason], seen: set[tuple], rows: list[dict]) -> None:
    for raw in rows:
        dedupe_key = (
            normalize_player_name(raw["player_name"]),
            int(raw["season"]),
            str(raw["team_abbr"]).upper(),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        pool.append(_row_from_dict(raw))


def _build_pool_legacy(
    *,
    use_bref: bool,
    use_api: bool,
    bref_delay_s: float,
) -> list[PlayerSeason]:
    pool = load_sample_pool()
    seen = {
        (normalize_player_name(p.player_name), p.season, p.team_abbr.upper())
        for p in pool
    }

    _merge_rows(pool, seen, load_historical_fixtures())

    if use_bref:
        for year in range(BREF_START, BREF_END + 1):
            rows = fetch_bref_season(year, delay_s=bref_delay_s)
            _merge_rows(pool, seen, rows)

    if use_api:
        for season in season_labels(NBA_API_START, NBA_API_END):
            rows = fetch_season_stats(season)
            _merge_rows(pool, seen, rows)

    cached = read_cache("nba", "player_pool")
    if cached:
        _merge_rows(pool, seen, cached)

    return pool


def _enrich_rows_with_career_positions(rows: list[dict]) -> list[dict]:
    career_map = merge_career_position_maps(
        build_career_position_map(rows),
        load_career_position_overrides(),
    )
    return [apply_career_position(row, career_map) for row in rows]


def build_pool(
    *,
    use_bref: bool = True,
    use_api: bool = False,
    bref_delay_s: float = 0.0,
) -> list[PlayerSeason]:
    if use_bref and has_bundled_data():
        rows = load_all_bundled(start_year=BUNDLE_START, end_year=BUNDLE_END)
        rows = _enrich_rows_with_career_positions(rows)
        pool = [_row_from_dict(raw) for raw in rows]
        if use_api:
            seen = {
                (normalize_player_name(p.player_name), p.season, p.team_abbr.upper())
                for p in pool
            }
            for season in season_labels(NBA_API_START, NBA_API_END):
                _merge_rows(pool, seen, fetch_season_stats(season))
        return dedupe_player_seasons(pool, "nba")

    pool = _build_pool_legacy(
        use_bref=use_bref,
        use_api=use_api,
        bref_delay_s=bref_delay_s,
    )
    return dedupe_player_seasons(pool, "nba")


def ingest_bref_history(
    start_year: int = BREF_START,
    end_year: int = BREF_END,
    *,
    delay_s: float = 3.0,
) -> int:
    """Download and cache BRef seasons. Returns row count."""
    rows = fetch_bref_range(start_year, end_year, delay_s=delay_s)
    return len(rows)


def persist_pool(players: list[PlayerSeason]) -> None:
    payload = [
        {
            "player_id": p.player_id,
            "player_name": p.player_name,
            "team": p.team,
            "team_abbr": p.team_abbr,
            "season": p.season,
            "position": p.position,
            "position_raw": p.position_raw,
            "stats": p.stats,
            "decade": p.decade,
        }
        for p in players
    ]
    write_cache("nba", "player_pool", payload)
