"""
Page 6 — Analyse Graphique Technique
Croisements MA 19/38/361 · MFI · RSI
Afrika Markets Intelligence
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from data.brvm_scraper import get_actions
from frontend.auth_ui import render_auth_sidebar, require_auth
from frontend.auth_client import get_market_history

st.set_page_config(
    page_title="Analyse Graphique — Afrika Markets",
    page_icon="📐",
    layout="wide",
)

LANG = st.sidebar.selectbox("🌐 Langue / Language", ["Français", "English"])
FR = LANG == "Français"

render_auth_sidebar(fr=FR)
require_auth(fr=FR)

# ── Palette Afrika Markets ────────────────────────────────────
C = {
    "bg":       "rgba(0,0,0,0)",
    "grid":     "#1F2232",
    "text":     "#E8E8E8",
    "gold":     "#FFD700",
    "green":    "#00CC66",
    "red":      "#FF4444",
    "blue":     "#00BFFF",
    "orange":   "#FF6B35",
    "purple":   "#A855F7",
    "ma19":     "#00CC66",
    "ma38":     "#FFD700",
    "ma361":    "#FF6B35",
    "rsi":      "#00BFFF",
    "mfi":      "#A855F7",
    "vol":      "#006B3F",
    "price":    "#E8E8E8",
}

LAYOUT_BASE = dict(
    plot_bgcolor=C["bg"],
    paper_bgcolor=C["bg"],
    font_color=C["text"],
    margin=dict(t=30, b=10, l=60, r=20),
)


# ── Fonctions indicateurs ─────────────────────────────────────

def calc_ma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=1).mean()


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Money Flow Index — nécessite high, low, close, volume.
    Sur BRVM on approche : high≈cours_ouv max cours, low≈cours_ouv min cours.
    """
    tp = (df["high"] + df["low"] + df["cours"]) / 3
    raw_mf = tp * df["volume"]
    pos_mf = raw_mf.where(tp > tp.shift(1), 0)
    neg_mf = raw_mf.where(tp < tp.shift(1), 0)
    pos_sum = pos_mf.rolling(period, min_periods=1).sum()
    neg_sum = neg_mf.rolling(period, min_periods=1).sum()
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + mfr))


def detect_crossings(ma_fast: pd.Series, ma_slow: pd.Series) -> dict:
    """Détecte les croisements golden cross / death cross."""
    crosses = {"golden": [], "death": []}
    prev_diff = ma_fast - ma_slow
    for i in range(1, len(prev_diff)):
        if pd.isna(prev_diff.iloc[i - 1]) or pd.isna(prev_diff.iloc[i]):
            continue
        if prev_diff.iloc[i - 1] < 0 and prev_diff.iloc[i] >= 0:
            crosses["golden"].append(i)
        elif prev_diff.iloc[i - 1] > 0 and prev_diff.iloc[i] <= 0:
            crosses["death"].append(i)
    return crosses


def signal_global(rsi: float, mfi: float, ma19: float, ma38: float, ma361: float) -> tuple:
    """Génère un signal global pondéré."""
    score = 0
    reasons = []

    # RSI
    if rsi < 30:
        score += 2
        reasons.append("RSI survendu (<30)" if FR else "RSI oversold (<30)")
    elif rsi < 45:
        score += 1
        reasons.append("RSI en zone basse" if FR else "RSI in low zone")
    elif rsi > 70:
        score -= 2
        reasons.append("RSI suracheté (>70)" if FR else "RSI overbought (>70)")
    elif rsi > 55:
        score -= 1
        reasons.append("RSI en zone haute" if FR else "RSI in high zone")

    # MFI
    if mfi < 20:
        score += 2
        reasons.append("MFI survendu (<20)" if FR else "MFI oversold (<20)")
    elif mfi > 80:
        score -= 2
        reasons.append("MFI suracheté (>80)" if FR else "MFI overbought (>80)")

    # Alignement MA
    if ma19 > ma38 > ma361:
        score += 2
        reasons.append("MAs haussières alignées" if FR else "Bullish MA alignment")
    elif ma19 < ma38 < ma361:
        score -= 2
        reasons.append("MAs baissières alignées" if FR else "Bearish MA alignment")

    # Cross MA19/MA38
    if ma19 > ma38:
        score += 1
        reasons.append("MA19 > MA38 (momentum ↑)" if FR else "MA19 > MA38 (momentum ↑)")
    else:
        score -= 1
        reasons.append("MA19 < MA38 (momentum ↓)" if FR else "MA19 < MA38 (momentum ↓)")

    if score >= 3:
        return "🟢 ACHAT FORT", C["green"], score, reasons
    elif score >= 1:
        return "🟡 ACHAT MODÉRÉ", C["gold"], score, reasons
    elif score == 0:
        return "⚪ NEUTRE", "#888888", score, reasons
    elif score >= -2:
        return "🟡 VENTE MODÉRÉE", C["orange"], score, reasons
    else:
        return "🔴 VENTE FORTE", C["red"], score, reasons


