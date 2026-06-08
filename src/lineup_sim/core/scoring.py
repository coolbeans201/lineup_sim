"""Transparent scoring engine — wins from raw stats, z-scores for context."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd

from lineup_sim.core.models import (
    Lineup,
    PlayerRating,
    PlayerSeason,
    Preset,
    RosterSlot,
    ScoreResult,
)
from lineup_sim.core.presets import get_preset
from lineup_sim.core.stat_labels import integer_record
from lineup_sim.sports.registry import get_sport_plugin


def _cohort_frame(players: Iterable[PlayerSeason], sport: str) -> pd.DataFrame:
    rows = []
    for p in players:
        row = {
            "player_id": p.player_id,
            "season": p.season,
            "decade": p.decade,
            "position": p.position,
            **p.stats,
        }
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _z(value: float, mean: float, std: float) -> float:
    if std <= 1e-9:
        return 0.0
    return (value - mean) / std


def preset_weighted_composite(player: PlayerSeason, preset: Preset) -> float:
    """Weighted sum from preset stat_weights (no sport-specific overrides)."""
    plugin = get_sport_plugin(preset.sport)
    weighted = 0.0
    total_w = 0.0

    for stat, weight in preset.stat_weights.items():
        if stat not in player.stats:
            continue
        effective_weight = weight * plugin.stat_tracking_factor(player, stat)
        if effective_weight <= 0:
            continue
        direction = plugin.stat_direction(stat)
        weighted += player.stats[stat] * effective_weight * direction
        total_w += effective_weight

    return weighted / total_w if total_w else 0.0


def player_stat_composite(player: PlayerSeason, preset: Preset) -> float:
    """Weighted average of raw per-game stats (the score that drives wins)."""
    plugin = get_sport_plugin(preset.sport)
    custom = plugin.stat_composite(player, preset)
    if custom is not None:
        return custom
    return preset_weighted_composite(player, preset)


def player_composite_z(
    player: PlayerSeason,
    preset: Preset,
    cohort: pd.DataFrame,
) -> tuple[float, dict[str, float]]:
    """Era-relative z-scores vs position/season peers — display context only."""
    plugin = get_sport_plugin(preset.sport)
    weights = preset.stat_weights
    stat_zs: dict[str, float] = {}
    weighted = 0.0
    total_w = 0.0

    cohort_slice = plugin.cohort_slice(cohort, player)

    for stat, weight in weights.items():
        if stat not in player.stats:
            continue
        effective_weight = weight * plugin.stat_tracking_factor(player, stat)
        if effective_weight <= 0:
            continue
        if stat not in cohort_slice.columns or cohort_slice.empty:
            stat_zs[stat] = 0.0
            continue
        mean = float(cohort_slice[stat].mean())
        std = float(cohort_slice[stat].std(ddof=0))
        direction = plugin.stat_direction(stat)
        z = _z(player.stats[stat], mean, std) * direction
        stat_zs[stat] = z
        weighted += z * effective_weight
        total_w += effective_weight

    composite = weighted / total_w if total_w else 0.0
    return composite, stat_zs


def _slot_weight(slot: RosterSlot, preset: Preset) -> float:
    pos_weight = preset.position_weights.get(slot.position or "", 1.0)
    return slot.weight * pos_weight


def _median_slot_rating(
    players: Iterable[PlayerSeason],
    preset: Preset,
    slot: RosterSlot,
) -> float | None:
    from lineup_sim.core.constraints import eligible_for_slot

    values = [
        player_stat_composite(player, preset) * _slot_weight(slot, preset)
        for player in players
        if eligible_for_slot(player, slot, preset.sport)
    ]
    if not values:
        return None
    return float(np.median(values))


def _estimated_lineup_rating_baseline(players: list[PlayerSeason], preset: Preset) -> float:
    """Typical team rating if every slot drew a median pool player at that position."""
    slot_medians: list[float] = []
    slot_weights: list[float] = []
    for slot in preset.slots:
        median_rating = _median_slot_rating(players, preset, slot)
        if median_rating is None:
            continue
        slot_medians.append(median_rating)
        slot_weights.append(_slot_weight(slot, preset))
    if not slot_medians:
        return 0.0
    return float(np.average(slot_medians, weights=slot_weights))


def _pool_rating_baseline(players: list[PlayerSeason], preset: Preset) -> float:
    if preset.sport == "nfl":
        return _estimated_lineup_rating_baseline(players, preset)
    if preset.rating_baseline is not None:
        return preset.rating_baseline
    composites = [player_stat_composite(p, preset) for p in players]
    if not composites:
        return 0.0
    return float(np.median(composites))


def projected_wins(
    team_rating: float,
    max_games: int,
    *,
    baseline: float,
    slope: float,
) -> float:
    """Logistic curve anchored so an average-stat lineup projects ~.500 ball."""
    win_pct = win_pct_from_rating(team_rating, baseline=baseline, slope=slope)
    return round(win_pct * max_games, 1)


def win_pct_from_rating(team_rating: float, *, baseline: float, slope: float) -> float:
    return 1.0 / (1.0 + math.exp(-slope * (team_rating - baseline)))


def rating_for_win_pct(target_win_pct: float, *, baseline: float, slope: float) -> float:
    if target_win_pct <= 0.0 or target_win_pct >= 1.0:
        return float("inf")
    return baseline - math.log(1.0 / target_win_pct - 1.0) / slope


def _build_record_notes(
    *,
    preset: Preset,
    raw_mean: float,
    team_rating: float,
    balance_adj: float,
    weakest: PlayerRating,
    wins: float,
    losses: float,
    win_pct: float,
    rating_baseline: float,
) -> list[str]:
    wins_no_penalty = projected_wins(
        raw_mean,
        preset.max_games,
        baseline=rating_baseline,
        slope=preset.win_rating_slope,
    )
    wins_int, losses_int = integer_record(wins, preset.max_games)
    near_perfect = max(preset.max_games - 2, preset.max_games * 0.9)
    rating_near_perfect = rating_for_win_pct(
        near_perfect / preset.max_games,
        baseline=rating_baseline,
        slope=preset.win_rating_slope,
    )
    notes = [
        f"Mean stat score (before balance): {raw_mean:.2f}",
        (
            f"Weakest link: {weakest.player.player_name} ({weakest.slot_rating:.2f}) "
            f"→ balance penalty −{balance_adj:.2f}"
        ),
        f"Team rating: {raw_mean:.2f} − {balance_adj:.2f} = {team_rating:.2f}",
        (
            f"Win rate: {win_pct * 100:.1f}% from a logistic curve vs pool median baseline "
            f"({rating_baseline:.1f})"
        ),
        f"Projected: {wins_int}-{losses_int} over {preset.max_games} games",
    ]
    if balance_adj > 0.01:
        notes.append(f"Without balance penalty this lineup would project ~{wins_no_penalty:.0f} wins.")
    notes.append(
        f"A {near_perfect:.0f}-{preset.max_games - near_perfect:.0f} pace needs team rating "
        f"~{rating_near_perfect:.1f} on this curve."
    )
    notes.append(
        "Games like 82-0 treat peak-all-time rosters as undefeated. This sim deliberately caps win rate below "
        "100%, so even S+ teams can show a few projected losses."
    )
    return notes


def _formula_notes(preset: Preset, rating_baseline: float) -> list[str]:
    notes = [
        "Slot rating = weighted raw per-game stats × slot/position weight.",
        "Composite Z = era-relative context vs position/season peers (display only).",
        f"Balance penalty = {preset.balance_penalty} × (mean − weakest slot).",
        f"Projected wins = logistic(team_rating − {rating_baseline:.1f} pool median) × season length.",
    ]
    if preset.sport == "nba":
        notes.append(
            "STL/BLK are omitted from scoring for seasons before 1973-74 (not tracked on Basketball Reference)."
        )
    if preset.sport == "nfl":
        notes.append(
            "Offense uses per-game fantasy scaling (pass yards 0.04/pt, rush/rec yards 0.1/pt, "
            "pass TD 4, rush/rec TD 6). Defense uses sacks, tackles, and interceptions."
        )
        notes.append(
            "NFL win curve baseline is the weighted median slot rating across the player pool "
            "(a typical lineup projects near .500)."
        )
    return notes


def grade_from_rating(team_rating: float, preset: Preset) -> str:
    thresholds = preset.grade_thresholds or {
        "S+": 11.0,
        "A+": 9.0,
        "A": 7.0,
        "B": 5.0,
        "C": 4.0,
        "D": 2.5,
    }
    ordered = sorted(thresholds.items(), key=lambda kv: kv[1], reverse=True)
    for label, cutoff in ordered:
        if team_rating >= cutoff:
            return label
    return "F"


def score_lineup(
    lineup: Lineup,
    cohort: list[PlayerSeason] | None = None,
) -> ScoreResult:
    preset = get_preset(lineup.preset_slug)
    plugin = get_sport_plugin(preset.sport)
    pool = cohort or plugin.load_player_pool()
    cohort_df = _cohort_frame(pool, preset.sport)
    rating_baseline = _pool_rating_baseline(pool, preset)

    slot_map = {s.slot_id: s for s in preset.slots}
    ratings: list[PlayerRating] = []
    category_totals: dict[str, float] = {k: 0.0 for k in preset.stat_weights}

    for assignment in lineup.assignments:
        if assignment.player is None:
            continue
        player = assignment.player
        stat_score = player_stat_composite(player, preset)
        composite_z, stat_zs = player_composite_z(player, preset, cohort_df)
        slot = slot_map[assignment.slot_id]
        slot_rating = stat_score * _slot_weight(slot, preset)
        ratings.append(
            PlayerRating(
                player=player,
                slot_id=assignment.slot_id,
                composite_z=composite_z,
                slot_rating=slot_rating,
                stat_zs=stat_zs,
            )
        )
        for stat, value in player.stats.items():
            if stat in category_totals:
                category_totals[stat] += value

    if not ratings:
        return ScoreResult(
            team_rating=0.0,
            projected_wins=0.0,
            projected_losses=float(preset.max_games),
            max_games=preset.max_games,
            grade="F",
            player_ratings=[],
            category_totals=category_totals,
            weakest_slot_id=None,
            balance_adjustment=0.0,
            formula_notes=[
                "Slot rating = weighted raw per-game stats × slot/position weight.",
                "Composite Z = era-relative context vs position/season peers (display only).",
                "Team rating = weighted mean slot ratings minus balance penalty for weak slot.",
            ],
        )

    weights = [_slot_weight(slot_map[r.slot_id], preset) for r in ratings]
    raw_mean = float(np.average([r.slot_rating for r in ratings], weights=weights))
    weakest = min(ratings, key=lambda r: r.slot_rating)
    balance_adj = preset.balance_penalty * max(0.0, raw_mean - weakest.slot_rating)
    team_rating = raw_mean - balance_adj

    wins = projected_wins(
        team_rating,
        preset.max_games,
        baseline=rating_baseline,
        slope=preset.win_rating_slope,
    )
    wins_int, losses_int = integer_record(wins, preset.max_games)
    losses = float(losses_int)
    win_pct = win_pct_from_rating(
        team_rating,
        baseline=rating_baseline,
        slope=preset.win_rating_slope,
    )

    return ScoreResult(
        team_rating=round(team_rating, 3),
        projected_wins=wins,
        projected_losses=losses,
        max_games=preset.max_games,
        grade=grade_from_rating(team_rating, preset),
        player_ratings=ratings,
        category_totals={k: round(v, 2) for k, v in category_totals.items()},
        weakest_slot_id=weakest.slot_id,
        balance_adjustment=round(balance_adj, 3),
        win_pct=round(win_pct, 4),
        record_notes=_build_record_notes(
            preset=preset,
            raw_mean=raw_mean,
            team_rating=team_rating,
            balance_adj=balance_adj,
            weakest=weakest,
            wins=wins,
            losses=losses,
            win_pct=win_pct,
            rating_baseline=rating_baseline,
        ),
        formula_notes=_formula_notes(preset, rating_baseline),
    )
