"""Lineup Sim — Streamlit entrypoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.cache import score_shared_lineup
from app.components import render_score_panel
from app.theme import apply_theme, render_theme_selector
from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import lineup_from_dict
from lineup_sim.daily.share import decode_share_payload

st.set_page_config(
    page_title="Lineup Sim",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("views/sandbox.py", title="Sandbox", icon="🧪"),
    st.Page("views/compare.py", title="What-If", icon="⚖️"),
    st.Page("views/daily.py", title="Daily", icon="📅"),
]

pg = st.navigation(pages)

render_theme_selector()

share_token = st.query_params.get("share")
dismissed_share = st.session_state.get("_dismiss_share_token")
if share_token and share_token != dismissed_share:
    try:
        payload = decode_share_payload(share_token)
        preset = get_preset(payload["lineup"]["preset_slug"])
        lineup = lineup_from_dict(preset, payload["lineup"])
        score = score_shared_lineup(
            preset.slug,
            json.dumps(payload["lineup"]),
            lineup.sport,
        )
        st.subheader("Shared lineup")
        if payload.get("date"):
            st.caption(f"Daily puzzle — {payload['date']}")
        render_score_panel(score, preset_slug=preset.slug)
        if st.button("Dismiss shared lineup", key="dismiss_share"):
            st.session_state["_dismiss_share_token"] = share_token
            st.rerun()
        st.divider()
    except Exception as exc:
        st.error(f"Could not load share link: {exc}")

pg.run()
apply_theme()
