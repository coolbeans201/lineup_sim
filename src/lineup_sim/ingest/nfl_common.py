"""Shared NFL team abbreviation normalization."""

from __future__ import annotations

# Pro Football Reference / Fantasy Data Pros codes -> Lineup Sim codes.
TEAM_ABBR_MAP: dict[str, str] = {
    "GNB": "GB",
    "KAN": "KC",
    "NOR": "NO",
    "SFO": "SF",
    "TAM": "TB",
    "NWE": "NE",
    "NYC": "NYG",
    "RAM": "LAR",
    "SDG": "LAC",
    "SD": "LAC",
    "OAK": "LV",
    "STL": "LAR",
    "PHO": "ARI",
    "CRD": "ARI",
    "RAI": "LV",
    "CLT": "IND",
    "OTI": "TEN",
    "HST": "HOU",
    "BAL": "BAL",  # 1996+ Ravens; 1980s Colts used BAL in some tables
    "ARI": "ARI",
    "ATL": "ATL",
    "BUF": "BUF",
    "CAR": "CAR",
    "CHI": "CHI",
    "CIN": "CIN",
    "CLE": "CLE",
    "DAL": "DAL",
    "DEN": "DEN",
    "DET": "DET",
    "GB": "GB",
    "HOU": "HOU",
    "IND": "IND",
    "JAX": "JAX",
    "KC": "KC",
    "LAC": "LAC",
    "LAR": "LAR",
    "LV": "LV",
    "MIA": "MIA",
    "MIN": "MIN",
    "NE": "NE",
    "NO": "NO",
    "NYG": "NYG",
    "NYJ": "NYJ",
    "PHI": "PHI",
    "PIT": "PIT",
    "SEA": "SEA",
    "SF": "SF",
    "TB": "TB",
    "TEN": "TEN",
    "WAS": "WAS",
}

MULTI_TEAM_CODES = frozenset({"2TM", "3TM"})


def normalize_team_abbr(team_raw: str) -> str | None:
    code = str(team_raw or "").strip().upper()
    if not code or code in MULTI_TEAM_CODES:
        return None
    return TEAM_ABBR_MAP.get(code, code)
