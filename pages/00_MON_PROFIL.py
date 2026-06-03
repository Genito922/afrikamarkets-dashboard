"""
00_MON_PROFIL.py — Afrika Markets Intelligence
Profil utilisateur + changement et reset de mot de passe
"""
import streamlit as st
import re
from datetime import datetime
from utils.i18n import t, get_lang

st.set_page_config(
    page_title="Mon Profil — Afrika Markets",
    page_icon="👤",
    layout="wide"
)

lang = get_lang()

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
st.markdown(f"""
<div style='background: linear-gradient(135deg, #006B3F, #C9A84C);
     padding: 20px; border-radius: 12px; margin-bottom: 30px;'>
    <h1 style='color:white; margin:0;'>{t("profile_title", lang)}</h1>
    <p style='color:rgba(255,255,255,0.85); margin:5px 0 0;'>
        {t("profile_subtitle", lang)}
    </p>
</div>
""", unsafe_allow_html=True)

# ── Vérification connexion ───────────────────────────────────
if "user" not in st.session_state or not st.session_state.get("authenticated", False):
    st.warning(t("must_be_logged_in", lang))
    st.stop()

user       = st.session_state.get("user", {})
plan       = st.session_state.get("plan", "free")
plan_labels = {
    "free":    t("plan_free", lang),
    "starter": t("plan_starter", lang),
    "pro":     t("plan_pro", lang),
    "expert":  t("plan_expert", lang),
}
plan_pills  = {"free": "pill-free", "starter": "pill-starter", "pro": "pill-pro", "expert": "pill-expert"}

# ── Onglets ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    t("tab_account", lang),
    t("tab_change_password", lang),
    t("tab_reset", lang),
])

