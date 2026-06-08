"""Bundled Pro Football Reference seasons (1970-1998) via Fantasy Data Pros CSVs."""

from __future__ import annotations

import json
import re
import time
import urllib.request
from io import StringIO
from pathlib import Path

import pandas as pd

from lineup_sim.core.models import decade_label
from lineup_sim.ingest.nfl_common import normalize_team_abbr
from lineup_sim.ingest.nfl_positions import normalize_nfl_position

BUNDLE_DIR = Path(__file__).resolve().parents[3] / "data" / "bundled" / "nfl" / "pfr_per_season"
PFR_START = 1970
PFR_END = 1998
MIN_GAMES = 6
FDP_YEARLY_URL = (
    "https://raw.githubusercontent.com/fantasydatapros/data/master/yearly/{year}.csv"
)
PFR_DEFENSE_URL = "https://www.pro-football-reference.com/years/{year}/defense.htm"
PFR_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.pro-football-reference.com/",
}


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _num(value) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clean_player_name(name: str) -> str:
    return str(name or "").split("*")[0].split("+")[0].strip()


def _player_id(player_name: str, season: int, team_abbr: str) -> str:
    return f"pfr_{_slugify(player_name)}_{season}_{team_abbr}"


def _offense_stats_from_record(record: dict) -> dict[str, float]:
    pass_yds = _num(record.get("PassingYds"))
    rush_yds = _num(record.get("RushingYds"))
    rec_yds = _num(record.get("ReceivingYds"))
    pass_td = _num(record.get("PassingTD"))
    rush_td = _num(record.get("RushingTD"))
    rec_td = _num(record.get("ReceivingTD"))

    if pass_yds == 0 and "Yds" in record and "Yds.2" in record:
        pass_yds = _num(record.get("Yds"))
        rush_yds = _num(record.get("Yds.1"))
        rec_yds = _num(record.get("Yds.2"))
    if pass_td == 0 and "TD" in record:
        pass_td = _num(record.get("TD"))

    games = _num(record.get("G"))
    return {
        "games": games,
        "pass_yds": pass_yds,
        "rush_yds": rush_yds,
        "rec_yds": rec_yds,
        "pass_td": pass_td,
        "rush_td": rush_td,
        "rec_td": rec_td,
        "yards": pass_yds + rush_yds + rec_yds,
        "td": pass_td + rush_td + rec_td,
        "sacks": 0.0,
        "tackles": 0.0,
        "interceptions": 0.0,
    }


def row_from_offense_record(record: dict, *, season: int, min_games: int = MIN_GAMES) -> dict | None:
    player_name = _clean_player_name(str(record.get("Player", "")))
    if not player_name or player_name.lower() == "player":
        return None

    raw_pos = str(record.get("Pos", "") or "").strip().upper()
    if not raw_pos or raw_pos == "0":
        return None

    pos = normalize_nfl_position(raw_pos)
    if pos is None:
        return None

    games = int(_num(record.get("G")))
    if games < min_games:
        return None

    team_abbr = normalize_team_abbr(str(record.get("Tm", "")))
    if not team_abbr:
        return None

    return {
        "player_id": _player_id(player_name, season, team_abbr),
        "player_name": player_name,
        "team": team_abbr,
        "team_abbr": team_abbr,
        "season": season,
        "position": pos,
        "position_raw": raw_pos,
        "stats": _offense_stats_from_record(record),
        "decade": decade_label(season),
        "source": "pfr_offense",
    }


