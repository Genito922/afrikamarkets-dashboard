"""
Page 0 — Profil investisseur + recommandations personnalisées
Conçu pour investisseurs diaspora Canada → BRVM
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.brvm_scraper import get_actions
from frontend.auth_ui import render_auth_sidebar, require_auth

st.set_page_config(page_title="Mon Profil BRVM", layout="wide")

LANG = st.sidebar.selectbox("🌐 Langue / Language", ["Français", "English"])
FR = LANG == "Français"

render_auth_sidebar(fr=FR)
require_auth(fr=FR)

st.title("👤 Mon Profil Investisseur" if FR else "👤 My Investor Profile")
st.markdown(
    "Répondez à 5 questions pour obtenir des recommandations personnalisées BRVM."
    if FR else
    "Answer 5 questions to get personalized BRVM recommendations."
)

st.markdown("---")

# ── Questionnaire ────────────────────────────────────────────
st.subheader("1️⃣ Votre budget d'investissement" if FR else "1️⃣ Your investment budget")
col1, col2 = st.columns(2)
with col1:
    budget_cad = st.slider("Budget disponible (CAD $)" if FR else "Available budget (CAD $)",
                           500, 50000, 5000, step=500)
with col2:
    taux = st.number_input("1 CAD = X FCFA", value=445.0)
    budget_fcfa = budget_cad * taux
    st.metric("Équivalent FCFA", f"{budget_fcfa:,.0f} FCFA")

st.markdown("---")
st.subheader("2️⃣ Votre horizon d'investissement" if FR else "2️⃣ Your investment horizon")
horizon = st.radio(
    "Pour combien de temps ?" if FR else "For how long?",
    ["< 1 an / Short term", "1-3 ans / Medium term", "3-5 ans / Long term", "> 5 ans / Very long term"],
    horizontal=True,
)

st.markdown("---")
st.subheader("3️⃣ Votre tolérance au risque" if FR else "3️⃣ Your risk tolerance")
col3, col4 = st.columns([2,1])
with col3:
    risque = st.select_slider(
        "Si votre investissement perd 20% en 3 mois, vous :" if FR
        else "If your investment drops 20% in 3 months, you would:",
        options=[
            "😰 Vendez tout immédiatement",
            "😟 Vendez une partie",
            "😐 Attendez et observez",
            "😌 Achetez davantage",
            "😎 Doublez la mise",
        ],
    )
with col4:
    score_risque = {
        "😰 Vendez tout immédiatement": 1,
        "😟 Vendez une partie": 2,
        "😐 Attendez et observez": 3,
        "😌 Achetez davantage": 4,
        "😎 Doublez la mise": 5,
    }[risque]
    
    color = ["#FF4444","#FF8C00","#FFD700","#90EE90","#00CC66"][score_risque-1]
    st.markdown(f"""
    <div style="background:{color}20; border:2px solid {color};
                border-radius:10px; padding:15px; text-align:center;">
        <h3 style="color:{color}; margin:0;">
            {"Conservateur" if score_risque==1 else
             "Prudent" if score_risque==2 else
             "Équilibré" if score_risque==3 else
             "Dynamique" if score_risque==4 else
             "Agressif"}
        </h3>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.subheader("4️⃣ Vos objectifs" if FR else "4️⃣ Your objectives")
objectifs = st.multiselect(
    "Que recherchez-vous ?" if FR else "What are you looking for?",
    ["💰 Croissance du capital / Capital growth",
     "📈 Dividendes réguliers / Regular dividends",
     "🛡️ Préservation du capital / Capital preservation",
     "🌍 Investir en Afrique / Invest in Africa",
     "💱 Diversification hors CAD / CAD diversification"],
    default=["💰 Croissance du capital / Capital growth",
             "🌍 Investir en Afrique / Invest in Africa"],
)

st.markdown("---")
st.subheader("5️⃣ Votre disponibilité" if FR else "5️⃣ Your availability")
temps = st.radio(
    "Combien de temps par mois pour suivre vos investissements ?" if FR
    else "How much time per month to monitor investments?",
    ["< 1h (passif / passive)", "1-3h (semi-actif)", "> 3h (actif / active)"],
    horizontal=True,
)

st.markdown("---")

