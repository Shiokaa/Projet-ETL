# Contrat de sortie : schémas pandera des 8 tables écrites dans data/processed/.
import pandas as pd
import pandera.pandas as pa

VERSION = "1.0.0"
OWNER = "Tom"

DATE = pd.DatetimeTZDtype("us", "UTC")

END_AFTER_BEGIN = pa.Check(
    lambda df: df["begin_at"].isna() | df["end_at"].isna() | (df["end_at"] >= df["begin_at"]),
    error="end_at >= begin_at",
)


def identifier():
    return pa.Column("Int64", pa.Check.ge(1), unique=True)


def link(nullable=False):
    return pa.Column("Int64", pa.Check.ge(1), nullable=nullable)


def text(nullable=False):
    return pa.Column("str", pa.Check.str_length(min_value=1), nullable=nullable)


def choice(values, nullable=False):
    return pa.Column("str", pa.Check.isin(values), nullable=nullable)


def table(name, description, columns, checks=None, unique=None):
    return pa.DataFrameSchema(
        columns,
        checks=checks,
        unique=unique,
        strict=True,
        name=name,
        description=description,
        metadata={"version": VERSION, "owner": OWNER},
    )


SCHEMAS = {
    "leagues": table(
        "leagues",
        "Ligues ayant au moins une série, un tournoi ou un match depuis 2020.",
        {
            "id": identifier(),
            "name": text(),
            "slug": text(),
            "url": text(nullable=True),
            "modified_at": pa.Column(DATE),
        },
    ),
    "series": table(
        "series",
        "Saisons d'une ligue (ex. « LEC Spring 2024 »).",
        {
            "id": identifier(),
            "league_id": link(),
            "name": text(nullable=True),
            "full_name": text(),
            "season": text(nullable=True),
            "year": pa.Column("int64", pa.Check.ge(2000)),
            "begin_at": pa.Column(DATE),
            "end_at": pa.Column(DATE, nullable=True),
            "winner_team_id": link(nullable=True),
            "slug": text(),
            "modified_at": pa.Column(DATE),
        },
        checks=[END_AFTER_BEGIN],
    ),
    "tournaments": table(
        "tournaments",
        "Phases d'une saison (saison régulière, playoffs…).",
        {
            "id": identifier(),
            "series_id": link(),
            "league_id": link(),
            "name": text(),
            "type": choice(["online", "offline", "online/offline"], nullable=True),
            "country": text(nullable=True),
            "region": choice(["ASIA", "EEU", "ME", "NA", "OCE", "SA", "WEU"], nullable=True),
            "tier": choice(["s", "a", "b", "c", "d"], nullable=True),
            "has_bracket": pa.Column("bool"),
            "begin_at": pa.Column(DATE),
            "end_at": pa.Column(DATE, nullable=True),
            "winner_team_id": link(nullable=True),
            "slug": text(),
            "modified_at": pa.Column(DATE),
            "prizepool_amount": pa.Column("Int64", pa.Check.gt(0), nullable=True),
            "prizepool_currency": pa.Column("str", pa.Check.str_matches(r"^[A-Z]{3}$"), nullable=True),
        },
        checks=[
            END_AFTER_BEGIN,
            pa.Check(
                lambda df: df["prizepool_amount"].isna() == df["prizepool_currency"].isna(),
                error="prizepool_amount et prizepool_currency sont vides ensemble",
            ),
        ],
    ),
    "teams": table(
        "teams",
        "Équipes professionnelles.",
        {
            "id": identifier(),
            "name": text(),
            "acronym": text(nullable=True),
            "location": text(nullable=True),
            "slug": text(),
            "modified_at": pa.Column(DATE),
        },
    ),
    "players": table(
        "players",
        "Joueurs professionnels et leur équipe actuelle.",
        {
            "id": identifier(),
            "name": text(),
            "first_name": text(nullable=True),
            "last_name": text(nullable=True),
            "nationality": pa.Column("str", pa.Check.str_matches(r"^[A-Z]{2}$"), nullable=True),
            "role": choice(["top", "jun", "mid", "adc", "sup"], nullable=True),
            "active": pa.Column("bool"),
            "current_team_id": link(nullable=True),
            "slug": text(),
            "modified_at": pa.Column(DATE),
        },
    ),
    "matches": table(
        "matches",
        "Matchs entre deux équipes, depuis 2020.",
        {
            "id": identifier(),
            "tournament_id": link(),
            "series_id": link(),
            "league_id": link(),
            "name": text(),
            "status": choice(["not_started", "running", "finished", "canceled", "postponed"]),
            "number_of_games": pa.Column("int64", pa.Check.ge(1)),
            "game_version": text(nullable=True),
            "begin_at": pa.Column(DATE),
            "end_at": pa.Column(DATE, nullable=True),
            "scheduled_at": pa.Column(DATE),
            "rescheduled": pa.Column("bool"),
            "forfeit": pa.Column("bool"),
            "draw": pa.Column("bool"),
            "winner_team_id": link(nullable=True),
            "slug": text(),
            "modified_at": pa.Column(DATE),
            "year": pa.Column("Int64", pa.Check.ge(2020)),
            "duration_minutes": pa.Column("float64", pa.Check.gt(0), nullable=True),
        },
        checks=[
            END_AFTER_BEGIN,
            pa.Check(lambda df: ~(df["draw"] & df["winner_team_id"].notna()), error="un match nul n'a pas de gagnant"),
        ],
    ),
    "match_teams": table(
        "match_teams",
        "Les 2 équipes de chaque match, avec leur score.",
        {
            "match_id": pa.Column("int64", pa.Check.ge(1)),
            "team_id": pa.Column("int64", pa.Check.ge(1)),
            "score": pa.Column("int64", pa.Check.ge(0)),
            "is_winner": pa.Column("boolean", nullable=True),
        },
        checks=[
            pa.Check(lambda df: df.groupby("match_id")["team_id"].transform("size") == 2, error="2 équipes par match"),
        ],
        unique=["match_id", "team_id"],
    ),
    "games": table(
        "games",
        "Parties de chaque match (un BO5 = jusqu'à 5 parties).",
        {
            "id": identifier(),
            "match_id": link(),
            "position": pa.Column("int64", pa.Check.in_range(1, 5)),
            "status": choice(["not_started", "running", "finished", "not_played"]),
            "winner_team_id": link(nullable=True),
            "forfeit": pa.Column("bool"),
            "begin_at": pa.Column(DATE, nullable=True),
            "end_at": pa.Column(DATE, nullable=True),
            "length_minutes": pa.Column("float64", pa.Check.in_range(1, 95), nullable=True),
        },
        checks=[END_AFTER_BEGIN],
    ),
}
