"""Sandbox mode — free build or spin-assisted drafting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.components import (
    draft_context_key,
    draft_free_build_sequential,
    draft_spin_lineup_sequential,
    draft_slot_lineup,
    draft_slot_lineup_sequential,
    ensure_lineup_session,
    pick_then_assign_sport,
    uses_spin_draft,
    render_global_sidebar,
    render_score_panel,
    render_seed_spin_controls,
    render_draft_header,
    render_share_panel,
    reset_lineup_session,
    score_current_lineup,
)
from lineup_sim.core.roster import empty_lineup, lineup_to_dict
from lineup_sim.sports.registry import get_sport_plugin

st.title("Sandbox")
st.caption("Build lineups freely or under team-era spins — one pick revealed at a time.")

sport, preset, build_mode = render_global_sidebar(page="sandbox", show_build_mode=True)
plugin = get_sport_plugin(sport)
player_pool = plugin.load_player_pool()
spin_draft = uses_spin_draft(sport=sport, build_mode=build_mode)
draft_key = draft_context_key(
    page="sandbox",
    sport=sport,
    preset_slug=preset.slug,
    build_mode=build_mode,
)
ensure_lineup_session(
    session_key=draft_key,
    preset=preset,
    lineup_attr="sandbox_lineup",
    key_attr="sandbox_key",
)

lineup = st.session_state.sandbox_lineup
seed_spins: list = []

if build_mode == "Random spins (seed)":
    seed_spins = render_seed_spin_controls(
        preset=preset,
        sport=sport,
        player_pool=player_pool,
        key_prefix=draft_key,
        sidebar=True,
    )
elif build_mode == "Pick team & era" and spin_draft:
    st.caption("Set team and era for the current pick only — future picks stay hidden.")

render_draft_header(
    button_key=f"{draft_key}_reset",
    on_reset=lambda: reset_lineup_session(
        preset=preset,
        lineup_attr="sandbox_lineup",
        label="Lineup",
        key_prefixes=[draft_key],
    ),
)
if build_mode == "Free build":
    if pick_then_assign_sport(sport):
        lineup = draft_free_build_sequential(
            sport=sport,
            preset=preset,
            lineup=lineup,
            player_pool=player_pool,
            key_prefix=draft_key,
        )
    else:
        lineup = draft_slot_lineup(
            sport=sport,
            preset=preset,
            lineup=lineup,
            spin_pools_by_slot={slot.slot_id: None for slot in preset.slots},
            key_prefix=draft_key,
        )
elif spin_draft:
    lineup = draft_spin_lineup_sequential(
        sport=sport,
        preset=preset,
        lineup=lineup,
        build_mode=build_mode,
        player_pool=player_pool,
        key_prefix=draft_key,
        seed_spins=seed_spins or None,
    )
else:
    lineup = draft_slot_lineup_sequential(
        sport=sport,
        preset=preset,
        lineup=lineup,
        key_prefix=draft_key,
        seed_spins=seed_spins or None,
        build_mode=build_mode,
        player_pool=player_pool,
    )

st.session_state.sandbox_lineup = lineup

filled = sum(1 for a in lineup.assignments if a.player is not None)
if filled > 0 and filled == preset.slot_count:
    st.divider()
    st.subheader("Results")
    score = score_current_lineup(lineup)
    render_score_panel(score, preset_slug=preset.slug)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Export lineup JSON",
            data=json.dumps(lineup_to_dict(lineup), indent=2),
            file_name="lineup.json",
            mime="application/json",
            key=f"{draft_key}_export",
        )
    with col2:
        render_share_panel(lineup=lineup, score=score, key_prefix=f"{draft_key}_share")
