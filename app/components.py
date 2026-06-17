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

from lineup_sim.core.models import (
    Lineup,
    PlayerSeason,
    Preset,
    RosterSlot,
    ScoreResult,
    SpinConstraint,
)
from lineup_sim.core.presets import get_preset, list_presets
from lineup_sim.core.constraints import (
    eligible_for_slot,
    generate_spins,
    players_fitting_open_slots,
    pool_for_spin,
    resolve_spin_for_pick,
    used_spin_keys,
)
from lineup_sim.core.spin_options import PICK_SPIN_SPORTS, spin_options_for_pick, spin_options_for_slot
from lineup_sim.core.roster import (
    PickSwapPlan,
    assign_player,
    eligible_open_slots,
    empty_lineup,
    find_player_in_pool,
    offense_first_draft,
    open_slots,
    player_pool_key,
    reassign_player,
    swap_plans_for_new_pick,
    swappable_assignments,
)
from lineup_sim.core.roster_identity import assigned_identities, player_identity
from lineup_sim.core.scoring import _slot_weight, player_stat_composite, score_lineup
from lineup_sim.core.stat_labels import (
    era_column_label,
    format_projected_record,
    format_stat_display_string,
    format_stat_display_value,
    lineup_breakdown_caption,
    player_era_display,
    stat_accumulates_in_lineup_total,
    stat_display_label,
)
from lineup_sim.ingest.readiness import sport_pool_ready
from lineup_sim.sports.registry import get_sport_plugin

from app.cache import load_player_pool_cached, score_lineup_for_ui


def player_option_label(player, *, sport: str | None = None, compact: bool = False) -> str:
    if sport == "nfl":
        from lineup_sim.sports.nfl.display import format_player_dropdown_stats

        stats = format_player_dropdown_stats(player)
        label = (
            f"{player.player_name} ({player.season} {player.team_abbr}, {player.position}) — {stats}"
        )
    elif sport == "mlb":
        label = (
            f"{player.player_name} ({player.decade} {player.team_abbr}, "
            f"{player.position_raw or player.position})"
        )
        if not compact:
            from lineup_sim.sports.mlb.display import format_player_dropdown_stats

            label += f" — {format_player_dropdown_stats(player)}"
    elif sport == "nba":
        from lineup_sim.sports.nba.display import format_player_dropdown_stats

        stats = format_player_dropdown_stats(player)
        label = f"{player.player_name} ({player.season}, {player.team_abbr}) — {stats}"
    else:
        stats = ", ".join(f"{k} {v:g}" for k, v in player.stats.items())
        label = f"{player.player_name} ({player.season}, {player.team_abbr}) — {stats}"
    if sport == "nba":
        from lineup_sim.sports.nba.positions import eligible_lineup_positions

        positions = sorted(eligible_lineup_positions(player.position_raw or player.position))
        if len(positions) > 1:
            label += f" · {'/'.join(positions)}"
    return label


def _picker_option_labels(
    candidates: list[PlayerSeason],
    *,
    sport: str,
    cache_key: str,
) -> list[str]:
    """Build selectbox labels once per candidate set — avoids reformatting on every rerun."""
    signature = tuple(player_pool_key(p) for p in candidates)
    bucket = st.session_state.setdefault("_picker_label_cache", {})
    entry = bucket.get(cache_key)
    if entry and entry.get("signature") == signature:
        return entry["labels"]
    labels = [player_option_label(p, sport=sport) for p in candidates]
    bucket[cache_key] = {"signature": signature, "labels": labels}
    return labels


def slot_position_label(slot_id: str, preset_slug: str) -> str:
    preset = get_preset(preset_slug)
    slot = next((s for s in preset.slots if s.slot_id == slot_id), None)
    if slot and slot.position:
        return slot.position
    return slot_id.upper()


def format_player_stat_summary(player, preset: Preset) -> str:
    plugin = get_sport_plugin(preset.sport)
    parts: list[str] = []
    for stat in preset.stat_weights:
        label = stat_display_label(stat, sport=preset.sport)
        if plugin.stat_tracking_factor(player, stat) <= 0:
            parts.append(f"{label} n/a")
        else:
            parts.append(
                f"{label} {format_stat_display_string(player.stats.get(stat, 0), stat, sport=preset.sport)}"
            )
    return " · ".join(parts)


def locked_in_player_rows(lineup: Lineup, preset: Preset) -> list[dict]:
    plugin = get_sport_plugin(preset.sport)
    slot_map = {s.slot_id: s for s in preset.slots}
    rows: list[dict] = []
    for assignment in lineup.assignments:
        if assignment.player is None:
            continue
        player = assignment.player
        slot = slot_map[assignment.slot_id]
        era_label = era_column_label(sport=preset.sport)
        row: dict = {
            "Slot": slot.position or slot.label,
            "Player": player.player_name,
            era_label: player_era_display(player, sport=preset.sport),
        }
        for stat in preset.stat_weights:
            label = stat_display_label(stat, sport=preset.sport)
            if plugin.stat_tracking_factor(player, stat) <= 0:
                row[label] = "n/a"
            else:
                row[label] = format_stat_display_value(
                    player.stats.get(stat, 0), stat, sport=preset.sport
                )
        rows.append(row)
    return rows


