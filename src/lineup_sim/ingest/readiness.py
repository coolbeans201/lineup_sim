"""Local data readiness checks and import hints for the UI."""

from __future__ import annotations

from lineup_sim.ingest.bref_bundle import has_bundled_data as has_nba_bref_bundle
from lineup_sim.ingest.mlb import has_bundled_tenures
from lineup_sim.ingest.nfl_bundle import has_nflverse_bundled_data
from lineup_sim.ingest.pfr_bundle import has_pfr_bundled_data, has_pfr_defense_data


def import_command_hint(sport: str) -> str:
    if sport == "nba":
        return ".venv\\Scripts\\python.exe scripts\\import_bref_bundle.py --download"
    if sport == "nfl":
        return (
            ".venv\\Scripts\\python.exe scripts\\bootstrap_data.py "
            "(or import_pfr_bundle.py + import_nfl_bundle.py)"
        )
    if sport == "mlb":
        return (
            "Place Lahman zip at data/raw/lahman/lahman_1871-2025_csv.zip, then run "
            ".venv\\Scripts\\python.exe scripts\\import_lahman_bundle.py"
        )
    return ".venv\\Scripts\\python.exe scripts\\bootstrap_data.py"


def sport_pool_ready(sport: str, *, pool_size: int) -> tuple[bool, str | None]:
    """Return (ready, user-facing message) for spin/daily modes."""
    if sport == "nba":
        if pool_size < 500:
            return False, (
                "NBA player pool is too small for spin drafts. "
                f"Run: `{import_command_hint('nba')}`"
            )
        return True, None

    if sport == "nfl":
        if pool_size < 200:
            return False, (
                "NFL player pool is too small for spin drafts. "
                f"Run: `{import_command_hint('nfl')}`"
            )
        return True, None

    if sport == "mlb":
        if not has_bundled_tenures() or pool_size < 500:
            return False, (
                "MLB requires the Lahman tenure bundle (~37k rows). "
                "Download the SABR Lahman CSV zip to `data/raw/lahman/`, then run "
                f"`{import_command_hint('mlb')}`"
            )
        return True, None

    return pool_size > 0, None


def sport_data_summary(sport: str) -> dict[str, bool]:
    if sport == "nba":
        return {"bref_bundle": has_nba_bref_bundle()}
    if sport == "nfl":
        return {
            "pfr_offense": has_pfr_bundled_data(),
            "pfr_defense": has_pfr_defense_data(),
            "nflverse": has_nflverse_bundled_data(),
        }
    if sport == "mlb":
        return {"lahman_tenures": has_bundled_tenures()}
    return {}
