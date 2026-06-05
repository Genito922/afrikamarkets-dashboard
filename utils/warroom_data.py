"""
utils/warroom_data.py
Données réelles War Room — ACLED OAuth (nouveau système 2025) + IMF + fallback.
Auth : email + password myACLED → access_token (24h) + refresh_token.
Cache 6h pour les données, token renouvelé automatiquement.
"""
import os
import time
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── Pays UEMOA ────────────────────────────────────────────────────────────────
UEMOA_COUNTRIES = {
    "CI": {"nom": "Côte d'Ivoire", "flag": "🇨🇮", "impact_brvm": "fort",    "iso3": "CIV"},
    "SN": {"nom": "Sénégal",       "flag": "🇸🇳", "impact_brvm": "fort",    "iso3": "SEN"},
    "BF": {"nom": "Burkina Faso",  "flag": "🇧🇫", "impact_brvm": "moyen",  "iso3": "BFA"},
    "ML": {"nom": "Mali",          "flag": "🇲🇱", "impact_brvm": "moyen",  "iso3": "MLI"},
    "NE": {"nom": "Niger",         "flag": "🇳🇪", "impact_brvm": "faible", "iso3": "NER"},
    "BJ": {"nom": "Bénin",         "flag": "🇧🇯", "impact_brvm": "moyen",  "iso3": "BEN"},
    "TG": {"nom": "Togo",          "flag": "🇹🇬", "impact_brvm": "moyen",  "iso3": "TGO"},
    "GW": {"nom": "Guinée-Bissau", "flag": "🇬🇼", "impact_brvm": "faible", "iso3": "GNB"},
}

FALLBACK = {
    "CI": {"risque": 2, "note": "Stable",               "events_90d": 8,   "gdp_growth": 6.5, "inflation": 3.2},
    "SN": {"risque": 2, "note": "Stable",               "events_90d": 5,   "gdp_growth": 8.3, "inflation": 2.8},
    "BF": {"risque": 8, "note": "Transition militaire", "events_90d": 142, "gdp_growth": 2.1, "inflation": 5.4},
    "ML": {"risque": 8, "note": "Transition militaire", "events_90d": 118, "gdp_growth": 3.2, "inflation": 6.1},
    "NE": {"risque": 9, "note": "Transition militaire", "events_90d": 87,  "gdp_growth": 6.9, "inflation": 4.2},
    "BJ": {"risque": 3, "note": "Stable",               "events_90d": 22,  "gdp_growth": 6.0, "inflation": 1.8},
    "TG": {"risque": 4, "note": "Stable",               "events_90d": 12,  "gdp_growth": 5.5, "inflation": 4.1},
    "GW": {"risque": 5, "note": "Fragile",              "events_90d": 18,  "gdp_growth": 4.5, "inflation": 3.9},
}

# ── Cache ─────────────────────────────────────────────────────────────────────
_CACHE: dict = {}
CACHE_TTL_DATA  = 6 * 3600   # données : 6h
CACHE_TTL_TOKEN = 23 * 3600  # token : 23h (expire à 24h)

def _cache_get(key):
    if key in _CACHE:
        ts, data = _CACHE[key]
        ttl = CACHE_TTL_TOKEN if key == "acled_token" else CACHE_TTL_DATA
        if time.time() - ts < ttl:
            return data
    return None

def _cache_set(key, data):
    _CACHE[key] = (time.time(), data)


# ── ACLED OAuth — nouveau système myACLED ────────────────────────────────────
def _get_acled_token() -> str | None:
    """Obtient un access_token via email + password (OAuth myACLED)."""
    cached = _cache_get("acled_token")
    if cached:
        return cached

    email    = os.getenv("ACLED_EMAIL", "")
    password = os.getenv("ACLED_PASSWORD", "")

    if not email or not password:
        logger.warning("[WarRoom] ACLED_EMAIL/ACLED_PASSWORD manquants — fallback")
        return None

    try:
        r = requests.post(
            "https://acleddata.com/api/auth/token",
            json={"email": email, "password": password},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        token = data.get("access_token") or data.get("token")
        if token:
            _cache_set("acled_token", token)
            logger.info("[WarRoom] ACLED token obtenu OK")
        return token
    except Exception as exc:
        logger.error("[WarRoom] ACLED auth erreur : %s", exc)
        return None


def fetch_acled_events() -> dict[str, int]:
    """Retourne {iso2: nb_events_90j} via API ACLED OAuth."""
    cached = _cache_get("acled")
    if cached:
        return cached

    token = _get_acled_token()
    if not token:
        return {}

    since = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
    iso3s = "|".join(v["iso3"] for v in UEMOA_COUNTRIES.values())

    try:
        r = requests.get(
            "https://acleddata.com/api/acled/read",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "iso":              iso3s,
                "event_date":       since,
                "event_date_where": ">=",
                "fields":           "iso,event_date,event_type",
                "limit":            5000,
                "format":           "json",
            },
            timeout=15,
        )
        r.raise_for_status()
        events = r.json().get("data", [])

        iso3_counts: dict[str, int] = {}
        for e in events:
            iso3 = e.get("iso", "")
            iso3_counts[iso3] = iso3_counts.get(iso3, 0) + 1

        iso3_to_iso2 = {v["iso3"]: k for k, v in UEMOA_COUNTRIES.items()}
        result = {iso3_to_iso2[k]: v for k, v in iso3_counts.items() if k in iso3_to_iso2}
        _cache_set("acled", result)
        logger.info("[WarRoom] ACLED OK — %d événements", len(events))
        return result

    except Exception as exc:
        logger.error("[WarRoom] ACLED fetch erreur : %s", exc)
        return {}


