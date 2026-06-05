"""
Page 5 — War Room : Risques géopolitiques UEMOA
Données réelles : ACLED (sécurité) + IMF (macro) + fallback statique
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from frontend.auth_ui import render_auth_sidebar, require_plan
from utils.i18n import t, get_lang
from utils.warroom_data import get_warroom_data, get_cache_status

st.set_page_config(page_title="War Room BRVM", layout="wide")

lang = get_lang()
FR   = lang == "fr"

render_auth_sidebar(fr=FR)
require_plan("pro", fr=FR)

# ── Header ────────────────────────────────────────────────────────────────────
st.title(t("warroom_title", lang))

# ── Chargement données ────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    return get_warroom_data()

with st.spinner("🌍 Chargement données ACLED + IMF…"):
    rows = load_data()

risques = pd.DataFrame(rows)

# Traduction impact
IMPACT_LABELS = {
    "fort":   {"fr": "Fort",   "en": "High",   "es": "Alto",  "pt": "Alto",  "zh": "高",   "ar": "عالي"},
    "moyen":  {"fr": "Moyen",  "en": "Medium", "es": "Medio", "pt": "Médio", "zh": "中等", "ar": "متوسط"},
    "faible": {"fr": "Faible", "en": "Low",    "es": "Bajo",  "pt": "Baixo", "zh": "低",   "ar": "منخفض"},
}
risques["impact_label"] = risques["impact_brvm"].map(
    lambda k: IMPACT_LABELS.get(k, {}).get(lang, k)
)

# ── Source indicator ──────────────────────────────────────────────────────────
sources = risques["source"].unique()
has_live = "ACLED+IMF" in sources
cache    = get_cache_status()

col_src, col_upd = st.columns([3, 1])
with col_src:
    if has_live:
        st.success("📡 Données live — ACLED (sécurité 90j) + IMF (macro 2025)")
    else:
        st.warning("⚠️ APIs indisponibles — données estimées. Configurez ACLED_API_KEY + ACLED_EMAIL.")
with col_upd:
    if rows:
        st.caption(f"🕐 {rows[0]['updated_at']}")

# ── KPIs ──────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
stables  = risques[risques["risque"] <= 3]
fragiles = risques[(risques["risque"] > 3) & (risques["risque"] <= 6)]
risques_ = risques[risques["risque"] > 6]

col1.metric(t("stable_countries", lang),    len(stables),  help="Score ≤ 3/10")
col2.metric(t("fragile_countries", lang),   len(fragiles), help="Score 4–6/10")
col3.metric(t("high_risk_countries", lang), len(risques_), help="Score > 6/10")
avg_events = int(risques["events_90d"].mean())
col4.metric("📊 Événements moy. 90j", avg_events, help="Source ACLED")

st.markdown("---")

# ── Graphiques ────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    t("risk_map_title", lang),
    "📈 Données macro IMF",
    "🔒 Événements sécuritaires"
])

with tab1:
    fig_risk = px.bar(
        risques.sort_values("risque", ascending=True),
        x="risque",
        y="pays",
        orientation="h",
        color="risque",
        color_continuous_scale=["#00CC66", "#FFD700", "#FF4444"],
        text="note",
        title=t("risk_chart_label", lang),
        labels={"risque": t("risk_level", lang), "pays": ""},
        hover_data={"events_90d": True, "gdp_growth": True, "inflation": True},
    )
    fig_risk.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        coloraxis_showscale=False,
        height=380,
    )
    fig_risk.update_traces(textposition="outside")
    st.plotly_chart(fig_risk, use_container_width=True)

with tab2:
    fig_macro = go.Figure()
    fig_macro.add_trace(go.Bar(
        name="Croissance PIB (%)",
        x=risques["pays"],
        y=risques["gdp_growth"],
        marker_color="#00CC66",
        text=risques["gdp_growth"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    ))
    fig_macro.add_trace(go.Bar(
        name="Inflation (%)",
        x=risques["pays"],
        y=risques["inflation"],
        marker_color="#FF8C00",
        text=risques["inflation"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    ))
    fig_macro.update_layout(
        barmode="group",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        height=380,
        legend=dict(orientation="h", y=1.1),
        title="Indicateurs macro IMF 2025 — Zone UEMOA",
    )
    st.plotly_chart(fig_macro, use_container_width=True)
    st.caption("Source : FMI World Economic Outlook Database")

with tab3:
    fig_acled = px.bar(
        risques.sort_values("events_90d", ascending=False),
        x="pays",
        y="events_90d",
        color="events_90d",
        color_continuous_scale=["#00CC66", "#FFD700", "#FF4444"],
        title="Événements sécuritaires ACLED — 90 derniers jours",
        labels={"events_90d": "Nb événements", "pays": ""},
        text="events_90d",
    )
    fig_acled.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        coloraxis_showscale=False,
        height=380,
    )
    fig_acled.update_traces(textposition="outside")
    st.plotly_chart(fig_acled, use_container_width=True)
    st.caption("Source : ACLED (Armed Conflict Location & Event Data Project)")

st.markdown("---")

# ── Tableau détaillé ──────────────────────────────────────────────────────────
st.subheader(t("detailed_analysis", lang))

for _, r in risques.sort_values("risque").iterrows():
    color  = "#0D3B27" if r["risque"] <= 3 else "#3B2D0D" if r["risque"] <= 6 else "#3B0D0D"
    border = "#00CC66" if r["risque"] <= 3 else "#FFD700" if r["risque"] <= 6 else "#FF4444"
    src_badge = "🔴 Live" if r["source"] == "ACLED+IMF" else "📌 Estimé"

    st.markdown(f"""
    <div style="background:{color}; padding:14px 16px; border-radius:8px;
                border-left:4px solid {border}; margin:6px 0;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span>
                <b style="font-size:1.05em">{r["flag"]} {r["pays"]}</b>
                &nbsp;&nbsp;
                <span style="font-size:.85em; opacity:.8">{src_badge}</span>
            </span>
            <span style="color:{border}; font-weight:700; font-size:1.1em">{r["risque"]}/10</span>
        </div>
        <div style="margin-top:6px; font-size:.9em; opacity:.85;">
            📌 {r["note"]}
            &nbsp;|&nbsp;
            {t("impact_brvm", lang)} BRVM : <b>{r["impact_label"]}</b>
            &nbsp;|&nbsp;
            🔫 {r["events_90d"]} événements (90j)
            &nbsp;|&nbsp;
            📈 PIB {r["gdp_growth"]}%
            &nbsp;|&nbsp;
            💹 Inflation {r["inflation"]}%
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── Info footer ───────────────────────────────────────────────────────────────
st.info(t("warroom_info", lang))

with st.expander("🔧 Statut APIs & Cache"):
    c1, c2 = st.columns(2)
    c1.metric("ACLED", cache.get("acled", "Non chargé"))
    c2.metric("IMF",   cache.get("imf",   "Non chargé"))

    if not has_live:
        st.markdown("""
        **Pour activer les données live :**
        1. Crée un compte gratuit sur [acleddata.com](https://acleddata.com/register)
        2. Récupère ta clé API
        3. Ajoute dans Railway → Variables :
           ```
           ACLED_API_KEY = ta_clé
           ACLED_EMAIL   = ton@email.com
           ```
        4. Les données IMF sont publiques (aucune clé requise)
        """)
