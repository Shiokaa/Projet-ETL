# Transformation : nettoie les données brutes de data/raw/ et écrit une table CSV par entité dans data/processed/.
import gzip
import json

import pandas as pd

from config import PROCESSED_DIR, RAW_DIR
from scripts.validate.validate import validate_raw, validate_table

CURRENCIES = {
    "Euro": "EUR",
    "United States Dollar": "USD",
    "Chinese Yuan": "CNY",
    "Brazilian Real": "BRL",
    "South Korean Won": "KRW",
    "Polish Zloty": "PLN",
    "Vietnamese Dong": "VND",
    "Japanese Yen": "JPY",
    "Swedish Krona": "SEK",
    "Russian Ruble": "RUB",
    "Mexican Peso": "MXN",
    "Argentine Peso": "ARS",
    "Australian Dollar": "AUD",
}

# Colonnes conservées pour chaque table : nom brut -> nom final.
COLUMNS = {
    "leagues": {"id": "id", "name": "name", "slug": "slug", "url": "url", "modified_at": "modified_at"},
    "series": {
        "id": "id",
        "league_id": "league_id",
        "name": "name",
        "full_name": "full_name",
        "season": "season",
        "year": "year",
        "begin_at": "begin_at",
        "end_at": "end_at",
        "winner_id": "winner_team_id",
        "slug": "slug",
        "modified_at": "modified_at",
    },
    "tournaments": {
        "id": "id",
        "serie_id": "series_id",
        "league_id": "league_id",
        "name": "name",
        "type": "type",
        "country": "country",
        "region": "region",
        "tier": "tier",
        "prizepool": "prizepool",
        "has_bracket": "has_bracket",
        "begin_at": "begin_at",
        "end_at": "end_at",
        "winner_id": "winner_team_id",
        "slug": "slug",
        "modified_at": "modified_at",
    },
    "teams": {
        "id": "id",
        "name": "name",
        "acronym": "acronym",
        "location": "location",
        "slug": "slug",
        "modified_at": "modified_at",
    },
    "players": {
        "id": "id",
        "name": "name",
        "first_name": "first_name",
        "last_name": "last_name",
        "nationality": "nationality",
        "role": "role",
        "active": "active",
        "current_team_id": "current_team_id",
        "slug": "slug",
        "modified_at": "modified_at",
    },
    "matches": {
        "id": "id",
        "tournament_id": "tournament_id",
        "serie_id": "series_id",
        "league_id": "league_id",
        "name": "name",
        "status": "status",
        "number_of_games": "number_of_games",
        "game_version": "game_version",
        "begin_at": "begin_at",
        "end_at": "end_at",
        "scheduled_at": "scheduled_at",
        "rescheduled": "rescheduled",
        "forfeit": "forfeit",
        "draw": "draw",
        "winner_id": "winner_team_id",
        "slug": "slug",
        "modified_at": "modified_at",
    },
    "games": {
        "id": "id",
        "match_id": "match_id",
        "position": "position",
        "status": "status",
        "winner_team_id": "winner_team_id",
        "length": "length",
        "forfeit": "forfeit",
        "begin_at": "begin_at",
        "end_at": "end_at",
    },
}

DATE_COLUMNS = ["begin_at", "end_at", "scheduled_at", "modified_at"]
MIN_GAME_SECONDS = 60
MAX_GAME_SECONDS = 95 * 60


def load(name):
    with gzip.open(RAW_DIR / f"{name}.json.gz", "rt", encoding="utf-8") as f:
        return json.load(f)


def clean(rows, table):
    df = pd.DataFrame(rows)[list(COLUMNS[table])].rename(columns=COLUMNS[table])
    # Les copies imbriquées sont ajoutées après les lignes de premier niveau : on garde ces dernières.
    df = df.drop_duplicates(subset="id").reset_index(drop=True)
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].str.strip().replace("", None)
        if col in DATE_COLUMNS:
            df[col] = pd.to_datetime(df[col], utc=True)
        # Sans ça, un identifiant avec des vides devient un décimal (75013.0).
        if col == "id" or col.endswith("_id"):
            df[col] = df[col].astype("Int64")
    if {"begin_at", "end_at"} <= set(df.columns):
        # Fin avant le début (ex. série 7032) : une des deux est fausse, on garde le début.
        df.loc[df["end_at"] < df["begin_at"], "end_at"] = pd.NaT
    return df


