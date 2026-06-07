"""
War Room Data Pipeline — Afrika Markets Intelligence
Sources (toutes gratuites, sans clé API) :
  1. IMF DataMapper API  → PIB croissance (NGDP_RPCH) + inflation (PCPIPCH)
  2. World Bank WGI API  → Stabilité politique (PV.EST) → score risque 1–10
  3. HDX/ACLED CSV       → nombre d'événements violents (90 derniers jours)
                           Fallback statique si HDX indisponible.
"""
import io
import logging
import math
from datetime import date, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Référentiel UEMOA ─────────────────────────────────────────

UEMOA = [
    {"iso2": "CI", "iso3": "CIV", "nom": "Côte d'Ivoire", "flag": "🇨🇮", "impact_brvm": "fort"},
    {"iso2": "SN", "iso3": "SEN", "nom": "Sénégal",        "flag": "🇸🇳", "impact_brvm": "fort"},
    {"iso2": "BF", "iso3": "BFA", "nom": "Burkina Faso",   "flag": "🇧🇫", "impact_brvm": "moyen"},
    {"iso2": "ML", "iso3": "MLI", "nom": "Mali",           "flag": "🇲🇱", "impact_brvm": "moyen"},
    {"iso2": "NE", "iso3": "NER", "nom": "Niger",          "flag": "🇳🇪", "impact_brvm": "faible"},
    {"iso2": "BJ", "iso3": "BEN", "nom": "Bénin",          "flag": "🇧🇯", "impact_brvm": "moyen"},
    {"iso2": "TG", "iso3": "TGO", "nom": "Togo",           "flag": "🇹🇬", "impact_brvm": "moyen"},
    {"iso2": "GW", "iso3": "GNB", "nom": "Guinée-Bissau",  "flag": "🇬🇼", "impact_brvm": "faible"},
]

# Textes curatés — invariants (mis à jour manuellement)
_SITUATION = {
    "CI": "Croissance soutenue par la filière cacao et les investissements publics. Stabilité politique post-2020.",
    "SN": "Transition présidentielle réussie. Début d'exploitation pétrolière (Sangomar). Croissance élevée attendue.",
    "BF": "Transition militaire en cours. Instabilité sécuritaire au Nord. Retrait de l'espace CEDEAO.",
    "ML": "Transition militaire prolongée. Alliance avec la Russie (Wagner). Sanctions CEDEAO partiellement levées.",
    "NE": "Coup d'État juillet 2023. Sanctions CEDEAO. Exportations pétrole via pipeline Nigéria.",
    "BJ": "Stabilité politique. Programmes d'investissement port de Cotonou. Légère tension sécurité nord.",
    "TG": "Stabilité relative. Hub logistique Lomé actif. Légère pression sociale.",
    "GW": "Instabilité institutionnelle récurrente. Economie de subsistance dominée par la noix de cajou.",
}

_MARKET_IMPACT = {
    "CI": "Impact direct fort sur la BRVM (60% de la capitalisation)",
    "SN": "Fort impact — 2ème plus grande économie UEMOA",
    "BF": "Impact indirect via sentiment régional",
    "ML": "Faible exposition BRVM directe",
    "NE": "Très faible exposition BRVM",
    "BJ": "Impact modéré — hub régional",
    "TG": "Impact modéré",
    "GW": "Très faible exposition BRVM",
}

# Fallback statique ACLED (mis à jour trimestriellement)
_ACLED_FALLBACK = {
    "CI": 8, "SN": 5, "BF": 142, "ML": 118,
    "NE": 87, "BJ": 22, "TG": 12, "GW": 18,
}


# ── Helpers ───────────────────────────────────────────────────

def _f(val, default=None) -> Optional[float]:
    try:
        v = float(val)
        return None if math.isnan(v) else round(v, 2)
    except (TypeError, ValueError):
        return default


def _wb_to_risk(pv_est: Optional[float]) -> int:
    """WGI PV.EST [-2.5, +2.5] → score risque [1, 10]."""
    if pv_est is None:
        return 5
    normalized = (pv_est + 2.5) / 5.0   # 0..1
    return max(1, min(10, round(10 - normalized * 9)))


def _risk_to_note(risk: int) -> str:
    if risk <= 3: return "Stable"
    if risk <= 5: return "Modéré"
    if risk <= 7: return "Fragile"
    return "Transition militaire"


# ── Sources de données ────────────────────────────────────────

def fetch_imf(iso3: str) -> dict:
    """IMF DataMapper : PIB croissance + inflation pour l'année la plus récente."""
    result = {}
    for indicator, key in [("NGDP_RPCH", "gdp_growth"), ("PCPIPCH", "inflation")]:
        try:
            r = httpx.get(
                f"https://www.imf.org/external/datamapper/api/v1/{indicator}/{iso3}",
                timeout=12,
            )
            r.raise_for_status()
            values = r.json().get("values", {}).get(indicator, {}).get(iso3, {})
            if values:
                latest = max(values.keys())
                result[key] = _f(values[latest])
        except Exception as exc:
            logger.warning("[IMF] %s %s — %s", iso3, indicator, exc)
    return result


