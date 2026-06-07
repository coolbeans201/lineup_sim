"""Download BRef per-game CSV and build offline season bundles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.bref_bundle import (
    BUNDLE_DIR,
    BUNDLE_END,
    BUNDLE_START,
    DEFAULT_CSV_NAME,
    download_default_csv,
    import_csv_to_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Basketball Reference per-game CSV into bundled JSON")
    parser.add_argument(
        "--csv",
        type=Path,
        help=f"Path to Player Per Game.csv (default: download to data/raw/{DEFAULT_CSV_NAME})",
    )
    parser.add_argument("--start", type=int, default=BUNDLE_START)
    parser.add_argument("--end", type=int, default=BUNDLE_END)
    parser.add_argument("--min-games", type=int, default=20)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the default GitHub CSV if --csv is not provided",
    )
    args = parser.parse_args()

    if args.csv:
        csv_path = args.csv
    else:
        csv_path = ROOT / "data" / "raw" / DEFAULT_CSV_NAME
        if args.download or not csv_path.exists():
            print(f"Downloading {DEFAULT_CSV_NAME}...")
            csv_path = download_default_csv(dest=csv_path)
        elif not csv_path.exists():
            parser.error(
                f"CSV not found at {csv_path}. Pass --csv or run with --download."
            )

    print(f"Importing {csv_path} -> {BUNDLE_DIR} ({args.start}-{args.end}, GP>={args.min_games})...")
    counts = import_csv_to_bundle(
        csv_path,
        start_year=args.start,
        end_year=args.end,
        min_games=args.min_games,
    )
    total = sum(counts.values())
    print(f"Wrote {len(counts)} seasons, {total} player-season rows")
    if counts:
        sample = sorted(counts.items())[:3] + sorted(counts.items())[-3:]
        print("Sample season counts:", sample)


if __name__ == "__main__":
    main()
