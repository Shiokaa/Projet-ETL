# Charge les CSV de data/processed/ dans SQLite par upsert, en une seule transaction.
from pathlib import Path

import pandas as pd

from config import DB_PATH, PROCESSED_DIR
from scripts.load.db import get_connection

SCHEMA_FILE = Path(__file__).with_name("schema.sql")

# Ordre imposé par les clés étrangères : un parent est chargé avant ses enfants.
TABLES = {
    "leagues": ("id",),
    "teams": ("id",),
    "series": ("id",),
    "tournaments": ("id",),
    "players": ("id",),
    "matches": ("id",),
    "match_teams": ("match_id", "team_id"),
    "games": ("id",),
}


def read_rows(name):
    df = pd.read_csv(PROCESSED_DIR / f"{name}.csv", dtype_backend="numpy_nullable")
    df = df.astype(object).where(df.notna(), None)
    return list(df.columns), list(df.itertuples(index=False, name=None))


def upsert(conn, name, keys):
    columns, rows = read_rows(name)
    names = ", ".join(f'"{c}"' for c in columns)
    marks = ", ".join("?" for _ in columns)
    conflict = ", ".join(f'"{k}"' for k in keys)
    updates = ", ".join(f'"{c}" = excluded."{c}"' for c in columns if c not in keys)
    sql = f'INSERT INTO "{name}" ({names}) VALUES ({marks}) ON CONFLICT({conflict}) DO UPDATE SET {updates}'
    conn.executemany(sql, rows)
    return len(rows)


def check(conn, expected):
    for name, count in expected.items():
        (found,) = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()
        if found != count:
            raise RuntimeError(f"{name} : {found} lignes en base, {count} dans le CSV")
    broken = conn.execute("PRAGMA foreign_key_check").fetchall()
    if broken:
        raise RuntimeError(f"{len(broken)} liens cassés, premier : {broken[0]}")


def load():
    with get_connection() as conn:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        expected = {}
        for name, keys in TABLES.items():
            expected[name] = upsert(conn, name, keys)
            print(f"{name} : {expected[name]} lignes")
        check(conn, expected)
    print(f"Base chargée : {DB_PATH}")
