"""What-if lineup comparison."""

from __future__ import annotations

from dataclasses import dataclass

from lineup_sim.core.models import Lineup, ScoreResult
from lineup_sim.core.scoring import score_lineup
from lineup_sim.sports.registry import get_sport_plugin


@dataclass
class CompareRow:
    slot_id: str
    slot_label: str
    lineup_a_player: str | None
    lineup_b_player: str | None
    rating_a: float | None
    rating_b: float | None
    rating_delta: float | None


@dataclass
class CompareResult:
    score_a: ScoreResult
    score_b: ScoreResult
    rating_delta: float
    wins_delta: float
    grade_a: str
    grade_b: str
    rows: list[CompareRow]
    category_deltas: dict[str, float]
    winner: str


def compare_lineups(lineup_a: Lineup, lineup_b: Lineup) -> CompareResult:
    plugin = get_sport_plugin(lineup_a.sport)
    cohort = plugin.load_player_pool()
    score_a = score_lineup(lineup_a, cohort)
    score_b = score_lineup(lineup_b, cohort)

    from lineup_sim.core.presets import get_preset

    preset = get_preset(lineup_a.preset_slug)
    slot_labels = {s.slot_id: s.label for s in preset.slots}
    ratings_a = {r.slot_id: r.slot_rating for r in score_a.player_ratings}
    ratings_b = {r.slot_id: r.slot_rating for r in score_b.player_ratings}

    players_a = {a.slot_id: a.player.player_name if a.player else None for a in lineup_a.assignments}
    players_b = {a.slot_id: a.player.player_name if a.player else None for a in lineup_b.assignments}

    rows: list[CompareRow] = []
    for slot in preset.slots:
        ra = ratings_a.get(slot.slot_id)
        rb = ratings_b.get(slot.slot_id)
        rows.append(
            CompareRow(
                slot_id=slot.slot_id,
                slot_label=slot.label,
                lineup_a_player=players_a.get(slot.slot_id),
                lineup_b_player=players_b.get(slot.slot_id),
                rating_a=ra,
                rating_b=rb,
                rating_delta=(ra - rb) if ra is not None and rb is not None else None,
            )
        )

    category_deltas = {
        stat: score_a.category_totals.get(stat, 0.0) - score_b.category_totals.get(stat, 0.0)
        for stat in preset.stat_weights
    }

    if score_a.team_rating > score_b.team_rating:
        winner = lineup_a.label
    elif score_b.team_rating > score_a.team_rating:
        winner = lineup_b.label
    else:
        winner = "Tie"

    return CompareResult(
        score_a=score_a,
        score_b=score_b,
        rating_delta=round(score_a.team_rating - score_b.team_rating, 3),
        wins_delta=round(score_a.projected_wins - score_b.projected_wins, 1),
        grade_a=score_a.grade,
        grade_b=score_b.grade,
        rows=rows,
        category_deltas=category_deltas,
        winner=winner,
    )