# ── En-tête ───────────────────────────────────────────────────
st.markdown(f"""
<div style='background:linear-gradient(135deg,#0D1B2A,#006B3F 60%,#FFD700 120%);
     padding:18px 24px; border-radius:12px; margin-bottom:16px;
     border-left:4px solid #FFD700;'>
    <h2 style='color:white; margin:0; font-size:1.5em;'>
        📐 {'Analyse Graphique Technique' if FR else 'Technical Chart Analysis'}
    </h2>
    <p style='color:rgba(255,255,255,0.75); margin:4px 0 0; font-size:0.9em;'>
        {'Croisements MA 19/38/361 · Money Flow Index · RSI' if FR
         else 'MA 19/38/361 Crossings · Money Flow Index · RSI'}
    </p>
</div>
""", unsafe_allow_html=True)

# ── Contrôles ─────────────────────────────────────────────────
df_live = get_actions()
if df_live.empty:
    st.error("Données BRVM indisponibles")
    st.stop()

col_sel, col_per, col_rsi, col_mfi = st.columns([3, 2, 1, 1])

with col_sel:
    titre = st.selectbox(
        "📌 " + ("Titre" if FR else "Stock"),
        df_live["symbole"].tolist(),
        format_func=lambda x: f"{x} — {df_live[df_live['symbole']==x]['nom'].values[0][:45]}",
    )

with col_per:
    period = st.selectbox(
        "📅 " + ("Période" if FR else "Period"),
        [90, 180, 365],
        format_func=lambda x: f"{x} {'jours' if FR else 'days'}",
        index=1,
    )

with col_rsi:
    rsi_period = st.number_input("RSI", min_value=5, max_value=30, value=14, step=1)

with col_mfi:
    mfi_period = st.number_input("MFI", min_value=5, max_value=30, value=14, step=1)

# ── Chargement données historiques ───────────────────────────
hist_data, hist_code = get_market_history(titre, days=period)

row_live = df_live[df_live["symbole"] == titre].iloc[0]

if hist_code != 200 or not hist_data.get("data"):
    # ── Fallback : simulation sur données live ────────────────
    st.warning(
        "⏳ Historique insuffisant — simulation sur données récentes disponibles." if FR
        else "⏳ Insufficient history — simulation on available recent data."
    )
    n = 90
    np.random.seed(42)
    base = row_live["cours"]
    noise = np.random.randn(n).cumsum() * (base * 0.005)
    prices = np.clip(base + noise - noise[-1], base * 0.7, base * 1.4)
    volumes = np.random.randint(500, 50000, n)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")
    df_hist = pd.DataFrame({
        "date":       dates,
        "cours":      prices,
        "volume":     volumes.astype(float),
        "cours_ouv":  prices * (1 + np.random.randn(n) * 0.005),
    })
    df_hist["high"] = df_hist[["cours", "cours_ouv"]].max(axis=1) * (1 + abs(np.random.randn(n) * 0.003))
    df_hist["low"]  = df_hist[["cours", "cours_ouv"]].min(axis=1) * (1 - abs(np.random.randn(n) * 0.003))
    is_simulated = True
