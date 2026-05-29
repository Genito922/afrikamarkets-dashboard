"""
Afrika Markets Intelligence — Dashboard principal
Investment Intelligence Platform for African Frontier Markets
"""
import streamlit as st
from data.brvm_scraper import get_actions, get_indices, get_marche
from frontend.auth_ui import render_auth_sidebar
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd

st.set_page_config(
    page_title="Afrika Markets Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Langue ──────────────────────────────────────────────────
LANG = st.sidebar.selectbox("🌐 Langue / Language", ["Français", "English"])
FR = LANG == "Français"

T = {
    "title":        "Afrika Markets Intelligence",
    "subtitle":     "Investment Intelligence Platform — Marchés Frontier Africains" if FR else "Investment Intelligence Platform for African Frontier Markets",
    "refresh":      "🔄 Actualiser" if FR else "🔄 Refresh",
    "cap_actions":  "Capitalisation Actions" if FR else "Market Cap (Equities)",
    "cap_oblig":    "Capitalisation Obligations" if FR else "Market Cap (Bonds)",
    "transactions": "Transactions du jour" if FR else "Daily Transactions",
    "top5":         "🏆 Top 5 Performances" if FR else "🏆 Top 5 Performers",
    "flop5":        "📉 Flop 5" if FR else "📉 Bottom 5",
    "indices":      "📊 Indices BRVM" if FR else "📊 BRVM Indices",
    "sectoriel":    "🏭 Performance Sectorielle" if FR else "🏭 Sector Performance",
    "maj":          "Dernière mise à jour" if FR else "Last updated",
}

# ── Header ──────────────────────────────────────────────────
st.markdown(f"""
<div style='background: linear-gradient(135deg, #006B3F, #FFD700);
     padding: 20px; border-radius: 12px; margin-bottom: 20px;'>
    <h1 style='color:white; margin:0;'>🌍 {T["title"]}</h1>
    <p style='color:rgba(255,255,255,0.85); margin:5px 0 0;'>{T["subtitle"]}</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────
st.sidebar.image("https://www.brvm.org/sites/default/files/brvm_logo.png", width=150)
st.sidebar.markdown("---")
if st.sidebar.button(T["refresh"]):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown(f"*{T['maj']} : {datetime.now().strftime('%H:%M:%S')}*")

render_auth_sidebar(fr=FR)

# ── Chargement données ───────────────────────────────────────
with st.spinner("Chargement données BRVM..." if FR else "Loading BRVM data..."):
    df = get_actions()
    indices = get_indices()
    marche = get_marche()

# ── KPIs marché ──────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    val = marche.get("Capitalisation Actions", "N/A")
    st.metric(T["cap_actions"], val)
with col2:
    val = marche.get("Capitalisation des obligations", "N/A")
    st.metric(T["cap_oblig"], val)
with col3:
    val = marche.get("Valeur des transactions", "N/A")
    st.metric(T["transactions"], val)

st.markdown("---")

# ── Indices ──────────────────────────────────────────────────
st.subheader(T["indices"])
if indices["marche"]:
    cols = st.columns(len(indices["marche"]))
    for i, idx in enumerate(indices["marche"]):
        with cols[i]:
            st.metric(
                label=idx["nom"],
                value=f"{idx['cloture']:.2f}",
                delta=f"{idx['variation']:+.2f}%",
            )

st.markdown("---")

# ── Performance sectorielle ──────────────────────────────────
st.subheader(T["sectoriel"])
if indices["sectoriel"]:
    df_sec = pd.DataFrame(indices["sectoriel"])
    df_sec["nom"] = df_sec["nom"].str.replace("BRVM - ", "").str.replace("BRVM – ", "")
    fig = px.bar(
        df_sec.sort_values("var_ytd"),
        x="var_ytd", y="nom",
        orientation="h",
        color="var_ytd",
        color_continuous_scale=["#FF4444", "#FFD700", "#00CC66"],
        title="Performance YTD par secteur (%)" if FR else "YTD Performance by Sector (%)",
        labels={"var_ytd": "Variation YTD (%)", "nom": ""},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        height=350,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Top 5 / Flop 5 ───────────────────────────────────────────
col_top, col_flop = st.columns(2)

if not df.empty:
    top5  = df.nlargest(5, "variation")
    flop5 = df.nsmallest(5, "variation")

    with col_top:
        st.subheader(T["top5"])
        for _, r in top5.iterrows():
            st.markdown(f"""
            <div style='background:#0D3B27; padding:10px; border-radius:8px;
                        border-left:4px solid #00CC66; margin:5px 0;'>
                <b>{r["symbole"]}</b> — {r["nom"][:35]}<br>
                <span style="color:#00CC66; font-size:1.2em;">
                    {r["cours"]:,.0f} FCFA &nbsp; +{r["variation"]:.2f}%
                </span>
            </div>""", unsafe_allow_html=True)

    with col_flop:
        st.subheader(T["flop5"])
        for _, r in flop5.iterrows():
            st.markdown(f"""
            <div style='background:#3B0D0D; padding:10px; border-radius:8px;
                        border-left:4px solid #FF4444; margin:5px 0;'>
                <b>{r["symbole"]}</b> — {r["nom"][:35]}<br>
                <span style="color:#FF4444; font-size:1.2em;">
                    {r["cours"]:,.0f} FCFA &nbsp; {r["variation"]:.2f}%
                </span>
            </div>""", unsafe_allow_html=True)