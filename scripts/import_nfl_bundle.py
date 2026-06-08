"""Fetch nflverse player seasons and write data/bundled/nfl/player_seasons.json."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.nfl import fetch_season_stats
from lineup_sim.ingest.nfl_bundle import NFLVERSE_END, NFLVERSE_START, save_bundled_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Import nflverse seasons into bundled JSON.")
    parser.add_argument("--start", type=int, default=NFLVERSE_START)
    parser.add_argument("--end", type=int, default=NFLVERSE_END)
    args = parser.parse_args()

    rows: list[dict] = []
    seen: set[tuple[str, int, str]] = set()
    for season in range(args.start, args.end + 1):
        season_rows = fetch_season_stats(season)
        added = 0
        for raw in season_rows:
            key = (raw["player_id"], raw["season"], raw["team_abbr"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(raw)
            added += 1
        print(f"{season}: {added} player-seasons")

    path = save_bundled_rows(rows)
    print(f"Wrote {len(rows)} rows to {path}")


if __name__ == "__main__":
    main()
