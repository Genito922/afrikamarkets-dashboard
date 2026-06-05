"""
Page 9 — Marchés Internationaux (Expert Premium)
Commodities : Cacao · Café · Or · WTI
Indices obligataires : FGBL · Eurobond · T-Note US
Crypto : BTC · ETH · BNB · XRP
Forex : EUR/XOF · USD/XOF · CAD/XOF · EUR/USD · USD/CAD · GBP/USD
Analyse technique MA 16/19/246/361 + RSI + MFI + impact BRVM
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from frontend.auth_ui import render_auth_sidebar, require_plan
from utils.i18n import t, get_lang

st.set_page_config(
    page_title="Marchés Internationaux — Afrika Markets",
    page_icon="🌐",
    layout="wide",
)

lang = get_lang()
FR = lang == "fr"

render_auth_sidebar(fr=FR)
require_plan("expert_premium", fr=FR)

# ── Palette ───────────────────────────────────────────────────
C = {
    "bg":    "rgba(0,0,0,0)",
    "grid":  "#1F2232",
    "text":  "#E8E8E8",
    "gold":  "#FFD700",
    "green": "#00CC66",
    "red":   "#FF4444",
    "blue":  "#00BFFF",
    "orange":"#FF6B35",
    "purple":"#A855F7",
    "ma16":  "#00BFFF",
    "ma19":  "#00CC66",
    "ma246": "#FFD700",
    "ma361": "#FF6B35",
}

LAYOUT_BASE = dict(
    plot_bgcolor=C["bg"],
    paper_bgcolor=C["bg"],
    font_color=C["text"],
    margin=dict(t=30, b=10, l=60, r=20),
)

# ── Assets par catégorie ──────────────────────────────────────
ASSETS = {
    "commodities": {
        "CC=F":  {"label": "🍫 Cacao",   "unit": "USD/t",   "impact": "Fort — CI/Ghana = 60 % prod. mondiale"},
        "KC=F":  {"label": "☕ Café",    "unit": "USD/lb",  "impact": "Fort — Côte d'Ivoire 3e exportateur"},
        "GC=F":  {"label": "🥇 Or",      "unit": "USD/oz",  "impact": "Moyen — refuge diaspora & mines UEMOA"},
        "CL=F":  {"label": "🛢️ WTI",     "unit": "USD/bbl", "impact": "Moyen — coût énergie & inflation UEMOA"},
    },
    "indices": {
        "GBL=F":  {"label": "🇩🇪 FGBL (Bund 10y)",  "unit": "pts",   "impact": "Faible — taux Europe → flux diaspora"},
        "ZN=F":   {"label": "🇺🇸 T-Note US 10y",    "unit": "pts",   "impact": "Faible — taux USD → financement UEMOA"},
        "^EURONEXT": {"label": "🇪🇺 Euronext 100", "unit": "pts",   "impact": "Moyen — liquidités investisseurs Europe"},
        "^GSPC":  {"label": "🇺🇸 S&P 500",         "unit": "pts",   "impact": "Faible — appétit risque global"},
    },
    "crypto": {
        "BTC-USD": {"label": "₿ Bitcoin",   "unit": "USD", "impact": "Moyen — transferts diaspora vers Afrique"},
        "ETH-USD": {"label": "⬡ Ethereum",  "unit": "USD", "impact": "Faible — DeFi & tokenisation actifs"},
        "BNB-USD": {"label": "◈ BNB",       "unit": "USD", "impact": "Faible — paiements mobiles Afrique"},
        "XRP-USD": {"label": "✦ XRP",       "unit": "USD", "impact": "Moyen — remises internationales rapides"},
    },
    # Forex — paires liées à la diaspora & au franc CFA
    # EUR/XOF et dérivés sont calculés (XOF arrimé EUR à 655.957)
    "forex": {
        "EURUSD=X": {"label": "EUR / USD", "unit": "USD",  "impact": "Clé — EUR/XOF = EUR/USD × 655.957"},
        "USDCAD=X": {"label": "USD / CAD", "unit": "CAD",  "impact": "Fort — diaspora Canada raisonne en CAD"},
        "GBPUSD=X": {"label": "GBP / USD", "unit": "USD",  "impact": "Moyen — diaspora UK & transferts SWIFT"},
        "USDCHF=X": {"label": "USD / CHF", "unit": "CHF",  "impact": "Faible — refuge & liquidités Europe"},
        "EURGBP=X": {"label": "EUR / GBP", "unit": "GBP",  "impact": "Faible — taux croisé France/UK diaspora"},
    },
}

IMPACT_BRVM = {
    "commodities": {
        "fr": "Le cacao et le café représentent ~40 % des recettes d'exportation de Côte d'Ivoire. Une hausse du cacao soutient les résultats des entreprises agricoles cotées à la BRVM (SOGB, SAPH). L'or reste un actif refuge pour la diaspora.",
        "en": "Cocoa and coffee represent ~40% of Côte d'Ivoire's export revenues. A cocoa price rise boosts results of BRVM-listed agro companies (SOGB, SAPH). Gold remains a safe haven for the diaspora.",
    },
    "indices": {
        "fr": "Les taux obligataires (FGBL, T-Note) influencent le coût de refinancement des États UEMOA. Une remontée des taux européens contracte les flux d'investissement vers les marchés émergents africains.",
        "en": "Bond rates (FGBL, T-Note) influence UEMOA sovereign refinancing costs. Rising European rates compress investment flows to African emerging markets.",
    },
    "crypto": {
        "fr": "Les cryptomonnaies facilitent les transferts de la diaspora (Canada, France) vers la Côte d'Ivoire avec des frais réduits. BTC et XRP sont les plus utilisés pour les remises vers l'Afrique de l'Ouest.",
        "en": "Cryptocurrencies enable low-cost remittances from the diaspora (Canada, France) to Côte d'Ivoire. BTC and XRP are the most used for West Africa transfers.",
    },
    "forex": {
        "fr": "Le franc CFA (XOF) est arrimé à l'euro à un taux fixe de **655,957 XOF = 1 EUR**. Tout mouvement EUR/USD se répercute directement sur le pouvoir d'achat de la diaspora canadienne et britannique. Un EUR fort = transferts plus coûteux depuis le Canada (CAD/XOF moins favorable).",
        "en": "The CFA franc (XOF) is pegged to the euro at a fixed rate of **655.957 XOF = 1 EUR**. Any EUR/USD move directly impacts the diaspora's purchasing power. A strong EUR = more expensive transfers from Canada (CAD/XOF less favorable).",
    },
}

# ── Indicateurs techniques ────────────────────────────────────
def calc_ma(s: pd.Series, p: int) -> pd.Series:
    return s.rolling(min(p, len(s)), min_periods=1).mean()

def calc_rsi(s: pd.Series, p: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(com=p-1, min_periods=p).mean()
    l = (-d.clip(upper=0)).ewm(com=p-1, min_periods=p).mean()
    return 100 - (100 / (1 + g / l.replace(0, np.nan)))

def calc_mfi(df: pd.DataFrame, p: int = 14) -> pd.Series:
    tp  = (df["high"] + df["low"] + df["close"]) / 3
    mf  = tp * df["volume"]
    pos = mf.where(tp > tp.shift(1), 0).rolling(p, min_periods=1).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(p, min_periods=1).sum()
    return 100 - (100 / (1 + pos / neg.replace(0, np.nan)))

def detect_crossings(fast: pd.Series, slow: pd.Series):
    diff = fast - slow
    golden, death = [], []
    for i in range(1, len(diff)):
        if pd.isna(diff.iloc[i-1]) or pd.isna(diff.iloc[i]):
            continue
        if diff.iloc[i-1] < 0 and diff.iloc[i] >= 0:
            golden.append(i)
        elif diff.iloc[i-1] > 0 and diff.iloc[i] <= 0:
            death.append(i)
    return {"golden": golden, "death": death}

def signal_summary(rsi: float, ma16: float, ma19: float, ma246: float, ma361: float) -> tuple:
    score = 0
    if rsi < 30:   score += 2
    elif rsi > 70: score -= 2
    if ma16 > ma19 > ma246:   score += 2
    elif ma16 < ma19 < ma246: score -= 2
    if ma19 > ma246 > ma361:  score += 1
    elif ma19 < ma246 < ma361: score -= 1
    label = ("🟢 Achat fort" if FR else "🟢 Strong Buy") if score >= 3 else \
            ("🟡 Achat modéré" if FR else "🟡 Moderate Buy") if score >= 1 else \
            ("🔴 Vente modérée" if FR else "🔴 Moderate Sell") if score <= -1 else \
            ("🔴 Vente forte" if FR else "🔴 Strong Sell") if score <= -3 else \
            ("⚪ Neutre" if FR else "⚪ Neutral")
    color = C["green"] if score >= 1 else C["red"] if score <= -1 else "#888"
    return label, color, score


# ── Chargement données via yfinance ──────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def load_asset(ticker: str, days: int = 365) -> pd.DataFrame:
    try:
        import yfinance as yf
        end   = datetime.utcnow()
        start = end - timedelta(days=days + 30)
        df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                         end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
        df = df.rename(columns={"adj close": "close"})
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                df[col] = df.get("close", 0)
        df = df[["date", "open", "high", "low", "close", "volume"]].dropna()
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def make_simulated(days: int = 180, base: float = 100.0) -> pd.DataFrame:
    np.random.seed(42)
    noise  = np.random.randn(days).cumsum() * (base * 0.008)
    close  = np.clip(base + noise - noise[-1], base * 0.6, base * 1.5)
    volume = np.random.randint(1000, 500000, days).astype(float)
    dates  = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="B")
    return pd.DataFrame({
        "date": dates, "open": close * (1 + np.random.randn(days) * 0.003),
        "high": close * (1 + abs(np.random.randn(days) * 0.005)),
        "low":  close * (1 - abs(np.random.randn(days) * 0.005)),
        "close": close, "volume": volume,
    })


# ── En-tête ───────────────────────────────────────────────────
st.markdown(f"""
<div style='background:linear-gradient(135deg,#0D0D1F,#1A0533 50%,#2D1B69 100%);
     padding:18px 24px; border-radius:12px; margin-bottom:16px;
     border-left:4px solid #8B5CF6;'>
    <h2 style='color:white; margin:0; font-size:1.5em;'>
        🌐 {"Marchés Internationaux" if FR else "International Markets"}
        &nbsp;<span style='font-size:0.6em; background:#8B5CF6; padding:3px 8px;
        border-radius:12px; vertical-align:middle;'>Expert Premium</span>
    </h2>
    <p style='color:rgba(255,255,255,0.7); margin:4px 0 0; font-size:0.9em;'>
        {"Commodities · Indices obligataires · Crypto · Impact BRVM" if FR else
         "Commodities · Bond indices · Crypto · BRVM Impact"}
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs principales ──────────────────────────────────────────
tab_comm, tab_idx, tab_forex, tab_crypto, tab_impact = st.tabs([
    "🌾 Commodities",
    "📊 Indices & Taux",
    "💱 Forex & CFA",
    "₿ Crypto",
    "🔗 Impact BRVM",
])

