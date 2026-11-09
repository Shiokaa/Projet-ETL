# Éléments d'affichage communs : tous les graphiques partagent la même couleur, les mêmes marges et le même thème.
import plotly.graph_objects as go
import streamlit as st

COLORS = {
    "light": {"series": "#2a78d6", "text": "#0b0b0b", "muted": "#52514e", "grid": "#e4e3df"},
    "dark": {"series": "#3987e5", "text": "#f0efec", "muted": "#c3c2b7", "grid": "#383835"},
}


def colors():
    return COLORS.get(st.context.theme.type or "light", COLORS["light"])


def style(fig, height=300):
    c = colors()
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=c["muted"], size=13),
        showlegend=False,
        bargap=0.35,
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(showgrid=False, linecolor=c["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=c["grid"], zeroline=False)
    return fig


def column_chart(df, x, y, hover, height=300):
    c = colors()
    fig = go.Figure(
        go.Bar(
            x=df[x],
            y=df[y],
            marker=dict(color=c["series"], cornerradius=4),
            hovertemplate=hover + "<extra></extra>",
        )
    )
    fig.update_xaxes(type="category")
    return style(fig, height)


def histogram(df, start, count, step, unit, hover, height=300):
    c = colors()
    fig = go.Figure(
        go.Bar(
            x=df[start],
            y=df[count],
            width=step * 0.9,
            offset=0,
            customdata=df[start] + step,
            marker=dict(color=c["series"], cornerradius=3),
            hovertemplate=hover + "<extra></extra>",
        )
    )
    fig.update_xaxes(dtick=10, ticksuffix=f" {unit}")
    return style(fig, height)


def ranked_bars(df, label, value, hover, customdata=None, height=340):
    c = colors()
    fig = go.Figure(
        go.Bar(
            x=df[value],
            y=df[label],
            orientation="h",
            marker=dict(color=c["series"], cornerradius=4),
            text=df[value],
            textposition="outside",
            textfont=dict(color=c["text"]),
            customdata=customdata,
            hovertemplate=hover + "<extra></extra>",
            cliponaxis=False,
        )
    )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(visible=False, range=[0, df[value].max() * 1.3])
    return style(fig, height)


def card(title, subtitle):
    box = st.container(border=True)
    box.markdown(f"**{title}**")
    box.caption(subtitle)
    return box
