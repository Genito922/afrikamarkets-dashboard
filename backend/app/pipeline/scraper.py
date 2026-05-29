"""
BRVM Scraper — pure Python, pas de dépendance Streamlit.
Utilisé uniquement par le pipeline backend.
"""
import requests
import pandas as pd
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

SECTEUR_MAP: dict[str, str] = {
    "ABJC": "Services",    "BICC": "Finance",      "BICB": "Finance",
    "BOAB": "Finance",     "BOABF": "Finance",     "BOAC": "Finance",
    "BOAN": "Finance",     "BOAS": "Finance",      "CABC": "Finance",
    "CBIBF": "Finance",    "CFAC": "Finance",      "CIEC": "Énergie",
    "ECOC": "Finance",     "ETIT": "Télécoms",     "FTSC": "Agriculture",
    "GBC": "Finance",      "GGBC": "Finance",      "LLBC": "Finance",
    "LTIC": "Finance",     "NEIC": "Finance",      "NSBC": "Finance",
    "ONTBF": "Services",   "ORDI": "Finance",      "PALC": "Agriculture",
    "PRSC": "Services",    "SAFC": "Finance",      "SCRC": "Services",
    "SDSC": "Services",    "SEMC": "Industrie",    "SGBC": "Finance",
    "SHEC": "Énergie",     "SIBC": "Finance",      "SICC": "Services",
    "SICF": "Finance",     "SIVC": "Agriculture",  "SLBC": "Finance",
    "SMBC": "Finance",     "SNTS": "Télécoms",     "SOGC": "Industrie",
    "SOLC": "Agriculture", "SPHC": "Services",     "STAC": "Agriculture",
    "STBC": "Finance",     "SVOC": "Industrie",    "TTLC": "Télécoms",
    "TTLS": "Télécoms",    "UNXC": "Services",     "USAC": "Agriculture",
}


def _get(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
    r.raise_for_status()
    return BeautifulSoup(r.content, "html.parser")


def _num(val: str) -> float:
    try:
        return float(str(val).replace("\xa0", "").replace(" ", "").replace(",", "."))
    except Exception:
        return 0.0


def fetch_actions() -> pd.DataFrame:
    """Retourne un DataFrame avec tous les cours actions BRVM."""
    soup = _get("https://www.brvm.org/fr/cours-actions/0/all")
    for table in soup.find_all("table"):
        headers = [th.text.strip() for th in table.find_all("th")]
        if "Symbole" in headers:
            rows = []
            for tr in table.find_all("tr")[1:]:
                cols = [td.text.strip() for td in tr.find_all("td")]
                if len(cols) >= 7:
                    rows.append({
                        "symbole":      cols[0],
                        "nom":          cols[1],
                        "volume":       _num(cols[2]),
                        "cours_veille": _num(cols[3]),
                        "cours_ouv":    _num(cols[4]),
                        "cours":        _num(cols[5]),
                        "variation":    _num(cols[6]),
                    })
            df = pd.DataFrame(rows)
            df["secteur"] = df["symbole"].map(SECTEUR_MAP)
            return df
    return pd.DataFrame()


def fetch_indices() -> dict:
    """Retourne {"marche": [...], "sectoriel": [...]}."""
    soup = _get("https://www.brvm.org/fr/indices/0")
    result: dict = {"marche": [], "sectoriel": []}
    for table in soup.find_all("table"):
        headers = " ".join(th.text.strip() for th in table.find_all("th"))
        if "Fermeture" not in headers:
            continue
        for tr in table.find_all("tr")[1:]:
            cols = [td.text.strip() for td in tr.find_all("td")]
            if len(cols) < 4:
                continue
            entry = {
                "nom":          cols[0],
                "cloture_prec": _num(cols[1]),
                "cloture":      _num(cols[2]),
                "variation":    _num(cols[3]),
                "var_ytd":      _num(cols[4]) if len(cols) > 4 else 0.0,
            }
            is_sectoriel = (
                "BRVM -" in cols[0]
                and "COMPOSITE" not in cols[0]
                and "30" not in cols[0]
            )
            result["sectoriel" if is_sectoriel else "marche"].append(entry)
    return result


def fetch_marche() -> dict:
    """Retourne les activités globales du marché."""
    soup = _get("https://www.brvm.org/fr/cours-actions/0/all")
    for table in soup.find_all("table"):
        headers = " ".join(th.text.strip() for th in table.find_all("th"))
        if "Activités du marché" not in headers:
            continue
        out = {}
        for tr in table.find_all("tr")[1:]:
            cols = [td.text.strip() for td in tr.find_all("td")]
            if len(cols) >= 2:
                out[cols[0]] = cols[1]
        return out
    return {}