def check_link(child, column, parent, required):
    orphans = child[column].notna() & ~child[column].isin(parent["id"])
    if required and orphans.any():
        raise ValueError(f"{orphans.sum()} valeurs de {column} sans correspondance")
    if orphans.any():
        print(f"  {column} : {orphans.sum()} liens vers une ligne absente, mis à vide")
        child.loc[orphans, column] = None


def transform():
    print("Contrats d'entrée :")
    raw = {
        name: validate_raw(name, load(name))
        for name in ["leagues", "series", "tournaments", "matches", "teams", "players"]
    }
    # Matchs « TBD vs TBD » sans équipes : inexploitables.
    matches_raw = [m for m in raw["matches"] if m["opponents"]]

    # Le filtre de date de l'extraction écarte les séries et tournois commencés fin 2019
    # alors que leurs matchs datent de 2020 : on les récupère depuis leurs copies imbriquées.
    series = clean(
        raw["series"] + [t["serie"] for t in raw["tournaments"]] + [m["serie"] for m in matches_raw], "series"
    )
    tournaments = clean(raw["tournaments"] + [m["tournament"] for m in matches_raw], "tournaments")
    prizepool = tournaments.pop("prizepool").str.split(" ", n=1, expand=True)
    tournaments["prizepool_amount"] = pd.to_numeric(prizepool[0].str.replace(",", "")).astype("Int64")
    tournaments["prizepool_currency"] = prizepool[1].map(CURRENCIES)
    tournaments["tier"] = tournaments["tier"].str.lower().replace("unranked", None)

    for m in matches_raw:
        m["game_version"] = (m["videogame_version"] or {}).get("name")
    matches = clean(matches_raw, "matches")

    games = clean(
        [{**g, "winner_team_id": g["winner"]["id"]} for m in matches_raw for g in m["games"]], "games"
    )
    # 0 = durée manquante ; une partie ne finit pas en moins d'une minute ;
    # au-delà du record pro (94 min 37 s), PandaScore compte les pauses.
    length = games.pop("length")
    games["length_minutes"] = (
        length.where((length >= MIN_GAME_SECONDS) & (length <= MAX_GAME_SECONDS)) / 60
    ).round(1)

    match_teams = pd.DataFrame(
        [{"match_id": m["id"], "team_id": r["team_id"], "score": r["score"]} for m in matches_raw for r in m["results"]]
    ).drop_duplicates(subset=["match_id", "team_id"])
    winner = match_teams["match_id"].map(matches.set_index("id")["winner_team_id"])
    match_teams["is_winner"] = (match_teams["team_id"] == winner).where(winner.notna()).astype("boolean")

    matches["year"] = matches["begin_at"].fillna(matches["scheduled_at"]).dt.year.astype("Int64")
    matches["duration_minutes"] = matches["id"].map(games.groupby("match_id")["length_minutes"].sum(skipna=False).round(1))

    players = clean(
        [{**p, "current_team_id": (p["current_team"] or {}).get("id")} for p in raw["players"]], "players"
    )
    teams = clean(raw["teams"], "teams")

    used_leagues = set(series["league_id"]) | set(tournaments["league_id"]) | set(matches["league_id"])
    leagues = clean([lg for lg in raw["leagues"] if lg["id"] in used_leagues], "leagues")

    print("Vérification des liens :")
    check_link(series, "league_id", leagues, required=True)
    check_link(tournaments, "series_id", series, required=True)
    check_link(tournaments, "league_id", leagues, required=True)
    check_link(matches, "tournament_id", tournaments, required=True)
    check_link(matches, "series_id", series, required=True)
    check_link(matches, "league_id", leagues, required=True)
    check_link(games, "match_id", matches, required=True)
    check_link(match_teams, "match_id", matches, required=True)
    check_link(match_teams, "team_id", teams, required=True)
    for table in [series, tournaments, matches, games]:
        check_link(table, "winner_team_id", teams, required=False)
    check_link(players, "current_team_id", teams, required=False)

    tables = {
        "leagues": leagues,
        "series": series,
        "tournaments": tournaments,
        "teams": teams,
        "players": players,
        "matches": matches,
        "match_teams": match_teams,
        "games": games,
    }
    print("Contrats de sortie :")
    tables = {name: validate_table(name, df) for name, df in tables.items()}
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
        print(f"{name} : {len(df)} lignes -> {name}.csv")