else:
    df_hist = pd.DataFrame(hist_data["data"])
    df_hist["date"] = pd.to_datetime(df_hist["date"])
    df_hist = df_hist.sort_values("date").reset_index(drop=True)
    if "cours_ouv" not in df_hist.columns:
        df_hist["cours_ouv"] = df_hist["cours"]
    df_hist["high"] = df_hist[["cours", "cours_ouv"]].max(axis=1)
    df_hist["low"]  = df_hist[["cours", "cours_ouv"]].min(axis=1)
    is_simulated = False

# ── Calcul des indicateurs ────────────────────────────────────
df_hist["ma19"]  = calc_ma(df_hist["cours"], 19)
df_hist["ma38"]  = calc_ma(df_hist["cours"], 38)
df_hist["ma361"] = calc_ma(df_hist["cours"], min(361, len(df_hist)))
df_hist["rsi"]   = calc_rsi(df_hist["cours"], rsi_period)
df_hist["mfi"]   = calc_mfi(df_hist, mfi_period)

# Croisements
cross_19_38  = detect_crossings(df_hist["ma19"], df_hist["ma38"])
cross_19_361 = detect_crossings(df_hist["ma19"], df_hist["ma361"])
cross_38_361 = detect_crossings(df_hist["ma38"], df_hist["ma361"])

# Signal global
last = df_hist.iloc[-1]
sig_label, sig_color, sig_score, sig_reasons = signal_global(
    rsi=last["rsi"] if pd.notna(last["rsi"]) else 50,
    mfi=last["mfi"] if pd.notna(last["mfi"]) else 50,
    ma19=last["ma19"],
    ma38=last["ma38"],
    ma361=last["ma361"],
)

# ── Signal en haut ────────────────────────────────────────────
total_crosses = (len(cross_19_38["golden"]) + len(cross_19_38["death"]) +
                 len(cross_19_361["golden"]) + len(cross_19_361["death"]))

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Signal global" if FR else "Global Signal", sig_label)
c2.metric("RSI actuel" if FR else "Current RSI",
          f"{last['rsi']:.1f}" if pd.notna(last['rsi']) else "N/A",
          delta="Survendu" if (pd.notna(last['rsi']) and last['rsi'] < 30) else
                "Suracheté" if (pd.notna(last['rsi']) and last['rsi'] > 70) else "Neutre")
c3.metric("MFI actuel" if FR else "Current MFI",
          f"{last['mfi']:.1f}" if pd.notna(last['mfi']) else "N/A")
c4.metric("Croisements détectés" if FR else "Crossings detected", total_crosses)
c5.metric("Cours actuel" if FR else "Current Price",
          f"{row_live['cours']:,.0f} FCFA",
          delta=f"{row_live['variation']:+.2f}%")

# Raisons du signal
with st.expander(
    f"{'Détail du signal' if FR else 'Signal breakdown'} — Score : {sig_score:+d}",
    expanded=False,
):
    for r in sig_reasons:
        st.markdown(f"• {r}")

st.markdown("---")

# ══════════════════════════════════════════════════════════════
# ── GRAPHIQUE PRINCIPAL — 4 sous-graphes ─────────────────────
# ══════════════════════════════════════════════════════════════

fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    row_heights=[0.50, 0.15, 0.175, 0.175],
    vertical_spacing=0.02,
    subplot_titles=(
        f"{'Cours & Moyennes Mobiles' if FR else 'Price & Moving Averages'} — {titre}",
        "Volume",
        f"RSI ({rsi_period})",
        f"MFI ({mfi_period})",
    ),
)

dates = df_hist["date"]

# ── Row 1 : Cours + MA ────────────────────────────────────────
# Cours
fig.add_trace(go.Scatter(
    x=dates, y=df_hist["cours"],
    name="Cours" if FR else "Price",
    line=dict(color=C["price"], width=1.8),
    fill="tozeroy",
    fillcolor="rgba(232,232,232,0.04)",
    hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.0f} FCFA<extra></extra>",
), row=1, col=1)