# ── Contrôles communs ─────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("**🌐 Marchés Intl.**")
    period_intl = st.selectbox(
        "Période" if FR else "Period",
        [90, 180, 365],
        index=1,
        format_func=lambda x: f"{x} j" if FR else f"{x}d",
        key="period_intl",
    )
    rsi_p = st.number_input("RSI", 5, 30, 14, key="rsi_intl")
    mfi_p = st.number_input("MFI", 5, 30, 14, key="mfi_intl")


def render_asset_chart(ticker: str, meta: dict, period: int, rsi_period: int, mfi_period: int):
    with st.spinner(f"{'Chargement' if FR else 'Loading'} {meta['label']}…"):
        df = load_asset(ticker, period)

    simulated = False
    if df.empty or len(df) < 20:
        st.caption(f"⚠️ {'Données live indisponibles — simulation' if FR else 'Live data unavailable — simulation'}")
        df = make_simulated(period, base=1000.0)
        simulated = True

    # Indicateurs
    df["ma16"]  = calc_ma(df["close"], 16)
    df["ma19"]  = calc_ma(df["close"], 19)
    df["ma246"] = calc_ma(df["close"], min(246, len(df)))
    df["ma361"] = calc_ma(df["close"], min(361, len(df)))
    df["rsi"]   = calc_rsi(df["close"], rsi_period)
    df["mfi"]   = calc_mfi(df, mfi_period)

    last = df.iloc[-1]
    sig_label, sig_color, _ = signal_summary(
        rsi=last["rsi"] if pd.notna(last["rsi"]) else 50,
        ma16=last["ma16"], ma19=last["ma19"],
        ma246=last["ma246"], ma361=last["ma361"],
    )

    # KPIs
    prev  = df.iloc[-2]["close"] if len(df) > 1 else last["close"]
    chg   = ((last["close"] - prev) / prev * 100) if prev else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(meta["label"], f"{last['close']:,.2f} {meta['unit']}", f"{chg:+.2f}%")
    c2.metric("RSI",  f"{last['rsi']:.1f}" if pd.notna(last["rsi"]) else "—")
    c3.metric("MFI",  f"{last['mfi']:.1f}" if pd.notna(last["mfi"]) else "—")
    c4.metric("Signal", sig_label)

    # Cross détection 19/246
    cross = detect_crossings(df["ma19"], df["ma246"])

    # Chart 3 panels : prix+MA / RSI / MFI
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.225, 0.225],
        vertical_spacing=0.02,
        subplot_titles=(f"{meta['label']} — MA 16/19/246/361", f"RSI ({rsi_period})", f"MFI ({mfi_period})"),
    )

    dates = df["date"]

    fig.add_trace(go.Scatter(x=dates, y=df["close"], name="Prix",
        line=dict(color=C["text"], width=1.8),
        fill="tozeroy", fillcolor="rgba(232,232,232,0.04)",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=dates, y=df["ma16"],  name="MA16",
        line=dict(color=C["ma16"], width=1.2, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=dates, y=df["ma19"],  name="MA19",
        line=dict(color=C["ma19"], width=1.5)), row=1, col=1)
    if df["ma246"].notna().sum() > 5:
        fig.add_trace(go.Scatter(x=dates, y=df["ma246"], name="MA246",
            line=dict(color=C["ma246"], width=1.5, dash="dash")), row=1, col=1)
    if df["ma361"].notna().sum() > 5:
        fig.add_trace(go.Scatter(x=dates, y=df["ma361"], name="MA361",
            line=dict(color=C["ma361"], width=1.5, dash="dot")), row=1, col=1)

    for idx in cross["golden"]:
        if idx < len(df):
            fig.add_trace(go.Scatter(x=[dates.iloc[idx]], y=[df["close"].iloc[idx]],
                mode="markers+text", text=["GC"], textposition="top center",
                textfont=dict(color=C["green"], size=9),
                marker=dict(symbol="triangle-up", size=13, color=C["green"]),
                showlegend=False,
                hovertemplate="<b>Golden Cross 19/246</b><br>%{x|%d %b %Y}<extra></extra>",
            ), row=1, col=1)
    for idx in cross["death"]:
        if idx < len(df):
            fig.add_trace(go.Scatter(x=[dates.iloc[idx]], y=[df["close"].iloc[idx]],
                mode="markers+text", text=["DC"], textposition="bottom center",
                textfont=dict(color=C["red"], size=9),
                marker=dict(symbol="triangle-down", size=13, color=C["red"]),
                showlegend=False,
                hovertemplate="<b>Death Cross 19/246</b><br>%{x|%d %b %Y}<extra></extra>",
            ), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=dates, y=df["rsi"], name=f"RSI({rsi_period})",
        line=dict(color=C["blue"], width=1.8)), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, row=2, col=1, fillcolor="rgba(255,68,68,0.08)", line_width=0)
    fig.add_hrect(y0=0,  y1=30,  row=2, col=1, fillcolor="rgba(0,204,102,0.08)", line_width=0)
    for y, c in [(70, C["red"]), (50, "#555"), (30, C["green"])]:
        fig.add_hline(y=y, row=2, col=1, line=dict(color=c, width=1, dash="dot"))

    # MFI
    fig.add_trace(go.Scatter(x=dates, y=df["mfi"], name=f"MFI({mfi_period})",
        line=dict(color=C["purple"], width=1.8),
        fill="tozeroy", fillcolor="rgba(168,85,247,0.07)"), row=3, col=1)
    fig.add_hrect(y0=80, y1=100, row=3, col=1, fillcolor="rgba(255,68,68,0.08)", line_width=0)
    fig.add_hrect(y0=0,  y1=20,  row=3, col=1, fillcolor="rgba(0,204,102,0.08)", line_width=0)
    for y, c in [(80, C["red"]), (50, "#555"), (20, C["green"])]:
        fig.add_hline(y=y, row=3, col=1, line=dict(color=c, width=1, dash="dot"))

    axis_style = dict(showgrid=True, gridcolor=C["grid"], color=C["text"], zeroline=False)
    fig.update_layout(**LAYOUT_BASE, height=620, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    bgcolor="rgba(0,0,0,0.3)", font=dict(size=10)))
    for r in range(1, 4):
        fig.update_xaxes(row=r, col=1, **axis_style, showticklabels=(r == 3))
    fig.update_yaxes(row=1, col=1, **axis_style)
    fig.update_yaxes(row=2, col=1, **axis_style, range=[0, 100], tickvals=[0, 30, 50, 70, 100])
    fig.update_yaxes(row=3, col=1, **axis_style, range=[0, 100], tickvals=[0, 20, 50, 80, 100])
    for ann in fig.layout.annotations:
        ann.font.color = "#aaa"; ann.font.size = 10

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
    <div style='background:#0D1B2A; border-left:3px solid #FFD700;
                padding:10px 14px; border-radius:6px; font-size:0.85em; color:#ccc;'>
        📌 <b>Impact BRVM :</b> {meta['impact']}
    </div>
    """, unsafe_allow_html=True)

    if simulated:
        st.caption("⚠️ Données simulées — installez `yfinance` et configurez la connexion.")
    st.markdown("")


# ═══════════════════════════════════════════════════
# TAB 1 — Commodities
# ═══════════════════════════════════════════════════
with tab_comm:
    st.markdown(f"### 🌾 {'Commodités — Prix mondiaux' if FR else 'Commodities — World Prices'}")
    st.caption(
        "Prix en temps réel (yfinance) — Futures CME/ICE" if FR else
        "Real-time prices (yfinance) — CME/ICE Futures"
    )

    for ticker, meta in ASSETS["commodities"].items():
        with st.expander(f"{meta['label']} — {ticker}", expanded=(ticker == "CC=F")):
            render_asset_chart(ticker, meta, period_intl, rsi_p, mfi_p)


# ═══════════════════════════════════════════════════
# TAB 2 — Indices & Taux
# ═══════════════════════════════════════════════════
with tab_idx:
    st.markdown(f"### 📊 {'Indices Obligataires & Boursiers' if FR else 'Bond & Equity Indices'}")
    st.caption(
        "FGBL (Bund 10 ans), T-Note US 10 ans, Euronext 100, S&P 500" if FR else
        "FGBL (10Y Bund), US 10Y T-Note, Euronext 100, S&P 500"
    )

    for ticker, meta in ASSETS["indices"].items():
        with st.expander(f"{meta['label']} — {ticker}", expanded=(ticker == "GBL=F")):
            render_asset_chart(ticker, meta, period_intl, rsi_p, mfi_p)


# ═══════════════════════════════════════════════════
# TAB 3 — Forex & CFA
# ═══════════════════════════════════════════════════
with tab_forex:
    st.markdown(f"### 💱 {'Marchés des Changes & Franc CFA' if FR else 'FX Markets & CFA Franc'}")

    # ── Bandeau EUR/XOF live ──────────────────────────────
    df_eurusd = load_asset("EURUSD=X", 7)
    eurusd = df_eurusd.iloc[-1]["close"] if not df_eurusd.empty else 1.08
    xof_per_eur  = 655.957                    # taux fixe CFA/EUR
    xof_per_usd  = xof_per_eur / eurusd
    df_usdcad    = load_asset("USDCAD=X", 7)
    usdcad       = df_usdcad.iloc[-1]["close"] if not df_usdcad.empty else 1.36
    xof_per_cad  = xof_per_usd / usdcad

    st.markdown(f"""
    <div style='background:linear-gradient(90deg,#0D1B2A,#1A2A1A);
                border:1px solid #FFD700; border-radius:10px; padding:14px 20px;
                margin-bottom:12px;'>
        <span style='color:#FFD700; font-weight:700; font-size:1.05em;'>
            🏦 Parités CFA (XOF) en temps réel
        </span>
        <div style='display:flex; gap:40px; margin-top:10px; flex-wrap:wrap;'>
            <div>
                <span style='color:#aaa; font-size:0.85em;'>EUR / XOF</span><br>
                <span style='color:white; font-size:1.4em; font-weight:700;'>655.957</span>
                <span style='color:#00CC66; font-size:0.8em;'> taux fixe</span>
            </div>
            <div>
                <span style='color:#aaa; font-size:0.85em;'>USD / XOF</span><br>
                <span style='color:white; font-size:1.4em; font-weight:700;'>{xof_per_usd:,.1f}</span>
                <span style='color:#aaa; font-size:0.8em;'> ≈ calculé</span>
            </div>
            <div>
                <span style='color:#aaa; font-size:0.85em;'>CAD / XOF</span><br>
                <span style='color:white; font-size:1.4em; font-weight:700;'>{xof_per_cad:,.1f}</span>
                <span style='color:#aaa; font-size:0.8em;'> ≈ calculé</span>
            </div>
            <div>
                <span style='color:#aaa; font-size:0.85em;'>EUR / USD</span><br>
                <span style='color:white; font-size:1.4em; font-weight:700;'>{eurusd:.4f}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "ℹ️ **Le franc CFA est arrimé à l'euro à 655,957 XOF = 1 EUR** (taux fixe depuis 1999). "
        "EUR/XOF ne fluctue pas, mais **USD/XOF et CAD/XOF varient** selon EUR/USD et USD/CAD — "
        "ce qui impacte directement le pouvoir d'achat de la diaspora lors des transferts."
        if FR else
        "ℹ️ **The CFA franc is pegged to the euro at 655.957 XOF = 1 EUR** (fixed since 1999). "
        "EUR/XOF doesn't move, but **USD/XOF and CAD/XOF fluctuate** with EUR/USD and USD/CAD — "
        "directly impacting diaspora purchasing power when sending money home."
    )

    # ── EUR/XOF implicite — courbe reconstituée ───────────
    st.markdown(f"#### 📈 {'Évolution USD/XOF & CAD/XOF (reconstituée)' if FR else 'USD/XOF & CAD/XOF trend (derived)'}")

    df_eur = load_asset("EURUSD=X", period_intl)
    df_cad = load_asset("USDCAD=X", period_intl)

    if not df_eur.empty and not df_cad.empty:
        merged = df_eur[["date", "close"]].rename(columns={"close": "eurusd"}).merge(
            df_cad[["date", "close"]].rename(columns={"close": "usdcad"}),
            on="date", how="inner",
        )
        merged["usdxof"] = xof_per_eur / merged["eurusd"]
        merged["cadxof"] = merged["usdxof"] / merged["usdcad"]

        fig_xof = go.Figure()
        fig_xof.add_trace(go.Scatter(
            x=merged["date"], y=merged["usdxof"],
            name="USD / XOF", line=dict(color=C["gold"], width=2),
            hovertemplate="USD/XOF: %{y:,.1f}<extra></extra>",
        ))
        fig_xof.add_trace(go.Scatter(
            x=merged["date"], y=merged["cadxof"],
            name="CAD / XOF", line=dict(color=C["blue"], width=2, dash="dash"),
            hovertemplate="CAD/XOF: %{y:,.1f}<extra></extra>",
        ))
        fig_xof.update_layout(
            **LAYOUT_BASE, height=320, hovermode="x unified",
            yaxis=dict(showgrid=True, gridcolor=C["grid"], color=C["text"],
                       title="XOF", tickformat=",.0f"),
            xaxis=dict(showgrid=True, gridcolor=C["grid"], color=C["text"]),
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        bgcolor="rgba(0,0,0,0.3)"),
        )
        st.plotly_chart(fig_xof, use_container_width=True)
        st.caption(
            "Source : EUR/XOF taux fixe 655.957 · USD/XOF = 655.957 / EUR/USD · CAD/XOF = USD/XOF / USD/CAD"
        )
    else:
        st.warning("Données EUR/USD ou USD/CAD indisponibles pour reconstruire les parités XOF.")

    st.markdown("---")

    # ── Paires forex individuelles ────────────────────────
    st.markdown(f"#### 📊 {'Analyse technique — Paires de change' if FR else 'Technical Analysis — FX Pairs'}")
    st.caption(
        "Volume forex (OTC) = indicatif — MFI moins fiable que sur actions. RSI & MA restent pertinents."
        if FR else
        "Forex volume (OTC) = indicative — MFI less reliable than on equities. RSI & MA remain relevant."
    )

    for ticker, meta in ASSETS["forex"].items():
        with st.expander(f"{meta['label']} — {ticker}", expanded=(ticker == "EURUSD=X")):
            render_asset_chart(ticker, meta, period_intl, rsi_p, mfi_p)


