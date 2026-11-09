-- Schéma SQLite des 8 tables chargées depuis data/processed/. Relançable sans effet (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS leagues (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    url TEXT,
    modified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    acronym TEXT,
    location TEXT,
    slug TEXT NOT NULL,
    modified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES leagues(id),
    name TEXT,
    full_name TEXT NOT NULL,
    season TEXT,
    year INTEGER NOT NULL,
    begin_at TEXT NOT NULL,
    end_at TEXT,
    winner_team_id INTEGER REFERENCES teams(id),
    slug TEXT NOT NULL,
    modified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY,
    series_id INTEGER NOT NULL REFERENCES series(id),
    league_id INTEGER NOT NULL REFERENCES leagues(id),
    name TEXT NOT NULL,
    type TEXT,
    country TEXT,
    region TEXT,
    tier TEXT,
    has_bracket INTEGER NOT NULL CHECK (has_bracket IN (0, 1)),
    begin_at TEXT NOT NULL,
    end_at TEXT,
    winner_team_id INTEGER REFERENCES teams(id),
    slug TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    prizepool_amount INTEGER,
    prizepool_currency TEXT
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    nationality TEXT,
    role TEXT,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    current_team_id INTEGER REFERENCES teams(id),
    slug TEXT NOT NULL,
    modified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
    series_id INTEGER NOT NULL REFERENCES series(id),
    league_id INTEGER NOT NULL REFERENCES leagues(id),
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    number_of_games INTEGER NOT NULL,
    game_version TEXT,
    begin_at TEXT NOT NULL,
    end_at TEXT,
    scheduled_at TEXT NOT NULL,
    rescheduled INTEGER NOT NULL CHECK (rescheduled IN (0, 1)),
    forfeit INTEGER NOT NULL CHECK (forfeit IN (0, 1)),
    draw INTEGER NOT NULL CHECK (draw IN (0, 1)),
    winner_team_id INTEGER REFERENCES teams(id),
    slug TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    year INTEGER NOT NULL,
    duration_minutes REAL
);

CREATE TABLE IF NOT EXISTS match_teams (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    team_id INTEGER NOT NULL REFERENCES teams(id),
    score INTEGER NOT NULL,
    is_winner INTEGER CHECK (is_winner IN (0, 1)),
    PRIMARY KEY (match_id, team_id)
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    position INTEGER NOT NULL,
    status TEXT NOT NULL,
    winner_team_id INTEGER REFERENCES teams(id),
    forfeit INTEGER NOT NULL CHECK (forfeit IN (0, 1)),
    begin_at TEXT,
    end_at TEXT,
    length_minutes REAL
);

CREATE INDEX IF NOT EXISTS idx_series_league ON series(league_id);
CREATE INDEX IF NOT EXISTS idx_tournaments_series ON tournaments(series_id);
CREATE INDEX IF NOT EXISTS idx_matches_tournament ON matches(tournament_id);
CREATE INDEX IF NOT EXISTS idx_matches_series ON matches(series_id);
CREATE INDEX IF NOT EXISTS idx_match_teams_team ON match_teams(team_id);
CREATE INDEX IF NOT EXISTS idx_games_match ON games(match_id);
