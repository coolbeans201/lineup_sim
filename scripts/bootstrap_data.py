"""One-command local data setup for Lineup Sim."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and import all local player pools (NBA, NFL, MLB)."
    )
    parser.add_argument(
        "--with-defense",
        action="store_true",
        help="Include PFR defensive players for 1970-1998 (required for NFL two-way historical defense)",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip stats.nba.com refresh during NBA ingest",
    )
    args = parser.parse_args()

    lahman_zip = ROOT / "data" / "raw" / "lahman" / "lahman_1871-2025_csv.zip"
    if not lahman_zip.exists():
        print(
            "NOTE: MLB import needs the SABR Lahman CSV zip at:\n"
            f"  {lahman_zip}\n"
            "Download from https://sabr.org/lahman-database/ before MLB will import.\n"
        )

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "ingest_all.py"),
        "--import-bundle",
    ]
    if args.with_defense:
        cmd.append("--with-defense")
    if args.skip_api:
        cmd.append("--skip-api")

    print("Running full local data bootstrap...")
    subprocess.check_call(cmd)
    print("Done. Start the app with: .venv\\Scripts\\streamlit run app/main.py")


if __name__ == "__main__":
    main()
