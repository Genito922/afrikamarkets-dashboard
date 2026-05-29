"""
Page 1 — Tous les cours actions BRVM
"""
import streamlit as st
import plotly.express as px
from data.brvm_scraper import get_actions
from frontend.auth_ui import render_auth_sidebar

st.set_page_config(page_title="Marché BRVM — Afrika Markets", layout="wide")

LANG = st.sidebar.selectbox("🌐 Langue / Language", ["Français", "English"])
FR = LANG == "Français"

render_auth_sidebar(fr=FR)

st.title("📊 Marché Actions BRVM" if FR else "📊 BRVM Equity Market")

df = get_actions()

if df.empty:
    st.error("Données indisponibles" if FR else "Data unavailable")
    st.stop()

# Filtres
col1, col2, col3 = st.columns(3)
with col1:
    secteurs = ["Tous / All"] + sorted(df["secteur"].dropna().unique().tolist())
    secteur = st.selectbox("Secteur" if FR else "Sector", secteurs)
with col2:
    tri = st.selectbox(
        "Trier par" if FR else "Sort by",
        ["variation", "cours", "volume", "symbole"]
    )
with col3:
    ordre = st.selectbox("Ordre" if FR else "Order", 
                         ["Décroissant / Desc", "Croissant / Asc"])

# Filtrage
df_f = df.copy()
if secteur != "Tous / All":
    df_f = df_f[df_f["secteur"] == secteur]

asc = "Croissant" in ordre
df_f = df_f.sort_values(tri, ascending=asc)

# KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Titres" if FR else "Stocks", len(df_f))
c2.metric("Hausse / Up", len(df_f[df_f["variation"] > 0]))
c3.metric("Baisse / Down", len(df_f[df_f["variation"] < 0]))
c4.metric("Stable", len(df_f[df_f["variation"] == 0]))

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
    title="Cours veille vs Cours clôture" if FR else "Previous vs Closing Price",
    labels={
        "cours_veille": "Cours veille (FCFA)" if FR else "Previous Price (FCFA)",
        "cours": "Cours clôture (FCFA)" if FR else "Closing Price (FCFA)",
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
st.subheader("Cours détaillés" if FR else "Detailed Quotes")
df_show = df_f.rename(columns={
    "symbole": "Symbole",
    "nom": "Société" if FR else "Company",
    "volume": "Volume",
    "cours_veille": "Veille / Prev",
    "cours_ouv": "Ouverture / Open",
    "cours": "Clôture / Close",
    "variation": "Var (%)",
    "secteur": "Secteur" if FR else "Sector",
})

st.dataframe(
    df_show.style.format({"Var (%)": "{:.2f}%", "Volume": "{:,.0f}",
              "Veille / Prev": "{:,.0f}", "Clôture / Close": "{:,.0f}"}),
    use_container_width=True,
    height=500,
)

st.caption(
    "Source : brvm.org — données temps réel (cache 15 min) · Pipeline DB automatique toutes les 15 min"
    if FR else
    "Source: brvm.org — real-time data (15 min cache) · Automated DB pipeline every 15 min"
)
