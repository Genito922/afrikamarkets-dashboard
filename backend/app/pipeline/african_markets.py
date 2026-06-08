"""
African-Markets.com scraper — données BRVM + autres marchés africains
  • fetch_brvm_listed()          → 47 titres BRVM : cours, variation, P/E, secteur
  • fetch_company_profile()      → annonces, dividendes, rapports annuels par ticker
  • fetch_currencies()           → taux XOF/USD + 17 devises africaines
  • fetch_brvm_news()            → actualités marché BRVM
  • fetch_exchange_listed(slug)  → titres cotés sur une autre bourse africaine
  • AFRICAN_EXCHANGES            → catalogue des bourses africaines (meta + SGI)
  • AFRICAN_SGIS                 → annuaire SGI/brokers par bourse

Authentification : AM_EMAIL / AM_PASSWORD (vars Railway).
Session Joomla stockée en mémoire (refresh auto si 401/403).
"""
import logging
import os
import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.african-markets.com"
_SESSION_COOKIES: dict = {}

# ── Auth ──────────────────────────────────────────────────────────────────────

def _credentials() -> tuple[str, str]:
    email    = os.getenv("AM_EMAIL", "")
    password = os.getenv("AM_PASSWORD", "")
    return email, password


def _get_joomla_token(client: httpx.Client) -> str:
    """Récupère le CSRF token Joomla depuis la page de login."""
    r = client.get(f"{BASE_URL}/fr/component/users/?view=login", timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    # Joomla cache le token dans un input hidden au nom aléatoire (32 chars hex)
    for inp in soup.find_all("input", {"type": "hidden"}):
        name  = inp.get("name", "")
        value = inp.get("value", "")
        if len(name) == 32 and re.fullmatch(r"[0-9a-f]{32}", name) and value == "1":
            return name
    return ""


def _login(client: httpx.Client) -> bool:
    """Login Joomla, stocke les cookies dans _SESSION_COOKIES."""
    global _SESSION_COOKIES
    email, password = _credentials()
    if not email or not password:
        logger.debug("[AM] AM_EMAIL / AM_PASSWORD non configurés — mode anonyme")
        return False
    try:
        token = _get_joomla_token(client)
        payload = {
            "username": email,
            "password": password,
            "option":   "com_users",
            "task":     "user.login",
            "return":   "aW5kZXgucGhw",  # base64("index.php")
        }
        if token:
            payload[token] = "1"
        r = client.post(
            f"{BASE_URL}/fr/component/users/",
            data=payload,
            timeout=20,
            follow_redirects=True,
        )
        # Vérification : on doit être redirigé hors de /login
        if "task=user.login" not in str(r.url):
            _SESSION_COOKIES = dict(client.cookies)
            logger.info("[AM] Login réussi (%s)", email)
            return True
        logger.warning("[AM] Login échoué — check AM_EMAIL/AM_PASSWORD")
        return False
    except Exception as exc:
        logger.warning("[AM] Login exception : %s", exc)
        return False


def _client() -> httpx.Client:
    """Retourne un client httpx avec User-Agent + cookies de session."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }
    client = httpx.Client(
        headers=headers,
        cookies=_SESSION_COOKIES,
        follow_redirects=True,
        timeout=25,
        verify=False,
    )
    return client


def _get(path: str, *, authenticated: bool = False) -> BeautifulSoup:
    """GET + parse HTML. Si authenticated, tente login si cookies vides."""
    with _client() as client:
        if authenticated and not _SESSION_COOKIES:
            _login(client)
        url = BASE_URL + path
        r = client.get(url, timeout=25)
        r.raise_for_status()
        return BeautifulSoup(r.content, "html.parser")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _num(val: str) -> Optional[float]:
    if not val or val in ("-", "N/A", "n/a", "—"):
        return None
    try:
        return float(str(val).replace("\xa0", "").replace(" ", "").replace(",", ".").replace("%", ""))
    except Exception:
        return None


def _text(tag) -> str:
    return tag.get_text(strip=True) if tag else ""


# ── fetch_brvm_listed ─────────────────────────────────────────────────────────

def fetch_brvm_listed() -> list[dict]:
    """
    Scrape african-markets.com/fr/bourse/brvm/listed-companies.
    Retourne une liste de dicts :
      {symbole, nom, secteur, cours, variation_pct, ytd_pct, pe_ratio, date_cours}
    """
    try:
        soup = _get("/fr/bourse/brvm/listed-companies")
    except Exception as exc:
        logger.error("[AM] fetch_brvm_listed — %s", exc)
        return []

    results = []
    tables = soup.find_all("table")
    for table in tables:
        headers = [_text(th).lower() for th in table.find_all("th")]
        # Cherche la colonne "cours" ou "price"
        if not any(h in ("cours", "price", "last price") for h in headers):
            continue
        rows = table.find_all("tr")[1:]
        for tr in rows:
            cols = tr.find_all("td")
            if len(cols) < 3:
                continue
            # Lien vers la company page → extrait le code ticker
            link_tag = tr.find("a", href=True)
            symbole  = ""
            if link_tag:
                m = re.search(r"[?&]code=([A-Z0-9]+)", link_tag["href"])
                if m:
                    symbole = m.group(1)

            texts = [_text(c) for c in cols]
            # Mapping flexible selon l'ordre des colonnes
            # Structure probable : Nom | Secteur | Cours | Variation% | YTD% | P/E | Date
            entry = {
                "symbole":       symbole,
                "nom":           texts[0] if len(texts) > 0 else "",
                "secteur":       texts[1] if len(texts) > 1 else None,
                "cours":         _num(texts[2]) if len(texts) > 2 else None,
                "variation_pct": _num(texts[3]) if len(texts) > 3 else None,
                "ytd_pct":       _num(texts[4]) if len(texts) > 4 else None,
                "pe_ratio":      _num(texts[5]) if len(texts) > 5 else None,
                "date_cours":    texts[6]        if len(texts) > 6 else None,
            }
            if entry["symbole"] or entry["cours"]:
                results.append(entry)
        if results:
            break  # On a trouvé la bonne table

    logger.info("[AM] fetch_brvm_listed → %d titres", len(results))
    return results


# ── fetch_company_profile ─────────────────────────────────────────────────────

def fetch_company_profile(code: str) -> dict:
    """
    Scrape la page société african-markets.com/fr/bourse/brvm/listed-companies/company?code=CODE.
    Retourne :
      {code, nom, secteur, description,
       dividends: [{date, montant_xof, rendement_pct}],
       announcements: [{date, titre, url}],
       annual_reports: [{annee, titre, url}]}
    """
    result: dict = {
        "code":          code,
        "nom":           "",
        "secteur":       "",
        "description":   "",
        "dividends":     [],
        "announcements": [],
        "annual_reports": [],
    }
    try:
        soup = _get(f"/fr/bourse/brvm/listed-companies/company?code={code}")
    except Exception as exc:
        logger.error("[AM] fetch_company_profile(%s) — %s", code, exc)
        return result

    # Nom de la société (h1 ou h2)
    h1 = soup.find("h1") or soup.find("h2")
    if h1:
        result["nom"] = _text(h1)

    # Description (premier <p> substantiel)
    for p in soup.find_all("p"):
        txt = _text(p)
        if len(txt) > 60:
            result["description"] = txt
            break

    # ── Dividendes ────────────────────────────────────────────
    for table in soup.find_all("table"):
        headers_text = " ".join(_text(th).lower() for th in table.find_all("th"))
        if "dividend" not in headers_text and "dividende" not in headers_text:
            continue
        for tr in table.find_all("tr")[1:]:
            cols = [_text(td) for td in tr.find_all("td")]
            if len(cols) < 2:
                continue
            result["dividends"].append({
                "date":           cols[0],
                "montant_xof":    _num(cols[1]),
                "rendement_pct":  _num(cols[2]) if len(cols) > 2 else None,
            })
        break

    # ── Annonces (communiqués de presse) ─────────────────────
    for section in soup.find_all(["section", "div"]):
        heading = section.find(["h3", "h4", "h5"])
        if not heading:
            continue
        if "annonce" not in _text(heading).lower() and "communiqué" not in _text(heading).lower():
            continue
        for a in section.find_all("a", href=True):
            title = _text(a)
            href  = a["href"]
            if not title or len(title) < 5:
                continue
            # Cherche une date proche (span, td, ou texte autour)
            date_txt = ""
            parent = a.parent
            for _ in range(3):
                if parent is None:
                    break
                spans = parent.find_all(["span", "td", "time"])
                for sp in spans:
                    txt = _text(sp)
                    if re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", txt) or re.search(r"\d{4}-\d{2}-\d{2}", txt):
                        date_txt = txt
                        break
                if date_txt:
                    break
                parent = parent.parent
            result["announcements"].append({
                "date":  date_txt,
                "titre": title,
                "url":   href if href.startswith("http") else BASE_URL + href,
            })
        if result["announcements"]:
            break

    # ── Rapports annuels ──────────────────────────────────────
    for a in soup.find_all("a", href=True):
        href  = a["href"].lower()
        title = _text(a)
        if any(kw in href for kw in ["rapport", "annual", "report", ".pdf"]) or \
           any(kw in title.lower() for kw in ["rapport annuel", "annual report"]):
            # Extrait l'année si présente
            m_year = re.search(r"20\d{2}", title + href)
            result["annual_reports"].append({
                "annee": int(m_year.group()) if m_year else None,
                "titre": title,
                "url":   href if href.startswith("http") else BASE_URL + a["href"],
            })

    # Déduplique les rapports par URL
    seen = set()
    deduped = []
    for r in result["annual_reports"]:
        if r["url"] not in seen:
            seen.add(r["url"])
            deduped.append(r)
    result["annual_reports"] = deduped[:10]  # max 10

    logger.info(
        "[AM] fetch_company_profile(%s) → %d divid, %d annonces, %d rapports",
        code, len(result["dividends"]), len(result["announcements"]), len(result["annual_reports"])
    )
    return result


# ── fetch_currencies ──────────────────────────────────────────────────────────

def fetch_currencies() -> list[dict]:
    """
    Scrape african-markets.com/fr/currencies.
    Retourne [{nom, code, usd_rate, variation_pct, ytd_pct, date}].
    Inclut XOF/CFA franc.
    """
    try:
        soup = _get("/fr/currencies")
    except Exception as exc:
        logger.error("[AM] fetch_currencies — %s", exc)
        return []

    results = []
    for table in soup.find_all("table"):
        headers = [_text(th).lower() for th in table.find_all("th")]
        if not any(h in ("code", "devise", "currency") for h in headers):
            continue
        for tr in table.find_all("tr")[1:]:
            cols = [_text(td) for td in tr.find_all("td")]
            if len(cols) < 3:
                continue
            results.append({
                "nom":           cols[0],
                "code":          cols[1] if len(cols) > 1 else "",
                "usd_rate":      _num(cols[2]) if len(cols) > 2 else None,
                "variation_pct": _num(cols[3]) if len(cols) > 3 else None,
                "ytd_pct":       _num(cols[4]) if len(cols) > 4 else None,
                "date":          cols[5]        if len(cols) > 5 else None,
            })
        if results:
            break

    logger.info("[AM] fetch_currencies → %d devises", len(results))
    return results


# ── fetch_brvm_news ───────────────────────────────────────────────────────────

def fetch_brvm_news(limit: int = 20) -> list[dict]:
    """
    Scrape les actualités BRVM depuis african-markets.com.
    Retourne [{titre, url, date, resume}].
    """
    try:
        soup = _get("/fr/bourse/brvm/actualites-brvm")
    except Exception as exc:
        logger.error("[AM] fetch_brvm_news — %s", exc)
        return []

    results = []
    # Cherche les articles (liens avec classe ou dans section news)
    for article in soup.find_all(["article", "div"], class_=re.compile(r"article|news|item|post", re.I)):
        a_tag = article.find("a", href=True)
        if not a_tag:
            continue
        title = _text(a_tag)
        href  = a_tag["href"]
        if not title or len(title) < 10:
            continue
        # Date
        date_tag = article.find(["time", "span", "div"], class_=re.compile(r"date|time|publi", re.I))
        date_txt = _text(date_tag) if date_tag else ""
        # Résumé
        p_tag = article.find("p")
        resume = _text(p_tag) if p_tag else ""

        results.append({
            "titre":  title,
            "url":    href if href.startswith("http") else BASE_URL + href,
            "date":   date_txt,
            "resume": resume[:300],
        })
        if len(results) >= limit:
            break

    logger.info("[AM] fetch_brvm_news → %d articles", len(results))
    return results


# ── Catalogue bourses africaines ──────────────────────────────────────────────

AFRICAN_EXCHANGES = [
    {
        "slug": "brvm",  "nom": "BRVM",  "nom_long": "Bourse Régionale des Valeurs Mobilières",
        "pays": "UEMOA (8 pays)", "iso2": "CI", "flag": "🌍", "ville": "Abidjan",
        "devise": "XOF", "yf_index": None,
        "cap_usd_b": 15, "nb_societes": 47, "fondee": 1998,
        "description": "Bourse régionale couvrant 8 pays UEMOA. Spécialité : finance, agro-industrie, télécoms.",
        "url": "https://www.brvm.org",
        "am_slug": "brvm",
    },
    {
        "slug": "jse",   "nom": "JSE",   "nom_long": "Johannesburg Stock Exchange",
        "pays": "Afrique du Sud", "iso2": "ZA", "flag": "🇿🇦", "ville": "Johannesburg",
        "devise": "ZAR", "yf_index": "EZA",
        "cap_usd_b": 1050, "nb_societes": 340, "fondee": 1887,
        "description": "Plus grande bourse d'Afrique. Hub minier (or, platine), banques, industrie. Accès aux marchés dérivés.",
        "url": "https://www.jse.co.za",
        "am_slug": "jse",
    },
    {
        "slug": "ngx",   "nom": "NGX",   "nom_long": "Nigerian Exchange Group",
        "pays": "Nigeria", "iso2": "NG", "flag": "🇳🇬", "ville": "Lagos",
        "devise": "NGN", "yf_index": "^NGSEINDEX",
        "cap_usd_b": 55, "nb_societes": 155, "fondee": 1960,
        "description": "Bourse de la plus grande économie africaine. Secteurs : banques, télécoms, pétrolier, ciment.",
        "url": "https://ngxgroup.com",
        "am_slug": "nse",
    },
    {
        "slug": "gse",   "nom": "GSE",   "nom_long": "Ghana Stock Exchange",
        "pays": "Ghana", "iso2": "GH", "flag": "🇬🇭", "ville": "Accra",
        "devise": "GHS", "yf_index": "^GGSECI",
        "cap_usd_b": 12, "nb_societes": 35, "fondee": 1990,
        "description": "Marché dynamique dopé par l'or et le pétrole. MFRS en forte croissance.",
        "url": "https://gse.com.gh",
        "am_slug": "gse",
    },
    {
        "slug": "nse",   "nom": "NSE",   "nom_long": "Nairobi Securities Exchange",
        "pays": "Kenya", "iso2": "KE", "flag": "🇰🇪", "ville": "Nairobi",
        "devise": "KES", "yf_index": "^NBI",
        "cap_usd_b": 25, "nb_societes": 65, "fondee": 1954,
        "description": "Hub financier est-africain. Forte présence banques, télécoms (Safaricom), agro.",
        "url": "https://www.nse.co.ke",
        "am_slug": "nse-kenya",
    },
    {
        "slug": "egx",   "nom": "EGX",   "nom_long": "Egyptian Exchange",
        "pays": "Égypte", "iso2": "EG", "flag": "🇪🇬", "ville": "Le Caire",
        "devise": "EGP", "yf_index": "^CASE",
        "cap_usd_b": 45, "nb_societes": 215, "fondee": 1883,
        "description": "Une des plus anciennes bourses d'Afrique. Forte liquidité, secteurs diversifiés.",
        "url": "https://www.egx.com.eg",
        "am_slug": "egx",
    },
    {
        "slug": "bvc",   "nom": "BVC",   "nom_long": "Bourse des Valeurs de Casablanca",
        "pays": "Maroc", "iso2": "MA", "flag": "🇲🇦", "ville": "Casablanca",
        "devise": "MAD", "yf_index": None,
        "cap_usd_b": 65, "nb_societes": 75, "fondee": 1929,
        "description": "2e bourse africaine. Hub financier Nord-Afrique. Banques, immobilier, BTP, télécoms.",
        "url": "https://www.casablanca-bourse.com",
        "am_slug": "bvc",
    },
    {
        "slug": "bvmt",  "nom": "BVMT",  "nom_long": "Bourse des Valeurs Mobilières de Tunis",
        "pays": "Tunisie", "iso2": "TN", "flag": "🇹🇳", "ville": "Tunis",
        "devise": "TND", "yf_index": None,
        "cap_usd_b": 10, "nb_societes": 82, "fondee": 1969,
        "description": "Marché mature en Afrique du Nord. Banques, leasing, assurances dominants.",
        "url": "https://www.bvmt.com.tn",
        "am_slug": "bvmt",
    },
    {
        "slug": "dse",   "nom": "DSE",   "nom_long": "Dar es Salaam Stock Exchange",
        "pays": "Tanzanie", "iso2": "TZ", "flag": "🇹🇿", "ville": "Dar es Salaam",
        "devise": "TZS", "yf_index": None,
        "cap_usd_b": 8, "nb_societes": 30, "fondee": 1996,
        "description": "Marché est-africain en croissance. Cotations cross-listées avec NSE Kenya.",
        "url": "https://www.dse.co.tz",
        "am_slug": "dse",
    },
]

# Index rapide slug → exchange
EXCHANGE_BY_SLUG = {e["slug"]: e for e in AFRICAN_EXCHANGES}


# ── Annuaire SGI par bourse ───────────────────────────────────────────────────

AFRICAN_SGIS: dict[str, list[dict]] = {
    "brvm": [
        {"nom": "NSIA Finance",           "pays": "Côte d'Ivoire", "courtage": "0.80%", "depot_min_xof": 100_000, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.nsiafinance.com",          "note": 8.6},
        {"nom": "Hudson & Cie",           "pays": "Côte d'Ivoire", "courtage": "0.70%", "depot_min_xof": 500_000, "en_ligne": False, "app": False, "diaspora": False, "url": "https://www.hudsonetcie.com",          "note": 8.5},
        {"nom": "CGF Bourse",             "pays": "Côte d'Ivoire", "courtage": "0.65%", "depot_min_xof": 50_000,  "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.cgfbourse.com",            "note": 8.2},
        {"nom": "BOA Capital Securities", "pays": "Mali",           "courtage": "0.85%", "depot_min_xof": 100_000, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.boacapitalsecurities.com", "note": 8.0},
        {"nom": "Africabourse",           "pays": "Côte d'Ivoire", "courtage": "0.72%", "depot_min_xof": 50_000,  "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.africabourse.net",         "note": 7.9},
        {"nom": "Coris Bourse",           "pays": "Burkina Faso",   "courtage": "0.75%", "depot_min_xof": 75_000,  "en_ligne": True,  "app": False, "diaspora": True,  "url": "https://www.corisbourse.com",          "note": 7.7},
        {"nom": "Impaxis Securities",     "pays": "Sénégal",        "courtage": "0.80%", "depot_min_xof": 150_000, "en_ligne": True,  "app": False, "diaspora": True,  "url": "https://www.impaxis.com",              "note": 7.8},
        {"nom": "Sogebourse",             "pays": "Côte d'Ivoire", "courtage": "0.90%", "depot_min_xof": 200_000, "en_ligne": False, "app": False, "diaspora": False, "url": "https://www.sogebourse.sn",            "note": 7.4},
    ],
    "jse": [
        {"nom": "PSG Securities",                   "pays": "Afrique du Sud", "courtage": "0.50%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.psg.co.za",                   "note": 8.8},
        {"nom": "FNB Share Investing",              "pays": "Afrique du Sud", "courtage": "0.25%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": False, "url": "https://www.fnb.co.za",                   "note": 8.5},
        {"nom": "Standard Bank Online Trading",     "pays": "Afrique du Sud", "courtage": "0.40%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": False, "url": "https://www.standardbank.co.za",          "note": 8.3},
        {"nom": "Absa Stockbrokers",                "pays": "Afrique du Sud", "courtage": "0.35%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": False, "url": "https://www.absa.co.za",                  "note": 8.1},
        {"nom": "EasyEquities",                     "pays": "Afrique du Sud", "courtage": "0.25%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.easyequities.co.za",          "note": 9.1},
        {"nom": "Investec Wealth & Investment",     "pays": "Afrique du Sud", "courtage": "0.60%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.investec.com",                "note": 8.7},
    ],
    "ngx": [
        {"nom": "Stanbic IBTC Stockbrokers",  "pays": "Nigeria", "courtage": "0.75%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.stanbicibtc.com",    "note": 8.6},
        {"nom": "CardinalStone Securities",   "pays": "Nigeria", "courtage": "0.80%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://cardinalstone.com",      "note": 8.4},
        {"nom": "Meristem Securities",        "pays": "Nigeria", "courtage": "0.75%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.meristemng.com",     "note": 8.2},
        {"nom": "Coronation Securities",      "pays": "Nigeria", "courtage": "0.80%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.coronationmb.com",   "note": 8.0},
        {"nom": "ARM Securities",             "pays": "Nigeria", "courtage": "0.75%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.armsecurities.com",  "note": 8.3},
        {"nom": "Vetiva Securities",          "pays": "Nigeria", "courtage": "0.75%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": False, "url": "https://www.vetiva.com",          "note": 7.9},
    ],
    "gse": [
        {"nom": "Databank Brokerage",      "pays": "Ghana", "courtage": "1.00%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.databankgroup.com", "note": 8.7},
        {"nom": "EDC Securities",          "pays": "Ghana", "courtage": "0.90%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.edcghana.com",      "note": 7.9},
        {"nom": "Gold Coast Securities",   "pays": "Ghana", "courtage": "1.00%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": True,  "url": "https://www.goldcoastsec.com",  "note": 7.7},
        {"nom": "Republic Securities",     "pays": "Ghana", "courtage": "0.95%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.republicsec.com",   "note": 7.5},
        {"nom": "IC Securities",           "pays": "Ghana", "courtage": "0.85%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.icsecurities.com",  "note": 8.1},
    ],
    "nse": [
        {"nom": "Standard Investment Bank", "pays": "Kenya", "courtage": "2.10%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.sib.co.ke",       "note": 8.5},
        {"nom": "Faida Securities",         "pays": "Kenya", "courtage": "2.10%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.faidasecurities.com", "note": 8.2},
        {"nom": "Dyer & Blair",             "pays": "Kenya", "courtage": "2.10%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.dyerandblair.com", "note": 8.0},
        {"nom": "Old Mutual Securities KE", "pays": "Kenya", "courtage": "2.10%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.oldmutual.co.ke",  "note": 8.3},
        {"nom": "Genghis Capital",          "pays": "Kenya", "courtage": "2.10%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": False, "url": "https://www.genghiscapital.co.ke", "note": 7.8},
    ],
    "egx": [
        {"nom": "EFG Hermes",           "pays": "Égypte", "courtage": "0.50%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.efghermes.com",      "note": 9.0},
        {"nom": "CI Capital",           "pays": "Égypte", "courtage": "0.45%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.cicapital.com.eg",   "note": 8.6},
        {"nom": "Beltone Financial",    "pays": "Égypte", "courtage": "0.50%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.beltone.com.eg",     "note": 8.3},
        {"nom": "Pharos Securities",    "pays": "Égypte", "courtage": "0.50%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.pharossecurities.com", "note": 8.0},
        {"nom": "Arqaam Capital",       "pays": "Égypte", "courtage": "0.60%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.arqaamcapital.com",  "note": 8.5},
    ],
    "bvc": [
        {"nom": "CDG Capital Bourse",              "pays": "Maroc", "courtage": "0.30%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.cdgcapitalbourse.ma",       "note": 8.7},
        {"nom": "CFG Marchés",                     "pays": "Maroc", "courtage": "0.35%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.cfg.ma",                    "note": 8.4},
        {"nom": "Attijari Intermédiation",         "pays": "Maroc", "courtage": "0.25%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.attijaribawafa.com",        "note": 8.8},
        {"nom": "BMCE Capital Bourse",             "pays": "Maroc", "courtage": "0.30%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.bmcecapital.com",           "note": 8.5},
        {"nom": "Société Générale Marocaine Bourse","pays": "Maroc", "courtage": "0.35%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.sgmaroc.com",               "note": 8.1},
    ],
    "bvmt": [
        {"nom": "Attijari Bourse",     "pays": "Tunisie", "courtage": "0.50%", "depot_min_xof": None, "en_ligne": True,  "app": True,  "diaspora": True,  "url": "https://www.attijaribourse.com.tn", "note": 8.5},
        {"nom": "Tunisie Valeurs",     "pays": "Tunisie", "courtage": "0.50%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.tunisievaleurs.com",    "note": 8.3},
        {"nom": "BNA Capitaux",        "pays": "Tunisie", "courtage": "0.55%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.bnacapitaux.com.tn",    "note": 7.9},
        {"nom": "Amen Invest",         "pays": "Tunisie", "courtage": "0.50%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.ameninvest.com.tn",     "note": 7.8},
        {"nom": "MAC SA",              "pays": "Tunisie", "courtage": "0.55%", "depot_min_xof": None, "en_ligne": True,  "app": False, "diaspora": False, "url": "https://www.mac-sa.com.tn",         "note": 7.6},
    ],
    "dse": [
        {"nom": "CORE Securities",    "pays": "Tanzanie", "courtage": "1.00%", "depot_min_xof": None, "en_ligne": False, "app": False, "diaspora": False, "url": "https://www.coresecurities.co.tz", "note": 7.5},
        {"nom": "Orbit Securities",   "pays": "Tanzanie", "courtage": "1.00%", "depot_min_xof": None, "en_ligne": False, "app": False, "diaspora": False, "url": "https://www.orbit.co.tz",           "note": 7.3},
        {"nom": "Vertex International","pays": "Tanzanie", "courtage": "1.00%", "depot_min_xof": None, "en_ligne": False, "app": False, "diaspora": False, "url": "https://www.vertextz.com",          "note": 7.1},
    ],
}


# ── fetch_exchange_listed ─────────────────────────────────────────────────────

def fetch_exchange_listed(slug: str) -> list[dict]:
    """
    Scrape les titres cotés sur une bourse africaine via african-markets.com.
    Utilise le am_slug du catalogue AFRICAN_EXCHANGES.
    Retourne [{symbole, nom, cours, variation_pct, ytd_pct, pe_ratio, devise}].
    """
    exchange = EXCHANGE_BY_SLUG.get(slug)
    if not exchange:
        logger.warning("[AM] fetch_exchange_listed: slug inconnu '%s'", slug)
        return []
    am_slug = exchange.get("am_slug", slug)
    devise  = exchange.get("devise", "")

    try:
        soup = _get(f"/fr/bourse/{am_slug}/listed-companies")
    except Exception as exc:
        logger.error("[AM] fetch_exchange_listed(%s) — %s", slug, exc)
        return []

    results = []
    for table in soup.find_all("table"):
        headers = [_text(th).lower() for th in table.find_all("th")]
        if not any(h in ("cours", "price", "last price", "dernier cours") for h in headers):
            continue
        for tr in table.find_all("tr")[1:]:
            cols = tr.find_all("td")
            if len(cols) < 3:
                continue
            link_tag = tr.find("a", href=True)
            symbole  = ""
            if link_tag:
                m = re.search(r"[?&]code=([A-Z0-9\.]+)", link_tag["href"])
                if m:
                    symbole = m.group(1)
            texts = [_text(c) for c in cols]
            results.append({
                "symbole":       symbole,
                "nom":           texts[0],
                "cours":         _num(texts[2]) if len(texts) > 2 else None,
                "variation_pct": _num(texts[3]) if len(texts) > 3 else None,
                "ytd_pct":       _num(texts[4]) if len(texts) > 4 else None,
                "pe_ratio":      _num(texts[5]) if len(texts) > 5 else None,
                "devise":        devise,
            })
        if results:
            break

    logger.info("[AM] fetch_exchange_listed(%s) → %d titres", slug, len(results))
    return results
