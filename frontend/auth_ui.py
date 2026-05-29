"""
Composants UI d'authentification — sidebar + mur d'upgrade
Afrika Markets Intelligence
"""
import streamlit as st
from datetime import datetime
from frontend.auth_client import login, register, get_me, create_stripe_checkout, initiate_wave, initiate_orange

# Hiérarchie des plans
PLAN_RANK = {"free": 0, "trial": 1, "starter": 2, "pro": 3, "expert": 4}

PLAN_LABELS = {
    "free":    "Gratuit",
    "trial":   "Essai 14j",
    "starter": "Starter — 9.99 CAD/mois",
    "pro":     "Pro — 24.99 CAD/mois",
    "expert":  "Expert — 49.99 CAD/mois",
}

PLAN_COLORS = {
    "free":    "#888888",
    "trial":   "#00BFFF",
    "starter": "#FFD700",
    "pro":     "#00CC66",
    "expert":  "#FF6B35",
}

UPGRADE_PAGE_URL = "https://afrika-markets.streamlit.app"


def _init_session():
    """Initialise les clés de session si absentes."""
    if "jwt_token" not in st.session_state:
        st.session_state.jwt_token = None
    if "user" not in st.session_state:
        st.session_state.user = None


def _effective_plan(user: dict) -> str:
    """Retourne le plan effectif (trial donne accès comme 'starter' pendant 14j)."""
    if user["status"] == "trial":
        trial_end = user.get("trial_ends_at")
        if trial_end:
            if isinstance(trial_end, str):
                trial_end = datetime.fromisoformat(trial_end.replace("Z", ""))
            if datetime.utcnow() < trial_end:
                return "trial"  # rank=1, pas d'accès pro/expert en trial
    return user.get("plan", "free")


def is_logged_in() -> bool:
    _init_session()
    return st.session_state.jwt_token is not None


def current_user() -> dict | None:
    _init_session()
    return st.session_state.user


def has_plan(min_plan: str) -> bool:
    """Vérifie si l'utilisateur a au moins le plan requis."""
    if not is_logged_in():
        return False
    user = st.session_state.user
    if not user:
        return False
    plan = _effective_plan(user)
    return PLAN_RANK.get(plan, 0) >= PLAN_RANK.get(min_plan, 99)


# ── Sidebar Auth Widget ───────────────────────────────────────

def _handle_payment_return(fr: bool = True):
    """
    Détecte le retour depuis Stripe/Wave/Orange et rafraîchit le profil utilisateur.
    Stripe redirige vers ?payment=success&session_id=...
    """
    params = st.query_params
    payment_status = params.get("payment")

    if payment_status == "success" and is_logged_in():
        # Rafraîchir le profil pour récupérer le nouveau plan
        me, code = get_me(st.session_state.jwt_token)
        if code == 200:
            st.session_state.user = me

        plan = _effective_plan(st.session_state.user) if st.session_state.user else "free"
        plan_label = PLAN_LABELS.get(plan, plan)
        color = PLAN_COLORS.get(plan, "#00CC66")

        st.success(
            f"Paiement confirmé — Plan **{plan_label}** activé !" if fr
            else f"Payment confirmed — **{plan_label}** plan activated!"
        )
        # Nettoyer les query params pour éviter re-trigger
        st.query_params.clear()

    elif payment_status == "cancelled":
        st.warning(
            "Paiement annulé — aucun débit effectué." if fr
            else "Payment cancelled — no charge was made."
        )
        st.query_params.clear()


