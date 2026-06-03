"""
07_ABONNEMENT.py — Afrika Markets Intelligence
Page de souscription avec intégration Lemon Squeezy
"""
import streamlit as st
from utils.i18n import t, get_lang

st.set_page_config(
    page_title="Abonnement — Afrika Markets",
    page_icon="💳",
    layout="wide"
)

lang = get_lang()

# ── CSS personnalisé ─────────────────────────────────────────
st.markdown("""
<style>
.plan-card {
    background: #111418;
    border: 0.5px solid rgba(201,168,76,0.18);
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    position: relative;
    height: 100%;
}
.plan-card.popular {
    border-color: #C9A84C;
    box-shadow: 0 0 24px rgba(201,168,76,0.12);
}
.plan-badge {
    position: absolute;
    top: -14px;
    left: 50%;
    transform: translateX(-50%);
    background: #C9A84C;
    color: #0A0C0F;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 4px 16px;
    border-radius: 20px;
    white-space: nowrap;
}
.plan-name  { font-size:12px; letter-spacing:0.1em; text-transform:uppercase; color:#8A8580; margin-bottom:0.5rem; }
.plan-price { font-size:3rem; font-weight:700; color:#F0EDE8; line-height:1; }
.plan-price sub { font-size:14px; color:#8A8580; font-weight:400; }
.plan-desc  { font-size:13px; color:#8A8580; margin:1rem 0; padding-bottom:1rem; border-bottom:0.5px solid rgba(201,168,76,0.18); }
.feature-item { font-size:13px; color:#8A8580; padding:5px 0; text-align:left; }
.feature-item.active { color:#F0EDE8; }
.check { color:#C9A84C; margin-right:8px; }
.dash  { color:#3A3F47; margin-right:8px; }
.current-badge { background:rgba(46,204,113,0.1); border:0.5px solid #2ECC71; color:#2ECC71;
                 border-radius:6px; padding:4px 12px; font-size:12px; display:inline-block; margin-bottom:1rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────
st.markdown(f"""
<div style='background: linear-gradient(135deg, #006B3F, #C9A84C);
     padding: 20px; border-radius: 12px; margin-bottom: 30px; text-align:center;'>
    <h1 style='color:white; margin:0;'>{t("sub_title", lang)}</h1>
    <p style='color:rgba(255,255,255,0.85); margin:5px 0 0;'>
        {t("sub_subtitle", lang)}
    </p>
</div>
""", unsafe_allow_html=True)

# ── Plan actuel ──────────────────────────────────────────────
current_plan = st.session_state.get("plan", "free")
plan_labels  = {
    "free":    t("plan_free", lang),
    "starter": t("plan_starter", lang),
    "pro":     t("plan_pro", lang),
    "expert":  t("plan_expert", lang),
}

st.info(t("current_plan_info", lang).format(plan=plan_labels.get(current_plan, t("plan_free", lang))))

st.markdown("---")

# ── Grille des plans ─────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4, gap="medium")
LS = {
    "starter":        "https://afrika-markets-stock.lemonsqueezy.com/checkout/buy/737c9823-4248-488a-a736-e22820f23e18",
    "pro":            "https://afrika-markets-stock.lemonsqueezy.com/checkout/buy/ae008a73-cf01-41e6-b602-270c9a943409",
    "expert":         "https://afrika-markets-stock.lemonsqueezy.com/checkout/buy/12ca2955-7928-4a10-8266-59cfbcf13078",
    "expert_premium": "https://afrika-markets-stock.lemonsqueezy.com/checkout/buy/d7672acb-6acb-40f0-b5eb-a4022f7fc7c0",
}

# ── STARTER ─────────────────────────────────────────────────
with col1:
    is_current = current_plan == "starter"
    st.markdown(f"""
    <div class="plan-card">
        <p class="plan-name">Starter</p>
        <div class="plan-price">$29<sub>.99/mo</sub></div>
        <p class="plan-desc">{'Pour les investisseurs diaspora qui débutent sur la BRVM.' if lang=='fr' else 'For diaspora investors starting on the BRVM.' if lang=='en' else 'Para inversores de la diáspora que comienzan en la BRVM.' if lang=='es' else 'Para investidores da diáspora que começam na BRVM.' if lang=='pt' else '为在BRVM起步的侨民投资者。' if lang=='zh' else 'للمستثمرين من المغتربين المبتدئين في BRVM.'}</p>
        <div class="feature-item active"><span class="check">✓</span>Dashboard BRVM</div>
        <div class="feature-item active"><span class="check">✓</span>{'Tous les indices et secteurs' if lang=='fr' else 'All indices and sectors'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Top 10 mouvements journaliers' if lang=='fr' else 'Daily top 10 movers'}</div>
        <div class="feature-item active"><span class="check">✓</span>War Room {'géopolitique (basique)' if lang=='fr' else '(basic)'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Support par email' if lang=='fr' else 'Email support'}</div>
        <div class="feature-item"><span class="dash">—</span>{'Scoring IA' if lang=='fr' else 'AI Scoring'}</div>
        <div class="feature-item"><span class="dash">—</span>{'Simulateur de portefeuille' if lang=='fr' else 'Portfolio Simulator'}</div>
        <div class="feature-item"><span class="dash">—</span>{'Brief intelligence hebdo' if lang=='fr' else 'Weekly intel brief'}</div>
        <br/>
        {'<div class="current-badge">✓ Plan actuel</div>' if is_current else ''}
    </div>
    """, unsafe_allow_html=True)
    if not is_current:
        st.link_button(t("free_trial_btn", lang), LS["starter"], use_container_width=True)

# ── PRO ─────────────────────────────────────────────────────
with col2:
    is_current = current_plan == "pro"
    st.markdown(f"""
    <div class="plan-card popular">
        <div class="plan-badge">{t("most_popular", lang)}</div>
        <p class="plan-name">Pro</p>
        <div class="plan-price">$74<sub>.99/mo</sub></div>
        <p class="plan-desc">{'L\'avantage IA pour les investisseurs BRVM sérieux.' if lang=='fr' else 'The AI edge for serious BRVM investors.' if lang=='en' else 'La ventaja IA para inversores serios en BRVM.' if lang=='es' else 'A vantagem IA para investidores sérios na BRVM.' if lang=='pt' else '为认真的BRVM投资者提供AI优势。' if lang=='zh' else 'ميزة الذكاء الاصطناعي للمستثمرين الجادين في BRVM.'}</p>
        <div class="feature-item active"><span class="check">✓</span>{'Tout le plan Starter' if lang=='fr' else 'All Starter features'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Scoring &amp; classement IA' if lang=='fr' else 'AI Scoring &amp; ranking'}</div>
        <div class="feature-item active"><span class="check">✓</span>War Room {'complet' if lang=='fr' else 'full access'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Simulateur de portefeuille' if lang=='fr' else 'Portfolio Simulator'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Alertes prix &amp; risques' if lang=='fr' else 'Price &amp; risk alerts'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'SGI &amp; OPCVM Intelligence Center' if lang=='fr' else 'SGI &amp; OPCVM Intelligence Center'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Brief intelligence hebdomadaire' if lang=='fr' else 'Weekly intelligence brief'}</div>
        <br/>
        {'<div class="current-badge">✓ Plan actuel</div>' if is_current else ''}
    </div>
    """, unsafe_allow_html=True)
    if not is_current:
        st.link_button(t("free_trial_btn", lang), LS["pro"],
                       use_container_width=True, type="primary")

# ── EXPERT ───────────────────────────────────────────────────
with col3:
    is_current = current_plan == "expert"
    st.markdown(f"""
    <div class="plan-card">
        <p class="plan-name">Expert</p>
        <div class="plan-price">$199<sub>.99/mo</sub></div>
        <p class="plan-desc">{'Pour les conseillers financiers et investisseurs haute conviction.' if lang=='fr' else 'For financial advisors and high-conviction investors.' if lang=='en' else 'Para asesores financieros e inversores de alta convicción.' if lang=='es' else 'Para consultores financeiros e investidores de alta convicção.' if lang=='pt' else '为财务顾问和高确信度投资者。' if lang=='zh' else 'للمستشارين الماليين والمستثمرين عالي الإقناع.'}</p>
        <div class="feature-item active"><span class="check">✓</span>{'Tout le plan Pro' if lang=='fr' else 'All Pro features'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Briefing 1-on-1 mensuel' if lang=='fr' else 'Monthly 1-on-1 briefing'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Watchlists personnalisées' if lang=='fr' else 'Custom watchlists'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Export données CSV/PDF' if lang=='fr' else 'CSV/PDF data export'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Support prioritaire' if lang=='fr' else 'Priority support'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Rapports PDF clients' if lang=='fr' else 'Client PDF reports'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Accès anticipé aux nouvelles fonctionnalités' if lang=='fr' else 'Early access to new features'}</div>
        <br/>
        {'<div class="current-badge">✓ Plan actuel</div>' if is_current else ''}
    </div>
    """, unsafe_allow_html=True)
    if not is_current:
        st.link_button(t("free_trial_btn", lang), LS["expert"], use_container_width=True)

# ── EXPERT PREMIUM ───────────────────────────────────────────
with col4:
    is_current = current_plan == "expert_premium"
    st.markdown(f"""
    <div class="plan-card" style="border-color:rgba(168,85,247,0.5);">
        <p class="plan-name" style="color:#a855f7;">Expert Premium</p>
        <div class="plan-price">$299<sub>.99/mo</sub></div>
        <p class="plan-desc">{'Pour les institutions, family offices et gestionnaires de fonds.' if lang=='fr' else 'For institutions, family offices and fund managers.' if lang=='en' else 'Para instituciones, family offices y gestores de fondos.' if lang=='es' else 'Para instituições, family offices e gestores de fundos.' if lang=='pt' else '面向机构、家族办公室和基金经理。' if lang=='zh' else 'للمؤسسات ومكاتب العائلة ومديري الصناديق.'}</p>
        <div class="feature-item active"><span class="check">✓</span>{'Tout le plan Expert' if lang=='fr' else 'All Expert features'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Accès API données brutes' if lang=='fr' else 'Raw data API access'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Modèles de valorisation exclusifs' if lang=='fr' else 'Exclusive valuation models'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Briefings illimités' if lang=='fr' else 'Unlimited briefings'}</div>
        <div class="feature-item active"><span class="check">✓</span>{'Onboarding dédié' if lang=='fr' else 'Dedicated onboarding'}</div>
        <div class="feature-item active"><span class="check">✓</span>SLA 24/7</div>
        <div class="feature-item active"><span class="check">✓</span>{'Co-branding rapports clients' if lang=='fr' else 'Client report co-branding'}</div>
        <br/>
        {'<div class="current-badge">✓ Plan actuel</div>' if is_current else ''}
    </div>
    """, unsafe_allow_html=True)
    if not is_current:
        st.link_button(t("free_trial_btn", lang), LS["expert_premium"], use_container_width=True)

# ── Liens directs ────────────────────────────────────────────
st.markdown("---")
st.markdown(f"### {t('direct_links_title', lang)}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.link_button("Starter — $29.99/mo", LS["starter"], use_container_width=True)
with c2:
    st.link_button("Pro — $74.99/mo ⭐", LS["pro"], use_container_width=True, type="primary")
with c3:
    st.link_button("Expert — $199.99/mo", LS["expert"], use_container_width=True)
with c4:
    st.link_button("Expert Premium — $299.99/mo", LS["expert_premium"], use_container_width=True)

st.markdown("---")
st.caption(t("legal_note", lang))
