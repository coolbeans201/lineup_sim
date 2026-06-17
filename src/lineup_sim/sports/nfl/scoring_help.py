"""User-facing NFL scoring help — aligned with 20-0.com philosophy where applicable."""

from __future__ import annotations

from lineup_sim.core.models import Preset

_POSITION_ROLE_NOTES: dict[str, str] = {
    "QB": "Passing production and efficiency (yards, TDs) plus rushing.",
    "RB": "Total yards and touchdowns on the ground and through the air.",
    "WR": "Receiving production and touchdowns.",
    "TE": "Receiving production and touchdowns.",
    "FLEX": "RB/WR/TE scoring depending on who you slot.",
    "EDGE": "Getting to the quarterback — sacks, tackles, and takeaways.",
    "DT": "Interior disruption — sacks, tackles, and takeaways.",
    "LB": "Tackling, pass rush, and coverage takeaways.",
    "CB": "Coverage takeaways (interceptions) plus tackling.",
    "S": "Coverage takeaways plus tackling.",
    "D-FLEX": "EDGE/DT/LB/CB/S scoring depending on who you slot.",
}


def position_weight_summary(preset: Preset) -> list[str]:
    """Premium position multipliers for team rating (mirrors 20-0 two-way weights)."""
    weights = preset.position_weights
    if not weights:
        return ["Every starter counts equally (1.0×)."]
    premium = sorted(
        ((pos, w) for pos, w in weights.items() if w != 1.0),
        key=lambda item: (-item[1], item[0]),
    )
    if not premium:
        return ["Every starter counts equally (1.0×)."]
    lines = [f"{pos} {w:g}×" for pos, w in premium]
    lines.append("everyone else 1.0×")
    return lines


def position_role_notes(preset: Preset) -> list[str]:
    """What each roster spot rewards — qualitative, like 20-0's position blurbs."""
    seen: set[str] = set()
    lines: list[str] = []
    for slot in preset.slots:
        pos = slot.position or slot.label
        if pos in seen:
            continue
        note = _POSITION_ROLE_NOTES.get(pos)
        if not note:
            continue
        seen.add(pos)
        lines.append(f"{pos}: {note}")
    return lines


def nfl_formula_notes(preset: Preset, *, rating_baseline: float) -> list[str]:
    """Scoring explainer bullets for the UI and share breakdown."""
    notes = [
        "Era-relative context: Composite Z judges each pick against position/season peers, "
        "so a 1970s great can stand shoulder to shoulder with a modern one.",
        "Unlike 20-0.com, this sim shows slot ratings and the full math — use stats, season, "
        "and Composite Z together to read each pick.",
        "Your projected record is the position-weighted strength of all starters. Premium spots count more:",
    ]
    for line in position_weight_summary(preset):
        notes.append(f"  · {line}")
    notes.append(
        f"Balance is everything: a single weak spot drags the average down "
        f"(penalty = {preset.balance_penalty:g} × mean − weakest slot). "
        "Only a near-flawless roster runs the table."
    )
    notes.append(
        "Slot rating = per-game stat composite × position weight. "
        "Impact plays matter most — touchdowns, sacks, and interceptions carry extra weight. "
        "Offense uses fantasy scaling (pass yds 0.04/pt, rush/rec yds 0.1/pt, pass TD 4, rush/rec TD 6). "
        "Defense uses sacks, tackles, and interceptions."
    )
    notes.append("What each spot rewards:")
    for line in position_role_notes(preset):
        notes.append(f"  · {line}")
    notes.append(
        "Pre-1999 seasons lean on PFR box-score imports (offense plus optional curated defense); "
        "1999+ uses nflverse. Era peers in the pool keep cross-decade picks comparable."
    )
    notes.append(
        f"Projected wins = logistic(team_rating − {rating_baseline:.1f} pool median) × "
        f"{preset.max_games} games."
    )
    return notes