# MA 19
fig.add_trace(go.Scatter(
    x=dates, y=df_hist["ma19"],
    name="MA 19",
    line=dict(color=C["ma19"], width=1.5),
    hovertemplate="MA19: %{y:,.0f}<extra></extra>",
), row=1, col=1)

# MA 38
fig.add_trace(go.Scatter(
    x=dates, y=df_hist["ma38"],
    name="MA 38",
    line=dict(color=C["ma38"], width=1.5, dash="dash"),
    hovertemplate="MA38: %{y:,.0f}<extra></extra>",
), row=1, col=1)

# MA 361
if df_hist["ma361"].notna().sum() > 5:
    fig.add_trace(go.Scatter(
        x=dates, y=df_hist["ma361"],
        name="MA 361",
        line=dict(color=C["ma361"], width=1.5, dash="dot"),
        hovertemplate="MA361: %{y:,.0f}<extra></extra>",
    ), row=1, col=1)

# ── Marqueurs croisements MA19/MA38 ──────────────────────────
for idx in cross_19_38["golden"]:
    if idx < len(df_hist):
        fig.add_trace(go.Scatter(
            x=[dates.iloc[idx]],
            y=[df_hist["cours"].iloc[idx]],
            mode="markers+text",
            marker=dict(symbol="triangle-up", size=14, color=C["green"],
                        line=dict(color="white", width=1)),
            text=["GC"], textposition="top center",
            textfont=dict(color=C["green"], size=9),
            name="Golden Cross 19/38",
            showlegend=False,
            hovertemplate=f"<b>Golden Cross 19/38</b><br>%{{x|%d %b %Y}}<extra></extra>",
        ), row=1, col=1)

for idx in cross_19_38["death"]:
    if idx < len(df_hist):
        fig.add_trace(go.Scatter(
            x=[dates.iloc[idx]],
            y=[df_hist["cours"].iloc[idx]],
            mode="markers+text",
            marker=dict(symbol="triangle-down", size=14, color=C["red"],
                        line=dict(color="white", width=1)),
            text=["DC"], textposition="bottom center",
            textfont=dict(color=C["red"], size=9),
            name="Death Cross 19/38",
            showlegend=False,
            hovertemplate=f"<b>Death Cross 19/38</b><br>%{{x|%d %b %Y}}<extra></extra>",
        ), row=1, col=1)

# Croisements MA19/MA361
for idx in cross_19_361["golden"]:
    if idx < len(df_hist):
        fig.add_trace(go.Scatter(
            x=[dates.iloc[idx]], y=[df_hist["cours"].iloc[idx]],
            mode="markers",
            marker=dict(symbol="star", size=16, color=C["green"],
                        line=dict(color="white", width=1)),
            name="Golden Cross 19/361", showlegend=False,
            hovertemplate="<b>Golden Cross 19/361</b><br>%{x|%d %b %Y}<extra></extra>",
        ), row=1, col=1)

for idx in cross_19_361["death"]:
    if idx < len(df_hist):
        fig.add_trace(go.Scatter(
            x=[dates.iloc[idx]], y=[df_hist["cours"].iloc[idx]],
            mode="markers",
            marker=dict(symbol="star", size=16, color=C["red"],
                        line=dict(color="white", width=1)),
            name="Death Cross 19/361", showlegend=False,
            hovertemplate="<b>Death Cross 19/361</b><br>%{x|%d %b %Y}<extra></extra>",
        ), row=1, col=1)

# ── Row 2 : Volume ────────────────────────────────────────────
fig.add_trace(go.Bar(
    x=dates, y=df_hist["volume"],
    name="Volume",
    marker_color=C["vol"],
    opacity=0.7,
    hovertemplate="%{x|%d %b}<br>Vol: %{y:,.0f}<extra></extra>",
), row=2, col=1)

