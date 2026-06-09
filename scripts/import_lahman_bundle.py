"""Import SABR Lahman CSVs into bundled MLB franchise-decade tenure JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.lahman_bundle import import_tenures_to_bundle, spike_report
from lineup_sim.ingest.lahman_common import BUNDLE_DIR, DEFAULT_MIN_IP, DEFAULT_MIN_PA


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build MLB franchise-decade tenure pool from SABR Lahman CSVs."
    )
    parser.add_argument("--min-pa", type=int, default=DEFAULT_MIN_PA)
    parser.add_argument("--min-ip", type=float, default=DEFAULT_MIN_IP)
    parser.add_argument(
        "--lahman-dir",
        type=Path,
        default=None,
        help="Override path to extracted Lahman CSV directory",
    )
    args = parser.parse_args()

    print(
        f"Importing Lahman tenures -> {BUNDLE_DIR} "
        f"(min_pa={args.min_pa}, min_ip={args.min_ip})..."
    )
    rows = import_tenures_to_bundle(
        min_pa=args.min_pa,
        min_ip=args.min_ip,
        lahman_dir=args.lahman_dir,
    )
    out_path = BUNDLE_DIR / "tenures.json"
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Wrote {len(rows)} tenure rows ({size_mb:.1f} MB)")
    print()
    print(spike_report(rows, min_pa=args.min_pa, min_ip=args.min_ip))


if __name__ == "__main__":
    main()