def render_score_panel(score: ScoreResult, *, preset_slug: str | None = None) -> None:
    def format_slot(slot_id: str) -> str:
        if preset_slug:
            return slot_position_label(slot_id, preset_slug)
        return slot_id.upper()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Team rating", f"{score.team_rating:.2f}")
    col2.metric(
        "Projected record",
        format_projected_record(
            score.projected_wins,
            max_games=score.max_games,
            projected_losses=score.projected_losses,
        ),
    )
    col3.metric("Grade", score.grade)
    col4.metric("Balance penalty", f"{score.balance_adjustment:.2f}")

    if score.weakest_slot_id:
        st.caption(f"Weakest slot: {format_slot(score.weakest_slot_id)}")

    if score.player_ratings:
        st.subheader("Lineup breakdown")

        preset = get_preset(preset_slug) if preset_slug else None
        if preset:
            st.caption(lineup_breakdown_caption(preset))
        else:
            st.caption(
                "Per-game stats for each pick, weighted stat score, and slot rating "
                "(how much that player pulls team rating up or down)."
            )
        stat_cols = list(preset.stat_weights.keys()) if preset else []
        plugin = get_sport_plugin(preset.sport) if preset else None

        era_label = era_column_label(sport=preset.sport) if preset else "Season"
        rows = []
        for rating in score.player_ratings:
            row: dict = {
                "Slot": format_slot(rating.slot_id),
                "Player": rating.player.player_name,
                era_label: player_era_display(rating.player, sport=preset.sport if preset else None),
                "Team": rating.player.team_abbr,
            }
            for stat in stat_cols:
                label = stat_display_label(stat, sport=preset.sport)
                if plugin and plugin.stat_tracking_factor(rating.player, stat) <= 0:
                    row[label] = "n/a"
                else:
                    row[label] = format_stat_display_value(
                        rating.player.stats.get(stat, 0), stat, sport=preset.sport
                    )
            if preset:
                row["Stat score"] = round(player_stat_composite(rating.player, preset), 2)
            row["Slot rating"] = round(rating.slot_rating, 2)
            row["Composite Z"] = round(rating.composite_z, 2)
            rows.append(row)

        if stat_cols and score.category_totals:
            totals_row: dict = {
                "Slot": "Team totals",
                "Player": "—",
                era_label: "—",
                "Team": "—",
            }
            for stat in stat_cols:
                label = stat_display_label(stat, sport=preset.sport)
                if stat_accumulates_in_lineup_total(stat, sport=preset.sport):
                    totals_row[label] = format_stat_display_value(
                        score.category_totals.get(stat, 0), stat, sport=preset.sport
                    )
                else:
                    totals_row[label] = "—"
            totals_row["Stat score"] = "—"
            totals_row["Slot rating"] = "—"
            totals_row["Composite Z"] = "—"
            rows.append(totals_row)

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if preset and score.player_ratings:
            slot_map = {slot.slot_id: slot for slot in preset.slots}
            weights = [_slot_weight(slot_map[r.slot_id], preset) for r in score.player_ratings]
            raw_mean = sum(r.slot_rating * w for r, w in zip(score.player_ratings, weights)) / sum(weights)
            st.caption(
                f"Team rating math: weighted mean slot ratings ({raw_mean:.2f}) "
                f"− balance penalty ({score.balance_adjustment:.2f}) "
                f"= {score.team_rating:.2f} · stat totals are simple sums across the lineup"
            )

    with st.expander("Why this record?"):
        if score.record_notes:
            for note in score.record_notes:
                st.write(f"- {note}")
        else:
            st.write("Fill the lineup to see how projected wins are calculated.")

    with st.expander("How scoring works"):
        preset = get_preset(preset_slug) if preset_slug else None
        if preset and preset.sport == "nfl":
            st.caption(
                "Modeled after [20-0.com](https://www.20-0.com/) — era-relative peers, premium positions, "
                "and balance matter. This sim shows the full breakdown instead of hiding ratings."
            )
        for note in score.formula_notes:
            st.write(f"- {note}")


def render_share_panel(
    *,
    lineup: Lineup,
    score: ScoreResult,
    date: str | None = None,
    key_prefix: str = "share",
) -> None:
    from lineup_sim.daily.share import encode_share_payload, lineup_summary, share_full_url

    token = encode_share_payload(lineup, score, date=date)
    url = share_full_url(token)
    st.text_input("Share link", value=url, key=f"{key_prefix}_url")
    with st.expander("Compact share token"):
        st.code(token, language=None)
    st.caption(f"Summary: {lineup_summary(lineup)}")


def score_current_lineup(lineup: Lineup) -> ScoreResult:
    return score_lineup_for_ui(lineup)