# ════════════════════════════════════════════════════════════
# TAB 1 — INFORMATIONS DU COMPTE
# ════════════════════════════════════════════════════════════
with tab1:
    col_info, col_plan = st.columns([2, 1])

    with col_info:
        st.markdown(f"""<div class="profile-card"><h3>{t("personal_info", lang)}</h3>""",
                    unsafe_allow_html=True)

        with st.form("form_profil"):
            nom    = st.text_input(t("full_name", lang),
                                   value=user.get("nom", ""),
                                   placeholder="Jean-Claude Ndoubamoh")
            email  = st.text_input(t("email_label", lang),
                                   value=user.get("email", ""),
                                   disabled=True,
                                   help=t("email_help", lang))
            pays   = st.selectbox(t("country", lang),
                                  ["Côte d'Ivoire", "Canada", "France", "Belgique",
                                   "Sénégal", "Burkina Faso", "Mali", "Togo",
                                   "Bénin", "Niger", "Guinée-Bissau", "Autre"],
                                  index=0)
            devise = st.selectbox(t("currency", lang), ["USD", "EUR", "CAD", "FCFA"])

            submitted = st.form_submit_button(t("save", lang), use_container_width=True, type="primary")
            if submitted:
                st.session_state["user"] = {**user, "nom": nom, "pays": pays}
                st.success(t("profile_saved", lang))

        st.markdown("</div>", unsafe_allow_html=True)

    with col_plan:
        pill_class = plan_pills.get(plan, "pill-free")
        st.markdown(f"""
        <div class="profile-card">
            <h3>{t("subscription_section", lang)}</h3>
            <p>{t("current_plan_label", lang)}</p>
            <span class="plan-pill {pill_class}">{plan_labels.get(plan, t('plan_free', lang))}</span>
            <br/><br/>
            <p style="font-size:13px; color:#8A8580;">
                {t("member_since", lang)} {user.get('created_at', datetime.now().strftime('%B %Y'))}
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.link_button(t("upgrade_plan", lang),
                       "https://afrika-markets-stock.lemonsqueezy.com",
                       use_container_width=True)

        st.markdown(f"""
        <div class="profile-card" style="margin-top:1rem;">
            <h3>{t("stats_section", lang)}</h3>
        </div>
        """, unsafe_allow_html=True)
        st.metric(t("connections_month", lang), user.get("connexions_mois", 0))
        st.metric(t("active_alerts", lang),     user.get("alertes_actives", 0))
        st.metric(t("tracked_stocks", lang),    user.get("titres_suivis", 0))

# ════════════════════════════════════════════════════════════
# TAB 2 — CHANGER LE MOT DE PASSE
# ════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"### {t('change_password_title', lang)}")
    st.caption(t("change_password_caption", lang))

    with st.form("form_change_password"):
        ancien_mdp  = st.text_input(t("current_password", lang), type="password", placeholder="••••••••")
        nouveau_mdp = st.text_input(t("new_password", lang),     type="password",
                                    placeholder=t("min_8_chars", lang))
        confirm_mdp = st.text_input(t("confirm_password", lang), type="password",
                                    placeholder=t("min_8_chars", lang))

        if nouveau_mdp:
            checks = {
                t("min_8_chars", lang):  len(nouveau_mdp) >= 8,
                t("one_uppercase", lang): bool(re.search(r'[A-Z]', nouveau_mdp)),
                t("one_digit", lang):     bool(re.search(r'\d', nouveau_mdp)),
                t("one_special", lang):   bool(re.search(r'[^A-Za-z0-9]', nouveau_mdp)),
            }
            force  = sum(checks.values())
            labels = ["", t("strength_weak", lang), t("strength_medium", lang),
                      t("strength_strong", lang), t("strength_very_strong", lang)]
            colors = ["", "red", "orange", "blue", "green"]
            st.progress(force / 4)
            st.caption(f"{t('password_strength', lang)} : :{colors[force]}[{labels[force]}]")
            for label, ok in checks.items():
                st.caption(f"{'✅' if ok else '❌'} {label}")

        submitted = st.form_submit_button(t("update_password_btn", lang),
                                          use_container_width=True, type="primary")
        if submitted:
            if not ancien_mdp:
                st.error(t("err_enter_current_pwd", lang))
            elif len(nouveau_mdp) < 8:
                st.error(t("err_pwd_too_short", lang))
            elif nouveau_mdp != confirm_mdp:
                st.error(t("err_pwd_no_match", lang))
            else:
                st.success(t("password_updated", lang))
                st.balloons()

# ════════════════════════════════════════════════════════════
# TAB 3 — RÉINITIALISATION PAR EMAIL
# ════════════════════════════════════════════════════════════
with tab3:
    st.markdown(f"### {t('reset_pwd_title', lang)}")
    st.caption(t("reset_pwd_caption", lang))

    with st.form("form_reset_password"):
        email_reset = st.text_input(t("your_email", lang),
                                    placeholder="exemple@email.com",
                                    value=user.get("email", ""))

        submitted = st.form_submit_button(t("send_reset_link", lang), use_container_width=True)
        if submitted:
            if not email_reset or "@" not in email_reset:
                st.error(t("err_invalid_email", lang))
            else:
                st.success(t("reset_link_sent", lang).format(email=email_reset))
                st.info(t("check_spam", lang))

    st.markdown("---")
    st.markdown(f"""
    <div class="profile-card">
        <h3>{t("security_tips", lang)}</h3>
        <ul style="color:#8A8580; font-size:13px; padding-left:1.2rem;">
            <li>{'Utilisez un mot de passe unique pour Afrika Markets' if lang=='fr' else 'Use a unique password for Afrika Markets' if lang=='en' else 'Utilice una contraseña única para Afrika Markets' if lang=='es' else 'Use uma senha única para a Afrika Markets' if lang=='pt' else '为Afrika Markets使用唯一密码' if lang=='zh' else 'استخدم كلمة مرور فريدة لـ Afrika Markets'}</li>
            <li>{'Activez l\'authentification à deux facteurs dès que disponible' if lang=='fr' else 'Enable two-factor authentication when available' if lang=='en' else 'Active la autenticación de dos factores cuando esté disponible' if lang=='es' else 'Ative a autenticação de dois fatores quando disponível' if lang=='pt' else '尽快启用双因素认证' if lang=='zh' else 'فعّل المصادقة الثنائية عند توفرها'}</li>
            <li>{'Ne partagez jamais vos identifiants' if lang=='fr' else 'Never share your credentials' if lang=='en' else 'Nunca comparta sus credenciales' if lang=='es' else 'Nunca compartilhe suas credenciais' if lang=='pt' else '切勿分享您的账户信息' if lang=='zh' else 'لا تشارك بيانات اعتمادك أبداً'}</li>
            <li>{'Déconnectez-vous sur les appareils partagés' if lang=='fr' else 'Log out on shared devices' if lang=='en' else 'Cierre sesión en dispositivos compartidos' if lang=='es' else 'Saia em dispositivos compartilhados' if lang=='pt' else '在共享设备上退出登录' if lang=='zh' else 'سجّل الخروج على الأجهزة المشتركة'}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ── Zone de danger ───────────────────────────────────────────
st.markdown("---")
with st.expander(t("danger_zone", lang), expanded=False):
    st.warning(t("irreversible_warning", lang))
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(t("logout_btn", lang), use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success(t("logged_out", lang))
            st.rerun()
    with col_b:
        if st.button(t("delete_account_btn", lang), use_container_width=True, type="secondary"):
            st.error(t("delete_account_msg", lang))
