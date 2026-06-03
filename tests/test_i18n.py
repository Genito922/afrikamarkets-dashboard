"""
tests/test_i18n.py — Vérification du système de traductions
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
LANGS = ["fr", "en", "es", "pt", "zh", "ar"]


def test_all_translation_files_exist():
    for lang in LANGS:
        path = ROOT / "translations" / f"{lang}.json"
        assert path.exists(), f"Fichier manquant : translations/{lang}.json"


def test_all_translation_files_valid_json():
    for lang in LANGS:
        path = ROOT / "translations" / f"{lang}.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), f"{lang}.json : doit être un dict"
        assert len(data) > 0, f"{lang}.json : vide"


def test_fr_en_keys_match():
    """FR est la langue de référence — toutes ses clés doivent exister en EN."""
    with open(ROOT / "translations" / "fr.json", encoding="utf-8") as f:
        fr = json.load(f)
    with open(ROOT / "translations" / "en.json", encoding="utf-8") as f:
        en = json.load(f)
    missing = [k for k in fr if k not in en]
    assert not missing, f"Clés manquantes dans en.json : {missing}"


def test_i18n_t_function():
    import sys
    sys.path.insert(0, str(ROOT))
    # Import sans streamlit (mock)
    import importlib, types
    st_mock = types.ModuleType("streamlit")
    st_mock.session_state = {}
    sys.modules["streamlit"] = st_mock
    from utils.i18n import t
    assert t("market_title", "fr") == "📊 Marché Actions BRVM"
    assert t("market_title", "en") == "📊 BRVM Equity Market"
    assert t("nonexistent_key", "fr") == "nonexistent_key"
