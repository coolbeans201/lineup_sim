# Lineup Sim

Original roster builder inspired by [82-0](https://www.82-0.com/) and [20-0](https://www.20-0.com/) — not a clone. Build historical NBA and NFL lineups under constraints you choose, with **transparent scoring**.

## Features

- **Sandbox** — free build or spin-assisted drafting with per-pick stats and a full scoring breakdown
- **What-If** — compare two lineups side-by-side under identical constraints
- **Daily challenge** — shared seeded puzzle per day with a local leaderboard
- **Share links** — copy a full URL or compact token; opens the lineup breakdown in the app
- **Appearance** — light/dark toggle in the sidebar
- **Position swaps** — NBA-only optional toggle; NFL uses fixed slots (no swaps), like 20-0.com

## Current scope

The Streamlit UI supports **NBA** and **NFL**. MLB backend exists for later.

| Sport | Preset | Slots | UI |
|-------|--------|-------|-----|
| NBA | NBA All-Eras | 5 starters (PG–C) | Yes |
| NFL | NFL Offense | QB, RB, WR, TE, 2× FLEX (RB/WR/TE) | Yes |
| NFL | NFL Offense/Defense | 6 offense + EDGE, DT, LB, CB, S, D-FLEX | Yes |
| MLB | MLB Battery | 5 hitters + 2 pitchers | Backend only |

Scoring uses weighted raw stats (STL/BLK omitted before 1973-74), slot weights, a balance penalty, and a logistic projected record. See preset YAML in `data/presets/`.

## Data sources

- **NBA (primary):** Bundled Basketball Reference per-game seasons in `data/bundled/nba/bref_per_game/` (1962–present, career position eligibility merged at load).
- **NBA (legacy fallback):** `data/fixtures/nba/historical.json` + sparse cache if the bundle is missing.
- **NBA (optional refresh):** `nba_api` / stats.nba.com with roster positions from `CommonTeamRoster`.
- **NFL (1970–1998):** Pro Football Reference offense stats via [Fantasy Data Pros yearly CSVs](https://github.com/fantasydatapros/data) (`data/bundled/nfl/pfr_per_season/`). Optional `--with-defense` scrape for defensive players.
- **NFL (1999–present):** nflverse via `nflreadpy` (`data/bundled/nfl/nflverse/player_seasons.json`). Sample JSON is the offline fallback.
- **MLB:** sample JSON pool only (not in the UI yet).

```powershell
# One-time: download BRef per-game CSV and write bundled season JSON (~30s)
.\.venv\Scripts\python.exe scripts\import_bref_bundle.py --download

# One-time: PFR historical offense (1970-1998; ~1 min)
.\.venv\Scripts\python.exe scripts\import_pfr_bundle.py

# Optional: add PFR defensive players (slow; needs PFR access from your network)
.\.venv\Scripts\python.exe scripts\import_pfr_bundle.py --with-defense

# One-time: nflverse modern era (1999+; needs network; ~2-5 min)
.\.venv\Scripts\python.exe scripts\import_nfl_bundle.py

# Full ingest (auto-imports bundle if missing, then rebuilds player_pool cache)
.\.venv\Scripts\python.exe scripts\ingest_all.py
```

## Quick start

```powershell
cd lineup-sim
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\streamlit run app/main.py
```

The dev server runs headless (no auto-open browser tab on start or reload). Open [http://localhost:8501](http://localhost:8501) manually when you want to use the app.

After completing a lineup, copy the **Share link** from Sandbox or Daily. Paste it in the browser (or append `?share=…` to the app URL) to reload the full breakdown.

The daily leaderboard is stored locally in `data/leaderboard.json` (gitignored). One entry per name per puzzle is kept — your best rating wins.

## Project layout

```
src/lineup_sim/   # core engine, sport plugins, ingest, daily puzzle
app/              # Streamlit UI (sandbox, compare, daily)
data/presets/     # tunable constraint + scoring presets
data/sample/      # offline player pools
tests/
```

## Scoring (v1)

1. **Stat score** — weighted per-game stats (preset categories; STL/BLK skipped when untracked)
2. **Slot rating** — stat score × slot/position weight
3. **Team rating** — weighted mean minus balance penalty for weakest slot
4. **Projected record** — logistic curve × season length (`max_games` in preset)

Composite Z scores are display-only era context vs position/season peers.