# ═══════════════════════════════════════════════════
# TAB 4 — Crypto
# ═══════════════════════════════════════════════════
with tab_crypto:
    st.markdown(f"### ₿ {'Cryptomonnaies — Transferts & Remises' if FR else 'Crypto — Transfers & Remittances'}")
    st.caption(
        "BTC · ETH · BNB · XRP — cours USD via CoinGecko/Yahoo Finance" if FR else
        "BTC · ETH · BNB · XRP — USD price via CoinGecko/Yahoo Finance"
    )

    # Vue d'ensemble KPI rapide
    kpi_cols = st.columns(4)
    for i, (ticker, meta) in enumerate(ASSETS["crypto"].items()):
        df_q = load_asset(ticker, 7)
        if not df_q.empty and len(df_q) >= 2:
            last_p = df_q.iloc[-1]["close"]
            prev_p = df_q.iloc[-2]["close"]
            chg    = (last_p - prev_p) / prev_p * 100 if prev_p else 0
            kpi_cols[i].metric(meta["label"], f"${last_p:,.2f}", f"{chg:+.2f}%")
        else:
            kpi_cols[i].metric(meta["label"], "—")

    st.markdown("")

    for ticker, meta in ASSETS["crypto"].items():
        with st.expander(f"{meta['label']} — {ticker}", expanded=(ticker == "BTC-USD")):
            render_asset_chart(ticker, meta, period_intl, rsi_p, mfi_p)


