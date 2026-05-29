"""
BRVM Real-Time Scraper
Source : brvm.org
Cache  : 15 minutes
"""
import requests
import pandas as pd
from bs4 import BeautifulSoup
import streamlit as st
import urllib3
from datetime import datetime

urllib3.disable_warnings()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def _get(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
    r.raise_for_status()
    return BeautifulSoup(r.content, "html.parser")

def _clean_num(val: str) -> float:
    try:
        return float(str(val).replace(" ", "").replace(",", ".").replace("\xa0", ""))
    except:
        return 0.0

@st.cache_data(ttl=900)  # cache 15 min
def get_actions() -> pd.DataFrame:
    """Cours de toutes les actions BRVM."""
    soup = _get("https://www.brvm.org/fr/cours-actions/0/all")
    tables = soup.find_all("table")
    # Table 3 = cours actions
    for t in tables:
        ths = [h.text.strip() for h in t.find_all("th")]
        if "Symbole" in ths:
            rows = t.find_all("tr")[1:]
            data = []
            for row in rows:
                cols = [c.text.strip() for c in row.find_all("td")]
                if len(cols) >= 7:
                    data.append({
                        "symbole":      cols[0],
                        "nom":          cols[1],
                        "volume":       _clean_num(cols[2]),
                        "cours_veille": _clean_num(cols[3]),
                        "cours_ouv":    _clean_num(cols[4]),
                        "cours":        _clean_num(cols[5]),
                        "variation":    _clean_num(cols[6]),
                    })
            df = pd.DataFrame(data)
            df["secteur"] = df["symbole"].map(_get_secteur_map())
            return df
    return pd.DataFrame()

@st.cache_data(ttl=900)
def get_indices() -> dict:
    """Indices BRVM : composite, sectoriel."""
    soup = _get("https://www.brvm.org/fr/indices/0")
    tables = soup.find_all("table")
    indices = {"marche": [], "sectoriel": []}
    for t in tables:
        ths = [h.text.strip() for h in t.find_all("th")]
        if "Fermeture" in " ".join(ths):
            rows = t.find_all("tr")[1:]
            for row in rows:
                cols = [c.text.strip() for c in row.find_all("td")]
                if len(cols) >= 4:
                    entry = {
                        "nom":          cols[0],
                        "cloture_prec": _clean_num(cols[1]),
                        "cloture":      _clean_num(cols[2]),
                        "variation":    _clean_num(cols[3]),
                        "var_ytd":      _clean_num(cols[4]) if len(cols) > 4 else 0.0,
                    }
                    if "BRVM -" in cols[0] and "COMPOSITE" not in cols[0] and "30" not in cols[0]:
                        indices["sectoriel"].append(entry)
                    else:
                        indices["marche"].append(entry)
    return indices

@st.cache_data(ttl=900)
def get_marche() -> dict:
    """Activités globales du marché."""
    soup = _get("https://www.brvm.org/fr/cours-actions/0/all")
    tables = soup.find_all("table")
    result = {}
    for t in tables:
        ths = [h.text.strip() for h in t.find_all("th")]
        if "Activités du marché" in " ".join(ths):
            for row in t.find_all("tr")[1:]:
                cols = [c.text.strip() for c in row.find_all("td")]
                if len(cols) >= 2:
                    result[cols[0]] = cols[1]
    return result

def _get_secteur_map() -> dict:
    """Mapping symbole → secteur BRVM."""
    return {
        "ABJC": "Services", "BICC": "Finance", "BICB": "Finance",
        "BOAB": "Finance", "BOABF": "Finance", "BOAC": "Finance",
        "BOAN": "Finance", "BOAS": "Finance", "CABC": "Finance",
        "CBIBF": "Finance", "CFAC": "Finance", "CIEC": "Énergie",
        "ECOC": "Finance", "ETIT": "Télécoms", "FTSC": "Agriculture",
        "GBC": "Finance", "GGBC": "Finance", "LLBC": "Finance",
        "LTIC": "Finance", "NEIC": "Finance", "NSBC": "Finance",
        "ONTBF": "Services", "ORDI": "Finance", "PALC": "Agriculture",
        "PRSC": "Services", "SAFC": "Finance", "SCRC": "Services",
        "SDSC": "Services", "SEMC": "Industrie", "SGBC": "Finance",
        "SHEC": "Énergie", "SIBC": "Finance", "SICC": "Services",
        "SICF": "Finance", "SIVC": "Agriculture", "SLBC": "Finance",
        "SMBC": "Finance", "SNTS": "Télécoms", "SOGC": "Industrie",
        "SOLC": "Agriculture", "SPHC": "Services", "STAC": "Agriculture",
        "STBC": "Finance", "SVOC": "Industrie", "TTLC": "Télécoms",
        "TTLS": "Télécoms", "UNXC": "Services", "USAC": "Agriculture",
    }
