"""Shared Lahman CSV paths, league filters, and franchise display maps."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW_LAHMAN_DIR = ROOT / "data" / "raw" / "lahman"
BUNDLE_DIR = ROOT / "data" / "bundled" / "mlb" / "lahman"

# Major-league codes in Lahman (excludes Negro Leagues and independent loops).
MLB_LEAGUES = frozenset({"NL", "AL", "AA", "FL", "PL", "UA", "NAC"})

CLASSIC_DECADES = (
    "1950s",
    "1960s",
    "1970s",
    "1980s",
    "1990s",
    "2000s",
    "2010s",
    "2020s",
)
MODERN_DECADES = ("1980s", "1990s", "2000s", "2010s", "2020s")

# Lahman franchID -> sidebar/spin abbreviation (matches MLB plugin teams).
FRANCHISE_TO_ABBR: dict[str, str] = {
    "ANA": "LAA",
    "ARI": "ARI",
    "ATL": "ATL",
    "BAL": "BAL",
    "BOS": "BOS",
    "CHC": "CHC",
    "CHW": "CWS",
    "CIN": "CIN",
    "CLE": "CLE",
    "COL": "COL",
    "DET": "DET",
    "FLA": "MIA",
    "HOU": "HOU",
    "KCR": "KC",
    "LAD": "LAD",
    "MIL": "MIL",
    "MIN": "MIN",
    "NYM": "NYM",
    "NYY": "NYY",
    "OAK": "OAK",
    "PHI": "PHI",
    "PIT": "PIT",
    "SDP": "SD",
    "SEA": "SEA",
    "SFG": "SF",
    "STL": "STL",
    "TBD": "TB",
    "TEX": "TEX",
    "TOR": "TOR",
    "WSN": "WSH",
}

ACTIVE_FRANCHISES = frozenset(FRANCHISE_TO_ABBR)

DEFAULT_MIN_PA = 100
DEFAULT_MIN_IP = 20.0
POSITION_GAME_THRESHOLD = 10

BAT_COUNTING_COLS = (
    "G",
    "AB",
    "R",
    "H",
    "2B",
    "3B",
    "HR",
    "RBI",
    "SB",
    "CS",
    "BB",
    "SO",
    "IBB",
    "HBP",
    "SH",
    "SF",
    "GIDP",
)

PITCH_COUNTING_COLS = (
    "W",
    "L",
    "G",
    "GS",
    "CG",
    "SHO",
    "SV",
    "IPouts",
    "H",
    "ER",
    "HR",
    "BB",
    "SO",
    "IBB",
    "WP",
    "HBP",
    "BK",
    "BFP",
    "GF",
    "R",
    "SH",
    "SF",
    "GIDP",
)

APPEARANCE_POSITION_COLS = {
    "C": "G_c",
    "1B": "G_1b",
    "2B": "G_2b",
    "3B": "G_3b",
    "SS": "G_ss",
    "LF": "G_lf",
    "CF": "G_cf",
    "RF": "G_rf",
    "DH": "G_dh",
}


def lahman_csv_dir() -> Path:
    """Return extracted Lahman CSV folder (auto-extract zip when needed)."""
    extracted = RAW_LAHMAN_DIR / "extracted"
    if extracted.exists():
        for child in extracted.iterdir():
            if child.is_dir() and (child / "Batting.csv").exists():
                return child
    zip_path = RAW_LAHMAN_DIR / "lahman_1871-2025_csv.zip"
    if not zip_path.exists():
        raise FileNotFoundError(
            f"Lahman CSV zip not found at {zip_path}. "
            "Download from https://sabr.org/lahman-database/ and place it there."
        )
    import zipfile

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extracted)
    for child in extracted.iterdir():
        if child.is_dir() and (child / "Batting.csv").exists():
            return child
    raise FileNotFoundError(f"Could not locate Batting.csv under {extracted}")


def decade_for_year(year: int) -> str:
    if year < 1960:
        return "1950s"
    if year < 1970:
        return "1960s"
    if year < 1980:
        return "1970s"
    if year < 1990:
        return "1980s"
    if year < 2000:
        return "1990s"
    if year < 2010:
        return "2000s"
    if year < 2020:
        return "2010s"
    return "2020s"