# ── Row 3 : RSI ───────────────────────────────────────────────
fig.add_trace(go.Scatter(
    x=dates, y=df_hist["rsi"],
    name=f"RSI ({rsi_period})",
    line=dict(color=C["rsi"], width=1.8),
    hovertemplate="RSI: %{y:.1f}<extra></extra>",
), row=3, col=1)

# Zones RSI
fig.add_hrect(y0=70, y1=100, row=3, col=1,
              fillcolor="rgba(255,68,68,0.08)", line_width=0)
fig.add_hrect(y0=0, y1=30, row=3, col=1,
              fillcolor="rgba(0,204,102,0.08)", line_width=0)
fig.add_hline(y=70, row=3, col=1,
              line=dict(color=C["red"], width=1, dash="dot"))
fig.add_hline(y=50, row=3, col=1,
              line=dict(color="#555", width=1, dash="dot"))
fig.add_hline(y=30, row=3, col=1,
              line=dict(color=C["green"], width=1, dash="dot"))

# ── Row 4 : MFI ───────────────────────────────────────────────
fig.add_trace(go.Scatter(
    x=dates, y=df_hist["mfi"],
    name=f"MFI ({mfi_period})",
    line=dict(color=C["mfi"], width=1.8),
    fill="tozeroy",
    fillcolor="rgba(168,85,247,0.07)",
    hovertemplate="MFI: %{y:.1f}<extra></extra>",
), row=4, col=1)

# Zones MFI
fig.add_hrect(y0=80, y1=100, row=4, col=1,
              fillcolor="rgba(255,68,68,0.08)", line_width=0)
fig.add_hrect(y0=0, y1=20, row=4, col=1,
              fillcolor="rgba(0,204,102,0.08)", line_width=0)
fig.add_hline(y=80, row=4, col=1,
              line=dict(color=C["red"], width=1, dash="dot"))
fig.add_hline(y=50, row=4, col=1,
              line=dict(color="#555", width=1, dash="dot"))
fig.add_hline(y=20, row=4, col=1,
              line=dict(color=C["green"], width=1, dash="dot"))

# ── Mise en forme générale ────────────────────────────────────
axis_style = dict(
    showgrid=True, gridcolor=C["grid"],
    color=C["text"], zeroline=False,
)

fig.update_layout(
    **LAYOUT_BASE,
    height=820,
    hovermode="x unified",
    legend=dict(
        orientation="h", yanchor="bottom", y=1.01,
        bgcolor="rgba(0,0,0,0.3)", bordercolor="#333",
        font=dict(size=11),
    ),
    xaxis4=dict(**axis_style, rangeslider=dict(visible=False)),
)

# Axes Y
fig.update_yaxes(row=1, col=1, **axis_style, tickformat=",.0f", ticksuffix=" F")
fig.update_yaxes(row=2, col=1, **axis_style, tickformat=",.0f")
fig.update_yaxes(row=3, col=1, **axis_style, range=[0, 100],
                 tickvals=[0, 30, 50, 70, 100])
fig.update_yaxes(row=4, col=1, **axis_style, range=[0, 100],
                 tickvals=[0, 20, 50, 80, 100])

# Axes X
for r in range(1, 5):
    fig.update_xaxes(row=r, col=1, **axis_style, showticklabels=(r == 4))

# Titres sous-graphes
for ann in fig.layout.annotations:
    ann.font.color = "#aaa"
    ann.font.size = 11

st.plotly_chart(fig, use_container_width=True)

if is_simulated:
    st.caption("⚠️ " + (
        "Données simulées — l'historique réel se peuplera automatiquement."
        if FR else
        "Simulated data — real history will populate automatically."
    ))

# ══════════════════════════════════════════════════════════════
# ── TABLEAU DES CROISEMENTS ───────────────────────────────────
# ══════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🔁 " + ("Historique des croisements" if FR else "Crossing History"))