def _player_picker_sort_key(player: PlayerSeason, *, sport: str, preset: Preset | None) -> tuple:
    if preset is not None:
        return (-player_stat_composite(player, preset), player.player_name.lower())
    plugin = get_sport_plugin(sport)
    return (-plugin.season_value(player), player.player_name.lower())


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

    candidates = sorted(
        candidates,
        key=lambda p: _player_picker_sort_key(p, sport=sport, preset=preset),
    )
    if spin_pool is not None and sport in PICK_SPIN_SPORTS:
        if lineup is not None and preset is not None:
            open_positions = ", ".join(
                s.position for s in open_slots(lineup, preset) if s.position
            )
        else:
            open_positions = "open slots"
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

    labels = ["— Select —"] + _picker_option_labels(
        candidates,
        sport=sport,
        cache_key=key,
    )
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
    lineup: Lineup | None = None,
    pick_index: int | None = None,
) -> SpinConstraint | None:
    label = pick_label or slot.label
    if sport in PICK_SPIN_SPORTS:
        options = spin_options_for_pick(
            preset,
            pool,
            lineup=lineup,
            pick_index=pick_index,
        )
    else:
        options = spin_options_for_slot(preset, slot, pool)
    if not options:
        st.warning(f"No team+decade combos with players for {label}")
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
        spin_pool = pool_for_spin(pool, spin, sport=sport)
        if lineup is not None and sport in PICK_SPIN_SPORTS:
            count = len(players_fitting_open_slots(spin_pool, lineup, preset, sport))
        else:
            count = len(spin_pool)
        era_labels.append(f"{spin.era_label} ({count} players)")

    era_idx = st.selectbox(
        f"{label} — decade",
        range(len(era_options)),
        format_func=lambda i: era_labels[i],
        key=f"{key}_era",
    )
    return era_options[era_idx]


BUILD_MODE_FREE = "Free build"
BUILD_MODE_RANDOM = "Random spins (seed)"
BUILD_MODE_PICK = "Pick team & decade"
BUILD_MODES = (BUILD_MODE_FREE, BUILD_MODE_RANDOM, BUILD_MODE_PICK)


def block_spin_draft_if_unready(
    *,
    sport: str,
    build_mode: str | None,
    pool_size: int,
) -> None:
    """Stop the page when spin/daily modes need bundles that are not imported yet."""
    if build_mode == BUILD_MODE_FREE or build_mode is None:
        return
    ready, message = sport_pool_ready(sport, pool_size=pool_size)
    if not ready and message:
        st.error(message)
        st.stop()


UI_SPORTS = ("nba", "nfl", "mlb")

SIDEBAR_SPORT_KEY = "app_sport"
SIDEBAR_PRESET_KEY = "app_preset"
SIDEBAR_BUILD_MODE_KEY = "app_build_mode"
SIDEBAR_POSITION_SWAPS_KEY = "app_position_swaps"


def position_swaps_enabled() -> bool:
    return bool(st.session_state.get(SIDEBAR_POSITION_SWAPS_KEY, False))


def sidebar_help_caption(*, page: str, preset: Preset, build_mode: str | None) -> str:
    """Context-aware sidebar blurb — matches how drafting actually works on each page."""
    if preset.sport == "nba":
        base = (
            "Five starters (PG–C), any pick order. After each pick, assign the player to an "
            "open slot they qualify for. Multi-position players (PG/SG, G-F, etc.) let you "
            "choose among matching open slots. Enable Position swaps to move someone later "
            "and free a slot for a tight fit."
        )
        if page == "daily":
            return f"{base} Daily reveals one team+decade spin at a time."
        if page == "compare":
            if build_mode == BUILD_MODE_FREE:
                return f"{base} Build two lineups from the full pool."
            if build_mode == BUILD_MODE_RANDOM:
                return f"{base} Both lineups share the same seeded team+decade spins."
            if build_mode == BUILD_MODE_PICK:
                return f"{base} Both lineups share the same team+decade picks."
            return f"{base} Compare two lineups under identical constraints."
        if build_mode == BUILD_MODE_FREE:
            return f"{base} Full player pool — no team/decade spin."
        if build_mode == BUILD_MODE_RANDOM:
            return f"{base} Each pick uses a seeded team+decade spin."
        if build_mode == BUILD_MODE_PICK:
            return f"{base} You choose team+decade for each pick."
        return base
    if preset.sport == "nfl":
        base = (
            "Pick a player, then assign them to an open slot they qualify for. "
            "Offense/defense mode: complete all six offense starters before defense opens. "
            "FLEX is RB/WR/TE only — QBs stay at QB. No position swaps."
        )
        if page == "daily":
            return f"{base} Daily reveals one team+decade spin per pick."
        if page == "compare":
            if build_mode == BUILD_MODE_FREE:
                return f"{base} Build two lineups from the full pool."
            if build_mode == BUILD_MODE_RANDOM:
                return f"{base} Both lineups share the same seeded team+decade spins."
            if build_mode == BUILD_MODE_PICK:
                return f"{base} Both lineups share the same team+decade picks."
            return f"{base} Compare two lineups under identical constraints."
        if build_mode == BUILD_MODE_FREE:
            return f"{base} Full player pool — no team/decade spin."
        if build_mode == BUILD_MODE_RANDOM:
            return f"{base} Each pick uses a seeded team+decade spin."
        if build_mode == BUILD_MODE_PICK:
            return f"{base} You choose team+decade for each pick."
        return base
    if preset.sport == "mlb":
        base = (
            "Eleven slots (C–DH + SP + CL). Spin a franchise and decade, pick a player, "
            "then assign them to one open position they qualify for — multi-position players "
            "pick a single slot and stay there. Stats are franchise-decade tenure totals, not peak seasons."
        )
        if page == "daily":
            return f"{base} Daily reveals one team+decade spin per pick."
        if page == "compare":
            if build_mode == BUILD_MODE_FREE:
                return f"{base} Build two lineups from the full pool."
            if build_mode == BUILD_MODE_RANDOM:
                return f"{base} Both lineups share the same seeded team+decade spins."
            if build_mode == BUILD_MODE_PICK:
                return f"{base} Both lineups share the same team+decade picks."
            return f"{base} Compare two lineups under identical constraints."
        if build_mode == BUILD_MODE_FREE:
            return f"{base} Full player pool — no team/decade spin."
        if build_mode == BUILD_MODE_RANDOM:
            return f"{base} Each pick uses a seeded team+decade spin."
        if build_mode == BUILD_MODE_PICK:
            return f"{base} You choose team+decade for each pick."
        return base
    return preset.description


