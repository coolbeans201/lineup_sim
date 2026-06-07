"""Bundled Basketball Reference per-game seasons (offline-first NBA pool)."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import pandas as pd

from lineup_sim.core.models import decade_label
from lineup_sim.ingest.bref_common import MIN_GAMES, TEAM_ABBR_MAP
from lineup_sim.ingest.nba_position_eligibility import (
    apply_career_position,
    build_career_position_map,
    load_career_position_overrides,
    merge_career_position_maps,
)
from lineup_sim.sports.nba.positions import primary_position

BUNDLE_DIR = Path(__file__).resolve().parents[3] / "data" / "bundled" / "nba" / "bref_per_game"
RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
DEFAULT_CSV_URL = (
    "https://raw.githubusercontent.com/sumitrodatta/bball-reference-datasets/"
    "master/Data/Player%20Per%20Game.csv"
)
DEFAULT_CSV_NAME = "Player Per Game.csv"

BUNDLE_START = 1962
BUNDLE_END = 2026


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _num(value) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_team_abbr(team_raw: str) -> str:
    code = str(team_raw or "").strip().upper()
    return TEAM_ABBR_MAP.get(code, code)


def row_from_csv_record(record: dict, *, min_games: int = MIN_GAMES) -> dict | None:
    """Convert a sumitrodatta Player Per Game.csv row to our ingest dict."""
    if str(record.get("lg", "NBA")).upper() != "NBA":
        return None

    games = _num(record.get("g"))
    if games < min_games:
        return None

    season = int(record["season"])
    team_raw = str(record.get("team", "")).strip()
    if not team_raw or team_raw.upper() == "TOT":
        return None

    player_name = str(record.get("player", "")).strip()
    if not player_name:
        return None

    bref_id = str(record.get("player_id") or _slugify(player_name))
    team_abbr = normalize_team_abbr(team_raw)
    pos_value = record.get("pos")
    if pos_value is None or (isinstance(pos_value, float) and pd.isna(pos_value)):
        pos_raw = "G"
    else:
        pos_raw = str(pos_value).strip().upper() or "G"

    return {
        "player_id": f"bref_{bref_id}_{season}_{team_abbr}",
        "player_name": player_name,
        "team": team_raw,
        "team_abbr": team_abbr,
        "season": season,
        "position": primary_position(pos_raw),
        "position_raw": pos_raw,
        "stats": {
            "PTS": _num(record.get("pts_per_game")),
            "REB": _num(record.get("trb_per_game")),
            "AST": _num(record.get("ast_per_game")),
            "STL": _num(record.get("stl_per_game")),
            "BLK": _num(record.get("blk_per_game")),
        },
        "decade": decade_label(season),
    }


def rows_from_dataframe(df: pd.DataFrame, *, min_games: int = MIN_GAMES) -> list[dict]:
    rows: list[dict] = []
    for record in df.to_dict(orient="records"):
        row = row_from_csv_record(record, min_games=min_games)
        if row is not None:
            rows.append(row)
    return rows


def bundled_season_path(season: int) -> Path:
    return BUNDLE_DIR / f"{season}.json"


def load_bundled_season(season: int) -> list[dict] | None:
    path = bundled_season_path(season)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_bundled_season(season: int, rows: list[dict]) -> Path:
    path = bundled_season_path(season)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    return path


def bundled_years() -> list[int]:
    if not BUNDLE_DIR.exists():
        return []
    years: list[int] = []
    for path in BUNDLE_DIR.glob("*.json"):
        try:
            years.append(int(path.stem))
        except ValueError:
            continue
    return sorted(years)


def has_bundled_data() -> bool:
    return bool(bundled_years())


def download_default_csv(*, dest: Path | None = None, url: str = DEFAULT_CSV_URL) -> Path:
    target = dest or (RAW_DIR / DEFAULT_CSV_NAME)
    target.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "LineupSim/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        target.write_bytes(resp.read())
    return target


def import_csv_to_bundle(
    csv_path: Path,
    *,
    start_year: int = BUNDLE_START,
    end_year: int = BUNDLE_END,
    min_games: int = MIN_GAMES,
) -> dict[int, int]:
    """Write one JSON file per season. Returns {season: row_count}."""
    df = pd.read_csv(csv_path)
    if "lg" in df.columns:
        df = df[df["lg"].astype(str).str.upper() == "NBA"]
    if "season" not in df.columns and "Season" in df.columns:
        df = df.rename(columns={"Season": "season"})

    source_records = df.to_dict(orient="records")
    career_map = merge_career_position_maps(
        build_career_position_map(source_records),
        load_career_position_overrides(),
    )

    counts: dict[int, int] = {}
    for season in range(start_year, end_year + 1):
        season_df = df[df["season"] == season]
        if season_df.empty:
            continue
        rows = rows_from_dataframe(season_df, min_games=min_games)
        rows = [apply_career_position(row, career_map) for row in rows]
        save_bundled_season(season, rows)
        counts[season] = len(rows)
    return counts


def load_all_bundled(
    *,
    start_year: int = BUNDLE_START,
    end_year: int = BUNDLE_END,
) -> list[dict]:
    rows: list[dict] = []
    for season in range(start_year, end_year + 1):
        season_rows = load_bundled_season(season)
        if season_rows:
            rows.extend(season_rows)
    return rows