def row_from_defense_record(record: dict, *, season: int, min_games: int = MIN_GAMES) -> dict | None:
    player_name = _clean_player_name(str(record.get("Player", "")))
    if not player_name or player_name.lower() in {"player", "rk"}:
        return None

    raw_pos = str(record.get("Pos", "") or "").strip().upper()
    pos = normalize_nfl_position(raw_pos)
    if pos is None:
        return None

    games = int(_num(record.get("G")))
    if games < min_games:
        return None

    team_abbr = normalize_team_abbr(str(record.get("Tm", "")))
    if not team_abbr:
        return None

    sacks = _num(record.get("Sk") or record.get("Sacks") or record.get("Sk."))
    tackles = _num(record.get("Comb") or record.get("Tackles") or record.get("TacklesComb"))
    if tackles == 0:
        tackles = _num(record.get("Solo")) + _num(record.get("Ast"))
    interceptions = _num(record.get("Int") or record.get("INT"))

    return {
        "player_id": _player_id(player_name, season, team_abbr),
        "player_name": player_name,
        "team": team_abbr,
        "team_abbr": team_abbr,
        "season": season,
        "position": pos,
        "position_raw": raw_pos,
        "stats": {
            "yards": 0.0,
            "td": _num(record.get("TD")),
            "sacks": sacks,
            "tackles": tackles,
            "interceptions": interceptions,
        },
        "decade": decade_label(season),
        "source": "pfr_defense",
    }


def download_offense_csv(season: int) -> pd.DataFrame:
    url = FDP_YEARLY_URL.format(year=season)
    req = urllib.request.Request(url, headers={"User-Agent": "LineupSim/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return pd.read_csv(StringIO(resp.read().decode("utf-8")))


def scrape_defense_season(season: int, *, delay_s: float = 4.0) -> list[dict]:
    """Scrape PFR defense table; returns [] if blocked or unavailable."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    url = PFR_DEFENSE_URL.format(year=season)
    try:
        response = requests.get(url, headers=PFR_REQUEST_HEADERS, timeout=60)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", {"id": "defense"})
        if table is None:
            return []
        df = pd.read_html(StringIO(str(table)))[0]
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[-1]) if isinstance(c, tuple) else str(c) for c in df.columns]
        rows: list[dict] = []
        for record in df.to_dict(orient="records"):
            row = row_from_defense_record(record, season=season)
            if row is not None:
                rows.append(row)
        return rows
    except Exception:
        return []
    finally:
        if delay_s > 0:
            time.sleep(delay_s)


def offense_rows_for_season(season: int, *, min_games: int = MIN_GAMES) -> list[dict]:
    df = download_offense_csv(season)
    rows: list[dict] = []
    for record in df.to_dict(orient="records"):
        row = row_from_offense_record(record, season=season, min_games=min_games)
        if row is not None:
            rows.append(row)
    return rows


def bundled_season_path(season: int) -> Path:
    return BUNDLE_DIR / f"{season}.json"


def save_bundled_season(season: int, rows: list[dict]) -> Path:
    path = bundled_season_path(season)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    return path


def load_bundled_season(season: int) -> list[dict] | None:
    path = bundled_season_path(season)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


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


def has_pfr_bundled_data() -> bool:
    return bool(bundled_years())


def load_all_pfr_bundled(
    *,
    start_year: int = PFR_START,
    end_year: int = PFR_END,
) -> list[dict]:
    rows: list[dict] = []
    for season in range(start_year, end_year + 1):
        season_rows = load_bundled_season(season)
        if season_rows:
            rows.extend(season_rows)
    return rows


def import_seasons_to_bundle(
    *,
    start_year: int = PFR_START,
    end_year: int = PFR_END,
    min_games: int = MIN_GAMES,
    include_defense: bool = False,
    defense_delay_s: float = 4.0,
) -> dict[int, int]:
    counts: dict[int, int] = {}
    for season in range(start_year, end_year + 1):
        rows = offense_rows_for_season(season, min_games=min_games)
        if include_defense:
            defense_rows = scrape_defense_season(season, delay_s=defense_delay_s)
            seen = {(r["player_id"], r["season"], r["team_abbr"]) for r in rows}
            for row in defense_rows:
                key = (row["player_id"], row["season"], row["team_abbr"])
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
        save_bundled_season(season, rows)
        counts[season] = len(rows)
    return counts
