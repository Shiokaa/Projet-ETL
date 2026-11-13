# Charge les CSV de data/processed/ dans SQLite par upsert, en une seule transaction.
from pathlib import Path

import pandas as pd

from settings import DB_PATH, PROCESSED_DIR
from etl.load.db import get_connection

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
    key_idx = [columns.index(k) for k in keys]
    return [tuple(r[i] for i in key_idx) for r in rows]


def purge(conn, name, keys, kept):
    """Supprime les lignes que l'API ne renvoie plus (l'upsert seul ne supprime jamais)."""
    cols = ", ".join(f'"{k}"' for k in keys)
    typed = ", ".join(f'"{k}" INTEGER' for k in keys)  # sans type, SQLite ignore l'index
    conn.execute(f"CREATE TEMP TABLE kept ({typed}, PRIMARY KEY ({cols}))")
    conn.executemany(f"INSERT INTO kept VALUES ({', '.join('?' for _ in keys)})", kept)
    same = " AND ".join(f'k."{c}" = "{name}"."{c}"' for c in keys)
    conn.execute(f'DELETE FROM "{name}" WHERE NOT EXISTS (SELECT 1 FROM kept k WHERE {same})')
    conn.execute("DROP TABLE kept")


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
        kept = {}
        for name, keys in TABLES.items():
            kept[name] = upsert(conn, name, keys)
            print(f"{name} : {len(kept[name])} lignes")
        for name, keys in reversed(TABLES.items()):
            purge(conn, name, keys, kept[name])
        check(conn, {name: len(rows) for name, rows in kept.items()})
    print(f"Base chargée : {DB_PATH}")
