"""
07_ABONNEMENT.py — Afrika Markets Intelligence
Page de souscription avec intégration Lemon Squeezy
"""
import streamlit as st

st.set_page_config(
    page_title="Abonnement — Afrika Markets",
    page_icon="💳",
    layout="wide"
)

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
.plan-name {
    font-size: 12px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #8A8580;
    margin-bottom: 0.5rem;
}
.plan-price {
    font-size: 3rem;
    font-weight: 700;
    color: #F0EDE8;
    line-height: 1;
}
.plan-price sub {
    font-size: 14px;
    color: #8A8580;
    font-weight: 400;
}
.plan-desc {
    font-size: 13px;
    color: #8A8580;
    margin: 1rem 0;
    padding-bottom: 1rem;
    border-bottom: 0.5px solid rgba(201,168,76,0.18);
}
.feature-item {
    font-size: 13px;
    color: #8A8580;
    padding: 5px 0;
    text-align: left;
}
.feature-item.active { color: #F0EDE8; }
.check { color: #C9A84C; margin-right: 8px; }
.dash { color: #3A3F47; margin-right: 8px; }
.current-badge {
    background: rgba(46,204,113,0.1);
    border: 0.5px solid #2ECC71;
    color: #2ECC71;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    display: inline-block;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div style='background: linear-gradient(135deg, #006B3F, #C9A84C);
     padding: 20px; border-radius: 12px; margin-bottom: 30px; text-align:center;'>
    <h1 style='color:white; margin:0;'>💳 Abonnement</h1>
    <p style='color:rgba(255,255,255,0.85); margin:5px 0 0;'>
        Choisissez le plan adapté à votre stratégie d'investissement
    </p>
</div>
""", unsafe_allow_html=True)

# ── Plan actuel (depuis session state) ──────────────────────
current_plan = st.session_state.get("plan", "free")
plan_labels = {"free": "Gratuit", "starter": "Starter", "pro": "Pro", "expert": "Expert"}

st.info(f"📌 Votre plan actuel : **{plan_labels.get(current_plan, 'Gratuit')}**")

st.markdown("---")

# ── Grille des plans ─────────────────────────────────────────
col1, col2, col3 = st.columns(3, gap="medium")

LS_BASE = "https://afrika-markets-stock.lemonsqueezy.com/buy"

# ── STARTER ─────────────────────────────────────────────────
with col1:
    is_current = current_plan == "starter"
    st.markdown(f"""
    <div class="plan-card">
        <p class="plan-name">Starter</p>
        <div class="plan-price">$29<sub>.99/mo</sub></div>
        <p class="plan-desc">Pour les investisseurs diaspora qui débutent sur la BRVM.</p>
        <div class="feature-item active"><span class="check">✓</span>Dashboard BRVM en temps réel</div>
        <div class="feature-item active"><span class="check">✓</span>Tous les indices et secteurs</div>
        <div class="feature-item active"><span class="check">✓</span>Top 10 mouvements journaliers</div>
        <div class="feature-item active"><span class="check">✓</span>War Room géopolitique (basique)</div>
        <div class="feature-item active"><span class="check">✓</span>Support par email</div>
        <div class="feature-item"><span class="dash">—</span>Scoring IA des actions</div>
        <div class="feature-item"><span class="dash">—</span>Simulateur de portefeuille</div>
        <div class="feature-item"><span class="dash">—</span>Brief intelligence hebdo</div>
        <br/>
        {'<div class="current-badge">✓ Plan actuel</div>' if is_current else ''}
    </div>
    """, unsafe_allow_html=True)
    if not is_current:
        if st.button("Commencer l'essai gratuit", key="btn_starter", use_container_width=True):
            st.markdown(f'<meta http-equiv="refresh" content="0;url={LS_BASE}/starter">',
                        unsafe_allow_html=True)
            st.link_button("→ Souscrire Starter", f"{LS_BASE}/starter", use_container_width=True)

# ── PRO ─────────────────────────────────────────────────────
with col2:
    is_current = current_plan == "pro"
    st.markdown(f"""
    <div class="plan-card popular">
        <div class="plan-badge">Le plus populaire</div>
        <p class="plan-name">Pro</p>
        <div class="plan-price">$74<sub>.99/mo</sub></div>
        <p class="plan-desc">L'avantage IA pour les investisseurs BRVM sérieux.</p>
        <div class="feature-item active"><span class="check">✓</span>Tout le plan Starter</div>
        <div class="feature-item active"><span class="check">✓</span>Scoring &amp; classement IA</div>
        <div class="feature-item active"><span class="check">✓</span>War Room géopolitique complet</div>
        <div class="feature-item active"><span class="check">✓</span>Simulateur de portefeuille</div>
        <div class="feature-item active"><span class="check">✓</span>Alertes prix &amp; risques</div>
        <div class="feature-item active"><span class="check">✓</span>Brief intelligence hebdomadaire</div>
        <div class="feature-item"><span class="dash">—</span>Briefings 1-on-1 mensuels</div>
        <br/>
        {'<div class="current-badge">✓ Plan actuel</div>' if is_current else ''}
    </div>
    """, unsafe_allow_html=True)
    if not is_current:
        if st.button("Commencer l'essai gratuit", key="btn_pro", use_container_width=True, type="primary"):
            st.link_button("→ Souscrire Pro", f"{LS_BASE}/pro", use_container_width=True)

# ── EXPERT ───────────────────────────────────────────────────
with col3:
    is_current = current_plan == "expert"
    st.markdown(f"""
    <div class="plan-card">
        <p class="plan-name">Expert</p>
        <div class="plan-price">$199<sub>.99/mo</sub></div>
        <p class="plan-desc">Pour les conseillers financiers et investisseurs haute conviction.</p>
        <div class="feature-item active"><span class="check">✓</span>Tout le plan Pro</div>
        <div class="feature-item active"><span class="check">✓</span>Briefing 1-on-1 mensuel</div>
        <div class="feature-item active"><span class="check">✓</span>Watchlists personnalisées</div>
        <div class="feature-item active"><span class="check">✓</span>Export données CSV/PDF</div>
        <div class="feature-item active"><span class="check">✓</span>Support prioritaire</div>
        <div class="feature-item active"><span class="check">✓</span>Rapports PDF clients</div>
        <div class="feature-item active"><span class="check">✓</span>Accès anticipé aux nouvelles fonctionnalités</div>
        <br/>
        {'<div class="current-badge">✓ Plan actuel</div>' if is_current else ''}
    </div>
    """, unsafe_allow_html=True)
    if not is_current:
        if st.button("Commencer l'essai gratuit", key="btn_expert", use_container_width=True):
            st.link_button("→ Souscrire Expert", f"{LS_BASE}/expert", use_container_width=True)

# ── Liens directs Lemon Squeezy ──────────────────────────────
st.markdown("---")
st.markdown("### 🛒 Liens de souscription directs")

c1, c2, c3 = st.columns(3)
with c1:
    st.link_button("Starter — $29.99/mois", f"{LS_BASE}/starter", use_container_width=True)
with c2:
    st.link_button("Pro — $74.99/mois ⭐", f"{LS_BASE}/pro", use_container_width=True, type="primary")
with c3:
    st.link_button("Expert — $199.99/mois", f"{LS_BASE}/expert", use_container_width=True)

# ── Note légale ──────────────────────────────────────────────
st.markdown("---")
st.caption("""
💡 **Essai gratuit 14 jours** — Aucune carte bancaire requise · Annulation à tout moment  
🔒 Paiements sécurisés par **Lemon Squeezy** · Tous les prix en USD · Facturation mensuelle  
📧 Questions ? [hello@afrikamarkets.io](mailto:hello@afrikamarkets.io)
""")