# ═══════════════════════════════════════════════════
# TAB 4 — Impact BRVM
# ═══════════════════════════════════════════════════
with tab_impact:
    st.markdown(f"### 🔗 {'Corrélations Marchés Mondiaux ↔ BRVM' if FR else 'Global Markets ↔ BRVM Correlations'}")

    for cat, info in IMPACT_BRVM.items():
        label = {
            "commodities": "🌾 Commodités",
            "indices":     "📊 Indices & Taux",
            "crypto":      "₿ Crypto",
            "forex":       "💱 Forex & CFA",
        }[cat]
        col = {
            "commodities": C["gold"],
            "indices":     C["blue"],
            "crypto":      C["purple"],
            "forex":       C["green"],
        }[cat]
        st.markdown(f"""
        <div style='background:#0D1B2A; border-left:4px solid {col};
                    padding:14px 18px; border-radius:8px; margin:8px 0;'>
            <h4 style='color:{col}; margin:0 0 8px;'>{label}</h4>
            <p style='color:#ccc; margin:0; font-size:0.9em;'>
                {info.get(lang[:2], info["fr"])}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"### {'Résumé des corrélations' if FR else 'Correlation summary'}")

    corr_data = [
        {"Actif": "🍫 Cacao (CC=F)",   "Corrélation BRVM": "🔴 Forte",   "Direction": "↑ Cacao = ↑ BRVM-CI",         "Délai": "1–3 mois"},
        {"Actif": "☕ Café (KC=F)",    "Corrélation BRVM": "🟡 Modérée",  "Direction": "↑ Café = ↑ agro CI",          "Délai": "1–6 mois"},
        {"Actif": "🥇 Or (GC=F)",      "Corrélation BRVM": "🟡 Modérée",  "Direction": "↑ Or = ↑ mines BF",           "Délai": "2–4 mois"},
        {"Actif": "🛢️ WTI (CL=F)",     "Corrélation BRVM": "🟡 Modérée",  "Direction": "↑ WTI = ↑ inflation UEMOA",   "Délai": "1–2 mois"},
        {"Actif": "🇩🇪 FGBL",          "Corrélation BRVM": "🟢 Faible",   "Direction": "↑ taux EUR = ↓ flux marchés", "Délai": "3–6 mois"},
        {"Actif": "💱 EUR/USD",        "Corrélation BRVM": "🟡 Modérée",  "Direction": "↓ EUR = ↓ USD/XOF diaspora",  "Délai": "immédiat"},
        {"Actif": "💱 USD/CAD",        "Corrélation BRVM": "🟡 Modérée",  "Direction": "↑ USD/CAD = ↓ envois Canada", "Délai": "immédiat"},
        {"Actif": "₿ Bitcoin",         "Corrélation BRVM": "🟢 Faible",   "Direction": "↑ BTC = ↑ remises",           "Délai": "0–1 mois"},
        {"Actif": "✦ XRP",             "Corrélation BRVM": "🟢 Faible",   "Direction": "↑ XRP = ↓ frais transfert",   "Délai": "0–1 mois"},
    ]

    st.dataframe(
        pd.DataFrame(corr_data),
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "📌 Ces corrélations sont indicatives. Elles reflètent les dynamiques macro historiques entre les marchés mondiaux et l'économie UEMOA. Toujours croiser avec l'actualité géopolitique (War Room) et les fondamentaux des titres (page Titres)."
        if FR else
        "📌 Correlations are indicative. They reflect historical macro dynamics between global markets and the UEMOA economy. Always cross-check with geopolitical news (War Room) and stock fundamentals (Stocks page)."
    )
