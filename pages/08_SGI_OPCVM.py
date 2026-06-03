"""
Page 8 — SGI & OPCVM Intelligence Center
Classement SGI, recommandation IA, screener OPCVM, matching investisseur
Réservé aux plans Pro et supérieur
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from frontend.auth_ui import render_auth_sidebar, require_plan
from utils.i18n import t, get_lang

st.set_page_config(page_title="SGI & OPCVM — Afrika Markets", layout="wide")

lang = get_lang()
FR   = lang == "fr"

render_auth_sidebar(fr=FR)
require_plan("pro", fr=FR)

# ── Données SGI ──────────────────────────────────────────────────────────────

WEIGHTS = {
    "frais":             0.25,
    "facilite_ouverture": 0.15,
    "app_mobile":        0.10,
    "service_client":    0.15,
    "recherche":         0.15,
    "rapidite":          0.10,
    "reputation":        0.10,
}

SGI_DATA = [
    {
        "nom": "NSIA Finance",
        "pays": "Côte d'Ivoire",
        "founded": 2001,
        "courtage": "0.80%",
        "depot_min": 100_000,
        "presence_diaspora": True,
        "ouverture_en_ligne": True,
        "app_mobile": True,
        "scores": {
            "frais": 8.0, "facilite_ouverture": 9.0, "app_mobile": 9.5,
            "service_client": 8.5, "recherche": 8.0, "rapidite": 8.5, "reputation": 9.0,
        },
        "strengths_fr": ["Ouverture 100 % en ligne", "App mobile bien notée", "Présence diaspora Canada/France"],
        "strengths_en": ["100% online account opening", "Well-rated mobile app", "Diaspora-friendly (Canada/France)"],
        "weaknesses_fr": ["Frais légèrement supérieurs aux boutiques", "Support en heures ouvrées uniquement"],
        "weaknesses_en": ["Fees slightly above boutique brokers", "Support during business hours only"],
        "url": "https://www.nsiafinance.com",
    },
    {
        "nom": "Hudson & Cie",
        "pays": "Côte d'Ivoire",
        "founded": 1998,
        "courtage": "0.70%",
        "depot_min": 500_000,
        "presence_diaspora": False,
        "ouverture_en_ligne": False,
        "app_mobile": False,
        "scores": {
            "frais": 9.0, "facilite_ouverture": 4.5, "app_mobile": 3.0,
            "service_client": 9.0, "recherche": 9.5, "rapidite": 7.5, "reputation": 9.5,
        },
        "strengths_fr": ["Recherche de pointe", "Clientèle institutionnelle", "Réputation historique BRVM"],
        "strengths_en": ["Cutting-edge research", "Institutional client base", "Historical BRVM reputation"],
        "weaknesses_fr": ["Pas d'ouverture en ligne", "Dépôt minimum élevé", "Non adapté à la diaspora"],
        "weaknesses_en": ["No online account opening", "High minimum deposit", "Not diaspora-friendly"],
        "url": "https://www.hudsonetcie.com",
    },
    {
        "nom": "CGF Bourse",
        "pays": "Côte d'Ivoire",
        "founded": 1994,
        "courtage": "0.65%",
        "depot_min": 50_000,
        "presence_diaspora": False,
        "ouverture_en_ligne": True,
        "app_mobile": False,
        "scores": {
            "frais": 9.5, "facilite_ouverture": 7.0, "app_mobile": 2.0,
            "service_client": 7.5, "recherche": 7.5, "rapidite": 8.0, "reputation": 8.5,
        },
        "strengths_fr": ["Frais parmi les plus bas BRVM", "Dépôt minimum accessible", "Ancienneté et fiabilité"],
        "strengths_en": ["Among the lowest BRVM fees", "Accessible minimum deposit", "Track record and reliability"],
        "weaknesses_fr": ["Pas d'application mobile", "Interface web datée", "Support lent"],
        "weaknesses_en": ["No mobile app", "Outdated web interface", "Slow support"],
        "url": "https://www.cgfbourse.com",
    },
    {
        "nom": "BOA Capital Securities",
        "pays": "Mali",
        "founded": 2010,
        "courtage": "0.85%",
        "depot_min": 100_000,
        "presence_diaspora": True,
        "ouverture_en_ligne": True,
        "app_mobile": True,
        "scores": {
            "frais": 7.5, "facilite_ouverture": 8.5, "app_mobile": 8.0,
            "service_client": 8.0, "recherche": 7.0, "rapidite": 8.5, "reputation": 8.0,
        },
        "strengths_fr": ["Réseau bancaire BOA (13 pays)", "Idéal pour débutants", "Accès diaspora Afrique de l'Ouest"],
        "strengths_en": ["BOA banking network (13 countries)", "Ideal for beginners", "West African diaspora access"],
        "weaknesses_fr": ["Frais légèrement élevés", "Recherche limitée vs indépendants", "Couverture partielle BRVM"],
        "weaknesses_en": ["Slightly high fees", "Limited research vs independents", "Partial BRVM coverage"],
        "url": "https://www.boacapitalsecurities.com",
    },
    {
        "nom": "Coris Bourse",
        "pays": "Burkina Faso",
        "founded": 2008,
        "courtage": "0.75%",
        "depot_min": 75_000,
        "presence_diaspora": True,
        "ouverture_en_ligne": True,
        "app_mobile": False,
        "scores": {
            "frais": 8.5, "facilite_ouverture": 7.5, "app_mobile": 3.5,
            "service_client": 7.5, "recherche": 6.5, "rapidite": 7.5, "reputation": 7.5,
        },
        "strengths_fr": ["Solide réseau Coris Bank", "Bon rapport qualité/prix", "Accessible diaspora Burkina"],
        "strengths_en": ["Strong Coris Bank network", "Good value for money", "Burkina Faso diaspora access"],
        "weaknesses_fr": ["Pas d'app mobile", "Recherche macro limitée", "Couverture géographique restreinte"],
        "weaknesses_en": ["No mobile app", "Limited macro research", "Restricted geographic coverage"],
        "url": "https://www.corisbourse.com",
    },
    {
        "nom": "Africabourse",
        "pays": "Côte d'Ivoire",
        "founded": 2015,
        "courtage": "0.72%",
        "depot_min": 50_000,
        "presence_diaspora": True,
        "ouverture_en_ligne": True,
        "app_mobile": True,
        "scores": {
            "frais": 8.8, "facilite_ouverture": 9.0, "app_mobile": 8.5,
            "service_client": 7.0, "recherche": 6.0, "rapidite": 9.0, "reputation": 7.0,
        },
        "strengths_fr": ["Plateforme digitale moderne", "Ouverture 100 % en ligne", "Exécution rapide des ordres"],
        "strengths_en": ["Modern digital platform", "100% online opening", "Fast order execution"],
        "weaknesses_fr": ["Structure plus récente", "Recherche en développement", "Service client perfectible"],
        "weaknesses_en": ["Newer structure", "Research still developing", "Customer service needs improvement"],
        "url": "https://www.africabourse.net",
    },
    {
        "nom": "Sogebourse",
        "pays": "Côte d'Ivoire",
        "founded": 2000,
        "courtage": "0.90%",
        "depot_min": 200_000,
        "presence_diaspora": False,
        "ouverture_en_ligne": False,
        "app_mobile": False,
        "scores": {
            "frais": 7.0, "facilite_ouverture": 5.0, "app_mobile": 2.0,
            "service_client": 8.5, "recherche": 8.5, "rapidite": 7.0, "reputation": 9.0,
        },
        "strengths_fr": ["Appui Société Générale", "Service client premium", "Sérieux institutionnel"],
        "strengths_en": ["Société Générale backing", "Premium customer service", "Institutional credibility"],
        "weaknesses_fr": ["Frais élevés", "Pas d'ouverture en ligne", "Pas adapté à la diaspora"],
        "weaknesses_en": ["High fees", "No online opening", "Not diaspora-friendly"],
        "url": "https://www.sogebourse.sn",
    },
    {
        "nom": "Impaxis Securities",
        "pays": "Sénégal",
        "founded": 2007,
        "courtage": "0.80%",
        "depot_min": 150_000,
        "presence_diaspora": True,
        "ouverture_en_ligne": True,
        "app_mobile": False,
        "scores": {
            "frais": 8.0, "facilite_ouverture": 7.0, "app_mobile": 2.0,
            "service_client": 8.0, "recherche": 9.0, "rapidite": 7.5, "reputation": 8.5,
        },
        "strengths_fr": ["Recherche macroéconomique reconnue", "Présence forte au Sénégal", "Accès diaspora France/Belgique"],
        "strengths_en": ["Recognized macroeconomic research", "Strong Senegalese presence", "France/Belgium diaspora access"],
        "weaknesses_fr": ["Pas d'app mobile", "Dépôt minimum modéré", "Délais de traitement variables"],
        "weaknesses_en": ["No mobile app", "Moderate minimum deposit", "Variable processing times"],
        "url": "https://www.impaxis.com",
    },
]

def calc_score_global(scores: dict) -> float:
    return round(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS), 2)

def score_for_profile(sgi: dict, profile: dict) -> float:
    base = calc_score_global(sgi["scores"])
    bonus = 0.0
    if profile.get("diaspora") and sgi["presence_diaspora"]:
        bonus += 0.5
    if profile.get("amount", 0) < 500_000 and sgi["depot_min"] <= 100_000:
        bonus += 0.3
    if profile.get("experience") == "beginner" and sgi["ouverture_en_ligne"]:
        bonus += 0.3
    if profile.get("experience") == "beginner" and sgi["app_mobile"]:
        bonus += 0.2
    if profile.get("advice") == "yes" and sgi["scores"]["service_client"] >= 8.0:
        bonus += 0.4
    if profile.get("style") == "active" and sgi["scores"]["rapidite"] >= 8.5:
        bonus += 0.3
    if profile.get("style") == "longterm" and sgi["scores"]["recherche"] >= 8.5:
        bonus += 0.3
    if profile.get("experience") == "expert" and sgi["scores"]["recherche"] >= 9.0:
        bonus += 0.3
    return round(min(base + bonus, 10.0), 2)

# ── Données OPCVM ────────────────────────────────────────────────────────────

OPCVM_DATA = [
    {
        "nom": "SICAV ACTIONS BRVM",
        "gestionnaire": "NSIA Finance",
        "categorie": "actions",
        "risque": 4,
        "perf_1y": 12.4,
        "perf_3y": 38.7,
        "capital_min": 100_000,
        "frais_gestion": "1.50%",
        "liquidite": "hebdomadaire",
        "ai_score": 8.2,
        "desc_fr": "Exposition directe aux actions cotées BRVM. Idéal pour investisseurs dynamiques long terme.",
        "desc_en": "Direct exposure to BRVM-listed equities. Ideal for dynamic long-term investors.",
    },
    {
        "nom": "FCP OBLIGATAIRE UEMOA",
        "gestionnaire": "Hudson & Cie",
        "categorie": "obligataire",
        "risque": 2,
        "perf_1y": 6.1,
        "perf_3y": 18.9,
        "capital_min": 50_000,
        "frais_gestion": "0.80%",
        "liquidite": "mensuelle",
        "ai_score": 7.8,
        "desc_fr": "Obligations d'État et d'entreprises UEMOA. Rendement stable, risque limité.",
        "desc_en": "WAEMU government and corporate bonds. Stable yield, limited risk.",
    },
    {
        "nom": "SICAV DIVERSIFIÉE AFRICA GROWTH",
        "gestionnaire": "CGF Bourse",
        "categorie": "diversifie",
        "risque": 3,
        "perf_1y": 9.3,
        "perf_3y": 28.1,
        "capital_min": 75_000,
        "frais_gestion": "1.20%",
        "liquidite": "bimensuelle",
        "ai_score": 8.5,
        "desc_fr": "Mix actions (60%) + obligations (40%) sur marchés UEMOA. Équilibre rendement/risque.",
        "desc_en": "Mix of equities (60%) + bonds (40%) across WAEMU markets. Balanced return/risk.",
    },
    {
        "nom": "FCP MONÉTAIRE SÉCURITÉ",
        "gestionnaire": "BOA Capital Securities",
        "categorie": "monetaire",
        "risque": 1,
        "perf_1y": 4.2,
        "perf_3y": 12.8,
        "capital_min": 25_000,
        "frais_gestion": "0.50%",
        "liquidite": "quotidienne",
        "ai_score": 7.0,
        "desc_fr": "Instruments du marché monétaire UEMOA. Capital quasi-garanti, liquidité maximale.",
        "desc_en": "WAEMU money market instruments. Near-guaranteed capital, maximum liquidity.",
    },
    {
        "nom": "SICAV PREMIUM BRVM 30",
        "gestionnaire": "Africabourse",
        "categorie": "actions",
        "risque": 5,
        "perf_1y": 18.7,
        "perf_3y": 54.2,
        "capital_min": 200_000,
        "frais_gestion": "1.80%",
        "liquidite": "hebdomadaire",
        "ai_score": 8.9,
        "desc_fr": "Top 30 capitalisations BRVM, pondéré par momentum. Haute performance, haute volatilité.",
        "desc_en": "Top 30 BRVM capitalizations, weighted by momentum. High performance, high volatility.",
    },
    {
        "nom": "FCP OBLIGATIONS SOUVERAINES",
        "gestionnaire": "Impaxis Securities",
        "categorie": "obligataire",
        "risque": 2,
        "perf_1y": 5.8,
        "perf_3y": 17.4,
        "capital_min": 100_000,
        "frais_gestion": "0.75%",
        "liquidite": "mensuelle",
        "ai_score": 7.5,
        "desc_fr": "Obligations souveraines Côte d'Ivoire, Sénégal, Mali. Note crédit BBB moyenne.",
        "desc_en": "Sovereign bonds Ivory Coast, Senegal, Mali. Average credit rating BBB.",
    },
    {
        "nom": "SICAV REVENUS RÉGULIERS",
        "gestionnaire": "Coris Bourse",
        "categorie": "diversifie",
        "risque": 2,
        "perf_1y": 7.4,
        "perf_3y": 22.3,
        "capital_min": 50_000,
        "frais_gestion": "1.00%",
        "liquidite": "bimensuelle",
        "ai_score": 7.9,
        "desc_fr": "Mix obligations (70%) + dividendes (30%). Distributions trimestrielles régulières.",
        "desc_en": "Mix of bonds (70%) + dividend stocks (30%). Regular quarterly distributions.",
    },
]

# ── UI ───────────────────────────────────────────────────────────────────────

st.title(t("sgi_title", lang))
st.markdown(t("sgi_subtitle", lang))
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    t("sgi_module1", lang),
    t("sgi_module2", lang),
    t("sgi_module3", lang),
    t("sgi_module4", lang),
])

# ═══════════════════════════════════════════════════════════════════════════
# MODULE 1 — CLASSEMENT SGI
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader(t("sgi_module1", lang))
    st.caption(t("sgi_ranking_info", lang))

    # Pays filter
    pays_list = sorted(set(s["pays"] for s in SGI_DATA))
    pays_options = [t("sgi_all_countries", lang)] + pays_list
    col_f1, col_f2 = st.columns([2, 4])
    with col_f1:
        selected_pays = st.selectbox(t("sgi_country_filter", lang), pays_options)

    sgi_filtered = SGI_DATA if selected_pays == t("sgi_all_countries", lang) \
        else [s for s in SGI_DATA if s["pays"] == selected_pays]

    # Build ranked dataframe
    rows = []
    for sgi in sgi_filtered:
        rows.append({
            "SGI": sgi["nom"],
            t("sgi_score_global", lang): calc_score_global(sgi["scores"]),
            t("sgi_courtage", lang): sgi["courtage"],
            t("sgi_depot_min", lang): f"{sgi['depot_min']:,} FCFA",
            t("sgi_app_mobile", lang): t("sgi_yes", lang) if sgi["app_mobile"] else t("sgi_no", lang),
            t("sgi_ouverture_ligne", lang): t("sgi_yes", lang) if sgi["ouverture_en_ligne"] else t("sgi_no", lang),
            t("sgi_diaspora", lang): t("sgi_yes", lang) if sgi["presence_diaspora"] else t("sgi_no", lang),
            "Pays": sgi["pays"],
        })

    df_sgi = pd.DataFrame(rows).sort_values(t("sgi_score_global", lang), ascending=False).reset_index(drop=True)
    df_sgi.index = df_sgi.index + 1

    # Medal column
    def medal(rank):
        return ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else str(rank)

    df_sgi.insert(0, "#", [medal(i) for i in df_sgi.index])

    st.dataframe(
        df_sgi.style.background_gradient(subset=[t("sgi_score_global", lang)], cmap="YlGn"),
        use_container_width=True,
        hide_index=True,
    )

    # Bar chart
    fig = px.bar(
        df_sgi.sort_values(t("sgi_score_global", lang)),
        x=t("sgi_score_global", lang),
        y="SGI",
        orientation="h",
        color=t("sgi_score_global", lang),
        color_continuous_scale="YlGn",
        range_x=[0, 10],
        title=t("sgi_module1", lang),
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Expandable cards
    st.markdown("---")
    st.markdown(f"### {'Détail des SGI' if lang == 'fr' else 'SGI Details'}")
    for i, sgi in enumerate(sorted(sgi_filtered, key=lambda s: calc_score_global(s["scores"]), reverse=True)):
        score = calc_score_global(sgi["scores"])
        rank  = i + 1
        medal_icon = medal(rank)
        with st.expander(f"{medal_icon} **{sgi['nom']}** — {score}/10 | {sgi['pays']} | {t('sgi_filled', lang)} {sgi['founded']}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(t("sgi_courtage", lang), sgi["courtage"])
                st.metric(t("sgi_depot_min", lang), f"{sgi['depot_min']:,} FCFA")
            with c2:
                st.metric(t("sgi_app_mobile", lang), t("sgi_yes", lang) if sgi["app_mobile"] else t("sgi_no", lang))
                st.metric(t("sgi_ouverture_ligne", lang), t("sgi_yes", lang) if sgi["ouverture_en_ligne"] else t("sgi_no", lang))
            with c3:
                st.metric(t("sgi_diaspora", lang), t("sgi_yes", lang) if sgi["presence_diaspora"] else t("sgi_no", lang))
                st.metric(t("sgi_score_global", lang), f"{score}/10")

            strengths = sgi["strengths_fr"] if lang == "fr" else sgi["strengths_en"]
            weaknesses = sgi["weaknesses_fr"] if lang == "fr" else sgi["weaknesses_en"]

            col_s, col_w = st.columns(2)
            with col_s:
                st.markdown(f"**{t('sgi_strengths', lang)}**")
                for s in strengths:
                    st.markdown(f"• ✅ {s}")
            with col_w:
                st.markdown(f"**{t('sgi_weaknesses', lang)}**")
                for w in weaknesses:
                    st.markdown(f"• ⚠️ {w}")

            # Radar chart for criteria
            criteria_labels = {
                "frais":             "Frais" if lang == "fr" else "Fees",
                "facilite_ouverture": "Ouverture" if lang == "fr" else "Opening",
                "app_mobile":        "App",
                "service_client":    "Service" if lang == "fr" else "Support",
                "recherche":         "Recherche" if lang == "fr" else "Research",
                "rapidite":          "Rapidité" if lang == "fr" else "Speed",
                "reputation":        "Réputation" if lang == "fr" else "Reputation",
            }
            categories = list(criteria_labels.values())
            values = [sgi["scores"][k] for k in criteria_labels]
            values_closed = values + [values[0]]
            categories_closed = categories + [categories[0]]

            fig_r = go.Figure(go.Scatterpolar(
                r=values_closed, theta=categories_closed,
                fill="toself", name=sgi["nom"],
                line_color="#2ecc71",
            ))
            fig_r.update_layout(
                polar=dict(radialaxis=dict(range=[0, 10], visible=True)),
                showlegend=False, height=300,
                margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(fig_r, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════
# MODULE 2 — RECOMMANDATION IA
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader(t("sgi_module2", lang))

    with st.form("sgi_reco_form"):
        col1, col2 = st.columns(2)
        with col1:
            pays_residence = st.selectbox(
                t("sgi_q_country", lang),
                ["Canada", "France", "Belgique", "Suisse", "Côte d'Ivoire", "Sénégal",
                 "Mali", "Burkina Faso", "Togo", "Bénin", "Autre"],
            )
            montant = st.number_input(
                t("sgi_q_amount", lang), min_value=0, max_value=5_000_000,
                value=10_000, step=1_000,
            )
            experience = st.selectbox(
                t("sgi_q_experience", lang),
                [t("sgi_exp_beginner", lang), t("sgi_exp_intermediate", lang), t("sgi_exp_expert", lang)],
            )
        with col2:
            style = st.selectbox(
                t("sgi_q_style", lang),
                [t("sgi_style_active", lang), t("sgi_style_longterm", lang), t("sgi_style_mixed", lang)],
            )
            advice = st.radio(
                t("sgi_q_advice", lang),
                [t("sgi_advice_yes", lang), t("sgi_advice_no", lang)],
                horizontal=True,
            )
            horizon = st.selectbox(
                t("sgi_q_horizon", lang),
                [t("sgi_horizon_short", lang), t("sgi_horizon_medium", lang), t("sgi_horizon_long", lang)],
            )

        submitted = st.form_submit_button(t("sgi_get_reco", lang), use_container_width=True, type="primary")

    if submitted:
        # Build profile dict
        exp_map = {
            t("sgi_exp_beginner", lang): "beginner",
            t("sgi_exp_intermediate", lang): "intermediate",
            t("sgi_exp_expert", lang): "expert",
        }
        style_map = {
            t("sgi_style_active", lang): "active",
            t("sgi_style_longterm", lang): "longterm",
            t("sgi_style_mixed", lang): "mixed",
        }
        diaspora_countries = ["Canada", "France", "Belgique", "Suisse"]
        profile = {
            "diaspora":   pays_residence in diaspora_countries,
            "amount":     montant * 655.957,  # CAD → FCFA approx
            "experience": exp_map.get(experience, "beginner"),
            "style":      style_map.get(style, "mixed"),
            "advice":     "yes" if advice == t("sgi_advice_yes", lang) else "no",
        }

        # Score all SGIs
        scored = sorted(
            [(s, score_for_profile(s, profile)) for s in SGI_DATA],
            key=lambda x: x[1], reverse=True,
        )
        top3 = scored[:3]

        st.success(t("sgi_top_reco", lang))
        for rank, (sgi, score) in enumerate(top3, 1):
            medal_icon = ["🥇", "🥈", "🥉"][rank - 1]
            with st.container(border=True):
                c_title, c_score = st.columns([4, 1])
                with c_title:
                    st.markdown(f"### {medal_icon} {sgi['nom']}")
                    st.caption(sgi["pays"])
                with c_score:
                    st.metric(t("sgi_score_label", lang), f"{score}/10")

                strengths = sgi["strengths_fr"] if lang == "fr" else sgi["strengths_en"]
                weaknesses = sgi["weaknesses_fr"] if lang == "fr" else sgi["weaknesses_en"]

                col_p, col_c = st.columns(2)
                with col_p:
                    st.markdown(f"**{t('sgi_pros', lang)}**")
                    for s in strengths:
                        st.markdown(f"• ✅ {s}")
                with col_c:
                    st.markdown(f"**{t('sgi_cons', lang)}**")
                    for w in weaknesses:
                        st.markdown(f"• ⚠️ {w}")

                flags = []
                if sgi["ouverture_en_ligne"]:
                    flags.append(t("sgi_ouverture_ligne", lang))
                if sgi["app_mobile"]:
                    flags.append(t("sgi_app_mobile", lang))
                if sgi["presence_diaspora"]:
                    flags.append(t("sgi_diaspora", lang))
                if flags:
                    st.markdown("  ".join([f"`{f}`" for f in flags]))

                st.markdown(
                    f"🔗 [{t('sgi_open_account', lang)}]({sgi['url']})",
                    unsafe_allow_html=False,
                )

# ═══════════════════════════════════════════════════════════════════════════
# MODULE 3 — SCREENER OPCVM
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader(t("opcvm_title", lang))

    # Filters
    cat_options = {
        t("opcvm_all_cat", lang):  None,
        t("opcvm_actions", lang):  "actions",
        t("opcvm_oblig", lang):    "obligataire",
        t("opcvm_diversifie", lang): "diversifie",
        t("opcvm_monetaire", lang): "monetaire",
    }
    risk_options = {
        t("opcvm_risk_all", lang):    None,
        t("opcvm_risk_low", lang):    "low",
        t("opcvm_risk_medium", lang): "medium",
        t("opcvm_risk_high", lang):   "high",
    }

    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        sel_cat  = st.selectbox(t("opcvm_category", lang), list(cat_options.keys()))
    with cf2:
        sel_risk = st.selectbox(t("opcvm_risk", lang), list(risk_options.keys()))
    with cf3:
        min_score = st.slider(f"{t('opcvm_ai_score', lang)} min.", 0.0, 10.0, 0.0, 0.5)

    def risk_band(r):
        if r <= 2: return "low"
        if r == 3: return "medium"
        return "high"

    filtered_opcvm = [
        o for o in OPCVM_DATA
        if (cat_options[sel_cat] is None or o["categorie"] == cat_options[sel_cat])
        and (risk_options[sel_risk] is None or risk_band(o["risque"]) == risk_options[sel_risk])
        and o["ai_score"] >= min_score
    ]

    if not filtered_opcvm:
        st.warning("Aucun OPCVM ne correspond aux filtres sélectionnés." if lang == "fr"
                   else "No OPCVM matches the selected filters.")
    else:
        cat_label = {
            "actions":    t("opcvm_actions", lang),
            "obligataire": t("opcvm_oblig", lang),
            "diversifie": t("opcvm_diversifie", lang),
            "monetaire":  t("opcvm_monetaire", lang),
        }
        rows_op = []
        for o in filtered_opcvm:
            rows_op.append({
                t("opcvm_manager", lang): o["gestionnaire"],
                "OPCVM":                  o["nom"],
                t("opcvm_category", lang): cat_label.get(o["categorie"], o["categorie"]),
                t("opcvm_risk", lang):    "⭐" * o["risque"],
                t("opcvm_perf_1y", lang): f"+{o['perf_1y']}%",
                t("opcvm_perf_3y", lang): f"+{o['perf_3y']}%",
                t("opcvm_min_cap", lang): f"{o['capital_min']:,}",
                t("opcvm_fees", lang):    o["frais_gestion"],
                t("opcvm_ai_score", lang): o["ai_score"],
            })

        df_op = pd.DataFrame(rows_op).sort_values(t("opcvm_ai_score", lang), ascending=False)
        st.dataframe(
            df_op.style.background_gradient(subset=[t("opcvm_ai_score", lang)], cmap="YlGn"),
            use_container_width=True,
            hide_index=True,
        )

        # Expandable detail cards
        st.markdown("---")
        for o in sorted(filtered_opcvm, key=lambda x: x["ai_score"], reverse=True):
            desc = o["desc_fr"] if lang == "fr" else o["desc_en"]
            with st.expander(f"**{o['nom']}** — Score IA {o['ai_score']}/10 | {o['frais_gestion']} frais"):
                cc1, cc2, cc3, cc4 = st.columns(4)
                cc1.metric(t("opcvm_perf_1y", lang), f"+{o['perf_1y']}%")
                cc2.metric(t("opcvm_perf_3y", lang), f"+{o['perf_3y']}%")
                cc3.metric(t("opcvm_min_cap", lang), f"{o['capital_min']:,} FCFA")
                cc4.metric(t("opcvm_liquidity", lang), o["liquidite"])
                st.markdown(f"_{desc}_")
                st.markdown(f"**{t('opcvm_manager', lang)}** : {o['gestionnaire']}")

# ═══════════════════════════════════════════════════════════════════════════
# MODULE 4 — MATCHING INVESTISSEUR
# ═══════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader(t("sgi_module4", lang))

    with st.form("matching_form"):
        col1, col2 = st.columns(2)
        with col1:
            age       = st.slider(t("matching_age", lang), 18, 75, 35)
            income    = st.number_input(t("matching_income", lang), min_value=0, max_value=500_000,
                                        value=60_000, step=5_000)
            patrimoine = st.number_input(t("matching_patrimoine", lang), min_value=0, max_value=5_000_000,
                                         value=100_000, step=10_000)
        with col2:
            objective = st.selectbox(
                t("matching_objective", lang),
                [t("obj_retirement", lang), t("obj_wealth", lang),
                 t("obj_income", lang),     t("obj_capital", lang)],
            )
            risk_pref = st.select_slider(
                t("matching_risk_profile", lang),
                options=[
                    t("risk_conservative", lang), t("risk_balanced", lang),
                    t("risk_dynamic", lang),       t("risk_aggressive", lang),
                ],
                value=t("risk_balanced", lang),
            )

        gen_btn = st.form_submit_button(t("matching_generate", lang), use_container_width=True, type="primary")

    if gen_btn:
        # ── Allocation engine ──────────────────────────────────────────────
        risk_map = {
            t("risk_conservative", lang): 0,
            t("risk_balanced", lang):     1,
            t("risk_dynamic", lang):      2,
            t("risk_aggressive", lang):   3,
        }
        risk_idx = risk_map.get(risk_pref, 1)

        obj_map = {
            t("obj_retirement", lang): "retirement",
            t("obj_wealth", lang):     "wealth",
            t("obj_income", lang):     "income",
            t("obj_capital", lang):    "capital",
        }
        obj_key = obj_map.get(objective, "wealth")

        # Age factor: younger → more equity
        age_equity_adj = max(0, (50 - age) * 0.5)

        # Base allocations [actions, oblig, monetaire, diversifie] by risk
        base_alloc = [
            [10, 60, 20, 10],   # conservative
            [30, 40, 10, 20],   # balanced
            [55, 25,  5, 15],   # dynamic
            [75, 15,  5,  5],   # aggressive
        ][risk_idx]

        # Adjust for objective
        if obj_key == "income":
            base_alloc[1] += 10; base_alloc[0] -= 10
        elif obj_key == "capital":
            base_alloc[2] += 10; base_alloc[0] -= 10
        elif obj_key == "retirement":
            # More bonds as age increases
            bond_adj = min(20, max(0, (age - 40) * 1))
            base_alloc[1] += bond_adj; base_alloc[0] -= bond_adj

        # Age equity adjustment
        base_alloc[0] = max(0, min(80, base_alloc[0] + int(age_equity_adj)))
        # Normalise
        total = sum(base_alloc)
        alloc = [round(v / total * 100) for v in base_alloc]
        # Fix rounding
        alloc[0] += 100 - sum(alloc)

        alloc_labels = [
            t("opcvm_actions", lang),
            t("opcvm_oblig", lang),
            t("opcvm_monetaire", lang),
            t("opcvm_diversifie", lang),
        ]
        alloc_colors = ["#2ecc71", "#3498db", "#f39c12", "#9b59b6"]

        # Expected return estimate
        exp_returns = [11.5, 6.0, 4.2, 8.5]
        expected_return = sum(a * r / 100 for a, r in zip(alloc, exp_returns))

        st.markdown("---")
        st.subheader(t("matching_allocation", lang))

        col_donut, col_metrics = st.columns([2, 1])
        with col_donut:
            fig_pie = go.Figure(go.Pie(
                labels=alloc_labels, values=alloc,
                hole=0.55,
                marker_colors=alloc_colors,
                textinfo="label+percent",
            ))
            fig_pie.update_layout(
                showlegend=False,
                annotations=[dict(text=f"{expected_return:.1f}%", x=0.5, y=0.5,
                                  font_size=22, showarrow=False)],
                margin=dict(l=20, r=20, t=30, b=20), height=380,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_metrics:
            st.markdown("#### " + t("matching_profile", lang))
            st.metric(t("matching_expected_return", lang), f"{expected_return:.1f}%/an")
            st.metric(t("matching_risk_profile", lang), risk_pref)
            for lbl, val in zip(alloc_labels, alloc):
                st.markdown(f"- **{lbl}** : {val}%")

        # ── SGI recommendation ─────────────────────────────────────────────
        st.markdown("---")
        st.subheader(t("matching_sgi", lang))

        profile_m = {
            "diaspora":   True,
            "amount":     patrimoine * 0.20 * 655.957,
            "experience": "beginner" if risk_idx == 0 else ("expert" if risk_idx >= 2 else "intermediate"),
            "style":      "longterm" if obj_key in ("retirement", "wealth") else "mixed",
            "advice":     "yes" if risk_idx <= 1 else "no",
        }
        top_sgi = sorted(SGI_DATA, key=lambda s: score_for_profile(s, profile_m), reverse=True)[:2]

        sgi_cols = st.columns(2)
        for i, sgi in enumerate(top_sgi):
            score_m = score_for_profile(sgi, profile_m)
            with sgi_cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{'🥇' if i==0 else '🥈'} {sgi['nom']}**")
                    st.caption(sgi["pays"])
                    st.metric(t("sgi_score_global", lang), f"{score_m}/10")
                    st.markdown(f"🔗 [{t('sgi_open_account', lang)}]({sgi['url']})")

        # ── OPCVM recommendation ───────────────────────────────────────────
        st.markdown("---")
        st.subheader(t("matching_opcvm", lang))

        # Pick best OPCVM per main category based on allocation
        max_alloc_idx = alloc.index(max(alloc))
        main_cat_key  = ["actions", "obligataire", "monetaire", "diversifie"][max_alloc_idx]
        cat_opcvm = [o for o in OPCVM_DATA if o["categorie"] == main_cat_key]
        if not cat_opcvm:
            cat_opcvm = OPCVM_DATA
        best_opcvm = max(cat_opcvm, key=lambda o: o["ai_score"])

        with st.container(border=True):
            boc1, boc2, boc3 = st.columns(3)
            boc1.metric("OPCVM", best_opcvm["nom"])
            boc2.metric(t("opcvm_perf_1y", lang), f"+{best_opcvm['perf_1y']}%")
            boc3.metric(t("opcvm_ai_score", lang), f"{best_opcvm['ai_score']}/10")
            desc = best_opcvm["desc_fr"] if lang == "fr" else best_opcvm["desc_en"]
            st.markdown(f"_{desc}_")
            st.markdown(f"**{t('opcvm_manager', lang)}** : {best_opcvm['gestionnaire']} · {best_opcvm['frais_gestion']} {t('opcvm_fees', lang)}")

        # ── Disclaimer ─────────────────────────────────────────────────────
        st.markdown("---")
        disclaimer = (
            "⚠️ **Avertissement** : Ces recommandations sont générées automatiquement à titre informatif "
            "et ne constituent pas un conseil en investissement. Consultez un conseiller financier agréé "
            "avant tout investissement."
            if lang == "fr" else
            "⚠️ **Disclaimer**: These recommendations are generated automatically for informational purposes "
            "and do not constitute investment advice. Consult a licensed financial advisor before investing."
        )
        st.caption(disclaimer)