def render_auth_sidebar(fr: bool = True):
    """
    Affiche le bloc auth dans la sidebar.
    Si connecté : badge utilisateur + bouton déconnexion.
    Si non connecté : formulaire login/register dans un expander.
    """
    _init_session()
    _handle_payment_return(fr)

    st.sidebar.markdown("---")

    if is_logged_in():
        user = st.session_state.user
        plan = _effective_plan(user)
        color = PLAN_COLORS.get(plan, "#888")

        st.sidebar.markdown(f"""
        <div style="background:{color}18; border:1px solid {color};
                    border-radius:8px; padding:10px; margin-bottom:8px;">
            <b style="color:{color};">{"Connecté" if fr else "Logged in"}</b><br>
            <small>{user.get("full_name", "")}</small><br>
            <small style="color:{color};">{PLAN_LABELS.get(plan, plan)}</small>
        </div>
        """, unsafe_allow_html=True)

        if st.sidebar.button("🚪 Déconnexion" if fr else "🚪 Logout", use_container_width=True):
            st.session_state.jwt_token = None
            st.session_state.user = None
            st.rerun()

        if plan in ("free", "trial"):
            if st.sidebar.button("⬆️ Passer au Pro" if fr else "⬆️ Upgrade", use_container_width=True):
                st.session_state["show_upgrade"] = True
                st.rerun()

    else:
        with st.sidebar.expander("🔐 Connexion / Inscription" if fr else "🔐 Login / Register", expanded=False):
            tab_login, tab_register = st.tabs(
                ["Connexion" if fr else "Login", "Inscription" if fr else "Register"]
            )

            with tab_login:
                email_l = st.text_input("Email", key="login_email")
                pwd_l   = st.text_input("Mot de passe" if fr else "Password",
                                        type="password", key="login_pwd")
                if st.button("Se connecter" if fr else "Log in", key="btn_login",
                             use_container_width=True, type="primary"):
                    if email_l and pwd_l:
                        data, code = login(email_l, pwd_l)
                        if code == 200:
                            st.session_state.jwt_token = data["access_token"]
                            me, _ = get_me(data["access_token"])
                            st.session_state.user = me
                            st.success("Connecté !" if fr else "Logged in!")
                            st.rerun()
                        else:
                            st.error(data.get("detail", "Erreur"))
                    else:
                        st.warning("Remplissez tous les champs" if fr else "Fill all fields")

            with tab_register:
                name_r    = st.text_input("Nom complet" if fr else "Full name", key="reg_name")
                email_r   = st.text_input("Email", key="reg_email")
                pwd_r     = st.text_input("Mot de passe" if fr else "Password",
                                          type="password", key="reg_pwd")
                country_r = st.selectbox("Pays" if fr else "Country",
                                         ["CA", "CI", "SN", "BJ", "TG", "BF", "ML", "NE", "GW"],
                                         key="reg_country")
                if st.button("Créer mon compte" if fr else "Create account", key="btn_register",
                             use_container_width=True, type="primary"):
                    if name_r and email_r and pwd_r:
                        data, code = register(email_r, pwd_r, name_r, country_r)
                        if code == 200:
                            st.session_state.jwt_token = data["access_token"]
                            me, _ = get_me(data["access_token"])
                            st.session_state.user = me
                            st.success("Compte créé — essai 14 jours activé !" if fr
                                       else "Account created — 14-day trial activated!")
                            st.rerun()
                        else:
                            st.error(data.get("detail", "Erreur"))
                    else:
                        st.warning("Remplissez tous les champs" if fr else "Fill all fields")


# ── Mur d'accès ──────────────────────────────────────────────

def require_auth(fr: bool = True):
    """Stoppe la page si l'utilisateur n'est pas connecté."""
    _init_session()
    if not is_logged_in():
        st.markdown("""
        <div style="text-align:center; padding:60px 20px;">
            <h2>🔐</h2>
        </div>
        """, unsafe_allow_html=True)
        st.warning(
            "**Connectez-vous** pour accéder à cette fonctionnalité.\n\n"
            "Créez un compte gratuit et profitez de 14 jours d'essai."
            if fr else
            "**Log in** to access this feature.\n\n"
            "Create a free account and enjoy a 14-day trial."
        )
        st.stop()