def render_data_status(sport: str, *, pool_size: int) -> None:
    from lineup_sim.ingest.readiness import import_command_hint, sport_data_summary, sport_pool_ready

    summary = sport_data_summary(sport)
    ready, message = sport_pool_ready(sport, pool_size=pool_size)
    with st.sidebar.expander("Local data", expanded=not ready):
        if summary:
            for key, ok in summary.items():
                label = key.replace("_", " ")
                st.write(f"{'✓' if ok else '✗'} {label}")
        st.caption(f"Player pool: {pool_size:,} rows")
        if message:
            st.warning(message)
        st.code(import_command_hint(sport), language=None)


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
        default_slug = preset_slugs[0]
        if sport == "mlb" and "mlb_modern" in preset_slugs:
            default_slug = "mlb_modern"
        st.session_state[SIDEBAR_PRESET_KEY] = default_slug

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

    if sport == "nba":
        st.sidebar.checkbox(
            "Position swaps",
            key=SIDEBAR_POSITION_SWAPS_KEY,
            help=(
                "When picking, offer swaps that move a locked-in player to free a better slot "
                "(e.g. slide LeBron SF→PG, then lock your new pick at SF)."
            ),
        )

    pool = load_player_pool_cached(sport)
    render_data_status(sport, pool_size=len(pool))

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


def uses_spin_draft(*, sport: str, build_mode: str) -> bool:
    return sport in PICK_SPIN_SPORTS and build_mode != BUILD_MODE_FREE


def pick_then_assign_sport(sport: str) -> bool:
    """Sports that draft pick-then-assign (player first, slot second)."""
    return sport in PICK_SPIN_SPORTS


def offense_first_phase_caption(lineup: Lineup, preset: Preset) -> str | None:
    if not offense_first_draft(preset):
        return None
    slot_map = {s.slot_id: s for s in preset.slots}
    offense_slots = [s for s in preset.slots if s.side == "offense"]
    defense_slots = [s for s in preset.slots if s.side == "defense"]
    filled_offense = sum(
        1
        for a in lineup.assignments
        if a.player is not None and slot_map[a.slot_id].side == "offense"
    )
    if filled_offense < len(offense_slots):
        return f"Offense phase — {filled_offense}/{len(offense_slots)} filled"
    filled_defense = sum(
        1
        for a in lineup.assignments
        if a.player is not None and slot_map[a.slot_id].side == "defense"
    )
    return f"Defense phase — {filled_defense}/{len(defense_slots)} filled"


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
        try:
            st.session_state[spins_key] = generate_spins(preset, seed=int(seed))
        except ValueError as exc:
            st.error(str(exc))
            st.session_state[spins_key] = []
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
    if build_mode == BUILD_MODE_FREE:
        return None
    if build_mode == BUILD_MODE_RANDOM:
        if seed_spins:
            idx = preset.slots.index(slot)
            if idx < len(seed_spins):
                return pool_for_spin(
                    player_pool,
                    seed_spins[idx],
                    sport=sport,
                )
        return None
    if build_mode == BUILD_MODE_PICK:
        pick_label = (
            f"Pick {pick_index}"
            if pick_index is not None and sport in PICK_SPIN_SPORTS
            else None
        )
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


def _pending_pick_key(key_prefix: str) -> str:
    return f"{key_prefix}_pending_pick"


def clear_draft_widget_state(key_prefix: str) -> None:
    st.session_state.pop(_pending_pick_key(key_prefix), None)
    st.session_state.pop(_pending_swap_key(key_prefix), None)
    for key in list(st.session_state.keys()):
        if key.startswith(f"{key_prefix}_"):
            del st.session_state[key]


