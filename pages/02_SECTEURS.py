"""
Page 2 — Analyse sectorielle BRVM
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.brvm_scraper import get_actions, get_indices

st.set_page_config(page_title="Secteurs BRVM", layout="wide")
LANG = st.sidebar.selectbox("🌐 Langue / Language", ["Français", "English"])
FR = LANG == "Français"

st.title("🏭 Analyse Sectorielle BRVM" if FR else "🏭 BRVM Sector Analysis")

df = get_actions()
indices = get_indices()

# ── Performance sectorielle depuis les indices ────────────────
if indices["sectoriel"]:
    df_sec = pd.DataFrame(indices["sectoriel"])
    df_sec["nom"] = df_sec["nom"].str.replace("BRVM - ", "").str.replace("BRVM – ", "")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Performance YTD par secteur" if FR else "YTD Sector Performance")
        fig = px.bar(
            df_sec.sort_values("var_ytd"),
            x="var_ytd", y="nom",
            orientation="h",
            color="var_ytd",
            color_continuous_scale=["#FF4444", "#FFD700", "#00CC66"],
            labels={"var_ytd": "Variation YTD (%)", "nom": ""},
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            coloraxis_showscale=False,
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Variation journalière" if FR else "Daily Variation")
        colors = ["#00CC66" if v >= 0 else "#FF4444" for v in df_sec["variation"]]
        fig2 = go.Figure(go.Bar(
            x=df_sec["variation"],
            y=df_sec["nom"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.2f}%" for v in df_sec["variation"]],
            textposition="outside",
        ))
        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            height=350,
        )
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Composition par secteur ───────────────────────────────────
if not df.empty:
    st.subheader("Composition du marché par secteur" if FR else "Market Composition by Sector")

    df_comp = df.groupby("secteur").agg(
        nb_titres=("symbole", "count"),
        volume_total=("volume", "sum"),
        variation_moy=("variation", "mean"),
    ).reset_index()

    col3, col4 = st.columns(2)
    with col3:
        fig3 = px.pie(
            df_comp, values="nb_titres", names="secteur",
            title="Nombre de titres par secteur" if FR else "Number of stocks by sector",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        fig4 = px.pie(
            df_comp, values="volume_total", names="secteur",
            title="Volume échangé par secteur" if FR else "Trading volume by sector",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig4, use_container_width=True)

    # Tableau synthèse
    st.dataframe(
        df_comp.sort_values("variation_moy", ascending=False).rename(columns={
            "secteur": "Secteur" if FR else "Sector",
            "nb_titres": "Nb titres" if FR else "# Stocks",
            "volume_total": "Volume total",
            "variation_moy": "Var moy (%) / Avg Var (%)",
        }).style.format({
            "Volume total": "{:,.0f}",
            "Var moy (%) / Avg Var (%)": "{:.2f}%",
        }),
        use_container_width=True,
    )