cross_rows = []
labels = {
    ("19", "38",  "golden"): ("MA19 ✕ MA38",  "🟢 Golden Cross", C["green"]),
    ("19", "38",  "death"):  ("MA19 ✕ MA38",  "🔴 Death Cross",  C["red"]),
    ("19", "361", "golden"): ("MA19 ✕ MA361", "🟢 Golden Cross", C["green"]),
    ("19", "361", "death"):  ("MA19 ✕ MA361", "🔴 Death Cross",  C["red"]),
    ("38", "361", "golden"): ("MA38 ✕ MA361", "🟢 Golden Cross", C["green"]),
    ("38", "361", "death"):  ("MA38 ✕ MA361", "🔴 Death Cross",  C["red"]),
}

all_crosses = [
    (cross_19_38,  "19", "38"),
    (cross_19_361, "19", "361"),
    (cross_38_361, "38", "361"),
]

for cross_dict, fast, slow in all_crosses:
    for kind in ("golden", "death"):
        key = (fast, slow, kind)
        pair_label, type_label, color = labels[key]
        for idx in cross_dict[kind]:
            if idx < len(df_hist):
                row_c = df_hist.iloc[idx]
                cross_rows.append({
                    "Date": row_c["date"].strftime("%d/%m/%Y") if hasattr(row_c["date"], "strftime") else str(row_c["date"])[:10],
                    "Croisement" if FR else "Crossing": pair_label,
                    "Type": type_label,
                    f"Cours FCFA" if FR else "Price FCFA": f"{row_c['cours']:,.0f}",
                })

if cross_rows:
    df_crosses = pd.DataFrame(cross_rows).sort_values("Date", ascending=False)
    st.dataframe(
        df_crosses,
        use_container_width=True,
        hide_index=True,
        height=min(300, 40 + len(df_crosses) * 38),
    )
else:
    st.info(
        "Aucun croisement détecté sur la période sélectionnée." if FR
        else "No crossings detected for the selected period."
    )

# ══════════════════════════════════════════════════════════════
# ── INTERPRÉTATION ───────────────────────────────────────────
# ══════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🧠 " + ("Interprétation & Lecture" if FR else "Interpretation & Reading"))

col_rsi_int, col_mfi_int, col_ma_int = st.columns(3)