def reset_lineup_session(
    *,
    preset,
    lineup_attr: str,
    label: str,
    key_prefixes: list[str],
) -> None:
    st.session_state[lineup_attr] = empty_lineup(preset, label=label)
    for prefix in key_prefixes:
        clear_draft_widget_state(prefix)
    st.rerun()


def reset_compare_lineups(*, preset, key_prefixes: list[str]) -> None:
    st.session_state.compare_lineup_a = empty_lineup(preset, label="Lineup A")
    st.session_state.compare_lineup_b = empty_lineup(preset, label="Lineup B")
    for prefix in key_prefixes:
        clear_draft_widget_state(prefix)
    st.rerun()


def render_start_over_button(
    *,
    button_key: str,
    on_reset,
    label: str = "Reset lineup",
    help_text: str = "Clear all picks and draft again from scratch.",
) -> None:
    if st.button(label, key=button_key, type="secondary", help=help_text, use_container_width=True):
        on_reset()


def render_draft_header(*, button_key: str, on_reset) -> None:
    title_col, reset_col = st.columns([6, 1], vertical_alignment="center")
    with title_col:
        st.markdown("### Draft")
    with reset_col:
        render_start_over_button(button_key=button_key, on_reset=on_reset)


def queue_pick_assignment(
    *,
    key_prefix: str,
    pick_index: int,
    slot_id: str,
    player: PlayerSeason,
    slot_position: str | None,
    spin: SpinConstraint | None = None,
    swap: dict[str, str] | None = None,
) -> None:
    """Queue a confirmed pick; applied at the start of the next rerun (before widgets)."""
    payload: dict = {
        "pick_index": pick_index,
        "slot_id": slot_id,
        "player_id": player.player_id,
        "season": player.season,
        "team_abbr": player.team_abbr,
        "role": player.role,
        "slot_position": slot_position,
        "spin": spin,
    }
    if swap is not None:
        payload["swap"] = swap
    st.session_state[_pending_pick_key(key_prefix)] = payload
    st.rerun()


def apply_pending_pick(
    *,
    key_prefix: str,
    preset,
    lineup: Lineup,
    player_pool: list,
) -> Lineup:
    pending = st.session_state.pop(_pending_pick_key(key_prefix), None)
    if not pending:
        return lineup

    expected_pick = lineup_filled_count(lineup) + 1
    if pending["pick_index"] != expected_pick:
        return lineup

    player = find_player_in_pool(
        player_pool,
        player_id=pending["player_id"],
        season=pending.get("season"),
        team_abbr=pending.get("team_abbr"),
        role=pending.get("role"),
    )
    if player is None:
        return lineup

    swap = pending.get("swap")
    if swap:
        lineup = reassign_player(
            lineup,
            preset,
            from_slot_id=swap["from_slot_id"],
            to_slot_id=swap["to_slot_id"],
        )
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


def render_lineup_progress(
    lineup: Lineup,
    preset: Preset,
    *,
    key_prefix: str = "",
) -> Lineup:
    filled = lineup_filled_count(lineup)
    st.progress(filled / preset.slot_count)
    st.caption(f"{filled}/{preset.slot_count} picks complete")

    locked_rows = locked_in_player_rows(lineup, preset)
    if locked_rows:
        st.markdown("**Locked in**")
        st.dataframe(pd.DataFrame(locked_rows), use_container_width=True, hide_index=True)
        if filled < preset.slot_count:
            if preset.sport == "mlb":
                st.caption(
                    "Franchise-decade tenure totals for each pick so far. "
                    "Team rating, projected record, and full scoring breakdown appear after all picks are locked in."
                )
            else:
                st.caption(
                    "Per-game stats for each pick so far. "
                    "Team rating, projected record, and full scoring breakdown appear after all picks are locked in."
                )

    if key_prefix and position_swaps_enabled() and 0 < filled < preset.slot_count:
        lineup = render_position_swap(lineup=lineup, preset=preset, key_prefix=key_prefix)
    return lineup


def _pending_swap_key(key_prefix: str) -> str:
    return f"{key_prefix}_pending_swap"


def apply_pending_position_swap(
    lineup: Lineup,
    preset: Preset,
    key_prefix: str,
) -> Lineup:
    pending = st.session_state.pop(_pending_swap_key(key_prefix), None)
    if not pending:
        return lineup
    return reassign_player(
        lineup,
        preset,
        from_slot_id=pending["from_slot_id"],
        to_slot_id=pending["to_slot_id"],
    )


