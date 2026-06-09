"""Lahman franchise-decade tenure ingest tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lineup_sim.ingest.lahman_bundle import (
    build_tenure_rows,
    pool_for_franchise_decade,
    spike_report,
)
from lineup_sim.ingest.lahman_common import BUNDLE_DIR, lahman_csv_dir

BUNDLE_PATH = BUNDLE_DIR / "tenures.json"


def _load_rows() -> list[dict]:
    if BUNDLE_PATH.exists():
        with BUNDLE_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    return build_tenure_rows()


LAHMAN_ZIP = ROOT / "data" / "raw" / "lahman" / "lahman_1871-2025_csv.zip"


@pytest.mark.skipif(not LAHMAN_ZIP.exists(), reason="SABR Lahman zip not present under data/raw/lahman/")
def test_lahman_csv_present():
    csv_dir = lahman_csv_dir()
    assert (csv_dir / "Batting.csv").exists()
    assert (csv_dir / "Pitching.csv").exists()
    assert (csv_dir / "Appearances.csv").exists()


@pytest.mark.skipif(
    not BUNDLE_PATH.exists() and not LAHMAN_ZIP.exists(),
    reason="MLB Lahman bundle or source zip required",
)
def test_tenure_bundle_covers_active_franchises():
    rows = _load_rows()
    assert rows
    assert len(rows) > 1000
    decades = {row["decade"] for row in rows}
    assert "1990s" in decades
    assert "2000s" in decades
    abbrs = {row["team_abbr"] for row in rows}
    assert len(abbrs) == 30
    assert "NYY" in abbrs
    assert "LAD" in abbrs


@pytest.mark.skipif(
    not BUNDLE_PATH.exists() and not LAHMAN_ZIP.exists(),
    reason="MLB Lahman bundle or source zip required",
)
def test_nyy_1990s_pool_has_reasonable_size():
    rows = _load_rows()
    pool = pool_for_franchise_decade(rows, team_abbr="NYY", decade="1990s")
    assert 20 <= len(pool) <= 200
    batters = [r for r in pool if r["role"] == "bat"]
    assert any(r["player_name"] == "Derek Jeter" for r in batters)


@pytest.mark.skipif(
    not BUNDLE_PATH.exists() and not LAHMAN_ZIP.exists(),
    reason="MLB Lahman bundle or source zip required",
)
def test_batting_tenure_has_multi_position_and_dh():
    rows = _load_rows()
    pool = pool_for_franchise_decade(rows, team_abbr="NYY", decade="1990s")
    jeter = next(r for r in pool if r["player_name"] == "Derek Jeter")
    assert "SS" in jeter["positions"]
    assert "DH" in jeter["positions"]
    assert jeter["stats"]["PA"] >= 100


@pytest.mark.skipif(
    not BUNDLE_PATH.exists() and not LAHMAN_ZIP.exists(),
    reason="MLB Lahman bundle or source zip required",
)
def test_pitching_tenure_has_sp_and_rp_roles():
    rows = _load_rows()
    pool = pool_for_franchise_decade(rows, team_abbr="NYY", decade="1990s")
    mo = next(r for r in pool if r["player_name"] == "Mariano Rivera")
    assert mo["role"] == "pitch"
    assert "RP" in mo["positions"]
    assert mo["stats"]["SV"] > 0


@pytest.mark.skipif(
    not BUNDLE_PATH.exists() and not LAHMAN_ZIP.exists(),
    reason="MLB Lahman bundle or source zip required",
)
def test_spike_report_renders():
    rows = _load_rows()
    report = spike_report(rows, min_pa=100, min_ip=20)
    assert "Total tenure rows" in report
    assert "NYY 1990s" in report
