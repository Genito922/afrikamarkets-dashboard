"""
Page 4 — Simulateur de portefeuille BRVM
Pour investisseurs diaspora Canada
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.brvm_scraper import get_actions
from frontend.auth_ui import render_auth_sidebar, require_plan

st.set_page_config(page_title="Portefeuille BRVM", layout="wide")
LANG = st.sidebar.selectbox("🌐 Langue / Language", ["Français", "English"])
FR = LANG == "Français"

render_auth_sidebar(fr=FR)
require_plan("starter", fr=FR)

st.title("💼 Simulateur de Portefeuille" if FR else "💼 Portfolio Simulator")
st.markdown(
    "Construisez et simulez un portefeuille BRVM depuis le Canada." if FR
    else "Build and simulate a BRVM portfolio from Canada."
)

df = get_actions()
if df.empty:
    st.error("Données indisponibles")
    st.stop()

# ── Paramètres ───────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Paramètres" if FR else "⚙️ Settings")
budget_cad = st.sidebar.number_input(
    "Budget (CAD $)" if FR else "Budget (CAD $)",
    min_value=1000, max_value=500000, value=10000, step=1000
)
taux_xof = st.sidebar.number_input("1 CAD = X FCFA", value=445.0, step=1.0)
budget_fcfa = budget_cad * taux_xof

st.sidebar.metric(
    "Budget en FCFA",
    f"{budget_fcfa:,.0f} FCFA"
)

# ── Sélection titres ─────────────────────────────────────────
st.subheader("Sélection des titres" if FR else "Stock Selection")
titres_dispo = df["symbole"].tolist()
format_fn = lambda x: f"{x} — {df[df['symbole']==x]['nom'].values[0][:40]} ({df[df['symbole']==x]['cours'].values[0]:,.0f} FCFA)"

titres_choisis = st.multiselect(
    "Choisir les titres du portefeuille" if FR else "Choose portfolio stocks",
    titres_dispo,
    default=titres_dispo[:3],
    format_func=format_fn,
)

if not titres_choisis:
    st.warning("Sélectionnez au moins un titre" if FR else "Select at least one stock")
    st.stop()

# ── Allocation ───────────────────────────────────────────────
st.subheader("Allocation du portefeuille" if FR else "Portfolio Allocation")
df_sel = df[df["symbole"].isin(titres_choisis)].copy()

allocations = {}
cols = st.columns(len(titres_choisis))
total_pct = 0
for i, sym in enumerate(titres_choisis):
    with cols[i]:
        pct = st.slider(f"{sym} (%)", 0, 100, 100 // len(titres_choisis), key=f"alloc_{sym}")
        allocations[sym] = pct
        total_pct += pct

# Vérification allocation
if total_pct != 100:
    st.warning(f"Total allocation : {total_pct}% (doit être 100%)" if FR
               else f"Total allocation: {total_pct}% (must be 100%)")

# ── Résultats portefeuille ────────────────────────────────────
st.markdown("---")
st.subheader("📊 Résultats" if FR else "📊 Results")

rows = []
for sym in titres_choisis:
    row = df_sel[df_sel["symbole"] == sym].iloc[0]
    pct_alloc = allocations[sym] / 100
    montant_fcfa = budget_fcfa * pct_alloc
    montant_cad = budget_cad * pct_alloc
    nb_actions = int(montant_fcfa // row["cours"]) if row["cours"] > 0 else 0
    cout_reel = nb_actions * row["cours"]
    pnl_jour = nb_actions * (row["cours"] - row["cours_veille"])

    rows.append({
        "Symbole": sym,
        "Société" if FR else "Company": row["nom"][:35],
        "Alloc %": f"{allocations[sym]}%",
        "Montant CAD": montant_cad,
        "Montant FCFA": cout_reel,
        "Nb actions" if FR else "Shares": nb_actions,
        "Cours (FCFA)": row["cours"],
        "Var %": row["variation"],
        "P&L jour (FCFA)" if FR else "Daily P&L (FCFA)": pnl_jour,
    })

df_result = pd.DataFrame(rows)

# Métriques globales
total_investi = df_result["Montant FCFA"].sum()
total_pnl = df_result["P&L jour (FCFA)" if FR else "Daily P&L (FCFA)"].sum()
total_pnl_cad = total_pnl / taux_xof

c1, c2, c3, c4 = st.columns(4)
c1.metric("Budget CAD", f"${budget_cad:,.0f}")
c2.metric("Investi FCFA" if FR else "Invested FCFA", f"{total_investi:,.0f}")
c3.metric("P&L journalier" if FR else "Daily P&L",
          f"{total_pnl:+,.0f} FCFA",
          delta=f"${total_pnl_cad:+,.0f} CAD")
c4.metric("Liquidités FCFA" if FR else "Cash FCFA",
          f"{budget_fcfa - total_investi:,.0f}")

# Graphiques
col1, col2 = st.columns(2)
with col1:
    fig_pie = px.pie(
        df_result, values="Montant FCFA", names="Symbole",
        title="Répartition du portefeuille" if FR else "Portfolio Allocation",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    pnl_col = "P&L jour (FCFA)" if FR else "Daily P&L (FCFA)"
    colors = ["#00CC66" if v >= 0 else "#FF4444" for v in df_result[pnl_col]]
    fig_pnl = go.Figure(go.Bar(
        x=df_result["Symbole"],
        y=df_result[pnl_col],
        marker_color=colors,
        text=[f"{v:+,.0f}" for v in df_result[pnl_col]],
        textposition="outside",
    ))
    fig_pnl.update_layout(
        title="P&L journalier par titre" if FR else "Daily P&L by Stock",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        height=300,
    )
    st.plotly_chart(fig_pnl, use_container_width=True)

# Tableau détaillé
st.dataframe(
    df_result.style.format({
        "Montant CAD": "${:,.0f}",
        "Montant FCFA": "{:,.0f}",
        "Cours (FCFA)": "{:,.0f}",
        "Var %": "{:.2f}%",
        pnl_col: "{:+,.0f}",
    }).background_gradient(subset=["Var %"], cmap="RdYlGn"),
    use_container_width=True,
)
