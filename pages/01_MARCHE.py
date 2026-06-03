"""
Page 1 — Tous les cours actions BRVM
"""
import streamlit as st
import plotly.express as px
from data.brvm_scraper import get_actions
from frontend.auth_ui import render_auth_sidebar
from utils.i18n import t, get_lang

st.set_page_config(page_title="Marché BRVM — Afrika Markets", layout="wide")

lang = get_lang()
FR   = lang == "fr"

render_auth_sidebar(fr=FR)

st.title(t("market_title", lang))

df = get_actions()

if df.empty:
    st.error(t("data_unavailable", lang))
    st.stop()

# Filtres
col1, col2, col3 = st.columns(3)
with col1:
    secteurs = [t("all_filter", lang)] + sorted(df["secteur"].dropna().unique().tolist())
    secteur  = st.selectbox(t("sector", lang), secteurs)
with col2:
    tri = st.selectbox(
        t("sort_by", lang),
        ["variation", "cours", "volume", "symbole"]
    )
with col3:
    ordre_label = [t("descending", lang), t("ascending", lang)]
    ordre       = st.selectbox(t("order", lang), ordre_label)

# Filtrage
df_f = df.copy()
if secteur != t("all_filter", lang):
    df_f = df_f[df_f["secteur"] == secteur]

asc  = ordre == t("ascending", lang)
df_f = df_f.sort_values(tri, ascending=asc)

# KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric(t("stocks", lang),    len(df_f))
c2.metric(t("up", lang),        len(df_f[df_f["variation"] > 0]))
c3.metric(t("down", lang),      len(df_f[df_f["variation"] < 0]))
c4.metric(t("stable", lang),    len(df_f[df_f["variation"] == 0]))

st.markdown("---")

# Graphique bubble
fig = px.scatter(
    df_f,
    x="cours_veille", y="cours",
    size="volume",
    color="variation",
    color_continuous_scale=["#FF4444", "#FFD700", "#00CC66"],
    hover_name="nom",
    hover_data={"symbole": True, "variation": True, "volume": True},
    title=t("bubble_title", lang),
    labels={
        "cours_veille": t("prev_price_label", lang),
        "cours":        t("close_price_label", lang),
    },
    size_max=40,
)
fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="white",
    height=450,
)
st.plotly_chart(fig, use_container_width=True)

# Tableau complet
st.subheader(t("detailed_quotes", lang))
df_show = df_f.rename(columns={
    "symbole":    "Symbole",
    "nom":        t("company", lang),
    "volume":     t("volume", lang),
    "cours_veille": t("prev_col", lang),
    "cours_ouv":  t("open_col", lang),
    "cours":      t("close_col", lang),
    "variation":  "Var (%)",
    "secteur":    t("sector", lang),
})

st.dataframe(
    df_show.style.format({
        "Var (%)":           "{:.2f}%",
        t("volume", lang):   "{:,.0f}",
        t("prev_col", lang): "{:,.0f}",
        t("close_col", lang):"{:,.0f}",
    }),
    use_container_width=True,
    height=500,
)

st.caption(t("source_caption", lang))
