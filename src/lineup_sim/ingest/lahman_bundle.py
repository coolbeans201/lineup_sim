"""Build franchise-decade MLB tenure rows from bundled Lahman CSVs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from lineup_sim.ingest.lahman_common import (
    ACTIVE_FRANCHISES,
    APPEARANCE_POSITION_COLS,
    BAT_COUNTING_COLS,
    BUNDLE_DIR,
    DEFAULT_MIN_IP,
    DEFAULT_MIN_PA,
    FRANCHISE_TO_ABBR,
    MLB_LEAGUES,
    PITCH_COUNTING_COLS,
    POSITION_GAME_THRESHOLD,
    lahman_csv_dir,
)
from lineup_sim.sports.mlb.plugin import MLB_TEAMS

ABBR_TO_NAME = {team["abbr"]: team["name"] for team in MLB_TEAMS}


def _num(value: Any) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _player_name(people: pd.DataFrame) -> dict[str, str]:
    names: dict[str, str] = {}
    for row in people.itertuples(index=False):
        first = str(getattr(row, "nameFirst", "") or "").strip()
        last = str(getattr(row, "nameLast", "") or "").strip()
        names[str(row.playerID)] = f"{first} {last}".strip()
    return names


def _team_franchise_lookup(teams: pd.DataFrame) -> pd.DataFrame:
    lookup = teams[["yearID", "teamID", "franchID", "name"]].drop_duplicates()
    lookup = lookup[lookup["franchID"].isin(ACTIVE_FRANCHISES)]
    return lookup


def _attach_franchise(df: pd.DataFrame, team_lookup: pd.DataFrame) -> pd.DataFrame:
    out = df.merge(team_lookup, on=["yearID", "teamID"], how="inner")
    out = out[out["lgID"].isin(MLB_LEAGUES)]
    from lineup_sim.ingest.lahman_common import decade_for_year

    out["decade"] = out["yearID"].apply(lambda y: decade_for_year(int(y)))
    return out


def _sum_counting(group: pd.DataFrame, cols: tuple[str, ...]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for col in cols:
        if col in group.columns:
            totals[col] = float(group[col].fillna(0).sum())
    return totals


def _batting_rate_stats(totals: dict[str, float]) -> dict[str, float]:
    ab = totals.get("AB", 0.0)
    h = totals.get("H", 0.0)
    bb = totals.get("BB", 0.0)
    hbp = totals.get("HBP", 0.0)
    sf = totals.get("SF", 0.0)
    doubles = totals.get("2B", 0.0)
    triples = totals.get("3B", 0.0)
    hr = totals.get("HR", 0.0)

    pa = ab + bb + hbp + sf + totals.get("SH", 0.0)
    avg = h / ab if ab else 0.0
    obp_den = ab + bb + hbp + sf
    obp = (h + bb + hbp) / obp_den if obp_den else 0.0
    slg = (h + doubles + 2 * triples + 3 * hr) / ab if ab else 0.0
    ops = obp + slg

    out = dict(totals)
    out["PA"] = pa
    out["AVG"] = round(avg, 3)
    out["OBP"] = round(obp, 3)
    out["SLG"] = round(slg, 3)
    out["OPS"] = round(ops, 3)
    return out


def _pitching_rate_stats(totals: dict[str, float]) -> dict[str, float]:
    ip_outs = totals.get("IPouts", 0.0)
    ip = ip_outs / 3.0
    er = totals.get("ER", 0.0)
    h = totals.get("H", 0.0)
    bb = totals.get("BB", 0.0)

    era = (er / ip * 9.0) if ip else 0.0
    whip = (h + bb) / ip if ip else 0.0

    out = dict(totals)
    out["IP"] = round(ip, 1)
    out["ERA"] = round(era, 2)
    out["WHIP"] = round(whip, 2)
    out["K"] = totals.get("SO", 0.0)
    return out


def _eligible_bat_positions(pos_games: dict[str, float], *, has_batting: bool) -> list[str]:
    positions: list[str] = []
    for pos, games in pos_games.items():
        if games >= POSITION_GAME_THRESHOLD:
            positions.append(pos)
    if not positions and pos_games.get("OF", 0.0) >= POSITION_GAME_THRESHOLD:
        positions.append("OF")
    if has_batting:
        positions.append("DH")
    # Stable order for display.
    order = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "OF", "DH"]
    return [pos for pos in order if pos in positions]


def _pitch_positions(totals: dict[str, float]) -> tuple[str, list[str]]:
    gs = totals.get("GS", 0.0)
    g = totals.get("G", 0.0)
    sv = totals.get("SV", 0.0)
    relief_g = max(g - gs, 0.0)

    positions: list[str] = []
    if gs >= 5:
        positions.append("SP")
    if sv > 0 or relief_g >= 5:
        positions.append("RP")
    if not positions and g > 0:
        positions.append("RP" if gs < g else "SP")

    primary = "SP"
    if sv >= gs and sv > 0:
        primary = "RP"
    elif positions == ["RP"]:
        primary = "RP"
    return primary, positions


def _position_label(positions: list[str]) -> str:
    if not positions:
        return ""
    if len(positions) == 1:
        return positions[0]
    return "/".join(positions)


def _aggregate_appearances(app: pd.DataFrame, team_lookup: pd.DataFrame) -> pd.DataFrame:
    merged = _attach_franchise(app, team_lookup)
    grouped = merged.groupby(["playerID", "franchID", "decade"], as_index=False)
    rows: list[dict[str, Any]] = []
    for keys, chunk in grouped:
        player_id, franch_id, decade = keys
        pos_games: dict[str, float] = {}
        for pos, col in APPEARANCE_POSITION_COLS.items():
            if col in chunk.columns:
                pos_games[pos] = float(chunk[col].fillna(0).sum())
        if "G_of" in chunk.columns:
            pos_games["OF"] = float(chunk["G_of"].fillna(0).sum())
        else:
            pos_games["OF"] = 0.0
        rows.append(
            {
                "playerID": player_id,
                "franchID": franch_id,
                "decade": decade,
                "pos_games": pos_games,
            }
        )
    return pd.DataFrame(rows)


def build_tenure_rows(
    *,
    min_pa: int = DEFAULT_MIN_PA,
    min_ip: float = DEFAULT_MIN_IP,
    lahman_dir: Path | None = None,
) -> list[dict[str, Any]]:
    csv_dir = lahman_dir or lahman_csv_dir()
    batting = pd.read_csv(csv_dir / "Batting.csv")
    pitching = pd.read_csv(csv_dir / "Pitching.csv")
    appearances = pd.read_csv(csv_dir / "Appearances.csv")
    teams = pd.read_csv(csv_dir / "Teams.csv")
    people = pd.read_csv(csv_dir / "People.csv")

    names = _player_name(people)
    team_lookup = _team_franchise_lookup(teams)
    appearance_agg = _aggregate_appearances(appearances, team_lookup)
    appearance_map = {
        (row.playerID, row.franchID, row.decade): row.pos_games
        for row in appearance_agg.itertuples(index=False)
    }

    rows: list[dict[str, Any]] = []

    bat_merged = _attach_franchise(batting, team_lookup)
    for keys, group in bat_merged.groupby(["playerID", "franchID", "decade"]):
        player_id, franch_id, decade = keys
        totals = _sum_counting(group, BAT_COUNTING_COLS)
        pa = (
            totals.get("AB", 0.0)
            + totals.get("BB", 0.0)
            + totals.get("HBP", 0.0)
            + totals.get("SF", 0.0)
            + totals.get("SH", 0.0)
        )
        if pa < min_pa:
            continue

        stats = _batting_rate_stats(totals)
        seasons = sorted(int(y) for y in group["yearID"].unique())
        pos_games = appearance_map.get((player_id, franch_id, decade), {})
        positions = _eligible_bat_positions(pos_games, has_batting=True)
        primary = positions[0] if positions else "DH"
        if pos_games:
            field_positions = [p for p in positions if p != "DH"]
            if field_positions:
                primary = max(
                    field_positions,
                    key=lambda p: pos_games.get(p, pos_games.get("OF", 0.0)),
                )

        abbr = FRANCHISE_TO_ABBR[franch_id]
        rows.append(
            {
                "player_id": player_id,
                "player_name": names.get(player_id, player_id),
                "franchise_id": franch_id,
                "team_abbr": abbr,
                "team": ABBR_TO_NAME.get(abbr, str(group["name"].iloc[-1])),
                "decade": decade,
                "season": seasons[-1],
                "seasons_with_team": seasons,
                "role": "bat",
                "position": primary,
                "position_raw": _position_label(positions),
                "positions": positions,
                "stats": stats,
            }
        )

    pit_merged = _attach_franchise(pitching, team_lookup)
    for keys, group in pit_merged.groupby(["playerID", "franchID", "decade"]):
        player_id, franch_id, decade = keys
        totals = _sum_counting(group, PITCH_COUNTING_COLS)
        ip = totals.get("IPouts", 0.0) / 3.0
        if ip < min_ip:
            continue

        stats = _pitching_rate_stats(totals)
        seasons = sorted(int(y) for y in group["yearID"].unique())
        primary, positions = _pitch_positions(totals)
        abbr = FRANCHISE_TO_ABBR[franch_id]
        rows.append(
            {
                "player_id": player_id,
                "player_name": names.get(player_id, player_id),
                "franchise_id": franch_id,
                "team_abbr": abbr,
                "team": ABBR_TO_NAME.get(abbr, str(group["name"].iloc[-1])),
                "decade": decade,
                "season": seasons[-1],
                "seasons_with_team": seasons,
                "role": "pitch",
                "position": primary,
                "position_raw": _position_label(positions),
                "positions": positions,
                "stats": stats,
            }
        )

    return rows


def import_tenures_to_bundle(
    *,
    min_pa: int = DEFAULT_MIN_PA,
    min_ip: float = DEFAULT_MIN_IP,
    lahman_dir: Path | None = None,
    output_path: Path | None = None,
) -> list[dict[str, Any]]:
    rows = build_tenure_rows(min_pa=min_pa, min_ip=min_ip, lahman_dir=lahman_dir)
    out_path = output_path or (BUNDLE_DIR / "tenures.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    return rows


def pool_for_franchise_decade(
    rows: list[dict[str, Any]],
    *,
    team_abbr: str,
    decade: str,
) -> list[dict[str, Any]]:
    abbr = team_abbr.upper()
    return [r for r in rows if r["team_abbr"].upper() == abbr and r["decade"] == decade]


def spike_report(
    rows: list[dict[str, Any]],
    *,
    min_pa: int,
    min_ip: float,
) -> str:
    by_key: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["team_abbr"], row["decade"])
        by_key[key] = by_key.get(key, 0) + 1

    lines = [
        f"Total tenure rows: {len(rows)}",
        f"Filters: min_pa={min_pa}, min_ip={min_ip}",
        f"Unique franchise-decades: {len(by_key)}",
        "",
        "Sample spin pools:",
    ]
    for team_abbr, decade in [("NYY", "1990s"), ("LAD", "2000s"), ("BOS", "1970s")]:
        pool = pool_for_franchise_decade(rows, team_abbr=team_abbr, decade=decade)
        bat = [r for r in pool if r["role"] == "bat"]
        pitch = [r for r in pool if r["role"] == "pitch"]
        lines.append(
            f"  {team_abbr} {decade}: {len(pool)} total ({len(bat)} bat, {len(pitch)} pitch)"
        )
        for sample in pool[:3]:
            lines.append(
                f"    - {sample['player_name']} ({sample['role']}, {sample['position_raw']}) "
                f"seasons {sample['seasons_with_team'][0]}-{sample['seasons_with_team'][-1]} "
                f"OPS={sample['stats'].get('OPS', sample['stats'].get('ERA', 'n/a'))}"
            )

    counts = sorted(by_key.items(), key=lambda item: item[1], reverse=True)
    lines.extend(["", "Largest pools (top 5):"])
    for (abbr, decade), count in counts[:5]:
        lines.append(f"  {abbr} {decade}: {count}")
    lines.extend(["", "Smallest pools (bottom 5):"])
    for (abbr, decade), count in counts[-5:]:
        lines.append(f"  {abbr} {decade}: {count}")
    return "\n".join(lines)
