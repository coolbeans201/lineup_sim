"""Shared Streamlit UI helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from lineup_sim.core.models import Lineup, Preset, ScoreResult, SpinConstraint
from lineup_sim.core.presets import get_preset, list_presets
from lineup_sim.core.constraints import eligible_for_slot, generate_spins, pool_for_spin
from lineup_sim.core.spin_options import spin_options_for_slot
from lineup_sim.core.roster import assign_player, eligible_open_slots, empty_lineup, open_slots
from lineup_sim.core.roster_identity import assigned_identities, player_identity
from lineup_sim.core.scoring import score_lineup
from lineup_sim.sports.registry import get_sport_plugin


def player_option_label(player, *, sport: str | None = None) -> str:
    stats = ", ".join(f"{k} {v:g}" for k, v in player.stats.items())
    label = f"{player.player_name} ({player.season}, {player.team_abbr}) — {stats}"
    if sport == "nba":
        from lineup_sim.sports.nba.positions import eligible_lineup_positions

        positions = sorted(eligible_lineup_positions(player.position_raw or player.position))
        if len(positions) > 1:
            label += f" · {'/'.join(positions)}"
    return label


def slot_position_label(slot_id: str, preset_slug: str) -> str:
    preset = get_preset(preset_slug)
    slot = next((s for s in preset.slots if s.slot_id == slot_id), None)
    if slot and slot.position:
        return slot.position
    return slot_id.upper()


def render_score_panel(score: ScoreResult, *, preset_slug: str | None = None) -> None:
    def format_slot(slot_id: str) -> str:
        if preset_slug:
            return slot_position_label(slot_id, preset_slug)
        return slot_id.upper()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Team rating", f"{score.team_rating:.2f}")
    col2.metric("Projected record", f"{score.projected_wins:.0f}-{score.projected_losses:.0f}")
    col3.metric("Grade", score.grade)
    col4.metric("Balance penalty", f"{score.balance_adjustment:.2f}")

    if score.weakest_slot_id:
        st.caption(f"Weakest slot: {format_slot(score.weakest_slot_id)}")

    if score.player_ratings:
        rows = []
        for r in score.player_ratings:
            rows.append(
                {
                    "Slot": format_slot(r.slot_id),
                    "Player": r.player.player_name,
                    "Season": r.player.season,
                    "Stat score": round(r.slot_rating, 2),
                    "Composite Z": round(r.composite_z, 2),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if score.category_totals:
        st.subheader("Category totals")
        st.json(score.category_totals)

    with st.expander("Why this record?"):
        if score.record_notes:
            for note in score.record_notes:
                st.write(f"- {note}")
        else:
            st.write("Fill the lineup to see how projected wins are calculated.")

    with st.expander("How scoring works"):
        for note in score.formula_notes:
            st.write(f"- {note}")


def score_current_lineup(lineup: Lineup) -> ScoreResult:
    plugin = get_sport_plugin(lineup.sport)
    return score_lineup(lineup, plugin.load_player_pool())


def slot_player_picker(
    *,
    sport: str,
    slot,
    key: str,
    decade: str | None = None,
    spin_pool: list | None = None,
    lineup: Lineup | None = None,
    preset: Preset | None = None,
    label: str | None = None,
    enforce_position: bool | None = None,
    hide_all_taken: bool = False,
) -> object | None:
    plugin = get_sport_plugin(sport)
    if enforce_position is None:
        enforce_position = spin_pool is None or sport != "nba"

    if spin_pool is not None:
        candidates = list(spin_pool)
    else:
        candidates = plugin.load_player_pool()
        if slot.decade:
            candidates = [p for p in candidates if p.decade == slot.decade]
        if enforce_position and slot.position:
            candidates = [
                p
                for p in candidates
                if plugin.position_matches(p.position_raw or p.position, slot.position)
            ]
        if slot.side:
            candidates = [p for p in candidates if plugin.side_matches(p.position, slot.side)]

    if lineup is not None:
        if hide_all_taken:
            taken = assigned_identities(lineup)
            current_identity = None
        else:
            taken = assigned_identities(lineup, exclude_slot_id=slot.slot_id)
            current = next((a.player for a in lineup.assignments if a.slot_id == slot.slot_id), None)
            current_identity = player_identity(current) if current else None
        candidates = [
            p
            for p in candidates
            if player_identity(p) not in taken or player_identity(p) == current_identity
        ]

    if not candidates:
        st.warning(f"No players available for {slot.label}")
        return None

    candidates = sorted(candidates, key=lambda p: (-p.stats.get("PTS", 0), p.player_name))
    if spin_pool is not None and sport == "nba":
        if lineup is not None and preset is not None:
            open_positions = ", ".join(
                s.position for s in open_slots(lineup, preset) if s.position
            )
        else:
            open_positions = "PG, SG, SF, PF, C"
        caption = (
            f"{len(candidates)} players on team · "
            f"step 1: pick a player · step 2: confirm their slot ({open_positions} still open)"
        )
    else:
        caption = f"{len(candidates)} players in pool · position filter: {slot.position or 'any'}"
    if lineup is not None and (
        hide_all_taken and assigned_identities(lineup)
        or (not hide_all_taken and assigned_identities(lineup, exclude_slot_id=slot.slot_id))
    ):
        caption += " · already drafted players hidden"
    st.caption(caption)

    picker_label = label or slot.label
    if len(candidates) > 15:
        query = st.text_input(f"Search {picker_label}", "", key=f"{key}_search").lower()
        if query:
            candidates = [
                p
                for p in candidates
                if query in p.player_name.lower() or query in p.team_abbr.lower()
            ]
            st.caption(f"{len(candidates)} matches after search")

    labels = ["— Select —"] + [player_option_label(p, sport=sport) for p in candidates]
    choice = st.selectbox(picker_label, labels, key=key)
    if choice == "— Select —":
        return None
    try:
        idx = labels.index(choice) - 1
    except ValueError:
        return None
    return candidates[idx]


def spin_constraint_picker(
    *,
    sport: str,
    preset,
    slot,
    key: str,
    pool: list,
    pick_label: str | None = None,
) -> SpinConstraint | None:
    label = pick_label or slot.label
    options = spin_options_for_slot(preset, slot, pool)
    if not options:
        st.warning(f"No team-era combos with players for {label}")
        return None

    teams = sorted({spin.team_abbr: spin.team_name for spin in options}.items(), key=lambda item: item[1])
    team_labels = [f"{name} ({abbr})" for abbr, name in teams]
    team_idx = st.selectbox(
        f"{label} — team",
        range(len(teams)),
        format_func=lambda i: team_labels[i],
        key=f"{key}_team",
    )
    team_abbr = teams[team_idx][0]

    era_options = [spin for spin in options if spin.team_abbr == team_abbr]
    era_labels: list[str] = []
    for spin in era_options:
        count = len(
            pool_for_spin(
                pool,
                spin,
                sport=sport,
                position=None if sport == "nba" else slot.position,
                side=None if sport == "nba" else slot.side,
            )
        )
        era_labels.append(f"{spin.era_label} ({count} players)")

    era_idx = st.selectbox(
        f"{label} — era",
        range(len(era_options)),
        format_func=lambda i: era_labels[i],
        key=f"{key}_era",
    )
    return era_options[era_idx]


BUILD_MODES = ("Free build", "Random spins (seed)", "Pick team & era")

# Sports exposed in the Streamlit UI (NFL/MLB backends remain for later).
UI_SPORTS = ("nba",)

SIDEBAR_SPORT_KEY = "app_sport"
SIDEBAR_PRESET_KEY = "app_preset"
SIDEBAR_BUILD_MODE_KEY = "app_build_mode"


def sidebar_help_caption(*, page: str, preset: Preset, build_mode: str | None) -> str:
    """Context-aware sidebar blurb — matches how drafting actually works on each page."""
    if preset.sport == "nba":
        base = (
            "Five starters (PG–C), any pick order. After each pick, assign the player to an "
            "open slot they qualify for. Multi-position players (PG/SG, G-F, etc.) let you "
            "choose among matching open slots."
        )
        if page == "daily":
            return f"{base} Daily reveals one team+decade spin at a time."
        if page == "compare":
            if build_mode == "Free build":
                return f"{base} Build two lineups from the full pool."
            if build_mode == "Random spins (seed)":
                return f"{base} Both lineups share the same seeded team+decade spins."
            if build_mode == "Pick team & era":
                return f"{base} Both lineups share the same team+decade picks."
            return f"{base} Compare two lineups under identical constraints."
        if build_mode == "Free build":
            return f"{base} Full player pool — no team/decade spin."
        if build_mode == "Random spins (seed)":
            return f"{base} Each pick uses a seeded team+decade spin."
        if build_mode == "Pick team & era":
            return f"{base} You choose team+decade for each pick."
        return base
    return preset.description


def render_global_sidebar(
    *,
    page: str = "sandbox",
    show_build_mode: bool = False,
) -> tuple[str, Preset, str | None]:
    """Shared sidebar controls with stable keys and preset validation per sport."""
    if len(UI_SPORTS) == 1:
        sport = UI_SPORTS[0]
        st.session_state[SIDEBAR_SPORT_KEY] = sport
    else:
        if st.session_state.get(SIDEBAR_SPORT_KEY) not in UI_SPORTS:
            st.session_state[SIDEBAR_SPORT_KEY] = UI_SPORTS[0]
        sport = st.sidebar.selectbox(
            "Sport",
            list(UI_SPORTS),
            format_func=lambda s: s.upper(),
            key=SIDEBAR_SPORT_KEY,
        )
    presets = list_presets(sport)
    preset_slugs = [p.slug for p in presets]
    if not preset_slugs:
        st.sidebar.error(f"No presets configured for {sport.upper()}.")
        st.stop()

    current_preset = st.session_state.get(SIDEBAR_PRESET_KEY)
    if current_preset not in preset_slugs:
        st.session_state[SIDEBAR_PRESET_KEY] = preset_slugs[0]

    preset_slug = st.sidebar.selectbox(
        "Preset",
        preset_slugs,
        format_func=lambda s: get_preset(s).name,
        key=SIDEBAR_PRESET_KEY,
    )
    preset = get_preset(preset_slug)

    build_mode: str | None = None
    if show_build_mode:
        build_mode = st.sidebar.radio("Build mode", BUILD_MODES, key=SIDEBAR_BUILD_MODE_KEY)

    st.sidebar.caption(sidebar_help_caption(page=page, preset=preset, build_mode=build_mode))
    return sport, preset, build_mode


def draft_context_key(
    *,
    page: str,
    sport: str,
    preset_slug: str,
    build_mode: str | None = None,
    extra: str = "",
) -> str:
    parts = [page, sport, preset_slug]
    if build_mode:
        parts.append(build_mode.replace(" ", "_").replace("&", "and").replace("(", "").replace(")", ""))
    if extra:
        parts.append(extra)
    return "_".join(parts)


def ensure_lineup_session(
    *,
    session_key: str,
    preset,
    lineup_attr: str,
    key_attr: str,
    label: str = "Lineup",
) -> None:
    if st.session_state.get(key_attr) != session_key:
        st.session_state[lineup_attr] = empty_lineup(preset, label=label)
        st.session_state[key_attr] = session_key


def nba_uses_spin_draft(*, sport: str, build_mode: str) -> bool:
    return sport == "nba" and build_mode != "Free build"


def draft_slot_label(*, slot, sport: str, spin_draft: bool, pick_index: int) -> str:
    if spin_draft:
        return f"Pick {pick_index}"
    return slot.label


def render_seed_spin_controls(
    *,
    preset,
    sport: str,
    player_pool: list,
    key_prefix: str,
    sidebar: bool = False,
) -> list[SpinConstraint]:
    """Seed-based spins; returns the active spin list (may be empty)."""
    container = st.sidebar if sidebar else st
    seed = container.number_input("Spin seed", min_value=0, value=42, step=1, key=f"{key_prefix}_seed")
    spins_key = f"{key_prefix}_spins"
    if container.button("Regenerate spins", key=f"{key_prefix}_regen") or spins_key not in st.session_state:
        st.session_state[spins_key] = generate_spins(preset, seed=int(seed))
    spins: list[SpinConstraint] = st.session_state.get(spins_key, [])
    return spins


def spin_pool_for_slot(
    *,
    build_mode: str,
    sport: str,
    preset,
    slot,
    player_pool: list,
    key_prefix: str,
    seed_spins: list[SpinConstraint] | None = None,
    pick_index: int | None = None,
) -> list | None:
    if build_mode == "Free build":
        return None
    if build_mode == "Random spins (seed)":
        if seed_spins:
            idx = preset.slots.index(slot)
            if idx < len(seed_spins):
                return pool_for_spin(
                    player_pool,
                    seed_spins[idx],
                    sport=sport,
                )
        return None
    if build_mode == "Pick team & era":
        pick_label = f"Pick {pick_index}" if pick_index is not None and sport == "nba" else None
        spin = spin_constraint_picker(
            sport=sport,
            preset=preset,
            slot=slot,
            key=f"{key_prefix}_spin_{slot.slot_id}",
            pool=player_pool,
            pick_label=pick_label,
        )
        if spin is None:
            return None
        return pool_for_spin(
            player_pool,
            spin,
            sport=sport,
        )
    return None


def build_spin_pools_by_pick(
    *,
    build_mode: str,
    sport: str,
    preset,
    player_pool: list,
    key_prefix: str,
    seed_spins: list[SpinConstraint] | None = None,
) -> list[list | None]:
    return [
        spin_pool_for_slot(
            build_mode=build_mode,
            sport=sport,
            preset=preset,
            slot=slot,
            player_pool=player_pool,
            key_prefix=key_prefix,
            seed_spins=seed_spins,
            pick_index=i + 1,
        )
        for i, slot in enumerate(preset.slots)
    ]


def build_spin_pools_by_slot(
    *,
    build_mode: str,
    sport: str,
    preset,
    player_pool: list,
    key_prefix: str,
    seed_spins: list[SpinConstraint] | None = None,
) -> dict[str, list | None]:
    pools: dict[str, list | None] = {}
    for slot in preset.slots:
        pools[slot.slot_id] = spin_pool_for_slot(
            build_mode=build_mode,
            sport=sport,
            preset=preset,
            slot=slot,
            player_pool=player_pool,
            key_prefix=key_prefix,
            seed_spins=seed_spins,
        )
    return pools


def lineup_filled_count(lineup: Lineup) -> int:
    return sum(1 for a in lineup.assignments if a.player is not None)


def _pending_nba_pick_key(key_prefix: str) -> str:
    return f"{key_prefix}_pending_nba_pick"


def queue_nba_pick_assignment(
    *,
    key_prefix: str,
    pick_index: int,
    slot_id: str,
    player_id: str,
    slot_position: str | None,
    spin: SpinConstraint | None = None,
) -> None:
    """Queue a confirmed pick; applied at the start of the next rerun (before widgets)."""
    st.session_state[_pending_nba_pick_key(key_prefix)] = {
        "pick_index": pick_index,
        "slot_id": slot_id,
        "player_id": player_id,
        "slot_position": slot_position,
        "spin": spin,
    }
    st.rerun()


def apply_pending_nba_pick(
    *,
    key_prefix: str,
    preset,
    lineup: Lineup,
    player_pool: list,
) -> Lineup:
    pending = st.session_state.pop(_pending_nba_pick_key(key_prefix), None)
    if not pending:
        return lineup

    expected_pick = lineup_filled_count(lineup) + 1
    if pending["pick_index"] != expected_pick:
        return lineup

    player = next((p for p in player_pool if p.player_id == pending["player_id"]), None)
    if player is None:
        return lineup

    lineup = assign_player(lineup, preset, pending["slot_id"], player)

    spin = pending.get("spin")
    if spin is not None:
        pick_log = list(lineup.metadata.get("pick_log", []))
        pick_log.append(
            {
                "pick": pending["pick_index"],
                "team": spin.team_name,
                "era": spin.era_label,
                "player": player.player_name,
                "position": pending.get("slot_position"),
            }
        )
        lineup = Lineup(
            preset_slug=lineup.preset_slug,
            sport=lineup.sport,
            label=lineup.label,
            assignments=lineup.assignments,
            metadata={**lineup.metadata, "pick_log": pick_log},
        )

    player_widget_key = f"{key_prefix}_pick{pending['pick_index']}_player"
    st.session_state.pop(player_widget_key, None)
    return lineup


def render_nba_lineup_progress(lineup: Lineup, preset) -> None:
    filled = lineup_filled_count(lineup)
    st.progress(filled / preset.slot_count)
    st.caption(f"{filled}/{preset.slot_count} picks complete")

    locked = []
    slot_map = {s.slot_id: s for s in preset.slots}
    for assignment in lineup.assignments:
        if assignment.player is None:
            continue
        slot = slot_map[assignment.slot_id]
        locked.append(f"{slot.position}: {assignment.player.player_name} ({assignment.player.season})")
    if locked:
        st.markdown("**Locked in**")
        for row in locked:
            st.write(f"- {row}")


def spin_pool_for_pick(
    *,
    pick_index: int,
    build_mode: str,
    sport: str,
    preset,
    slot,
    player_pool: list,
    key_prefix: str,
    spins: list[SpinConstraint] | None = None,
) -> tuple[list | None, SpinConstraint | None]:
    if build_mode == "Pick team & era":
        pick_label = f"Pick {pick_index}" if sport == "nba" else None
        spin = spin_constraint_picker(
            sport=sport,
            preset=preset,
            slot=slot,
            key=f"{key_prefix}_spin_pick{pick_index}",
            pool=player_pool,
            pick_label=pick_label,
        )
        if spin is None:
            return None, None
        return pool_for_spin(player_pool, spin, sport=sport), spin
    if spins and pick_index <= len(spins):
        spin = spins[pick_index - 1]
        return pool_for_spin(player_pool, spin, sport=sport), spin
    return None, None


def nba_spin_round_picker(
    *,
    preset,
    lineup: Lineup,
    spin_pool: list | None,
    pick_index: int,
    key_prefix: str,
    spin: SpinConstraint | None = None,
) -> Lineup:
    if spin_pool is None or not open_slots(lineup, preset):
        return lineup

    placeholder = preset.slots[0]
    player = slot_player_picker(
        sport="nba",
        slot=placeholder,
        key=f"{key_prefix}_pick{pick_index}_player",
        spin_pool=spin_pool,
        lineup=lineup,
        preset=preset,
        label=f"Pick {pick_index} — player",
        enforce_position=False,
        hide_all_taken=True,
    )
    if player is None:
        return lineup

    eligible = eligible_open_slots(player, lineup, preset, "nba")
    if not eligible:
        st.warning(f"{player.player_name} does not fit any open position slot.")
        return lineup

    slot_labels = [slot.position or slot.label for slot in eligible]
    st.markdown(f"**Step 2 — assign {player.player_name}**")

    with st.form(key=f"{key_prefix}_pick{pick_index}_assign_form", clear_on_submit=True):
        if len(eligible) == 1:
            target = eligible[0]
            st.caption(
                f"Only **{target.position or target.label}** is open and eligible. "
                "Confirm to lock them in and continue."
            )
        else:
            st.caption(
                f"They qualify for **{' / '.join(slot_labels)}**. "
                "Choose a slot, then confirm to continue."
            )
            slot_idx = st.radio(
                f"Pick {pick_index} — assign to",
                range(len(eligible)),
                format_func=lambda i: slot_labels[i],
                horizontal=True,
            )
            target = eligible[slot_idx]

        slot_name = target.position or target.label
        submitted = st.form_submit_button(
            f"Lock in {player.player_name} at {slot_name}",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return lineup

    queue_nba_pick_assignment(
        key_prefix=key_prefix,
        pick_index=pick_index,
        slot_id=target.slot_id,
        player_id=player.player_id,
        slot_position=target.position,
        spin=spin,
    )
    return lineup


def nba_players_for_open_slots(
    player_pool: list,
    lineup: Lineup,
    preset: Preset,
) -> list:
    """Players who can fill at least one still-open lineup slot."""
    open = open_slots(lineup, preset)
    if not open:
        return []
    return [
        player
        for player in player_pool
        if any(eligible_for_slot(player, slot, "nba") for slot in open)
    ]


def draft_nba_free_build_lineup_sequential(
    *,
    preset,
    lineup: Lineup,
    player_pool: list,
    key_prefix: str,
) -> Lineup:
    """Full pool; pick a player, then assign to any open slot they qualify for."""
    lineup = apply_pending_nba_pick(
        key_prefix=key_prefix,
        preset=preset,
        lineup=lineup,
        player_pool=player_pool,
    )
    filled = lineup_filled_count(lineup)
    render_nba_lineup_progress(lineup, preset)

    if filled >= preset.slot_count:
        return lineup

    pick_index = filled + 1
    open = open_slots(lineup, preset)
    pick_pool = nba_players_for_open_slots(player_pool, lineup, preset)
    open_label = ", ".join(slot.position or slot.label for slot in open)

    st.markdown(f"### Pick {pick_index}")
    st.caption(
        f"{len(pick_pool)} players can fill an open slot ({open_label} open). "
        "Pick a player, confirm their slot, then move to the next pick."
    )

    if not pick_pool:
        st.warning("No players left who fit the open position slots.")
        return lineup

    return nba_spin_round_picker(
        preset=preset,
        lineup=lineup,
        spin_pool=pick_pool,
        pick_index=pick_index,
        key_prefix=key_prefix,
        spin=None,
    )


def draft_nba_spin_lineup_sequential(
    *,
    preset,
    lineup: Lineup,
    build_mode: str,
    player_pool: list,
    key_prefix: str,
    seed_spins: list[SpinConstraint] | None = None,
    fixed_spins: list[SpinConstraint] | None = None,
) -> Lineup:
    """Reveal one team+decade pick at a time; future spins stay hidden."""
    spins = fixed_spins or seed_spins
    lineup = apply_pending_nba_pick(
        key_prefix=key_prefix,
        preset=preset,
        lineup=lineup,
        player_pool=player_pool,
    )
    filled = lineup_filled_count(lineup)
    render_nba_lineup_progress(lineup, preset)

    if filled >= preset.slot_count:
        return lineup

    pick_index = filled + 1
    slot = preset.slots[pick_index - 1]
    spin_pool, spin = spin_pool_for_pick(
        pick_index=pick_index,
        build_mode=build_mode,
        sport="nba",
        preset=preset,
        slot=slot,
        player_pool=player_pool,
        key_prefix=key_prefix,
        spins=spins,
    )

    if spin is not None and spin_pool is not None:
        st.markdown(f"### Pick {pick_index}")
        st.caption(
            f"**{spin.team_name}** · {spin.era_label} · {len(spin_pool)} players available. "
            "Future picks stay hidden — make the best call you can with what you know now."
        )
    elif build_mode == "Pick team & era" and pick_index <= preset.slot_count:
        st.markdown(f"### Pick {pick_index}")
        st.caption("Choose team and era for this pick, then draft a player into an open position slot.")

    if spin_pool:
        pick_pool = nba_players_for_open_slots(spin_pool, lineup, preset)
        if not pick_pool:
            st.warning("No players in this spin pool fit the open position slots.")
        else:
            lineup = nba_spin_round_picker(
                preset=preset,
                lineup=lineup,
                spin_pool=pick_pool,
                pick_index=pick_index,
                key_prefix=key_prefix,
                spin=spin,
            )
    return lineup


def draft_nba_spin_lineup(
    *,
    preset,
    lineup: Lineup,
    spin_pools: list[list | None],
    key_prefix: str,
) -> Lineup:
    for pick_index, spin_pool in enumerate(spin_pools, start=1):
        lineup = nba_spin_round_picker(
            preset=preset,
            lineup=lineup,
            spin_pool=spin_pool,
            pick_index=pick_index,
            key_prefix=key_prefix,
        )
    return lineup


def draft_slot_lineup_sequential(
    *,
    sport: str,
    preset,
    lineup: Lineup,
    key_prefix: str,
    fixed_spins: list[SpinConstraint] | None = None,
    seed_spins: list[SpinConstraint] | None = None,
    build_mode: str = "Free build",
    player_pool: list | None = None,
    spin_pools_by_slot: dict[str, list | None] | None = None,
) -> Lineup:
    filled = lineup_filled_count(lineup)
    st.progress(filled / preset.slot_count)
    st.caption(f"{filled}/{preset.slot_count} slots filled")

    if filled >= preset.slot_count:
        return lineup

    slot = preset.slots[filled]
    pick_index = filled + 1
    spin_pool = None
    spin = None

    if spin_pools_by_slot is not None:
        spin_pool = spin_pools_by_slot.get(slot.slot_id)
    elif fixed_spins and pick_index <= len(fixed_spins):
        spin = fixed_spins[pick_index - 1]
        if player_pool is not None:
            spin_pool = pool_for_spin(player_pool, spin, sport=sport, position=slot.position, side=slot.side)
    elif seed_spins and pick_index <= len(seed_spins):
        spin = seed_spins[pick_index - 1]
        if player_pool is not None:
            spin_pool = pool_for_spin(player_pool, spin, sport=sport, position=slot.position, side=slot.side)

    if spin is not None:
        st.markdown(f"### {slot.label}")
        pool_size = len(spin_pool) if spin_pool else 0
        st.caption(
            f"**{spin.team_name}** · {spin.era_label} · {pool_size} players. "
            "Next spins stay hidden until this slot is filled."
        )
    else:
        st.markdown(f"### {slot.label}")

    player = slot_player_picker(
        sport=sport,
        slot=slot,
        key=f"{key_prefix}_{slot.slot_id}",
        spin_pool=spin_pool,
        lineup=lineup,
    )
    return assign_player(lineup, preset, slot.slot_id, player)


def draft_slot_lineup(
    *,
    sport: str,
    preset,
    lineup: Lineup,
    spin_pools_by_slot: dict[str, list | None],
    key_prefix: str,
) -> Lineup:
    for i, slot in enumerate(preset.slots):
        player = slot_player_picker(
            sport=sport,
            slot=slot,
            key=f"{key_prefix}_{slot.slot_id}",
            spin_pool=spin_pools_by_slot.get(slot.slot_id),
            lineup=lineup,
        )
        lineup = assign_player(lineup, preset, slot.slot_id, player)
    return lineup
