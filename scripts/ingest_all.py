"""Fetch and cache player pools from stat APIs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.bref_bundle import BUNDLE_END, BUNDLE_START, has_bundled_data
from lineup_sim.ingest.mlb import build_pool as build_mlb, has_bundled_tenures
from lineup_sim.ingest.nba import BREF_END, BREF_START, build_pool, ingest_bref_history, persist_pool
from lineup_sim.ingest.nfl import build_pool as build_nfl
from lineup_sim.ingest.nfl_bundle import has_nflverse_bundled_data
from lineup_sim.ingest.pfr_bundle import has_pfr_bundled_data, has_pfr_defense_data
from lineup_sim.sports.nba.plugin import NBAPlugin


def _run(script: str, *args: str) -> None:
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / script), *args])


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest player pools from stat APIs")
    parser.add_argument(
        "--bref-delay",
        type=float,
        default=3.0,
        help="Seconds between Basketball Reference requests (default 3)",
    )
    parser.add_argument(
        "--skip-bref",
        action="store_true",
        help="Skip BRef download (use bundled/fixtures/cache only)",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip stats.nba.com download (use fixtures/cache only)",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Only refresh stats.nba.com seasons (1996-2024)",
    )
    parser.add_argument(
        "--import-bundle",
        action="store_true",
        help="Download/import bundled pools before building player pools",
    )
    parser.add_argument(
        "--with-defense",
        action="store_true",
        help="Include PFR defensive players (1970-1998) when importing PFR bundle",
    )
    args = parser.parse_args()

    if args.import_bundle or not has_bundled_data():
        print("Building bundled BRef per-game seasons...")
        _run(
            "import_bref_bundle.py",
            "--download",
            "--start",
            str(BUNDLE_START),
            "--end",
            str(BUNDLE_END),
        )

    if not args.skip_bref and not args.api_only and not has_bundled_data():
        print(f"Loading Basketball Reference fixtures + optional live fetch {BREF_START}-{BREF_END}...")
        count = ingest_bref_history(BREF_START, BREF_END, delay_s=args.bref_delay)
        print(f"BRef rows processed: {count}")

    print("Building NBA pool...")
    pool = build_pool(
        use_bref=not args.skip_bref and not args.api_only,
        use_api=not args.skip_api,
        bref_delay_s=0.0,
    )
    persist_pool(pool)
    NBAPlugin().reload_pool()
    print(f"NBA pool: {len(pool)} player-seasons")

    need_pfr = args.import_bundle or not has_pfr_bundled_data()
    need_defense = args.with_defense and not has_pfr_defense_data()
    if need_pfr or need_defense:
        label = "PFR historical seasons (1970-1998)"
        if args.with_defense:
            label += " with defense"
        print(f"Building bundled {label}...")
        pfr_args = []
        if args.with_defense:
            pfr_args.append("--with-defense")
        _run("import_pfr_bundle.py", *pfr_args)

    if args.import_bundle or not has_nflverse_bundled_data():
        print("Building bundled nflverse seasons (1999-present)...")
        _run("import_nfl_bundle.py")

    nfl = build_nfl()
    print(f"NFL pool: {len(nfl)} player-seasons")

    lahman_zip = ROOT / "data" / "raw" / "lahman" / "lahman_1871-2025_csv.zip"
    if args.import_bundle or not has_bundled_tenures():
        if not lahman_zip.exists():
            print(
                f"SKIP MLB: Lahman zip not found at {lahman_zip}. "
                "Download from https://sabr.org/lahman-database/ and re-run."
            )
        else:
            print("Building bundled Lahman MLB tenure pool...")
            _run("import_lahman_bundle.py")

    mlb = build_mlb()
    print(f"MLB pool: {len(mlb)} franchise-decade tenure rows")


if __name__ == "__main__":
    main()
