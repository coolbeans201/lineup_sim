"""Import Pro Football Reference seasons (1970-1998) into bundled JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.pfr_bundle import (
    BUNDLE_DIR,
    PFR_END,
    PFR_START,
    import_seasons_to_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import PFR historical seasons (offense via Fantasy Data Pros CSV)."
    )
    parser.add_argument("--start", type=int, default=PFR_START)
    parser.add_argument("--end", type=int, default=PFR_END)
    parser.add_argument("--min-games", type=int, default=6)
    parser.add_argument(
        "--with-defense",
        action="store_true",
        help="Also scrape PFR defense tables (slower; may be blocked by PFR rate limits)",
    )
    parser.add_argument(
        "--defense-delay",
        type=float,
        default=4.0,
        help="Seconds between PFR defense requests (default 4)",
    )
    args = parser.parse_args()

    print(
        f"Importing PFR seasons {args.start}-{args.end} -> {BUNDLE_DIR} "
        f"(GP>={args.min_games}, defense={args.with_defense})..."
    )
    counts = import_seasons_to_bundle(
        start_year=args.start,
        end_year=args.end,
        min_games=args.min_games,
        include_defense=args.with_defense,
        defense_delay_s=args.defense_delay,
    )
    total = sum(counts.values())
    print(f"Wrote {len(counts)} seasons, {total} player-season rows")
    if counts:
        sample = sorted(counts.items())[:3] + sorted(counts.items())[-3:]
        print("Sample season counts:", sample)
    if not args.with_defense:
        print(
            "Offense only. Re-run with --with-defense to add defensive players "
            "(requires PFR access from your network)."
        )


if __name__ == "__main__":
    main()
