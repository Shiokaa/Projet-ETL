# Requêtes SQL de l'interface : connexion en lecture seule, statistiques sur les matchs terminés.
import sqlite3
from contextlib import closing

import pandas as pd

from settings import DB_PATH


def read_connection():
    return sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)


def query(sql, params=()):
    with closing(read_connection()) as conn:
        return pd.read_sql(sql, conn, params=params)


def scalar(sql, params=()):
    return query(sql, params).iloc[0, 0]


def where(years, league_ids):
    """Filtre commun : matchs terminés, dans la période et les ligues choisies (toutes si vide)."""
    clause = "m.status = 'finished' AND m.year BETWEEN ? AND ?"
    params = list(years)
    if league_ids:
        clause += f" AND m.league_id IN ({','.join('?' * len(league_ids))})"
        params += list(league_ids)
    return clause, params


def year_bounds():
    row = query("SELECT MIN(year) AS lo, MAX(year) AS hi FROM matches WHERE status = 'finished'").iloc[0]
    return int(row["lo"]), int(row["hi"])


def leagues():
    return query(
        "SELECT id, name FROM leagues WHERE id IN (SELECT DISTINCT league_id FROM matches WHERE status = 'finished') "
        "ORDER BY name"
    )


def kpis(years, league_ids):
    w, p = where(years, league_ids)
    return {
        "matches": scalar(f"SELECT COUNT(*) FROM matches m WHERE {w}", p),
        "leagues": scalar(f"SELECT COUNT(DISTINCT m.league_id) FROM matches m WHERE {w}", p),
        "teams": scalar(
            f"SELECT COUNT(DISTINCT mt.team_id) FROM match_teams mt JOIN matches m ON m.id = mt.match_id WHERE {w}", p
        ),
        "avg_game": scalar(f"SELECT AVG(g.length_minutes) FROM games g JOIN matches m ON m.id = g.match_id WHERE {w}", p),
        "active_players": scalar("SELECT COUNT(*) FROM players WHERE active = 1"),
    }


def matches_per_year(years, league_ids):
    w, p = where(years, league_ids)
    return query(f"SELECT m.year, COUNT(*) AS matches FROM matches m WHERE {w} GROUP BY m.year ORDER BY m.year", p)


def matches_per_league(years, league_ids, limit=10):
    w, p = where(years, league_ids)
    return query(
        f"SELECT l.name AS league, COUNT(*) AS matches FROM matches m JOIN leagues l ON l.id = m.league_id "
        f"WHERE {w} GROUP BY l.id ORDER BY matches DESC LIMIT ?",
        p + [limit],
    )


def top_teams(years, league_ids, limit=10):
    w, p = where(years, league_ids)
    return query(
        f"SELECT t.name AS team, SUM(mt.is_winner) AS wins, COUNT(*) AS played "
        f"FROM match_teams mt JOIN matches m ON m.id = mt.match_id JOIN teams t ON t.id = mt.team_id "
        f"WHERE {w} GROUP BY t.id ORDER BY wins DESC, played ASC LIMIT ?",
        p + [limit],
    )


def game_lengths(years, league_ids, bin_minutes=2):
    w, p = where(years, league_ids)
    return query(
        f"SELECT CAST(g.length_minutes / {bin_minutes} AS INTEGER) * {bin_minutes} AS start, COUNT(*) AS games "
        f"FROM games g JOIN matches m ON m.id = g.match_id WHERE {w} AND g.length_minutes IS NOT NULL "
        f"GROUP BY start ORDER BY start",
        p,
    )


def latest_matches(years, league_ids, limit=10):
    w, p = where(years, league_ids)
    return query(
        f"SELECT substr(m.begin_at, 1, 10) AS date, l.name AS league, m.name AS match, t.name AS winner "
        f"FROM matches m JOIN leagues l ON l.id = m.league_id LEFT JOIN teams t ON t.id = m.winner_team_id "
        f"WHERE {w} ORDER BY m.begin_at DESC LIMIT ?",
        p + [limit],
    )
