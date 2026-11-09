# Connexion SQLite : valide en cas de succès, annule en cas d'erreur, ferme dans tous les cas.
import sqlite3
from contextlib import contextmanager

from settings import DB_PATH


@contextmanager
def get_connection(path=DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")  # désactivé par défaut, à refaire à chaque connexion
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