def fetch_wb_stability(iso3: str) -> Optional[float]:
    """World Bank WGI : Political Stability and Absence of Violence (PV.EST)."""
    try:
        r = httpx.get(
            f"https://api.worldbank.org/v2/country/{iso3}/indicator/PV.EST",
            params={"format": "json", "mrv": 1, "per_page": 1},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 1 and data[1]:
            return _f(data[1][0].get("value"))
    except Exception as exc:
        logger.warning("[WorldBank] %s PV.EST — %s", iso3, exc)
    return None


def fetch_acled_hdx() -> dict:
    """
    Compte des événements violents (90 derniers jours) par pays UEMOA via HDX/ACLED CSV.
    Retourne le fallback statique en cas d'échec.
    """
    try:
        import pandas as pd

        # 1. Découvrir le package ACLED via la recherche CKAN (slug change régulièrement)
        search_r = httpx.get(
            "https://data.humdata.org/api/3/action/package_search",
            params={"q": "acled western africa", "rows": 5},
            timeout=15,
        )
        search_r.raise_for_status()
        results = search_r.json().get("result", {}).get("results", [])
        pkg = next(
            (p for p in results if "acled" in p.get("name", "").lower()),
            None,
        )
        if not pkg:
            raise ValueError("Aucun package ACLED trouvé via HDX search")
        logger.info("[ACLED/HDX] Package découvert : %s", pkg["name"])
        r = httpx.get(
            "https://data.humdata.org/api/3/action/package_show",
            params={"id": pkg["name"]},
            timeout=15,
        )
        r.raise_for_status()
        resources = r.json().get("result", {}).get("resources", [])
        csv_url = next(
            (res["url"] for res in resources if res.get("format", "").upper() == "CSV"),
            None,
        )
        if not csv_url:
            logger.warning("[ACLED/HDX] Aucune ressource CSV — fallback statique")
            return _ACLED_FALLBACK.copy()

        # 2. Télécharger et parser le CSV
        resp = httpx.get(csv_url, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), low_memory=False)

        # 3. Normaliser les noms de colonnes
        df.columns = [c.lower() for c in df.columns]
        if "event_date" not in df.columns:
            logger.warning("[ACLED/HDX] Colonne event_date absente — fallback statique")
            return _ACLED_FALLBACK.copy()

        # 4. Filtrer sur les 90 derniers jours
        df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
        cutoff = pd.Timestamp(date.today() - timedelta(days=90))
        df = df[df["event_date"] >= cutoff]

        # 5. Compter par pays
        COUNTRY_MAP = {
            "Ivory Coast": "CI", "Côte d'Ivoire": "CI", "Cote d'Ivoire": "CI",
            "Senegal": "SN", "Burkina Faso": "BF", "Mali": "ML",
            "Niger": "NE", "Benin": "BJ", "Togo": "TG", "Guinea-Bissau": "GW",
        }
        counts = _ACLED_FALLBACK.copy()
        if "country" in df.columns:
            for name, iso2 in COUNTRY_MAP.items():
                n = int((df["country"] == name).sum())
                if n > 0:
                    counts[iso2] = n

        logger.info("[ACLED/HDX] ✓ événements 90j récupérés")
        return counts

    except Exception as exc:
        logger.debug("[ACLED/HDX] Échec (%s) — fallback statique", exc)
        return _ACLED_FALLBACK.copy()


# ── Builder principal ─────────────────────────────────────────

async def build_warroom_payload() -> list:
    """
    Construit le payload complet War Room avec données réelles.
    Appelé par le job scheduler (hebdomadaire + boot).
    """
    import asyncio

    acled = fetch_acled_hdx()
    results = []

    for country in UEMOA:
        iso2, iso3 = country["iso2"], country["iso3"]

        imf  = fetch_imf(iso3)
        pv   = fetch_wb_stability(iso3)
        risk = _wb_to_risk(pv)

        results.append({
            "iso2":          iso2,
            "nom":           country["nom"],
            "flag":          country["flag"],
            "impact_brvm":   country["impact_brvm"],
            "risque":        risk,
            "note":          _risk_to_note(risk),
            "events_90d":    acled.get(iso2, 0),
            "gdp_growth":    imf.get("gdp_growth"),
            "inflation":     imf.get("inflation"),
            "pv_est":        pv,
            "situation":     _SITUATION.get(iso2, ""),
            "market_impact": _MARKET_IMPACT.get(iso2, ""),
        })

        await asyncio.sleep(0.5)   # rythme poli IMF/World Bank

    logger.info("[WarRoom] Payload construit — %d pays", len(results))
    return results
