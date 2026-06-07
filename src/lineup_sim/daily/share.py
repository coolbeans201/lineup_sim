"""Shareable result cards."""

from __future__ import annotations

import base64
import json
from urllib.parse import quote

from lineup_sim.core.models import ScoreResult
from lineup_sim.core.roster import lineup_to_dict
from lineup_sim.core.models import Lineup


def lineup_summary(lineup: Lineup) -> str:
    parts: list[str] = []
    for a in lineup.assignments:
        if a.player is None:
            continue
        p = a.player
        parts.append(f"{p.player_name} '{str(p.season)[-2:]}")
    return " · ".join(parts)


def encode_share_payload(lineup: Lineup, score: ScoreResult, *, date: str | None = None) -> str:
    payload = {
        "lineup": lineup_to_dict(lineup),
        "score": {
            "team_rating": score.team_rating,
            "projected_wins": score.projected_wins,
            "projected_losses": score.projected_losses,
            "grade": score.grade,
        },
        "date": date,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_share_payload(token: str) -> dict:
    padding = "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode(token + padding)
    return json.loads(raw.decode("utf-8"))


def share_url(token: str) -> str:
    return f"?share={quote(token)}"
