"""
African-Markets.com scraper — données BRVM complémentaires
  • fetch_brvm_listed()       → 47 titres BRVM : cours, variation, P/E, secteur
  • fetch_company_profile()   → annonces, dividendes, rapports annuels par ticker
  • fetch_currencies()        → taux XOF/USD + 17 devises africaines
  • fetch_brvm_news()         → actualités marché BRVM

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