def render_position_swap(
    *,
    lineup: Lineup,
    preset: Preset,
    key_prefix: str,
) -> Lineup:
    movable = swappable_assignments(lineup, preset, preset.sport)
    if not movable:
        return lineup

    slot_map = {s.slot_id: s for s in preset.slots}
    with st.expander("Move a player to another slot", expanded=False):
        st.caption(
            "Free a position for your next pick by moving someone who qualifies for multiple slots."
        )
        move_labels = [
            (
                f"{assignment.player.player_name} ({assignment.player.season}) "
                f"at {slot_map[assignment.slot_id].position or assignment.slot_id.upper()}"
            )
            for assignment, _ in movable
        ]
        move_idx = st.selectbox(
            "Player to move",
            range(len(movable)),
            format_func=lambda i: move_labels[i],
            key=f"{key_prefix}_swap_player",
        )
        assignment, targets = movable[move_idx]
        from_slot = slot_map[assignment.slot_id]
        target_labels = [slot.position or slot.label for slot in targets]
        target_idx = st.selectbox(
            "Move to",
            range(len(targets)),
            format_func=lambda i: target_labels[i],
            key=f"{key_prefix}_swap_target",
        )
        target_slot = targets[target_idx]
        from_label = from_slot.position or from_slot.label
        to_label = target_slot.position or target_slot.label
        if st.button(
            f"Move {assignment.player.player_name} from {from_label} → {to_label}",
            key=f"{key_prefix}_swap_confirm",
            type="secondary",
        ):
            st.session_state[_pending_swap_key(key_prefix)] = {
                "from_slot_id": assignment.slot_id,
                "to_slot_id": target_slot.slot_id,
            }
            st.rerun()
    return lineup


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
    lineup: Lineup | None = None,
) -> tuple[list | None, SpinConstraint | None]:
    spin_seed = None
    if build_mode == BUILD_MODE_RANDOM:
        spin_seed = int(st.session_state.get(f"{key_prefix}_seed", 42))

    if build_mode == BUILD_MODE_PICK:
        pick_label = f"Pick {pick_index}" if sport in PICK_SPIN_SPORTS else None
        spin = spin_constraint_picker(
            sport=sport,
            preset=preset,
            slot=slot,
            key=f"{key_prefix}_spin_pick{pick_index}",
            pool=player_pool,
            pick_label=pick_label,
            lineup=lineup,
            pick_index=pick_index,
        )
        if spin is None:
            return None, None
        return pool_for_spin(player_pool, spin, sport=sport), spin
    if spins and pick_index <= len(spins):
        seeded = spins[pick_index - 1]
        if lineup is not None and sport in PICK_SPIN_SPORTS:
            spin = resolve_spin_for_pick(
                pool=player_pool,
                preset=preset,
                lineup=lineup,
                sport=sport,
                pick_index=pick_index,
                spin=seeded,
                spins=spins,
                used=used_spin_keys(spins, pick_index),
                seed=spin_seed,
            )
        else:
            spin = seeded
        if spin is None:
            return None, None
        return pool_for_spin(player_pool, spin, sport=sport), spin
    return None, None


def _format_pick_swap_plan(
    plan: PickSwapPlan,
    *,
    new_player: PlayerSeason,
    slot_map: dict,
) -> str:
    from_pos = slot_map[plan.assign_slot_id].position or plan.assign_slot_id.upper()
    to_pos = slot_map[plan.move_to_slot_id].position or plan.move_to_slot_id.upper()
    assign_pos = from_pos
    return (
        f"Move {plan.occupant.player_name} ({from_pos}→{to_pos}), "
        f"then lock {new_player.player_name} at {assign_pos}"
    )


