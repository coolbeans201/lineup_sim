"""Shareable result cards."""

from __future__ import annotations

import base64
import json
from urllib.parse import quote

from lineup_sim.core.models import ScoreResult
from lineup_sim.core.roster import lineup_to_dict
from lineup_sim.core.models import Lineup


def lineup_summary(lineup: Lineup) -> str:
    from lineup_sim.core.presets import get_preset

    preset = get_preset(lineup.preset_slug)
    parts: list[str] = []
    for a in lineup.assignments:
        if a.player is None:
            continue
        p = a.player
        if preset.sport == "mlb":
            parts.append(f"{p.player_name} ({p.decade})")
        else:
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


def share_full_url(token: str, *, base_url: str | None = None) -> str:
    """Build a copyable URL for the current app page, when running under Streamlit."""
    relative = share_url(token)
    if base_url:
        return f"{base_url.rstrip('/')}{relative}"
    try:
        import streamlit as st

        page_url = getattr(st.context, "url", None)
        if page_url:
            base = str(page_url).split("?", 1)[0]
            return f"{base}{relative}"
        host = getattr(st.context, "host", None)
        if host:
            return f"http://{host}{relative}"
    except Exception:
        pass
    return relative
