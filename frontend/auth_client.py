"""
Client HTTP vers le FastAPI backend — Afrika Markets Intelligence
"""
import requests
import streamlit as st


def _api_url() -> str:
    try:
        return st.secrets["BRVM_API_URL"]
    except Exception:
        return "http://localhost:8001"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _safe_json(r):
    try:
        return r.json(), r.status_code
    except Exception:
        return {"detail": f"Erreur serveur (HTTP {r.status_code})"}, r.status_code


def _conn_error():
    return {"detail": "Serveur inaccessible — vérifiez la connexion"}, 503


def register(email, password, full_name, country="CA", phone=""):
    try:
        r = requests.post(
            f"{_api_url()}/auth/register",
            json={"email": email, "password": password,
                  "full_name": full_name, "country": country, "phone": phone},
            timeout=10,
        )
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def login(email, password):
    try:
        r = requests.post(
            f"{_api_url()}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def get_me(token):
    try:
        r = requests.get(
            f"{_api_url()}/auth/me",
            headers=_headers(token),
            timeout=10,
        )
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def validate_licence(token_licence):
    try:
        r = requests.get(
            f"{_api_url()}/licences/validate/{token_licence}",
            timeout=10,
        )
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def create_stripe_checkout(jwt_token, plan, success_url, cancel_url):
    try:
        r = requests.post(
            f"{_api_url()}/payments/stripe/checkout",
            json={"user_id": st.session_state.get("user", {}).get("id"),
                  "plan": plan,
                  "success_url": success_url,
                  "cancel_url": cancel_url},
            headers=_headers(jwt_token),
            timeout=10,
        )
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def initiate_wave(jwt_token, plan, phone):
    try:
        r = requests.post(
            f"{_api_url()}/payments/wave/initiate",
            json={"user_id": st.session_state.get("user", {}).get("id"),
                  "plan": plan, "phone": phone},
            headers=_headers(jwt_token),
            timeout=15,
        )
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def initiate_orange(jwt_token, plan, phone):
    try:
        r = requests.post(
            f"{_api_url()}/payments/orange/initiate",
            json={"user_id": st.session_state.get("user", {}).get("id"),
                  "plan": plan, "phone": phone},
            headers=_headers(jwt_token),
            timeout=15,
        )
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


# ── Market Data ───────────────────────────────────────────────

def get_market_actions():
    """Derniers cours actions depuis la base de données."""
    try:
        r = requests.get(f"{_api_url()}/market/actions", timeout=10)
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def get_market_history(symbole: str, days: int = 30):
    """Historique OHLCV d'une action (N jours max 365)."""
    try:
        r = requests.get(
            f"{_api_url()}/market/actions/{symbole}/history",
            params={"days": days},
            timeout=10,
        )
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def get_market_indices():
    """Derniers indices BRVM depuis la base."""
    try:
        r = requests.get(f"{_api_url()}/market/indices", timeout=10)
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()


def trigger_scrape():
    """Déclenche un scraping manuel (dev/admin)."""
    try:
        r = requests.post(f"{_api_url()}/market/scrape", timeout=30)
        return _safe_json(r)
    except requests.exceptions.ConnectionError:
        return _conn_error()