# ── IMF (public, sans auth) ───────────────────────────────────────────────────
def fetch_imf_macro() -> dict[str, dict]:
    cached = _cache_get("imf")
    if cached:
        return cached

    indicators = {"NGDP_RPCH": "gdp_growth", "PCPIPCH": "inflation"}
    result: dict[str, dict] = {iso2: {} for iso2 in UEMOA_COUNTRIES}

    for imf_ind, field in indicators.items():
        try:
            iso3s = ",".join(v["iso3"] for v in UEMOA_COUNTRIES.values())
            r = requests.get(
                f"https://www.imf.org/external/datamapper/api/v1/{imf_ind}/{iso3s}",
                timeout=10,
            )
            r.raise_for_status()
            data = r.json().get("values", {}).get(imf_ind, {})
            iso3_to_iso2 = {v["iso3"]: k for k, v in UEMOA_COUNTRIES.items()}
            year = str(datetime.utcnow().year)
            prev = str(datetime.utcnow().year - 1)
            for iso3, yearly in data.items():
                iso2 = iso3_to_iso2.get(iso3)
                if not iso2:
                    continue
                val = yearly.get(year) or yearly.get(prev)
                if val is not None:
                    result[iso2][field] = round(float(val), 1)
        except Exception as exc:
            logger.warning("[WarRoom] IMF %s erreur : %s", imf_ind, exc)

    if any(result.values()):
        _cache_set("imf", result)
    return result


# ── Score dynamique ───────────────────────────────────────────────────────────
def _compute_risk_score(iso2, events_90d, gdp_growth, inflation):
    score = 0.0
    if   events_90d >= 150: score += 5.0
    elif events_90d >= 80:  score += 4.0
    elif events_90d >= 40:  score += 3.0
    elif events_90d >= 20:  score += 2.0
    elif events_90d >= 10:  score += 1.0
    else:                   score += 0.5

    if   gdp_growth < 0: score += 2.0
    elif gdp_growth < 2: score += 1.5
    elif gdp_growth < 4: score += 1.0
    elif gdp_growth < 6: score += 0.5

    if   inflation > 10: score += 2.0
    elif inflation > 7:  score += 1.5
    elif inflation > 5:  score += 1.0
    elif inflation > 3:  score += 0.5

    if iso2 in {"BF", "ML", "NE"}:
        score = max(score, 7.5)

    score = min(10, max(1, round(score)))
    if   score <= 3: note = "Stable"
    elif score <= 6: note = "Fragile"
    elif score <= 8: note = "Transition / Instable"
    else:            note = "Crise sécuritaire"
    return int(score), note


# ── Point d'entrée ────────────────────────────────────────────────────────────
def get_warroom_data() -> list[dict]:
    acled  = fetch_acled_events()
    imf    = fetch_imf_macro()
    rows   = []

    for iso2, meta in UEMOA_COUNTRIES.items():
        fb = FALLBACK[iso2]
        events_90d = acled.get(iso2, fb["events_90d"])
        gdp_growth = imf.get(iso2, {}).get("gdp_growth", fb["gdp_growth"])
        inflation  = imf.get(iso2, {}).get("inflation",  fb["inflation"])

        if acled or imf.get(iso2):
            risque, note = _compute_risk_score(iso2, events_90d, gdp_growth, inflation)
        else:
            risque, note = fb["risque"], fb["note"]

        rows.append({
            "iso2":        iso2,
            "pays":        meta["nom"],
            "flag":        meta["flag"],
            "risque":      risque,
            "note":        note,
            "impact_brvm": meta["impact_brvm"],
            "events_90d":  events_90d,
            "gdp_growth":  gdp_growth,
            "inflation":   inflation,
            "source":      "ACLED+IMF" if (acled or imf.get(iso2)) else "Estimation",
            "updated_at":  datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
        })

    return sorted(rows, key=lambda x: x["risque"])


def get_cache_status() -> dict:
    status = {}
    for key in ["acled_token", "acled", "imf"]:
        if key in _CACHE:
            ts, _ = _CACHE[key]
            age = int((time.time() - ts) / 60)
            status[key] = f"Cache actif ({age} min)"
        else:
            status[key] = "Non chargé"
    return status