def pick_spin_round_picker(
    *,
    sport: str,
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
        sport=sport,
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

    eligible = eligible_open_slots(player, lineup, preset, sport)
    swap_plans = (
        swap_plans_for_new_pick(player, lineup, preset, sport)
        if sport == "nba" and position_swaps_enabled()
        else []
    )
    if not eligible and not swap_plans:
        st.warning(f"{player.player_name} does not fit any open position slot.")
        if position_swaps_enabled():
            st.caption("No swap is available to free a better slot for this pick.")
        return lineup

    slot_map = {s.slot_id: s for s in preset.slots}
    st.markdown(f"**Step 2 — assign {player.player_name}**")

    assignment_options: list[tuple[str, RosterSlot | None, PickSwapPlan | None, str]] = []
    for slot in eligible:
        label = slot.position or slot.label
        assignment_options.append(
            ("open", slot, None, f"Assign to open **{label}** slot")
        )
    for plan in swap_plans:
        assignment_options.append(
            (
                "swap",
                slot_map[plan.assign_slot_id],
                plan,
                _format_pick_swap_plan(plan, new_player=player, slot_map=slot_map),
            )
        )

    with st.form(key=f"{key_prefix}_pick{pick_index}_assign_form", clear_on_submit=True):
        if len(assignment_options) == 1:
            kind, target, plan, caption = assignment_options[0]
            st.caption(caption)
        else:
            if eligible and swap_plans:
                st.caption(
                    "Choose an open slot, or move someone already locked in to free a better fit."
                )
            elif swap_plans:
                st.caption(
                    "No open slot fits — move a multi-position player to free a spot for this pick."
                )
            else:
                open_labels = [slot.position or slot.label for slot in eligible]
                st.caption(
                    f"They qualify for **{' / '.join(open_labels)}**. "
                    "Choose a slot, then confirm to continue."
                )
            choice_idx = st.radio(
                f"Pick {pick_index} — how to assign",
                range(len(assignment_options)),
                format_func=lambda i: assignment_options[i][3],
            )
            kind, target, plan, _ = assignment_options[choice_idx]

        assert target is not None
        slot_name = target.position or target.label
        if kind == "swap" and plan is not None:
            submit_label = f"Swap & lock in {player.player_name} at {slot_name}"
        else:
            submit_label = f"Lock in {player.player_name} at {slot_name}"

        submitted = st.form_submit_button(
            submit_label,
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return lineup

    swap_payload = None
    if kind == "swap" and plan is not None:
        swap_payload = {
            "from_slot_id": plan.assign_slot_id,
            "to_slot_id": plan.move_to_slot_id,
        }

    queue_pick_assignment(
        key_prefix=key_prefix,
        pick_index=pick_index,
        slot_id=target.slot_id,
        player=player,
        slot_position=target.position,
        spin=spin,
        swap=swap_payload,
    )
    return lineup


def draftable_players_for_open_slots(
    player_pool: list,
    lineup: Lineup,
    preset: Preset,
    sport: str,
    *,
    include_swap_fits: bool = False,
) -> list:
    """Players who can fill an open slot, or an occupied slot via a position swap."""
    out = players_fitting_open_slots(player_pool, lineup, preset, sport)
    if include_swap_fits:
        seen = {player_pool_key(player) for player in out}
        for player in player_pool:
            key = player_pool_key(player)
            if key in seen:
                continue
            if swap_plans_for_new_pick(player, lineup, preset, sport):
                out.append(player)
                seen.add(key)
    return out


def draft_free_build_sequential(
    *,
    sport: str,
    preset,
    lineup: Lineup,
    player_pool: list,
    key_prefix: str,
) -> Lineup:
    """Full pool; pick a player, then assign to any open slot they qualify for."""
    lineup = apply_pending_position_swap(lineup, preset, key_prefix)
    lineup = apply_pending_pick(
        key_prefix=key_prefix,
        preset=preset,
        lineup=lineup,
        player_pool=player_pool,
    )
    filled = lineup_filled_count(lineup)
    lineup = render_lineup_progress(lineup, preset, key_prefix=key_prefix)
    filled = lineup_filled_count(lineup)

    if filled >= preset.slot_count:
        return lineup

    pick_index = filled + 1
    open = open_slots(lineup, preset)
    pick_pool = draftable_players_for_open_slots(
        player_pool,
        lineup,
        preset,
        sport,
        include_swap_fits=sport == "nba" and position_swaps_enabled(),
    )
    open_label = ", ".join(slot.position or slot.label for slot in open)

    st.markdown(f"### Pick {pick_index}")
    st.caption(
        f"{len(pick_pool)} players can fill an open slot ({open_label} open). "
        "Pick a player, confirm their slot, then move to the next pick."
    )

    if not pick_pool:
        st.warning("No players left who fit the open position slots.")
        return lineup

    return pick_spin_round_picker(
        sport=sport,
        preset=preset,
        lineup=lineup,
        spin_pool=pick_pool,
        pick_index=pick_index,
        key_prefix=key_prefix,
        spin=None,
    )


def draft_spin_lineup_sequential(
    *,
    sport: str,
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
    lineup = apply_pending_position_swap(lineup, preset, key_prefix)
    lineup = apply_pending_pick(
        key_prefix=key_prefix,
        preset=preset,
        lineup=lineup,
        player_pool=player_pool,
    )
    filled = lineup_filled_count(lineup)
    lineup = render_lineup_progress(lineup, preset, key_prefix=key_prefix)
    filled = lineup_filled_count(lineup)

    if filled >= preset.slot_count:
        return lineup

    pick_index = filled + 1
    slot = preset.slots[pick_index - 1]
    phase_caption = offense_first_phase_caption(lineup, preset)
    spin_pool, spin = spin_pool_for_pick(
        pick_index=pick_index,
        build_mode=build_mode,
        sport=sport,
        preset=preset,
        slot=slot,
        player_pool=player_pool,
        key_prefix=key_prefix,
        spins=spins,
        lineup=lineup,
    )

    if spin is not None and spin_pool is not None:
        st.markdown(f"### Pick {pick_index}")
        seeded_spin = (
            spins[pick_index - 1]
            if spins and pick_index <= len(spins)
            else None
        )
        spin_note = ""
        if (
            seeded_spin is not None
            and (seeded_spin.team_abbr, seeded_spin.era_label)
            != (spin.team_abbr, spin.era_label)
        ):
            spin_note = " (adjusted for open slots)"
        caption = (
            f"**{spin.team_name}** · {spin.era_label}{spin_note} · "
            f"{len(spin_pool)} players available. "
            "Future picks stay hidden — make the best call you can with what you know now."
        )
        if phase_caption:
            caption = f"{phase_caption} · {caption}"
        st.caption(caption)
    elif build_mode == BUILD_MODE_PICK and pick_index <= preset.slot_count:
        st.markdown(f"### Pick {pick_index}")
        pick_caption = "Choose team and decade for this pick, then draft a player into an open position slot."
        if phase_caption:
            pick_caption = f"{phase_caption} · {pick_caption}"
        st.caption(pick_caption)

    if spin_pool:
        pick_pool = draftable_players_for_open_slots(
            spin_pool,
            lineup,
            preset,
            sport,
            include_swap_fits=sport == "nba" and position_swaps_enabled(),
        )
        if not pick_pool:
            open_label = ", ".join(slot.position or slot.label for slot in open_slots(lineup, preset))
            st.warning(
                f"No players in this spin pool fit the open position slots ({open_label}). "
                "Try a different team/decade or reset the draft."
            )
        else:
            lineup = pick_spin_round_picker(
                sport=sport,
                preset=preset,
                lineup=lineup,
                spin_pool=pick_pool,
                pick_index=pick_index,
                key_prefix=key_prefix,
                spin=spin,
            )
    return lineup


def draft_compare_spin_lineups(
    *,
    sport: str,
    preset,
    lineup_a: Lineup,
    lineup_b: Lineup,
    build_mode: str,
    player_pool: list,
    side_a_key: str,
    side_b_key: str,
    shared_key: str,
    seed_spins: list[SpinConstraint] | None = None,
) -> tuple[Lineup, Lineup]:
    """Same spin constraint for both lineups; each side drafts independently."""
    lineup_a = apply_pending_position_swap(lineup_a, preset, side_a_key)
    lineup_b = apply_pending_position_swap(lineup_b, preset, side_b_key)
    lineup_a = apply_pending_pick(
        key_prefix=side_a_key,
        preset=preset,
        lineup=lineup_a,
        player_pool=player_pool,
    )
    lineup_b = apply_pending_pick(
        key_prefix=side_b_key,
        preset=preset,
        lineup=lineup_b,
        player_pool=player_pool,
    )

    filled_a = lineup_filled_count(lineup_a)
    filled_b = lineup_filled_count(lineup_b)
    pick_index = min(filled_a, filled_b) + 1

    if pick_index <= preset.slot_count:
        slot = preset.slots[pick_index - 1]
        phase_caption_a = offense_first_phase_caption(lineup_a, preset)
        phase_caption_b = offense_first_phase_caption(lineup_b, preset)
        phase_caption = phase_caption_a or phase_caption_b
        spin_pool, spin = spin_pool_for_pick(
            pick_index=pick_index,
            build_mode=build_mode,
            sport=sport,
            preset=preset,
            slot=slot,
            player_pool=player_pool,
            key_prefix=shared_key,
            spins=seed_spins,
            lineup=lineup_a,
        )

        if spin is not None and spin_pool is not None:
            st.markdown(f"### Pick {pick_index}")
            caption = (
                f"**{spin.team_name}** · {spin.era_label} · {len(spin_pool)} players. "
                "Both lineups face the same constraint — future picks stay hidden."
            )
            if phase_caption:
                caption = f"{phase_caption} · {caption}"
            st.caption(caption)
        elif build_mode == BUILD_MODE_PICK:
            st.markdown(f"### Pick {pick_index}")
            pick_caption = "Choose one team+decade constraint for both lineups."
            if phase_caption:
                pick_caption = f"{phase_caption} · {pick_caption}"
            st.caption(pick_caption)

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Lineup A")
            lineup_a = render_lineup_progress(lineup_a, preset, key_prefix=side_a_key)
            filled_a = lineup_filled_count(lineup_a)
            if filled_a < pick_index and spin_pool:
                pick_pool = draftable_players_for_open_slots(
                    spin_pool,
                    lineup_a,
                    preset,
                    sport,
                    include_swap_fits=sport == "nba" and position_swaps_enabled(),
                )
                if pick_pool:
                    lineup_a = pick_spin_round_picker(
                        sport=sport,
                        preset=preset,
                        lineup=lineup_a,
                        spin_pool=pick_pool,
                        pick_index=pick_index,
                        key_prefix=side_a_key,
                        spin=spin,
                    )
        with col_b:
            st.subheader("Lineup B")
            lineup_b = render_lineup_progress(lineup_b, preset, key_prefix=side_b_key)
            filled_b = lineup_filled_count(lineup_b)
            if filled_b < pick_index and spin_pool:
                pick_pool = draftable_players_for_open_slots(
                    spin_pool,
                    lineup_b,
                    preset,
                    sport,
                    include_swap_fits=sport == "nba" and position_swaps_enabled(),
                )
                if pick_pool:
                    lineup_b = pick_spin_round_picker(
                        sport=sport,
                        preset=preset,
                        lineup=lineup_b,
                        spin_pool=pick_pool,
                        pick_index=pick_index,
                        key_prefix=side_b_key,
                        spin=spin,
                    )
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Lineup A")
            lineup_a = render_lineup_progress(lineup_a, preset, key_prefix=side_a_key)
        with col_b:
            st.subheader("Lineup B")
            lineup_b = render_lineup_progress(lineup_b, preset, key_prefix=side_b_key)

    return lineup_a, lineup_b


def draft_slot_lineup_sequential(
    *,
    sport: str,
    preset,
    lineup: Lineup,
    key_prefix: str,
    fixed_spins: list[SpinConstraint] | None = None,
    seed_spins: list[SpinConstraint] | None = None,
    build_mode: str = BUILD_MODE_FREE,
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