# ── Génération du profil ─────────────────────────────────────
if st.button("🎯 Générer mon profil et mes recommandations" if FR
             else "🎯 Generate my profile and recommendations",
             type="primary", use_container_width=True):

    # Calcul profil
    if score_risque <= 2:
        profil = "CONSERVATEUR"
        profil_color = "#FFD700"
        profil_emoji = "🛡️"
        description = (
            "Vous privilégiez la sécurité du capital. BRVM vous offre des "
            "valeurs bancaires solides et des obligations d'État UEMOA."
            if FR else
            "You prioritize capital safety. BRVM offers solid banking stocks "
            "and UEMOA government bonds."
        )
        secteurs_rec = ["Finance", "Énergie"]
        strategie = "ETF sectoriel Finance BRVM + obligations État CI" if FR else "BRVM Finance sector + CI government bonds"

    elif score_risque == 3:
        profil = "ÉQUILIBRÉ"
        profil_color = "#00BFFF"
        profil_emoji = "⚖️"
        description = (
            "Vous cherchez un équilibre risque/rendement. BRVM offre "
            "des opportunités dans les secteurs Finance et Agriculture."
            if FR else
            "You seek a risk/return balance. BRVM offers opportunities "
            "in Finance and Agriculture sectors."
        )
        secteurs_rec = ["Finance", "Agriculture", "Services"]
        strategie = "Mix Finance 50% + Agriculture 30% + Services 20%"

    else:
        profil = "DYNAMIQUE"
        profil_color = "#00CC66"
        profil_emoji = "🚀"
        description = (
            "Vous acceptez la volatilité pour maximiser le rendement. "
            "BRVM Principal +57% en 2025 — c'est votre univers."
            if FR else
            "You accept volatility for maximum returns. "
            "BRVM Principal +57% in 2025 — this is your universe."
        )
        secteurs_rec = ["Agriculture", "Industrie", "Télécoms"]
        strategie = "BRVM Principal — titres croissance forte"

    # Affichage profil
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {profil_color}20, {profil_color}10);
                border: 2px solid {profil_color}; border-radius: 15px;
                padding: 25px; text-align: center; margin: 20px 0;">
        <h1 style="color:{profil_color}; margin:0;">{profil_emoji} {profil}</h1>
        <p style="color:white; font-size:1.1em; margin:10px 0;">{description}</p>
    </div>
    """, unsafe_allow_html=True)

    # Recommandations chiffrées
    st.subheader("📊 Allocation recommandée" if FR else "📊 Recommended Allocation")

    df_actions = get_actions()

    col_a, col_b = st.columns(2)

    with col_a:
        # Allocation budget
        if score_risque <= 2:
            allocations = {"Actions BRVM": 40, "Obligations État": 40, "Liquidités": 20}
        elif score_risque == 3:
            allocations = {"Actions BRVM": 60, "Obligations État": 25, "Liquidités": 15}
        else:
            allocations = {"Actions BRVM": 80, "Obligations État": 10, "Liquidités": 10}

        fig_alloc = px.pie(
            values=list(allocations.values()),
            names=list(allocations.keys()),
            color_discrete_sequence=["#00CC66", "#FFD700", "#00BFFF"],
            title=f"Allocation recommandée — Budget ${budget_cad:,} CAD",
        )
        fig_alloc.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
        )
        st.plotly_chart(fig_alloc, use_container_width=True)

    with col_b:
        st.markdown(f"""
        **{"Votre profil en chiffres" if FR else "Your profile in numbers"}**

        | {"Paramètre" if FR else "Parameter"} | {"Valeur" if FR else "Value"} |
        |---|---|
        | Budget | ${budget_cad:,} CAD = {budget_fcfa:,.0f} FCFA |
        | Horizon | {horizon} |
        | Profil | {profil} |
        | {"Actions BRVM" if FR else "BRVM Equities"} | {allocations["Actions BRVM"]}% = ${budget_cad * allocations["Actions BRVM"] / 100:,.0f} CAD |
        | {"Stratégie" if FR else "Strategy"} | {strategie} |
        | {"Suivi mensuel" if FR else "Monthly monitoring"} | {temps} |
        """)

    # Titres recommandés
    if not df_actions.empty:
        st.markdown("---")
        st.subheader("🎯 Titres recommandés pour votre profil" if FR
                     else "🎯 Recommended stocks for your profile")

        budget_actions_fcfa = budget_fcfa * allocations["Actions BRVM"] / 100
        df_rec = df_actions[df_actions["secteur"].isin(secteurs_rec)].copy()
        df_rec = df_rec[df_rec["cours"] > 0].sort_values("variation", ascending=False)

        if not df_rec.empty:
            # Pondération équipondérée
            n = min(5, len(df_rec))
            df_top = df_rec.head(n).copy()
            df_top["allocation_fcfa"] = budget_actions_fcfa / n
            df_top["nb_actions"] = (df_top["allocation_fcfa"] / df_top["cours"]).astype(int)
            df_top["cout_reel"] = df_top["nb_actions"] * df_top["cours"]

            for _, r in df_top.iterrows():
                signal_color = "#00CC66" if r["variation"] > 0 else "#FF4444" if r["variation"] < 0 else "#FFD700"
                st.markdown(f"""
                <div style="background:#1A1D2E; padding:12px; border-radius:8px;
                            border-left:4px solid {signal_color}; margin:6px 0;
                            display:flex; justify-content:space-between;">
                    <span>
                        <b>{r["symbole"]}</b> — {r["nom"][:40]}<br>
                        <small>{r["secteur"]} | {r["cours"]:,.0f} FCFA/action</small>
                    </span>
                    <span style="text-align:right;">
                        <b>{r["nb_actions"]} actions</b><br>
                        <small style="color:{signal_color};">{r["variation"]:+.2f}% aujourd'hui</small>
                    </span>
                </div>
                """, unsafe_allow_html=True)

            total_investi = df_top["cout_reel"].sum()
            st.success(
                f"💼 Portefeuille suggéré : {total_investi:,.0f} FCFA "
                f"({total_investi/taux:,.0f} CAD) sur {n} titres"
                if FR else
                f"💼 Suggested portfolio: {total_investi:,.0f} FCFA "
                f"({total_investi/taux:,.0f} CAD) across {n} stocks"
            )

    # Message rassurant
    st.markdown("---")
    st.info(
        """💡 **Pas besoin de 1 million pour investir en bourse.**
        
        Avec BRVM, vous pouvez commencer avec quelques centaines de dollars canadiens.
        Un broker agréé SGI à Abidjan peut exécuter vos ordres à distance.
        Ce dashboard vous donne l'analyse — vous gardez le contrôle."""
        if FR else
        """💡 **You don't need $1M to invest in the stock market.**
        
        With BRVM, you can start with a few hundred Canadian dollars.
        A licensed SGI broker in Abidjan can execute your orders remotely.
        This dashboard gives you the analysis — you keep control."""
    )