def require_plan(min_plan: str, fr: bool = True):
    """Stoppe la page et affiche le mur d'upgrade si le plan est insuffisant."""
    require_auth(fr)
    if not has_plan(min_plan):
        user = st.session_state.user
        current_plan = _effective_plan(user)
        needed_label = PLAN_LABELS.get(min_plan, min_plan)
        needed_color = PLAN_COLORS.get(min_plan, "#FFD700")

        st.markdown(f"""
        <div style="text-align:center; padding:40px 20px;
                    background:{needed_color}10; border-radius:15px;
                    border: 2px solid {needed_color}; margin: 30px 0;">
            <h2 style="color:{needed_color};">
                {"Fonctionnalité Premium" if fr else "Premium Feature"}
            </h2>
            <p style="color:white; font-size:1.1em;">
                {"Cette page requiert le plan" if fr else "This page requires the"}
                <b style="color:{needed_color};"> {needed_label}</b>
            </p>
            <p style="color:#aaa;">
                {"Votre plan actuel :" if fr else "Your current plan:"}
                <b>{PLAN_LABELS.get(current_plan, current_plan)}</b>
            </p>
        </div>
        """, unsafe_allow_html=True)

        _render_upgrade_options(fr)
        st.stop()


def _render_upgrade_options(fr: bool = True):
    """Affiche les options de paiement."""
    st.markdown("### " + ("Choisir un plan" if fr else "Choose a plan"))

    plans = [
        ("starter", "Starter", "9.99 CAD / mois", ["Dashboard complet", "Analyse titres", "Profil investisseur"]),
        ("pro",     "Pro",     "24.99 CAD / mois", ["Tout Starter", "Simulateur portefeuille", "Alertes prix"]),
        ("expert",  "Expert",  "49.99 CAD / mois", ["Tout Pro", "War Room risques", "Export Excel"]),
    ]

    cols = st.columns(3)
    for col, (plan_id, plan_name, price, features) in zip(cols, plans):
        color = PLAN_COLORS[plan_id]
        with col:
            st.markdown(f"""
            <div style="background:{color}18; border:2px solid {color};
                        border-radius:12px; padding:20px; text-align:center; min-height:200px;">
                <h3 style="color:{color}; margin:0;">{plan_name}</h3>
                <p style="color:white; font-size:1.1em;"><b>{price}</b></p>
                {"".join(f'<p style="color:#ccc; font-size:0.9em; margin:4px 0;">✓ {f}</p>' for f in features)}
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Choisir {plan_name}" if fr else f"Choose {plan_name}",
                         key=f"upgrade_{plan_id}", use_container_width=True):
                st.session_state["upgrading_plan"] = plan_id
                st.rerun()

    # Formulaire de paiement si un plan est sélectionné
    if "upgrading_plan" in st.session_state:
        selected = st.session_state["upgrading_plan"]
        st.markdown("---")
        st.markdown(f"### {'Paiement — Plan' if fr else 'Payment — Plan'} {selected.capitalize()}")

        method = st.radio(
            "Méthode de paiement" if fr else "Payment method",
            ["💳 Carte bancaire (Stripe)", "📱 Wave CI", "🟠 Orange Money CI"],
            horizontal=True,
        )

        token = st.session_state.jwt_token

        if method == "💳 Carte bancaire (Stripe)":
            if st.button("Payer par carte" if fr else "Pay by card", type="primary"):
                data, code = create_stripe_checkout(
                    token, selected,
                    success_url=UPGRADE_PAGE_URL,
                    cancel_url=UPGRADE_PAGE_URL,
                )
                if code == 200:
                    checkout_url = data.get("checkout_url")
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0; url={checkout_url}">',
                        unsafe_allow_html=True
                    )
                    st.info(f"[Cliquez ici pour payer]({checkout_url})")
                else:
                    st.error(data.get("detail", "Erreur Stripe"))

        elif method == "📱 Wave CI":
            phone = st.text_input("Numéro Wave (ex: +2250700000000)", key="wave_phone")
            if st.button("Payer via Wave", type="primary"):
                data, code = initiate_wave(token, selected, phone)
                if code == 200:
                    url = data.get("wave_launch_url")
                    st.info(f"[Ouvrir Wave pour payer]({url})")
                else:
                    st.error(data.get("detail", "Erreur Wave"))

        elif method == "🟠 Orange Money CI":
            phone = st.text_input("Numéro Orange (ex: +2250700000000)", key="om_phone")
            if st.button("Payer via Orange Money", type="primary"):
                data, code = initiate_orange(token, selected, phone)
                if code == 200:
                    url = data.get("payment_url")
                    st.info(f"[Ouvrir Orange Money pour payer]({url})")
                else:
                    st.error(data.get("detail", "Erreur Orange Money"))
