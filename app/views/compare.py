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
    draft_context_key,
    draft_nba_free_build_lineup_sequential,
    draft_slot_lineup,
    draft_slot_lineup_sequential,
    lineup_filled_count,
    nba_spin_round_picker,
    nba_uses_spin_draft,
    render_global_sidebar,
    render_nba_lineup_progress,
    render_score_panel,
    render_seed_spin_controls,
    spin_pool_for_pick,
)
from lineup_sim.core.compare import compare_lineups
from lineup_sim.core.roster import empty_lineup
from lineup_sim.sports.registry import get_sport_plugin

st.title("What-If Compare")
st.caption("Same constraints, two lineups — one pick at a time.")

sport, preset, build_mode = render_global_sidebar(page="compare", show_build_mode=True)
preset_slug = preset.slug
plugin = get_sport_plugin(sport)
player_pool = plugin.load_player_pool()
spin_draft = nba_uses_spin_draft(sport=sport, build_mode=build_mode)
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
if build_mode == "Random spins (seed)":
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

if build_mode == "Free build":
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Lineup A")
        if sport == "nba":
            lineup_a = draft_nba_free_build_lineup_sequential(
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
        if sport == "nba":
            lineup_b = draft_nba_free_build_lineup_sequential(
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
else:
    filled_a = lineup_filled_count(lineup_a)
    filled_b = lineup_filled_count(lineup_b)
    pick_index = min(filled_a, filled_b) + 1

    if pick_index <= preset.slot_count:
        slot = preset.slots[pick_index - 1]
        spin_pool, spin = spin_pool_for_pick(
            pick_index=pick_index,
            build_mode=build_mode,
            sport=sport,
            preset=preset,
            slot=slot,
            player_pool=player_pool,
            key_prefix=shared_key,
            spins=seed_spins or None,
        )
        if spin is not None and spin_pool is not None:
            st.markdown(f"### Pick {pick_index}")
            st.caption(
                f"**{spin.team_name}** · {spin.era_label} · {len(spin_pool)} players. "
                "Both lineups face the same constraint — future picks stay hidden."
            )
        elif build_mode == "Pick team & era":
            st.markdown(f"### Pick {pick_index}")
            st.caption("Choose one team+era constraint for both lineups.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Lineup A")
        if spin_draft:
            render_nba_lineup_progress(lineup_a, preset)
            if pick_index <= preset.slot_count and filled_a < pick_index and spin_pool:
                lineup_a = nba_spin_round_picker(
                    preset=preset,
                    lineup=lineup_a,
                    spin_pool=spin_pool,
                    pick_index=pick_index,
                    key_prefix=side_a_key,
                    spin=spin,
                )
        else:
            lineup_a = draft_slot_lineup_sequential(
                sport=sport,
                preset=preset,
                lineup=lineup_a,
                key_prefix=side_a_key,
                seed_spins=seed_spins or None,
                build_mode=build_mode,
                player_pool=player_pool,
            )
    with col_b:
        st.subheader("Lineup B")
        if spin_draft:
            render_nba_lineup_progress(lineup_b, preset)
            if pick_index <= preset.slot_count and filled_b < pick_index and spin_pool:
                lineup_b = nba_spin_round_picker(
                    preset=preset,
                    lineup=lineup_b,
                    spin_pool=spin_pool,
                    pick_index=pick_index,
                    key_prefix=side_b_key,
                    spin=spin,
                )
        else:
            lineup_b = draft_slot_lineup_sequential(
                sport=sport,
                preset=preset,
                lineup=lineup_b,
                key_prefix=side_b_key,
                seed_spins=seed_spins or None,
                build_mode=build_mode,
                player_pool=player_pool,
            )

st.session_state.compare_lineup_a = lineup_a
st.session_state.compare_lineup_b = lineup_b

filled_a = lineup_filled_count(lineup_a)
filled_b = lineup_filled_count(lineup_b)

if filled_a > 0 and filled_b > 0:
    result = compare_lineups(lineup_a, lineup_b)

    m1, m2, m3 = st.columns(3)
    m1.metric("Rating delta (A − B)", f"{result.rating_delta:+.2f}")
    m2.metric("Wins delta (A − B)", f"{result.wins_delta:+.1f}")
    m3.metric("Winner", result.winner)

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
    st.json(result.category_deltas)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Lineup A score")
        render_score_panel(result.score_a, preset_slug=preset_slug)
    with c2:
        st.markdown("### Lineup B score")
        render_score_panel(result.score_b, preset_slug=preset_slug)
else:
    st.info("Fill at least one slot in each lineup to compare.")
