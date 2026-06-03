"""
utils/i18n.py — Internationalisation Afrika Markets Intelligence
Langues : fr, en, es, pt, zh, ar
"""
import json
import functools
from pathlib import Path
import streamlit as st

ROOT_DIR = Path(__file__).parent.parent

LANGS: dict[str, str] = {
    "🇫🇷 Français":  "fr",
    "🇬🇧 English":   "en",
    "🇪🇸 Español":   "es",
    "🇧🇷 Português": "pt",
    "🇨🇳 中文":      "zh",
    "🇸🇦 العربية":   "ar",
}


@functools.lru_cache(maxsize=12)
def _load(lang: str) -> dict:
    """Charge le fichier JSON de traductions (mis en cache par langue)."""
    path = ROOT_DIR / "translations" / f"{lang}.json"
    if not path.exists():
        path = ROOT_DIR / "translations" / "fr.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def t(key: str, lang: str = "fr") -> str:
    """Retourne la traduction d'une clé. Retourne la clé si non trouvée."""
    return _load(lang).get(key, key)


def get_lang() -> str:
    """
    Affiche le sélecteur de langue dans la sidebar et retourne le code langue.
    Persiste dans st.session_state.lang entre les pages.
    """
    if "lang" not in st.session_state:
        st.session_state["lang"] = "fr"

    labels = list(LANGS.keys())
    codes  = list(LANGS.values())
    current_code = st.session_state.get("lang", "fr")
    current_idx  = codes.index(current_code) if current_code in codes else 0

    selected = st.sidebar.selectbox(
        "🌐 Language",
        labels,
        index=current_idx,
        key="lang_selector",
    )
    lang = LANGS[selected]
    st.session_state["lang"] = lang
    return lang
