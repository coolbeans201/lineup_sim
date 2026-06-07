"""Basketball Reference ingest for historical NBA per-game stats."""

from __future__ import annotations

import re
import time
from pathlib import Path
from io import StringIO
from urllib.parse import urljoin

import pandas as pd
import requests

from lineup_sim.ingest.bref_common import MIN_GAMES, TEAM_ABBR_MAP
from lineup_sim.ingest.cache import read_cache, write_cache
from lineup_sim.sports.nba.positions import primary_position

BREF_BASE = "https://www.basketball-reference.com"
FIXTURES_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "nba"
USER_AGENT = (
    "Mozilla/5.0 (compatible; LineupSim/0.1; +https://github.com/lineup-sim)"
)


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _parse_table(html: str) -> pd.DataFrame:
    tables = pd.read_html(StringIO(html))
    for table in tables:
        cols = [str(c).lower() for c in table.columns]
        if "player" in cols and "pts" in cols:
            return table
    raise ValueError("Per-game stats table not found")


def load_historical_fixtures() -> list[dict]:
    """Bundled BRef-format rows for 1960s-1990s (works offline; live BRef often blocked)."""
    path = FIXTURES_DIR / "historical.json"
    if not path.exists():
        return []
    import json

    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _fixture_rows_for_year(end_year: int) -> list[dict]:
    return [row for row in load_historical_fixtures() if int(row["season"]) == end_year]


def fetch_bref_season(end_year: int, *, delay_s: float = 3.0) -> list[dict]:
    """
    Fetch per-game stats for an NBA season ending in `end_year`.

    BRef URL pattern: /leagues/NBA_{end_year}_per_game.html
    """
    from lineup_sim.ingest.bref_bundle import load_bundled_season

    bundled = load_bundled_season(end_year)
    if bundled is not None:
        return bundled

    cache_key = f"bref_{end_year}"
    cached = read_cache("nba", cache_key)
    if cached is not None:
        return cached

    fixture_rows = _fixture_rows_for_year(end_year)
    if fixture_rows:
        write_cache("nba", cache_key, fixture_rows)
        return fixture_rows

    url = urljoin(BREF_BASE, f"/leagues/NBA_{end_year}_per_game.html")
    session = _session()
    resp = session.get(url, timeout=60)
    if resp.status_code != 200:
        write_cache("nba", cache_key, [])
        return []

    try:
        table = _parse_table(resp.text)
    except ValueError:
        write_cache("nba", cache_key, [])
        return []

    # Flatten multi-index columns if present
    if isinstance(table.columns, pd.MultiIndex):
        table.columns = [c[-1] if isinstance(c, tuple) else c for c in table.columns]

    colmap = {str(c).lower(): c for c in table.columns}
    rows: list[dict] = []

    for _, row in table.iterrows():
        player = str(row.get(colmap.get("player", "Player"), "")).strip()
        if not player or player.lower() == "player":
            continue
        team_raw = str(row.get(colmap.get("tm", "Tm"), "")).strip()
        if not team_raw or team_raw == "TOT":
            continue

        try:
            games = float(row.get(colmap.get("g", "G"), 0) or 0)
        except (TypeError, ValueError):
            games = 0
        if games < MIN_GAMES:
            continue

        pos_raw = str(row.get(colmap.get("pos", "Pos"), "G") or "G")
        team_abbr = TEAM_ABBR_MAP.get(team_raw, team_raw)
        player_id = f"bref_{_slugify(player)}_{end_year}_{team_abbr}"

        def _num(key: str) -> float:
            val = row.get(colmap.get(key, key.upper()), 0)
            try:
                return float(val or 0)
            except (TypeError, ValueError):
                return 0.0

        rows.append(
            {
                "player_id": player_id,
                "player_name": player,
                "team": team_raw,
                "team_abbr": team_abbr,
                "season": end_year,
                "position": primary_position(pos_raw),
                "position_raw": pos_raw,
                "stats": {
                    "PTS": _num("pts"),
                    "REB": _num("trb"),
                    "AST": _num("ast"),
                    "STL": _num("stl"),
                    "BLK": _num("blk"),
                },
            }
        )

    write_cache("nba", cache_key, rows)
    if delay_s:
        time.sleep(delay_s)
    return rows


def fetch_bref_range(start_year: int, end_year: int, *, delay_s: float = 3.0) -> list[dict]:
    all_rows: list[dict] = []
    for year in range(start_year, end_year + 1):
        all_rows.extend(fetch_bref_season(year, delay_s=delay_s))
    return all_rows
