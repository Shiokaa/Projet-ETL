# Dashboard Streamlit : vue d'ensemble des matchs LoL. Lancement : python -m streamlit run web/app.py
import streamlit as st

from web import components, queries

st.set_page_config(page_title="LoL esports", page_icon=":material/sports_esports:", layout="wide")

lo, hi = queries.year_bounds()
league_names = queries.leagues().set_index("id")["name"]

with st.sidebar:
    st.header("Filtres")
    years = st.slider("Années", lo, hi, (lo, hi))
    league_ids = st.multiselect("Ligues", league_names.index, format_func=league_names.get, placeholder="Toutes")
    st.caption("Les statistiques portent sur les matchs terminés. Le nombre de joueurs actifs ne dépend pas des filtres.")

kpi = queries.kpis(years, league_ids)
if kpi["matches"] == 0:
    st.info("Aucun match terminé pour ces filtres.")
    st.stop()

st.title("LoL esports")
st.caption(f"Matchs professionnels terminés, {years[0]} à {years[1]}" + (f", {len(league_ids)} ligue(s)" if league_ids else ""))

cols = st.columns(5)
tiles = [
    ("Matchs", f"{kpi['matches']:,}".replace(",", " ")),
    ("Ligues", kpi["leagues"]),
    ("Équipes", f"{kpi['teams']:,}".replace(",", " ")),
    ("Partie moyenne", f"{kpi['avg_game']:.0f} min"),
    ("Joueurs actifs", f"{kpi['active_players']:,}".replace(",", " ")),
]
for col, (label, value) in zip(cols, tiles):
    col.metric(label, value, border=True)

left, right = st.columns(2)
with left:
    box = components.card("Matchs par année", "Nombre de matchs terminés")
    df = queries.matches_per_year(years, league_ids)
    box.plotly_chart(
        components.column_chart(df, "year", "matches", "%{x} : %{y} matchs"), width="stretch"
    )
with right:
    box = components.card("Ligues les plus actives", "Les 10 ligues avec le plus de matchs")
    df = queries.matches_per_league(years, league_ids)
    box.plotly_chart(
        components.ranked_bars(df, "league", "matches", "%{y} : %{x} matchs"), width="stretch"
    )

left, right = st.columns(2)
with left:
    box = components.card("Équipes les plus victorieuses", "Les 10 équipes avec le plus de victoires")
    df = queries.top_teams(years, league_ids)
    df["rate"] = (df["wins"] / df["played"] * 100).round(0)
    box.plotly_chart(
        components.ranked_bars(
            df, "team", "wins", "%{y} : %{x} victoires sur %{customdata[0]} matchs (%{customdata[1]} %)",
            customdata=df[["played", "rate"]],
        ),
        width="stretch",
    )
with right:
    box = components.card("Durée des parties", "Nombre de parties par tranche de 2 minutes")
    df = queries.game_lengths(years, league_ids)
    box.plotly_chart(
        components.histogram(df, "start", "games", 2, "min", "%{x}–%{customdata} min : %{y} parties"),
        width="stretch",
    )

box = components.card("Derniers matchs terminés", "Les 10 plus récents")
box.dataframe(
    queries.latest_matches(years, league_ids),
    hide_index=True,
    width="stretch",
    column_config={"date": "Date", "league": "Ligue", "match": "Match", "winner": "Vainqueur"},
)
