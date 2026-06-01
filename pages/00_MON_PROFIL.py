"""
00_MON_PROFIL.py — Afrika Markets Intelligence
Profil utilisateur + changement et reset de mot de passe
"""
import streamlit as st
import re
from datetime import datetime

st.set_page_config(
    page_title="Mon Profil — Afrika Markets",
    page_icon="👤",
    layout="wide"
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
.profile-card {
    background: #111418;
    border: 0.5px solid rgba(201,168,76,0.18);
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
}
.profile-card h3 {
    color: #C9A84C;
    font-size: 14px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.plan-pill {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.pill-free     { background: rgba(138,133,128,0.15); color: #8A8580; border: 0.5px solid #8A8580; }
.pill-starter  { background: rgba(52,152,219,0.15);  color: #3498DB; border: 0.5px solid #3498DB; }
.pill-pro      { background: rgba(201,168,76,0.15);  color: #C9A84C; border: 0.5px solid #C9A84C; }
.pill-expert   { background: rgba(46,204,113,0.15);  color: #2ECC71; border: 0.5px solid #2ECC71; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div style='background: linear-gradient(135deg, #006B3F, #C9A84C);
     padding: 20px; border-radius: 12px; margin-bottom: 30px;'>
    <h1 style='color:white; margin:0;'>👤 Mon Profil</h1>
    <p style='color:rgba(255,255,255,0.85); margin:5px 0 0;'>
        Gérez vos informations et votre sécurité
    </p>
</div>
""", unsafe_allow_html=True)

# ── Vérification connexion ───────────────────────────────────
if "user" not in st.session_state or not st.session_state.get("authenticated", False):
    st.warning("🔒 Vous devez être connecté pour accéder à cette page.")
    st.stop()

user = st.session_state.get("user", {})
plan = st.session_state.get("plan", "free")
plan_labels = {"free": "Gratuit", "starter": "Starter", "pro": "Pro", "expert": "Expert"}
plan_pills  = {"free": "pill-free", "starter": "pill-starter", "pro": "pill-pro", "expert": "pill-expert"}

# ── Onglets ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Mon compte", "🔑 Changer le mot de passe", "📧 Réinitialisation"])

# ════════════════════════════════════════════════════════════
# TAB 1 — INFORMATIONS DU COMPTE
# ════════════════════════════════════════════════════════════
with tab1:
    col_info, col_plan = st.columns([2, 1])

    with col_info:
        st.markdown("""<div class="profile-card"><h3>📋 Informations personnelles</h3>""",
                    unsafe_allow_html=True)

        with st.form("form_profil"):
            nom       = st.text_input("Nom complet",
                                      value=user.get("nom", ""),
                                      placeholder="Jean-Claude Ndoubamoh")
            email     = st.text_input("Email",
                                      value=user.get("email", ""),
                                      disabled=True,
                                      help="L'email ne peut pas être modifié ici.")
            pays      = st.selectbox("Pays de résidence",
                                     ["Côte d'Ivoire", "Canada", "France", "Belgique",
                                      "Sénégal", "Burkina Faso", "Mali", "Togo",
                                      "Bénin", "Niger", "Guinée-Bissau", "Autre"],
                                     index=0)
            devise    = st.selectbox("Devise préférée",
                                     ["USD", "EUR", "CAD", "FCFA"])
            langue    = st.selectbox("Langue", ["Français", "English"])

            submitted = st.form_submit_button("💾 Sauvegarder", use_container_width=True,
                                              type="primary")
            if submitted:
                st.session_state["user"] = {**user, "nom": nom, "pays": pays}
                st.success("✅ Profil mis à jour avec succès !")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_plan:
        pill_class = plan_pills.get(plan, "pill-free")
        st.markdown(f"""
        <div class="profile-card">
            <h3>💳 Abonnement</h3>
            <p>Plan actuel</p>
            <span class="plan-pill {pill_class}">{plan_labels.get(plan, 'Gratuit')}</span>
            <br/><br/>
            <p style="font-size:13px; color:#8A8580;">
                Membre depuis {user.get('created_at', datetime.now().strftime('%B %Y'))}
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("⬆️ Changer de plan",
                        "https://afrika-markets-stock.lemonsqueezy.com",
                        use_container_width=True)

        st.markdown("""
        <div class="profile-card" style="margin-top:1rem;">
            <h3>📊 Statistiques</h3>
        </div>
        """, unsafe_allow_html=True)
        st.metric("Connexions ce mois", user.get("connexions_mois", 0))
        st.metric("Alertes actives", user.get("alertes_actives", 0))
        st.metric("Titres suivis", user.get("titres_suivis", 0))

# ════════════════════════════════════════════════════════════
# TAB 2 — CHANGER LE MOT DE PASSE (utilisateur connecté)
# ════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🔑 Changer votre mot de passe")
    st.caption("Vous devez connaître votre mot de passe actuel pour effectuer ce changement.")

    with st.form("form_change_password"):
        ancien_mdp   = st.text_input("Mot de passe actuel",
                                      type="password",
                                      placeholder="••••••••")
        nouveau_mdp  = st.text_input("Nouveau mot de passe",
                                      type="password",
                                      placeholder="Minimum 8 caractères")
        confirm_mdp  = st.text_input("Confirmer le nouveau mot de passe",
                                      type="password",
                                      placeholder="Répétez le nouveau mot de passe")

        # Indicateur de force
        if nouveau_mdp:
            force = 0
            checks = {
                "8 caractères minimum": len(nouveau_mdp) >= 8,
                "Une majuscule":        bool(re.search(r'[A-Z]', nouveau_mdp)),
                "Un chiffre":           bool(re.search(r'\d', nouveau_mdp)),
                "Un caractère spécial": bool(re.search(r'[^A-Za-z0-9]', nouveau_mdp)),
            }
            force = sum(checks.values())
            labels = ["", "Faible", "Moyen", "Fort", "Très fort"]
            colors = ["", "red", "orange", "blue", "green"]
            st.progress(force / 4)
            st.caption(f"Force : :{colors[force]}[{labels[force]}]")
            for label, ok in checks.items():
                st.caption(f"{'✅' if ok else '❌'} {label}")

        submitted = st.form_submit_button("🔒 Mettre à jour le mot de passe",
                                          use_container_width=True, type="primary")
        if submitted:
            if not ancien_mdp:
                st.error("Veuillez saisir votre mot de passe actuel.")
            elif len(nouveau_mdp) < 8:
                st.error("Le nouveau mot de passe doit contenir au moins 8 caractères.")
            elif nouveau_mdp != confirm_mdp:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                # ── Ici : appel à votre backend pour vérifier l'ancien mdp et mettre à jour ──
                # Exemple : backend.update_password(user_id, ancien_mdp, nouveau_mdp)
                st.success("✅ Mot de passe mis à jour avec succès !")
                st.balloons()

# ════════════════════════════════════════════════════════════
# TAB 3 — RÉINITIALISATION PAR EMAIL (mot de passe oublié)
# ════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📧 Réinitialiser votre mot de passe par email")
    st.caption("""
    Vous recevrez un lien de réinitialisation valable **30 minutes**.  
    Vérifiez aussi vos **spams** si vous ne recevez rien dans 5 minutes.
    """)

    with st.form("form_reset_password"):
        email_reset = st.text_input("Votre adresse email",
                                     placeholder="exemple@email.com",
                                     value=user.get("email", ""))

        submitted = st.form_submit_button("📨 Envoyer le lien de réinitialisation",
                                          use_container_width=True)
        if submitted:
            if not email_reset or "@" not in email_reset:
                st.error("Veuillez saisir une adresse email valide.")
            else:
                # ── Ici : appel à votre backend pour envoyer l'email de reset ──
                # Exemple : backend.send_reset_email(email_reset)
                st.success(f"""
                ✅ Un lien de réinitialisation a été envoyé à **{email_reset}**  
                Le lien est valable 30 minutes.
                """)
                st.info("📬 Pensez à vérifier vos spams si vous ne recevez pas l'email.")

    st.markdown("---")
    st.markdown("""
    <div class="profile-card">
        <h3>🛡️ Conseils de sécurité</h3>
        <ul style="color:#8A8580; font-size:13px; padding-left:1.2rem;">
            <li>Utilisez un mot de passe unique pour Afrika Markets</li>
            <li>Activez l'authentification à deux facteurs dès que disponible</li>
            <li>Ne partagez jamais vos identifiants</li>
            <li>Déconnectez-vous sur les appareils partagés</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ── Zone de danger ───────────────────────────────────────────
st.markdown("---")
with st.expander("⚠️ Zone de danger", expanded=False):
    st.warning("Les actions ci-dessous sont irréversibles.")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🚪 Se déconnecter", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Vous avez été déconnecté.")
            st.rerun()
    with col_b:
        if st.button("🗑️ Supprimer mon compte", use_container_width=True, type="secondary"):
            st.error("Pour supprimer votre compte, contactez : support@afrikamarkets.io")
