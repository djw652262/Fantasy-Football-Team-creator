from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "app.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS squad_entries (
                slot INTEGER PRIMARY KEY,
                player_id INTEGER,
                player_name TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS saved_lineups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gameweek INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS saved_lineup_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lineup_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                role TEXT NOT NULL,
                bench_order INTEGER,
                FOREIGN KEY (lineup_id) REFERENCES saved_lineups (id)
            );
            """
        )

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(squad_entries)").fetchall()
        }
        if "player_id" not in columns:
            connection.execute("ALTER TABLE squad_entries ADD COLUMN player_id INTEGER")

        existing = connection.execute("SELECT COUNT(*) AS count FROM squad_entries").fetchone()
        if existing["count"] == 0:
            defaults = [
                {"player_id": None, "player_name": "Lammens"},
                {"player_id": None, "player_name": "Tarkowski"},
                {"player_id": None, "player_name": "van Dijk"},
                {"player_id": None, "player_name": "Thiaw"},
                {"player_id": None, "player_name": "Mbeumo"},
                {"player_id": None, "player_name": "Fernandes"},
                {"player_id": None, "player_name": "Szoboszlai"},
                {"player_id": None, "player_name": "Thiago"},
                {"player_id": None, "player_name": "Ekitike"},
                {"player_id": None, "player_name": "Joao Pedro"},
                {"player_id": None, "player_name": "Donnarumma"},
                {"player_id": None, "player_name": "Semenyo"},
                {"player_id": None, "player_name": "Gvardiol"},
                {"player_id": None, "player_name": "Gabriel"},
                {"player_id": None, "player_name": "Ouattara"},
            ]
            connection.executemany(
                "INSERT INTO squad_entries (slot, player_id, player_name) VALUES (?, ?, ?)",
                [
                    (index, entry["player_id"], entry["player_name"])
                    for index, entry in enumerate(defaults, start=1)
                ],
            )


def get_squad_entries() -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            "SELECT slot, player_id, player_name FROM squad_entries ORDER BY slot ASC"
        ).fetchall()


def save_squad_entries(player_entries: list[dict]) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM squad_entries")
        connection.executemany(
            "INSERT INTO squad_entries (slot, player_id, player_name) VALUES (?, ?, ?)",
            [
                (
                    index,
                    entry.get("player_id"),
                    entry.get("player_name", "").strip(),
                )
                for index, entry in enumerate(player_entries, start=1)
            ],
        )


def save_lineup(gameweek: int, starters: list[str], bench: list[str], reserve_goalkeeper: str | None) -> None:
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO saved_lineups (gameweek) VALUES (?)",
            (gameweek,),
        )
        lineup_id = cursor.lastrowid

        connection.executemany(
            """
            INSERT INTO saved_lineup_players (lineup_id, player_name, role, bench_order)
            VALUES (?, ?, 'starter', NULL)
            """,
            [(lineup_id, player_name) for player_name in starters],
        )

        if reserve_goalkeeper:
            connection.execute(
                """
                INSERT INTO saved_lineup_players (lineup_id, player_name, role, bench_order)
                VALUES (?, ?, 'reserve_goalkeeper', 4)
                """,
                (lineup_id, reserve_goalkeeper),
            )

        connection.executemany(
            """
            INSERT INTO saved_lineup_players (lineup_id, player_name, role, bench_order)
            VALUES (?, ?, 'bench', ?)
            """,
            [
                (lineup_id, player_name, order)
                for order, player_name in enumerate(bench, start=1)
            ],
        )


def get_saved_lineups() -> list[dict]:
    with get_connection() as connection:
        lineups = connection.execute(
            "SELECT id, gameweek, created_at FROM saved_lineups ORDER BY gameweek DESC, id DESC"
        ).fetchall()
        rows = []
        for lineup in lineups:
            players = connection.execute(
                """
                SELECT player_name, role, bench_order
                FROM saved_lineup_players
                WHERE lineup_id = ?
                ORDER BY
                    CASE role
                        WHEN 'starter' THEN 0
                        WHEN 'bench' THEN 1
                        ELSE 2
                    END,
                    COALESCE(bench_order, 0) ASC,
                    player_name ASC
                """,
                (lineup["id"],),
            ).fetchall()
            rows.append(
                {
                    "id": lineup["id"],
                    "gameweek": lineup["gameweek"],
                    "created_at": lineup["created_at"],
                    "players": [dict(player) for player in players],
                }
            )
        return rows