with col_rsi_int:
    rsi_val = last["rsi"] if pd.notna(last["rsi"]) else 50
    rsi_zone = (
        "🔴 Suracheté (>70)" if rsi_val > 70 else
        "🟡 Zone haute (55-70)" if rsi_val > 55 else
        "🟢 Survendu (<30)" if rsi_val < 30 else
        "🟡 Zone basse (30-45)" if rsi_val < 45 else
        "⚪ Zone neutre (45-55)"
    )
    st.markdown(f"""
    <div style='background:#0D1B2A; border:1px solid {C["rsi"]}; border-radius:10px; padding:16px;'>
        <h4 style='color:{C["rsi"]}; margin:0 0 8px;'>RSI — {rsi_period} périodes</h4>
        <p style='color:white; font-size:1.6em; margin:0;'><b>{rsi_val:.1f}</b></p>
        <p style='color:#aaa; margin:4px 0;'>{rsi_zone}</p>
        <hr style='border-color:#333; margin:8px 0;'>
        <p style='color:#ccc; font-size:0.85em; margin:0;'>
            {'< 30 : Zone de survente, signal achat potentiel' if FR else '< 30: Oversold zone, potential buy signal'}<br>
            {'> 70 : Zone de surachat, signal vente potentiel' if FR else '> 70: Overbought zone, potential sell signal'}
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_mfi_int:
    mfi_val = last["mfi"] if pd.notna(last["mfi"]) else 50
    mfi_zone = (
        "🔴 Suracheté (>80)" if mfi_val > 80 else
        "🟡 Zone haute (60-80)" if mfi_val > 60 else
        "🟢 Survendu (<20)" if mfi_val < 20 else
        "🟡 Zone basse (20-40)" if mfi_val < 40 else
        "⚪ Zone neutre (40-60)"
    )
    st.markdown(f"""
    <div style='background:#0D1B2A; border:1px solid {C["mfi"]}; border-radius:10px; padding:16px;'>
        <h4 style='color:{C["mfi"]}; margin:0 0 8px;'>MFI — {mfi_period} périodes</h4>
        <p style='color:white; font-size:1.6em; margin:0;'><b>{mfi_val:.1f}</b></p>
        <p style='color:#aaa; margin:4px 0;'>{mfi_zone}</p>
        <hr style='border-color:#333; margin:8px 0;'>
        <p style='color:#ccc; font-size:0.85em; margin:0;'>
            {'Intègre le volume dans le momentum' if FR else 'Integrates volume into momentum'}<br>
            {'< 20 : Pression acheteuse forte' if FR else '< 20: Strong buying pressure'}<br>
            {'> 80 : Pression vendeuse forte' if FR else '> 80: Strong selling pressure'}
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_ma_int:
    ma19_v  = last["ma19"]
    ma38_v  = last["ma38"]
    ma361_v = last["ma361"]
    trend = (
        "📈 Haussière" if ma19_v > ma38_v > ma361_v else
        "📉 Baissière" if ma19_v < ma38_v < ma361_v else
        "↔️ Mixte / Indécise"
    ) if FR else (
        "📈 Bullish" if ma19_v > ma38_v > ma361_v else
        "📉 Bearish" if ma19_v < ma38_v < ma361_v else
        "↔️ Mixed / Undecided"
    )
    st.markdown(f"""
    <div style='background:#0D1B2A; border:1px solid {C["gold"]}; border-radius:10px; padding:16px;'>
        <h4 style='color:{C["gold"]}; margin:0 0 8px;'>
            {'Moyennes Mobiles' if FR else 'Moving Averages'}
        </h4>
        <p style='color:#ccc; margin:2px 0; font-size:0.9em;'>
            <span style='color:{C["ma19"]};'>■</span> MA19 : <b>{ma19_v:,.0f} F</b>
        </p>
        <p style='color:#ccc; margin:2px 0; font-size:0.9em;'>
            <span style='color:{C["ma38"]};'>■</span> MA38 : <b>{ma38_v:,.0f} F</b>
        </p>
        <p style='color:#ccc; margin:2px 0; font-size:0.9em;'>
            <span style='color:{C["ma361"]};'>■</span> MA361 : <b>{ma361_v:,.0f} F</b>
        </p>
        <hr style='border-color:#333; margin:8px 0;'>
        <p style='color:white; margin:0; font-size:1em;'><b>{'Tendance' if FR else 'Trend'} : {trend}</b></p>
    </div>
    """, unsafe_allow_html=True)

# ── Légende croisements ───────────────────────────────────────
st.markdown("---")
with st.expander("📖 " + ("Légende & Méthodologie" if FR else "Legend & Methodology"), expanded=False):
    st.markdown(f"""
    **{'Croisements de Moyennes Mobiles' if FR else 'Moving Average Crossings'}**
    - 🟢 **Golden Cross** : MA rapide passe **au-dessus** de MA lente → signal haussier
    - 🔴 **Death Cross** : MA rapide passe **en-dessous** de MA lente → signal baissier
    - **GC** (triangle ↑ sur graphe) = Golden Cross MA19/MA38
    - **DC** (triangle ↓ sur graphe) = Death Cross MA19/MA38
    - ⭐ = Croisement MA19/MA361 (signal long terme)

    **RSI — Relative Strength Index**
    - Mesure la vitesse et l'amplitude des variations de prix
    - Zone verte (<30) : survendu → rebond possible
    - Zone rouge (>70) : suracheté → correction possible

    **MFI — Money Flow Index**
    - Version pondérée par le volume du RSI
    - Intègre la pression acheteuse/vendeuse réelle
    - Plus fiable que le RSI seul en présence de forts volumes

    **{'Combinaison optimale' if FR else 'Optimal combination'}**
    - RSI survendu **+** MFI survendu **+** Golden Cross → signal achat fort
    - RSI suracheté **+** MFI suracheté **+** Death Cross → signal vente fort
    """)