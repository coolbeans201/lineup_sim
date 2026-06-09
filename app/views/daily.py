"""Daily challenge mode."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.cache import load_player_pool_cached
from app.components import (
    BUILD_MODES,
    draft_context_key,
    draft_spin_lineup_sequential,
    uses_spin_draft,
    ensure_lineup_session,
    render_global_sidebar,
    render_score_panel,
    render_draft_header,
    render_share_panel,
    reset_lineup_session,
    score_current_lineup,
)
from lineup_sim.core.roster import empty_lineup
from lineup_sim.daily.leaderboard import entries_for_day, format_leaderboard_record, submit_entry
from lineup_sim.daily.seed import daily_puzzle
from lineup_sim.daily.share import encode_share_payload, lineup_summary, share_full_url
from lineup_sim.ingest.readiness import sport_pool_ready

st.title("Daily Challenge")
st.caption("Same puzzle for everyone — one revealed pick at a time.")

sport, preset, _ = render_global_sidebar(page="daily", show_build_mode=False)
preset_slug = preset.slug
day = st.sidebar.date_input("Challenge date", value=date.today()).isoformat()
player_name = st.sidebar.text_input("Your name (for leaderboard)", value="Anonymous")
player_pool = load_player_pool_cached(sport)
ready, pool_message = sport_pool_ready(sport, pool_size=len(player_pool))
if not ready and pool_message:
    st.error(pool_message)
    st.stop()

try:
    puzzle = daily_puzzle(sport, preset_slug, day=day)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

spin_draft = uses_spin_draft(sport=sport, build_mode=BUILD_MODES[1])

st.subheader(f"Puzzle — {day}")
st.caption(f"Seed: {puzzle.seed} · picks reveal one at a time")

daily_key = draft_context_key(page="daily", sport=sport, preset_slug=preset_slug, extra=day)
ensure_lineup_session(
    session_key=daily_key,
    preset=preset,
    lineup_attr="daily_lineup",
    key_attr="daily_key",
    label="Daily",
)

lineup = st.session_state.daily_lineup

render_draft_header(
    button_key=f"{daily_key}_reset",
    on_reset=lambda: reset_lineup_session(
        preset=preset,
        lineup_attr="daily_lineup",
        label="Daily",
        key_prefixes=[daily_key],
    ),
)
lineup = draft_spin_lineup_sequential(
    sport=sport,
    preset=preset,
    lineup=lineup,
    build_mode=BUILD_MODES[1],
    player_pool=player_pool,
    key_prefix=daily_key,
    fixed_spins=puzzle.spins,
)

st.session_state.daily_lineup = lineup

filled = sum(1 for a in lineup.assignments if a.player is not None)
if filled == preset.slot_count:
    st.divider()
    st.subheader("Results")
    score = score_current_lineup(lineup)
    render_score_panel(score, preset_slug=preset_slug)

    if st.button("Submit to today's leaderboard"):
        share_token = encode_share_payload(lineup, score, date=day)
        entry = submit_entry(
            date=day,
            sport=sport,
            preset_slug=preset_slug,
            player_name=player_name,
            team_rating=score.team_rating,
            projected_wins=score.projected_wins,
            projected_losses=score.projected_losses,
            grade=score.grade,
            lineup_summary=lineup_summary(lineup),
            share_token=share_token,
        )
        st.success(f"Submitted! Leaderboard code: {entry.share_code}")
        render_share_panel(
            lineup=lineup,
            score=score,
            date=day,
            key_prefix="daily_share",
        )

st.subheader("Today's leaderboard")
entries = entries_for_day(day, sport, preset_slug)
if entries:
    rows = []
    for i, entry in enumerate(entries):
        share_link = share_full_url(entry.share_token) if entry.share_token else ""
        rows.append(
            {
                "Rank": i + 1,
                "Name": entry.player_name,
                "Grade": entry.grade,
                "Rating": entry.team_rating,
                "Record": format_leaderboard_record(entry, max_games=preset.max_games),
                "Lineup": entry.lineup_summary,
                "Share": share_link,
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Share": st.column_config.LinkColumn("Share", display_text="View lineup"),
        },
    )
else:
    st.info("No submissions yet for this puzzle.")
