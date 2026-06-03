"""
Page 5 — War Room : Risques géopolitiques UEMOA
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from frontend.auth_ui import render_auth_sidebar, require_plan
from utils.i18n import t, get_lang

st.set_page_config(page_title="War Room BRVM", layout="wide")

lang = get_lang()
FR   = lang == "fr"

render_auth_sidebar(fr=FR)
require_plan("pro", fr=FR)

st.title(t("warroom_title", lang))

# ── Données risques ───────────────────────────────────────────
risques = pd.DataFrame([
    {"pays": "Côte d'Ivoire", "risque": 2, "note": t("note_stable", lang),   "impact_brvm": t("impact_high", lang),   "flag": "🇨🇮"},
    {"pays": "Sénégal",        "risque": 2, "note": t("note_stable", lang),   "impact_brvm": t("impact_high", lang),   "flag": "🇸🇳"},
    {"pays": "Burkina Faso",   "risque": 8, "note": t("note_military", lang), "impact_brvm": t("impact_medium", lang), "flag": "🇧🇫"},
    {"pays": "Mali",           "risque": 8, "note": t("note_military", lang), "impact_brvm": t("impact_medium", lang), "flag": "🇲🇱"},
    {"pays": "Niger",          "risque": 9, "note": t("note_military", lang), "impact_brvm": t("impact_low", lang),    "flag": "🇳🇪"},
    {"pays": "Bénin",          "risque": 3, "note": t("note_stable", lang),   "impact_brvm": t("impact_medium", lang), "flag": "🇧🇯"},
    {"pays": "Togo",           "risque": 4, "note": t("note_stable", lang),   "impact_brvm": t("impact_medium", lang), "flag": "🇹🇬"},
    {"pays": "Guinée-Bissau",  "risque": 5, "note": t("note_fragile", lang),  "impact_brvm": t("impact_low", lang),    "flag": "🇬🇼"},
])

# KPIs risque
col1, col2, col3 = st.columns(3)
col1.metric(t("stable_countries", lang),    len(risques[risques["risque"] <= 4]))
col2.metric(t("fragile_countries", lang),   len(risques[(risques["risque"] > 4) & (risques["risque"] <= 7)]))
col3.metric(t("high_risk_countries", lang), len(risques[risques["risque"] > 7]))

st.markdown("---")

# Carte risques
st.subheader(t("risk_map_title", lang))
fig = px.bar(
    risques.sort_values("risque", ascending=True),
    x="risque", y="pays",
    orientation="h",
    color="risque",
    color_continuous_scale=["#00CC66", "#FFD700", "#FF4444"],
    text="note",
    title=t("risk_chart_label", lang),
    labels={"risque": t("risk_level", lang), "pays": ""},
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
st.subheader(t("detailed_analysis", lang))
for _, r in risques.sort_values("risque").iterrows():
    color  = "#0D3B27" if r["risque"] <= 4 else "#3B2D0D" if r["risque"] <= 7 else "#3B0D0D"
    border = "#00CC66" if r["risque"] <= 4 else "#FFD700" if r["risque"] <= 7 else "#FF4444"
    st.markdown(f"""
    <div style="background:{color}; padding:12px; border-radius:8px;
                border-left:4px solid {border}; margin:6px 0;">
        <b>{r["flag"]} {r["pays"]}</b> &nbsp;
        {t("risk_label", lang)} : <b>{r["risque"]}/10</b> &nbsp;|&nbsp;
        {r["note"]} &nbsp;|&nbsp;
        {t("impact_brvm", lang)} : <b>{r["impact_brvm"]}</b>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.info(t("warroom_info", lang))
