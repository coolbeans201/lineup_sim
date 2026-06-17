# Lineup Sim

Original roster builder inspired by [82-0](https://www.82-0.com/), [20-0](https://www.20-0.com/), and [162-0](https://diamond-draft.app/) — not a clone. Build historical NBA, NFL, and MLB lineups under constraints you choose, with **transparent scoring**.

**v1.0** — This repository ships **code and preset configuration only**. All player pools, caches, and leaderboard files are **local and gitignored**. After cloning, run the one-time data bootstrap below.

## Features

- **Sandbox** — free build or spin-assisted drafting with per-pick stats and a full scoring breakdown
- **What-If** — compare two lineups side-by-side under identical constraints (with share links per lineup)
- **Daily challenge** — shared seeded **team+decade spin** puzzle per day with a local leaderboard (spin modes only; no free build)
- **Share links** — copy a full URL or compact token; opens the lineup breakdown in the app
- **Appearance** — light/dark toggle in the sidebar
- **Position swaps** — NBA-only optional toggle; NFL and MLB use fixed slots (no swaps)
- **Local data panel** — sidebar shows which bundles are present and the import command to run

## Sports and presets

| Sport | Preset | Slots | Era window |
|-------|--------|-------|------------|
| NBA | NBA All-Eras | PG–C (5) | 1960s–2020s |
| NFL | NFL Offense | QB, RB, WR, TE, 2× FLEX | 1970–present |
| NFL | NFL Offense/Defense | 6 offense + EDGE, DT, LB, CB, S, D-FLEX | 1970–present |
| MLB | MLB Modern (1980+) | C–DH + SP + CL (11) | 1980s–2020s (default) |
| MLB | MLB Classic (All-Time) | Same 11 slots | 1950s–2020s |

Preset YAML lives in `data/presets/` (tracked in git).

### Build modes (Sandbox & What-If)

| Mode | Behavior |
|------|----------|
| **Free build** | Full player pool — no team/decade constraint |
| **Random spins (seed)** | Each pick uses a seeded team+decade spin |
| **Pick team & decade** | You choose team and decade for each pick |

NBA, NFL, and MLB use **team+decade** spins in the UI (MLB maps decades to franchise tenure windows). Daily always uses the puzzle’s fixed spin sequence.

Without imported data, **Free build** still works when a minimal pool exists; spin and Daily modes show an error and stop until bundles are imported.

## Quick start

```powershell
cd lineup-sim
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 1. Import local player data (required for real drafts)

```powershell
# Recommended one-command setup (NBA + NFL + MLB when Lahman zip is present)
.\.venv\Scripts\python.exe scripts\bootstrap_data.py --with-defense
```

`--with-defense` adds PFR defensive players (1970–1998) so **NFL Offense/Defense** historical defense slots work. Omit it if you only use NFL Offense or modern-era defense via nflverse.

**MLB prerequisite:** download the [SABR Lahman CSV zip](https://sabr.org/lahman-database/) and place it at:

```
data/raw/lahman/lahman_1871-2025_csv.zip
```

Then re-run bootstrap (or `scripts/import_lahman_bundle.py` alone).

### 2. Run tests and app

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\streamlit run app/main.py
```

Open [http://localhost:8501](http://localhost:8501) manually. The dev server does not auto-open a browser tab.

Without imported data, the app starts but spin/daily modes block with import instructions — pools are empty or too small to draft.

## Data layout (local only)

```
data/
  presets/          # YAML game configs (in git)
  bundled/          # Imported player pools (you generate these)
  raw/              # Source downloads (CSVs, Lahman zip)
  cache/            # Optional API/scrape cache
  sample/           # Optional tiny fallbacks (not in git)
  fixtures/         # Legacy NBA fixture JSON (optional)
  leaderboard.json  # Daily puzzle submissions (runtime)
```

| Output | Import script | Source |
|--------|---------------|--------|
| `data/bundled/nba/bref_per_game/*.json` | `import_bref_bundle.py --download` | [BRef per-game CSV](https://github.com/sumitrodatta/bball-reference-datasets) |
| `data/bundled/nfl/pfr_per_season/*.json` | `import_pfr_bundle.py` | [Fantasy Data Pros](https://github.com/fantasydatapros/data) |
| PFR defense rows (same files) | `import_pfr_bundle.py --with-defense` | Pro Football Reference (scrape; may be slow) |
| `data/bundled/nfl/nflverse/player_seasons.json` | `import_nfl_bundle.py` | nflverse / `nflreadpy` |
| `data/bundled/mlb/lahman/tenures.json` | `import_lahman_bundle.py` | SABR Lahman CSV zip |

### Individual import commands

```powershell
# NBA (~30s, auto-downloads CSV)
.\.venv\Scripts\python.exe scripts\import_bref_bundle.py --download

# NFL 1970-1998 offense (~1 min)
.\.venv\Scripts\python.exe scripts\import_pfr_bundle.py

# NFL 1970-1998 defense (slow; optional)
.\.venv\Scripts\python.exe scripts\import_pfr_bundle.py --with-defense

# NFL 1999-present (~2-5 min, network)
.\.venv\Scripts\python.exe scripts\import_nfl_bundle.py

# MLB franchise-decade tenures (~1-2 min; needs Lahman zip first)
.\.venv\Scripts\python.exe scripts\import_lahman_bundle.py

# All of the above + NBA API refresh
.\.venv\Scripts\python.exe scripts\ingest_all.py --import-bundle --with-defense
```

## Docker (optional)

The image contains code and presets only — **mount or populate `data/`** before use.

```powershell
docker build -t lineup-sim .
docker run -p 8501:8501 -v ${PWD}/data:/app/data lineup-sim
```

Run `bootstrap_data.py` inside the container (or on the host against the mounted volume) before drafting.

## Daily leaderboard and sharing

- Submissions persist in `data/leaderboard.json` (gitignored, single-machine).
- One entry per name per puzzle — best rating wins.
- Submitting stores a **share token**; the leaderboard **Share** column links to the full lineup breakdown.
- Copy share links from Sandbox, Daily, or What-If after completing a lineup.

## Project layout

```
src/lineup_sim/     # core engine, sport plugins, ingest, daily puzzle
app/                # Streamlit UI (sandbox, compare, daily)
data/presets/       # tunable constraint + scoring presets
scripts/            # bootstrap + per-sport import CLIs
tests/
```

## Scoring

1. **Stat score** — sport-specific composite (NBA per-game; NFL per-game fantasy scaling; MLB franchise-decade tenure totals)
2. **Slot rating** — stat score × slot/position weight
3. **Team rating** — weighted mean minus balance penalty for weakest slot
4. **Projected record** — logistic curve × season length (`max_games` in preset)

**NBA:** Per-game stats in tables and pickers; STL/BLK omitted before 1973–74.  
**NFL:** Inspired by [20-0.com](https://www.20-0.com/) — era-relative Composite Z vs position/season peers; position-weighted team rating (QB 1.5×, EDGE/CB 1.2× in two-way mode); balance penalty for weak slots. Season totals in tables; scoring uses per-game fantasy points internally. Offense-first two-way draft. Pre-1999 uses PFR box scores; 1999+ uses nflverse.  
**MLB:** Franchise-decade tenure totals (not single seasons); **Decade** column in breakdown tables; win curve projects ~100–115 wins for strong drafts over 162 games. Negro Leagues excluded.

Composite Z scores are display-only era context vs peers.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Bundle-dependent tests **skip** when local data is missing (no false greens). Import sport data first to run the full integration suite for that sport.

## Development notes

- Version: `1.0.0` (`pyproject.toml`, `src/lineup_sim/__init__.py`)
- Player pools are cached per Streamlit session (`app/cache.py`) to avoid reloading large JSON on every interaction.
- NBA BRef bundle covers 1962–2026; optional `nba_api` refresh covers 1996–2024 with roster positions.
