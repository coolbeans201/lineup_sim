# Lineup Sim

Original roster builder inspired by [82-0](https://www.82-0.com/) and [20-0](https://www.20-0.com/) — not a clone. Build historical lineups under constraints you choose, with **transparent scoring** and multi-sport support.

## Features

- **Sandbox** — free build or spin-assisted drafting with live score breakdown
- **What-If** — compare two lineups side-by-side
- **Daily challenge** — shared seeded puzzle per sport/day with local leaderboard
- **Shareable results** — encode lineups in a share token / URL

## Sports & presets

| Sport | Preset | Slots |
|-------|--------|-------|
| NBA | NBA All-Eras | 5 starters (PG, SG, SF, PF, C) |
| NFL | NFL Two-Way | 12 offense/defense starters |
| MLB | MLB Battery | 5 hitters + 2 pitchers |

Scoring uses era-relative z-scores, position weights, and a documented balance penalty. See preset YAML in `data/presets/`.

## Data sources

- **NBA (primary):** Bundled Basketball Reference per-game seasons in `data/bundled/nba/bref_per_game/` (1962–present, proper PG/SG/SF/PF/C labels). Built from the open [bball-reference-datasets](https://github.com/sumitrodatta/bball-reference-datasets) CSV.
- **NBA (legacy fallback):** `data/fixtures/nba/historical.json` + sparse cache if the bundle is missing.
- **NBA (optional refresh):** `nba_api` / stats.nba.com with roster positions from `CommonTeamRoster`.
- **NFL:** `nflreadpy` / nflverse + sample data
- **MLB:** `pybaseball` + sample data

```powershell
# One-time: download BRef per-game CSV and write bundled season JSON (~30s)
.\.venv\Scripts\python.exe scripts\import_bref_bundle.py --download

# Full ingest (auto-imports bundle if missing, then rebuilds player_pool cache)
.\.venv\Scripts\python.exe scripts\ingest_all.py

# Optional: also refresh stats.nba.com seasons
.\.venv\Scripts\python.exe scripts\ingest_all.py --import-bundle
```

## Quick start

```powershell
cd lineup-sim
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\streamlit run app/main.py
```

## Project layout

```
src/lineup_sim/   # core engine, sport plugins, ingest, daily puzzle
app/              # Streamlit UI (sandbox, compare, daily)
data/presets/     # tunable constraint + scoring presets
data/sample/      # offline player pools
tests/
```

## Scoring (v1)

1. **Player rating** — weighted z-scores vs same-season/position peers for preset stat categories
2. **Slot rating** — player composite × slot weight × position premium
3. **Team rating** — weighted mean minus balance penalty for weakest slot
4. **Projected record** — logistic curve × season length (`max_games` in preset)
