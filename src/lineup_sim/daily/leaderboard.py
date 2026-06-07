"""Local daily leaderboard storage."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from lineup_sim.core.models import LeaderboardEntry

LEADERBOARD_PATH = Path(__file__).resolve().parents[3] / "data" / "leaderboard.json"


def _load_rows() -> list[dict]:
    if not LEADERBOARD_PATH.exists():
        return []
    with LEADERBOARD_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _save_rows(rows: list[dict]) -> None:
    LEADERBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEADERBOARD_PATH.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


def submit_entry(
    *,
    date: str,
    sport: str,
    preset_slug: str,
    player_name: str,
    team_rating: float,
    projected_wins: float,
    grade: str,
    lineup_summary: str,
) -> LeaderboardEntry:
    share_code = secrets.token_urlsafe(8)
    entry = LeaderboardEntry(
        date=date,
        sport=sport,
        preset_slug=preset_slug,
        player_name=player_name or "Anonymous",
        team_rating=team_rating,
        projected_wins=projected_wins,
        grade=grade,
        share_code=share_code,
        lineup_summary=lineup_summary,
    )
    rows = _load_rows()
    rows.append(entry.__dict__)
    _save_rows(rows)
    return entry


def entries_for_day(date: str, sport: str, preset_slug: str) -> list[LeaderboardEntry]:
    rows = _load_rows()
    out: list[LeaderboardEntry] = []
    for raw in rows:
        if raw.get("date") == date and raw.get("sport") == sport and raw.get("preset_slug") == preset_slug:
            out.append(LeaderboardEntry(**raw))
    return sorted(out, key=lambda e: (e.team_rating, e.projected_wins), reverse=True)


def entry_by_share_code(code: str) -> LeaderboardEntry | None:
    for raw in _load_rows():
        if raw.get("share_code") == code:
            return LeaderboardEntry(**raw)
    return None
