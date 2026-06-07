"""Player name normalization for deduplication."""

from __future__ import annotations

import re


def normalize_player_name(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()
