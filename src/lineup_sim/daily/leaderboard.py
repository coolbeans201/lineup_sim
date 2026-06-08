"""Local daily leaderboard storage."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from lineup_sim.core.models import LeaderboardEntry

LEADERBOARD_PATH = Path(__file__).resolve().parents[3] / "data" / "leaderboard.json"


def _normalize_player_name(name: str) -> str:
    return (name or "Anonymous").strip() or "Anonymous"


def _same_puzzle_submission(raw: dict, *, date: str, sport: str, preset_slug: str, player_name: str) -> bool:
    return (
        raw.get("date") == date
        and raw.get("sport") == sport
        and raw.get("preset_slug") == preset_slug
        and _normalize_player_name(raw.get("player_name", "")) == _normalize_player_name(player_name)
    )


def _is_better_submission(candidate: LeaderboardEntry, existing: dict) -> bool:
    existing_rating = float(existing.get("team_rating", 0))
    if candidate.team_rating > existing_rating:
        return True
    if candidate.team_rating < existing_rating:
        return False
    return candidate.projected_wins > float(existing.get("projected_wins", 0))


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
    projected_losses: float | None = None,
) -> LeaderboardEntry:
    share_code = secrets.token_urlsafe(8)
    entry = LeaderboardEntry(
        date=date,
        sport=sport,
        preset_slug=preset_slug,
        player_name=_normalize_player_name(player_name),
        team_rating=team_rating,
        projected_wins=projected_wins,
        grade=grade,
        share_code=share_code,
        lineup_summary=lineup_summary,
        projected_losses=projected_losses,
    )
    rows = _load_rows()
    prior = next(
        (
            raw
            for raw in rows
            if _same_puzzle_submission(
                raw,
                date=date,
                sport=sport,
                preset_slug=preset_slug,
                player_name=player_name,
            )
        ),
        None,
    )
    if prior is not None and not _is_better_submission(entry, prior):
        return LeaderboardEntry(**prior)

    rows = [
        raw
        for raw in rows
        if not _same_puzzle_submission(
            raw,
            date=date,
            sport=sport,
            preset_slug=preset_slug,
            player_name=player_name,
        )
    ]
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


def format_leaderboard_record(entry: LeaderboardEntry, *, max_games: int) -> str:
    if entry.projected_losses is not None:
        return f"{entry.projected_wins:.0f}-{entry.projected_losses:.0f}"
    return f"{entry.projected_wins:.0f}-{max_games - entry.projected_wins:.0f}"
