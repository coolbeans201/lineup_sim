"""Generate historical NBA fixture JSON from curated season peaks (BRef-sourced stats)."""

from __future__ import annotations

import json
from pathlib import Path

# Peak regular-season per-game lines (Basketball Reference). STL/BLK 0.0 before 1973-74.
ROWS: list[dict] = [
    # 1960s · mostly C/PF/G
    {"player_name": "Wilt Chamberlain", "team_abbr": "GSW", "team": "Philadelphia Warriors", "season": 1962, "position": "C", "stats": {"PTS": 50.4, "REB": 25.7, "AST": 2.4, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Wilt Chamberlain", "team_abbr": "PHI", "team": "Philadelphia 76ers", "season": 1967, "position": "C", "stats": {"PTS": 24.1, "REB": 24.2, "AST": 7.8, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Bill Russell", "team_abbr": "BOS", "team": "Boston Celtics", "season": 1964, "position": "C", "stats": {"PTS": 15.0, "REB": 24.7, "AST": 4.7, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Wilt Chamberlain", "team_abbr": "PHI", "team": "Philadelphia 76ers", "season": 1968, "position": "C", "stats": {"PTS": 24.3, "REB": 23.8, "AST": 8.6, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Walt Bellamy", "team_abbr": "DET", "team": "Detroit Pistons", "season": 1962, "position": "C", "stats": {"PTS": 31.6, "REB": 19.0, "AST": 2.2, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Oscar Robertson", "team_abbr": "SAC", "team": "Cincinnati Royals", "season": 1965, "position": "PG", "position_raw": "PG-SG", "stats": {"PTS": 30.4, "REB": 10.4, "AST": 11.5, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Jerry West", "team_abbr": "LAL", "team": "Los Angeles Lakers", "season": 1965, "position": "SG", "stats": {"PTS": 31.0, "REB": 4.3, "AST": 5.1, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Elgin Baylor", "team_abbr": "LAL", "team": "Los Angeles Lakers", "season": 1963, "position": "SF", "stats": {"PTS": 34.0, "REB": 14.3, "AST": 4.8, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Bob Pettit", "team_abbr": "ATL", "team": "St. Louis Hawks", "season": 1962, "position": "PF", "stats": {"PTS": 31.1, "REB": 18.7, "AST": 3.4, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Willis Reed", "team_abbr": "NYK", "team": "New York Knicks", "season": 1970, "position": "C", "stats": {"PTS": 21.7, "REB": 13.9, "AST": 2.0, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "John Havlicek", "team_abbr": "BOS", "team": "Boston Celtics", "season": 1969, "position": "SF", "stats": {"PTS": 21.6, "REB": 7.0, "AST": 4.7, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Rick Barry", "team_abbr": "GSW", "team": "San Francisco Warriors", "season": 1967, "position": "SF", "stats": {"PTS": 35.6, "REB": 9.2, "AST": 3.5, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Hal Greer", "team_abbr": "PHI", "team": "Philadelphia 76ers", "season": 1968, "position": "SG", "stats": {"PTS": 24.1, "REB": 5.4, "AST": 4.5, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Lenny Wilkens", "team_abbr": "ATL", "team": "St. Louis Hawks", "season": 1968, "position": "PG", "stats": {"PTS": 19.4, "REB": 4.7, "AST": 8.2, "STL": 0.0, "BLK": 0.0}},
    {"player_name": "Dave DeBusschere", "team_abbr": "NYK", "team": "New York Knicks", "season": 1968, "position": "PF", "stats": {"PTS": 17.7, "REB": 13.0, "AST": 2.9, "STL": 0.0, "BLK": 0.0}},

    # 1970s
    {"player_name": "Kareem Abdul-Jabbar", "team_abbr": "MIL", "team": "Milwaukee Bucks", "season": 1972, "position": "C", "stats": {"PTS": 34.8, "REB": 16.6, "AST": 4.6, "STL": 1.2, "BLK": 4.6}},
    {"player_name": "Kareem Abdul-Jabbar", "team_abbr": "LAL", "team": "Los Angeles Lakers", "season": 1977, "position": "C", "stats": {"PTS": 26.2, "REB": 13.3, "AST": 3.9, "STL": 1.2, "BLK": 3.2}},
    {"player_name": "Julius Erving", "team_abbr": "PHI", "team": "Philadelphia 76ers", "season": 1976, "position": "SF", "stats": {"PTS": 29.3, "REB": 11.0, "AST": 5.0, "STL": 2.5, "BLK": 1.8}},
    {"player_name": "Bill Walton", "team_abbr": "POR", "team": "Portland Trail Blazers", "season": 1978, "position": "C", "stats": {"PTS": 18.9, "REB": 13.2, "AST": 5.0, "STL": 1.0, "BLK": 2.5}},
    {"player_name": "Rick Barry", "team_abbr": "GSW", "team": "Golden State Warriors", "season": 1975, "position": "SF", "stats": {"PTS": 30.6, "REB": 5.7, "AST": 6.2, "STL": 2.9, "BLK": 0.8}},
    {"player_name": "Moses Malone", "team_abbr": "HOU", "team": "Houston Rockets", "season": 1979, "position": "C", "stats": {"PTS": 24.8, "REB": 17.6, "AST": 1.8, "STL": 1.0, "BLK": 1.5}},
    {"player_name": "George Gervin", "team_abbr": "SAS", "team": "San Antonio Spurs", "season": 1978, "position": "SG", "stats": {"PTS": 27.1, "REB": 5.2, "AST": 2.6, "STL": 1.2, "BLK": 0.7}},
    {"player_name": "Pete Maravich", "team_abbr": "UTA", "team": "New Orleans Jazz", "season": 1977, "position": "SG", "stats": {"PTS": 31.1, "REB": 5.4, "AST": 5.4, "STL": 1.2, "BLK": 0.2}},
    {"player_name": "Bob McAdoo", "team_abbr": "LAC", "team": "Buffalo Braves", "season": 1975, "position": "C", "stats": {"PTS": 34.5, "REB": 14.1, "AST": 2.2, "STL": 1.1, "BLK": 2.1}},
    {"player_name": "Walt Frazier", "team_abbr": "NYK", "team": "New York Knicks", "season": 1975, "position": "PG", "stats": {"PTS": 20.9, "REB": 5.9, "AST": 7.3, "STL": 1.9, "BLK": 0.2}},
    {"player_name": "Bob Lanier", "team_abbr": "DET", "team": "Detroit Pistons", "season": 1974, "position": "C", "stats": {"PTS": 26.1, "REB": 11.5, "AST": 3.0, "STL": 1.0, "BLK": 2.0}},
    {"player_name": "Artis Gilmore", "team_abbr": "CHI", "team": "Chicago Bulls", "season": 1972, "position": "C", "stats": {"PTS": 17.5, "REB": 13.0, "AST": 2.6, "STL": 0.7, "BLK": 2.5}},
    {"player_name": "Dan Issel", "team_abbr": "DEN", "team": "Denver Nuggets", "season": 1977, "position": "PF", "stats": {"PTS": 22.9, "REB": 10.7, "AST": 2.5, "STL": 1.0, "BLK": 0.6}},
    {"player_name": "Billy Knight", "team_abbr": "IND", "team": "Indiana Pacers", "season": 1977, "position": "SF", "stats": {"PTS": 26.6, "REB": 7.5, "AST": 3.7, "STL": 1.3, "BLK": 0.3}},
    {"player_name": "World B Free", "team_abbr": "CLE", "team": "Cleveland Cavaliers", "season": 1979, "position": "SG", "stats": {"PTS": 28.8, "REB": 3.7, "AST": 4.2, "STL": 1.3, "BLK": 0.3}},
    {"player_name": "Elvin Hayes", "team_abbr": "WAS", "team": "Washington Bullets", "season": 1974, "position": "PF", "stats": {"PTS": 21.5, "REB": 12.3, "AST": 2.0, "STL": 1.0, "BLK": 2.4}},
    {"player_name": "Truck Robinson", "team_abbr": "NYK", "team": "New York Knicks", "season": 1978, "position": "PF", "stats": {"PTS": 22.0, "REB": 13.8, "AST": 3.5, "STL": 1.1, "BLK": 0.4}},
    {"player_name": "Bobby Jones", "team_abbr": "PHI", "team": "Philadelphia 76ers", "season": 1979, "position": "PF", "stats": {"PTS": 14.0, "REB": 5.9, "AST": 2.7, "STL": 1.5, "BLK": 1.2}},
    {"player_name": "Marques Johnson", "team_abbr": "MIL", "team": "Milwaukee Bucks", "season": 1979, "position": "SF", "stats": {"PTS": 24.3, "REB": 6.5, "AST": 4.0, "STL": 1.3, "BLK": 0.5}},

    # 1980s
    {"player_name": "Magic Johnson", "team_abbr": "LAL", "team": "Los Angeles Lakers", "season": 1987, "position": "PG", "position_raw": "PG", "decade": "1980s", "stats": {"PTS": 23.9, "REB": 6.3, "AST": 12.2, "STL": 1.7, "BLK": 0.5}},
    {"player_name": "Larry Bird", "team_abbr": "BOS", "team": "Boston Celtics", "season": 1986, "position": "SF", "stats": {"PTS": 25.8, "REB": 9.8, "AST": 6.8, "STL": 1.6, "BLK": 0.6}},
    {"player_name": "Michael Jordan", "team_abbr": "CHI", "team": "Chicago Bulls", "season": 1988, "position": "SG", "stats": {"PTS": 35.0, "REB": 5.5, "AST": 5.9, "STL": 3.2, "BLK": 1.6}},
    {"player_name": "Moses Malone", "team_abbr": "PHI", "team": "Philadelphia 76ers", "season": 1983, "position": "C", "stats": {"PTS": 24.5, "REB": 15.3, "AST": 1.3, "STL": 1.1, "BLK": 2.0}},
    {"player_name": "Isiah Thomas", "team_abbr": "DET", "team": "Detroit Pistons", "season": 1984, "position": "PG", "stats": {"PTS": 21.4, "REB": 4.5, "AST": 11.5, "STL": 2.5, "BLK": 0.3}},
    {"player_name": "Alex English", "team_abbr": "DEN", "team": "Denver Nuggets", "season": 1985, "position": "SF", "stats": {"PTS": 27.8, "REB": 5.7, "AST": 4.7, "STL": 1.4, "BLK": 0.7}},
    {"player_name": "Dominique Wilkins", "team_abbr": "ATL", "team": "Atlanta Hawks", "season": 1988, "position": "SF", "stats": {"PTS": 30.7, "REB": 7.0, "AST": 2.6, "STL": 1.3, "BLK": 0.6}},
    {"player_name": "Hakeem Olajuwon", "team_abbr": "HOU", "team": "Houston Rockets", "season": 1989, "position": "C", "stats": {"PTS": 24.8, "REB": 13.5, "AST": 1.8, "STL": 2.6, "BLK": 3.4}},
    {"player_name": "Patrick Ewing", "team_abbr": "NYK", "team": "New York Knicks", "season": 1990, "position": "C", "stats": {"PTS": 28.6, "REB": 11.0, "AST": 2.2, "STL": 1.0, "BLK": 4.0}},
    {"player_name": "Clyde Drexler", "team_abbr": "POR", "team": "Portland Trail Blazers", "season": 1988, "position": "SG", "stats": {"PTS": 27.7, "REB": 6.0, "AST": 5.8, "STL": 2.8, "BLK": 0.7}},
    {"player_name": "James Worthy", "team_abbr": "LAL", "team": "Los Angeles Lakers", "season": 1988, "position": "SF", "stats": {"PTS": 19.7, "REB": 5.0, "AST": 3.9, "STL": 1.1, "BLK": 0.7}},
    {"player_name": "Mark Aguirre", "team_abbr": "DAL", "team": "Dallas Mavericks", "season": 1984, "position": "SF", "stats": {"PTS": 29.5, "REB": 5.9, "AST": 3.1, "STL": 0.9, "BLK": 0.5}},
    {"player_name": "Bernard King", "team_abbr": "NYK", "team": "New York Knicks", "season": 1985, "position": "SF", "stats": {"PTS": 32.9, "REB": 5.8, "AST": 4.1, "STL": 1.0, "BLK": 0.2}},
    {"player_name": "Sidney Moncrief", "team_abbr": "MIL", "team": "Milwaukee Bucks", "season": 1983, "position": "SG", "stats": {"PTS": 22.5, "REB": 5.8, "AST": 4.5, "STL": 1.4, "BLK": 0.3}},
    {"player_name": "Fat Lever", "team_abbr": "DEN", "team": "Denver Nuggets", "season": 1988, "position": "PG", "stats": {"PTS": 18.9, "REB": 8.1, "AST": 7.2, "STL": 2.5, "BLK": 0.3}},

    # 1990s
    {"player_name": "Hakeem Olajuwon", "team_abbr": "HOU", "team": "Houston Rockets", "season": 1994, "position": "C", "stats": {"PTS": 27.8, "REB": 11.9, "AST": 3.6, "STL": 1.6, "BLK": 3.7}},
    {"player_name": "Michael Jordan", "team_abbr": "CHI", "team": "Chicago Bulls", "season": 1996, "position": "SG", "stats": {"PTS": 30.4, "REB": 6.6, "AST": 4.3, "STL": 2.2, "BLK": 0.5}},
    {"player_name": "Shaquille O'Neal", "team_abbr": "LAL", "team": "Los Angeles Lakers", "season": 2000, "position": "C", "stats": {"PTS": 29.7, "REB": 13.6, "AST": 3.8, "STL": 0.6, "BLK": 3.0}},
    {"player_name": "Karl Malone", "team_abbr": "UTA", "team": "Utah Jazz", "season": 1997, "position": "PF", "stats": {"PTS": 27.4, "REB": 9.9, "AST": 4.5, "STL": 1.4, "BLK": 0.4}},
    {"player_name": "John Stockton", "team_abbr": "UTA", "team": "Utah Jazz", "season": 1990, "position": "PG", "stats": {"PTS": 17.2, "REB": 2.6, "AST": 14.5, "STL": 2.7, "BLK": 0.2}},
    {"player_name": "Scottie Pippen", "team_abbr": "CHI", "team": "Chicago Bulls", "season": 1996, "position": "SF", "stats": {"PTS": 20.2, "REB": 6.5, "AST": 5.7, "STL": 1.9, "BLK": 1.1}},
    {"player_name": "David Robinson", "team_abbr": "SAS", "team": "San Antonio Spurs", "season": 1994, "position": "C", "stats": {"PTS": 29.8, "REB": 10.7, "AST": 4.8, "STL": 1.7, "BLK": 3.2}},
    {"player_name": "Charles Barkley", "team_abbr": "PHX", "team": "Phoenix Suns", "season": 1993, "position": "PF", "stats": {"PTS": 25.6, "REB": 12.2, "AST": 5.1, "STL": 1.6, "BLK": 1.0}},
    {"player_name": "Gary Payton", "team_abbr": "OKC", "team": "Seattle SuperSonics", "season": 1996, "position": "PG", "stats": {"PTS": 19.3, "REB": 4.2, "AST": 7.5, "STL": 2.9, "BLK": 0.2}},
    {"player_name": "Reggie Miller", "team_abbr": "IND", "team": "Indiana Pacers", "season": 1995, "position": "SG", "stats": {"PTS": 19.6, "REB": 3.0, "AST": 3.6, "STL": 1.3, "BLK": 0.2}},
    {"player_name": "Alonzo Mourning", "team_abbr": "MIA", "team": "Miami Heat", "season": 1999, "position": "C", "stats": {"PTS": 20.1, "REB": 10.3, "AST": 1.9, "STL": 0.9, "BLK": 3.9}},
    {"player_name": "Grant Hill", "team_abbr": "DET", "team": "Detroit Pistons", "season": 1996, "position": "SF", "stats": {"PTS": 21.2, "REB": 9.7, "AST": 7.2, "STL": 1.8, "BLK": 0.6}},
    {"player_name": "Mitch Richmond", "team_abbr": "SAC", "team": "Sacramento Kings", "season": 1996, "position": "SG", "stats": {"PTS": 23.1, "REB": 4.4, "AST": 3.7, "STL": 1.4, "BLK": 0.2}},
    {"player_name": "Tim Hardaway", "team_abbr": "MIA", "team": "Golden State Warriors", "season": 1992, "position": "PG", "stats": {"PTS": 23.4, "REB": 3.6, "AST": 10.6, "STL": 2.0, "BLK": 0.1}},
    {"player_name": "Dikembe Mutombo", "team_abbr": "ATL", "team": "Atlanta Hawks", "season": 1997, "position": "C", "stats": {"PTS": 13.3, "REB": 11.6, "AST": 1.4, "STL": 0.6, "BLK": 3.3}},

    # 2000s–2020s seed rows (API fills these when ingested; kept for offline use)
    {"player_name": "Steve Nash", "team_abbr": "PHX", "team": "Phoenix Suns", "season": 2005, "position": "PG", "stats": {"PTS": 15.5, "REB": 3.3, "AST": 11.5, "STL": 1.0, "BLK": 0.1}},
    {"player_name": "Chris Paul", "team_abbr": "NOP", "team": "New Orleans Hornets", "season": 2008, "position": "PG", "stats": {"PTS": 21.6, "REB": 4.9, "AST": 11.8, "STL": 2.7, "BLK": 0.3}},
    {"player_name": "Dwight Howard", "team_abbr": "ORL", "team": "Orlando Magic", "season": 2011, "position": "C", "stats": {"PTS": 22.9, "REB": 14.1, "AST": 1.4, "STL": 1.4, "BLK": 2.4}},
    {"player_name": "Marc Gasol", "team_abbr": "MEM", "team": "Memphis Grizzlies", "season": 2015, "position": "C", "stats": {"PTS": 17.4, "REB": 7.8, "AST": 4.2, "STL": 1.0, "BLK": 1.1}},
    {"player_name": "DeAndre Jordan", "team_abbr": "LAC", "team": "Los Angeles Clippers", "season": 2014, "position": "C", "stats": {"PTS": 10.4, "REB": 13.7, "AST": 1.4, "STL": 0.7, "BLK": 1.4}},
    {"player_name": "Giannis Antetokounmpo", "team_abbr": "MIL", "team": "Milwaukee Bucks", "season": 2024, "position": "PF", "stats": {"PTS": 30.4, "REB": 11.5, "AST": 6.5, "STL": 1.2, "BLK": 1.0}},
    {"player_name": "Anthony Davis", "team_abbr": "LAL", "team": "Los Angeles Lakers", "season": 2023, "position": "PF", "stats": {"PTS": 25.9, "REB": 12.5, "AST": 2.6, "STL": 1.1, "BLK": 2.0}},
    {"player_name": "Draymond Green", "team_abbr": "GSW", "team": "Golden State Warriors", "season": 2016, "position": "PF", "stats": {"PTS": 14.0, "REB": 9.5, "AST": 7.4, "STL": 1.6, "BLK": 1.4}},
]


def main() -> None:
    out: list[dict] = []
    for row in ROWS:
        slug = row["player_name"].lower().replace(" ", "-").replace(".", "")
        player_id = f"bref_{slug}_{row['season']}_{row['team_abbr']}"
        pos_raw = row.get("position_raw", row["position"])
        out.append(
            {
                "player_id": player_id,
                **row,
                "position_raw": pos_raw,
            }
        )
    path = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "nba" / "historical.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(out)} rows to {path}")


if __name__ == "__main__":
    main()
