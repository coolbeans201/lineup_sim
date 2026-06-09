"""What-if lineup comparison."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.components import (
    BUILD_MODE_FREE,
    BUILD_MODE_RANDOM,
    block_spin_draft_if_unready,
    draft_context_key,
    draft_compare_spin_lineups,
    draft_free_build_sequential,
    draft_slot_lineup,
    lineup_filled_count,
    pick_then_assign_sport,
    uses_spin_draft,
    render_global_sidebar,
    render_score_panel,
    render_share_panel,
    render_seed_spin_controls,
    render_draft_header,
    reset_compare_lineups,
)
from app.cache import load_player_pool_cached
from lineup_sim.core.compare import compare_lineups
from lineup_sim.core.roster import empty_lineup

st.title("What-If Compare")
st.caption("Same constraints, two lineups — one pick at a time.")

sport, preset, build_mode = render_global_sidebar(page="compare", show_build_mode=True)
preset_slug = preset.slug
player_pool = load_player_pool_cached(sport)
block_spin_draft_if_unready(sport=sport, build_mode=build_mode, pool_size=len(player_pool))
spin_draft = uses_spin_draft(sport=sport, build_mode=build_mode)
compare_key = draft_context_key(
    page="compare",
    sport=sport,
    preset_slug=preset_slug,
    build_mode=build_mode,
)
shared_key = f"{compare_key}_shared"
side_a_key = f"{compare_key}_a"
side_b_key = f"{compare_key}_b"

seed_spins: list = []
if build_mode == BUILD_MODE_RANDOM:
    seed_spins = render_seed_spin_controls(
        preset=preset,
        sport=sport,
        player_pool=player_pool,
        key_prefix=compare_key,
        sidebar=True,
    )

if st.session_state.get("compare_key") != compare_key:
    st.session_state.compare_lineup_a = empty_lineup(preset, label="Lineup A")
    st.session_state.compare_lineup_b = empty_lineup(preset, label="Lineup B")
    st.session_state.compare_key = compare_key
elif "compare_lineup_a" not in st.session_state or "compare_lineup_b" not in st.session_state:
    st.session_state.compare_lineup_a = empty_lineup(preset, label="Lineup A")
    st.session_state.compare_lineup_b = empty_lineup(preset, label="Lineup B")
    st.session_state.compare_key = compare_key

lineup_a = st.session_state.compare_lineup_a
lineup_b = st.session_state.compare_lineup_b

render_draft_header(
    button_key=f"{compare_key}_reset",
    on_reset=lambda: reset_compare_lineups(
        preset=preset,
        key_prefixes=[side_a_key, side_b_key, shared_key],
    ),
)

if build_mode == BUILD_MODE_FREE:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Lineup A")
        if pick_then_assign_sport(sport):
            lineup_a = draft_free_build_sequential(
                sport=sport,
                preset=preset,
                lineup=lineup_a,
                player_pool=player_pool,
                key_prefix=side_a_key,
            )
        else:
            lineup_a = draft_slot_lineup(
                sport=sport,
                preset=preset,
                lineup=lineup_a,
                spin_pools_by_slot={slot.slot_id: None for slot in preset.slots},
                key_prefix=side_a_key,
            )
    with col_b:
        st.subheader("Lineup B")
        if pick_then_assign_sport(sport):
            lineup_b = draft_free_build_sequential(
                sport=sport,
                preset=preset,
                lineup=lineup_b,
                player_pool=player_pool,
                key_prefix=side_b_key,
            )
        else:
            lineup_b = draft_slot_lineup(
                sport=sport,
                preset=preset,
                lineup=lineup_b,
                spin_pools_by_slot={slot.slot_id: None for slot in preset.slots},
                key_prefix=side_b_key,
            )
elif spin_draft:
    lineup_a, lineup_b = draft_compare_spin_lineups(
        sport=sport,
        preset=preset,
        lineup_a=lineup_a,
        lineup_b=lineup_b,
        build_mode=build_mode,
        player_pool=player_pool,
        side_a_key=side_a_key,
        side_b_key=side_b_key,
        shared_key=shared_key,
        seed_spins=seed_spins or None,
    )

st.session_state.compare_lineup_a = lineup_a
st.session_state.compare_lineup_b = lineup_b

filled_a = lineup_filled_count(lineup_a)
filled_b = lineup_filled_count(lineup_b)

if filled_a > 0 and filled_b > 0:
    result = compare_lineups(lineup_a, lineup_b)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rating delta (A − B)", f"{result.rating_delta:+.2f}")
    m2.metric("Wins delta (A − B)", f"{result.wins_delta:+.1f}")
    m3.metric("Grade A", result.grade_a)
    m4.metric("Grade B", result.grade_b)
    st.caption(f"Overall winner by team rating: **{result.winner}**")

    st.subheader("Slot comparison")
    rows = []
    for row in result.rows:
        rows.append(
            {
                "Slot": row.slot_label,
                "Lineup A": row.lineup_a_player or "—",
                "Lineup B": row.lineup_b_player or "—",
                "Rating A": row.rating_a,
                "Rating B": row.rating_b,
                "Delta": row.rating_delta,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Category deltas (A − B)")
    delta_rows = [
        {"Stat": stat, "Delta (A − B)": round(value, 2)}
        for stat, value in sorted(result.category_deltas.items())
    ]
    if delta_rows:
        st.dataframe(pd.DataFrame(delta_rows), use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Lineup A score")
        render_score_panel(result.score_a, preset_slug=preset_slug)
        if lineup_filled_count(lineup_a) == preset.slot_count:
            render_share_panel(
                lineup=lineup_a,
                score=result.score_a,
                key_prefix=f"{compare_key}_share_a",
            )
    with c2:
        st.markdown("### Lineup B score")
        render_score_panel(result.score_b, preset_slug=preset_slug)
        if lineup_filled_count(lineup_b) == preset.slot_count:
            render_share_panel(
                lineup=lineup_b,
                score=result.score_b,
                key_prefix=f"{compare_key}_share_b",
            )
else:
    st.info("Fill at least one slot in each lineup to compare.")
