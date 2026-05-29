"""
Page 5 — War Room : Risques géopolitiques UEMOA
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from frontend.auth_ui import render_auth_sidebar, require_plan

st.set_page_config(page_title="War Room BRVM", layout="wide")
LANG = st.sidebar.selectbox("🌐 Langue / Language", ["Français", "English"])
FR = LANG == "Français"

render_auth_sidebar(fr=FR)
require_plan("pro", fr=FR)

st.title("🌍 War Room — Risques UEMOA" if FR else "🌍 War Room — UEMOA Risks")

# ── Données risques statiques (à connecter à GEO_INTEL) ──────
risques = pd.DataFrame([
    {"pays": "Côte d'Ivoire", "risque": 2, "note": "Stable", "impact_brvm": "Fort",   "flag": "🇨🇮"},
    {"pays": "Sénégal",        "risque": 2, "note": "Stable", "impact_brvm": "Fort",   "flag": "🇸🇳"},
    {"pays": "Burkina Faso",   "risque": 8, "note": "Transition militaire", "impact_brvm": "Moyen", "flag": "🇧🇫"},
    {"pays": "Mali",           "risque": 8, "note": "Transition militaire", "impact_brvm": "Moyen", "flag": "🇲🇱"},
    {"pays": "Niger",          "risque": 9, "note": "Transition militaire", "impact_brvm": "Faible", "flag": "🇳🇪"},
    {"pays": "Bénin",          "risque": 3, "note": "Stable", "impact_brvm": "Moyen",  "flag": "🇧🇯"},
    {"pays": "Togo",           "risque": 4, "note": "Stable", "impact_brvm": "Moyen",  "flag": "🇹🇬"},
    {"pays": "Guinée-Bissau",  "risque": 5, "note": "Fragile", "impact_brvm": "Faible", "flag": "🇬🇼"},
])

# KPIs risque
col1, col2, col3 = st.columns(3)
col1.metric("Pays stables / Stable" if FR else "Stable Countries",
            len(risques[risques["risque"] <= 4]))
col2.metric("Pays fragiles / Fragile",
            len(risques[(risques["risque"] > 4) & (risques["risque"] <= 7)]))
col3.metric("Pays à risque élevé / High Risk",
            len(risques[risques["risque"] > 7]))

st.markdown("---")

# Carte risques
st.subheader("🗺️ Carte des risques UEMOA" if FR else "🗺️ UEMOA Risk Map")
fig = px.bar(
    risques.sort_values("risque", ascending=True),
    x="risque", y="pays",
    orientation="h",
    color="risque",
    color_continuous_scale=["#00CC66", "#FFD700", "#FF4444"],
    text="note",
    title="Niveau de risque par pays (1=faible, 10=élevé)" if FR
          else "Risk Level by Country (1=low, 10=high)",
    labels={"risque": "Niveau risque" if FR else "Risk Level", "pays": ""},
)
fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="white",
    coloraxis_showscale=False,
    height=350,
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Tableau détaillé
st.subheader("Analyse détaillée" if FR else "Detailed Analysis")
for _, r in risques.sort_values("risque").iterrows():
    color = "#0D3B27" if r["risque"] <= 4 else "#3B2D0D" if r["risque"] <= 7 else "#3B0D0D"
    border = "#00CC66" if r["risque"] <= 4 else "#FFD700" if r["risque"] <= 7 else "#FF4444"
    st.markdown(f"""
    <div style="background:{color}; padding:12px; border-radius:8px;
                border-left:4px solid {border}; margin:6px 0;">
        <b>{r["flag"]} {r["pays"]}</b> &nbsp;
        Risque : <b>{r["risque"]}/10</b> &nbsp;|&nbsp;
        {r["note"]} &nbsp;|&nbsp;
        Impact BRVM : <b>{r["impact_brvm"]}</b>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.info(
    "💡 Les marchés de transition (Burkina, Mali, Niger) représentent un risque de contagion sur la confiance des investisseurs BRVM, même si leur poids en capitalisation reste limité."
    if FR else
    "💡 Transition markets (Burkina, Mali, Niger) represent contagion risk on BRVM investor confidence, even though their market cap weight remains limited."
)
