"""
Paper Trading Live Dashboard
==============================
Streamlit dashboard temps reel connecte a la DB SQLite du paper engine.

Usage :
  streamlit run brvm-trading/paper/paper_dashboard.py
"""
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DB_PATH      = Path("brvm-trading/paper/paper_trades.db")
CAPITAL_INIT = 10_000
REFRESH_SEC  = 30

st.set_page_config(
    page_title="Paper Trading — Afrika Markets",
    page_icon="📈",
    layout="wide",
)

# ── Styles ────────────────────────────────────────────────────
st.markdown("""
<style>
  .stMetric label  { color: #9CA3AF !important; font-size: 0.75rem !important; }
  .stMetric value  { font-size: 1.5rem !important; }
  .block-container { padding-top: 1rem; }
  div[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)


# ── DB helpers ────────────────────────────────────────────────
@st.cache_data(ttl=REFRESH_SEC)
def load_trades() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as c:
        df = pd.read_sql("SELECT * FROM trades ORDER BY entry_time DESC", c)
    if df.empty:
        return df
    for col in ["entry_time", "exit_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data(ttl=REFRESH_SEC)
def load_snapshots() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as c:
        df = pd.read_sql("SELECT * FROM portfolio_snapshots ORDER BY ts", c)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    return df


@st.cache_data(ttl=REFRESH_SEC)
def load_signals() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as c:
        df = pd.read_sql(
            "SELECT * FROM signals ORDER BY ts DESC LIMIT 500", c
        )
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    return df


# ── Metriques ─────────────────────────────────────────────────
def compute_metrics(trades: pd.DataFrame, snaps: pd.DataFrame) -> dict:
    closed = trades[trades["status"] == "CLOSED"] if not trades.empty else pd.DataFrame()
    equity = snaps["equity"].iloc[-1] if not snaps.empty else CAPITAL_INIT
    pnl    = (equity / CAPITAL_INIT - 1) * 100

    if closed.empty:
        return dict(equity=equity, pnl=pnl, sharpe=0, win_rate=0,
                    pf=0, nb=0, avg_hold=0, max_dd=0, best=0, worst=0)

    pnls   = closed["pnl_pct"].dropna()
    wr     = (pnls > 0).mean() * 100
    gains  = pnls[pnls > 0].sum()
    losses = abs(pnls[pnls < 0].sum())
    pf     = gains / max(losses, 1e-10)
    sh     = (pnls.mean() / pnls.std()) * np.sqrt(252) if pnls.std() > 0 else 0

    avg_hold = (
        (closed["exit_time"] - closed["entry_time"])
        .dt.total_seconds().div(86400).mean()
        if "exit_time" in closed.columns else 0
    )

    if not snaps.empty and "equity" in snaps.columns:
        eq_s  = snaps["equity"]
        roll  = eq_s.cummax()
        max_dd = ((eq_s - roll) / roll).min() * 100
    else:
        max_dd = 0

    return dict(
        equity=equity, pnl=pnl, sharpe=sh, win_rate=wr,
        pf=pf, nb=len(closed), avg_hold=avg_hold,
        max_dd=max_dd, best=pnls.max()*100, worst=pnls.min()*100,
    )


# ── Plotly equity curve ───────────────────────────────────────
def equity_chart(snaps: pd.DataFrame) -> go.Figure:
    if snaps.empty:
        return go.Figure()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.05)

    fig.add_trace(go.Scatter(
        x=snaps["ts"], y=snaps["equity"],
        mode="lines", name="Equity",
        line=dict(color="#C9A84C", width=2),
        fill="tozeroy", fillcolor="rgba(201,168,76,0.06)",
    ), row=1, col=1)
    fig.add_hline(y=CAPITAL_INIT, line_dash="dash",
                  line_color="#4B5563", line_width=0.8, row=1, col=1)

    roll_max = snaps["equity"].cummax()
    dd = (snaps["equity"] - roll_max) / roll_max * 100
    fig.add_trace(go.Scatter(
        x=snaps["ts"], y=dd,
        mode="lines", name="Drawdown",
        line=dict(color="#EF4444", width=1.2),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.18)",
    ), row=2, col=1)

    fig.update_layout(
        plot_bgcolor="#0D0D1F", paper_bgcolor="#0D0D1F",
        font=dict(color="#E5E7EB", size=11),
        height=400, margin=dict(t=20, b=10, l=50, r=20),
        legend=dict(bgcolor="#1F2937", bordercolor="#374151", borderwidth=1),
        xaxis2=dict(gridcolor="#1F2937"),
        yaxis=dict(title="Capital ($)", gridcolor="#1F2937"),
        yaxis2=dict(title="DD (%)", gridcolor="#1F2937"),
    )
    return fig


def pnl_chart(trades: pd.DataFrame) -> go.Figure:
    closed = trades[trades["status"] == "CLOSED"].copy() if not trades.empty else pd.DataFrame()
    if closed.empty:
        return go.Figure()

    closed = closed.sort_values("entry_time").reset_index(drop=True)
    colors = ["#22C55E" if v > 0 else "#EF4444" for v in closed["pnl_pct"]]

    fig = go.Figure(go.Bar(
        x=list(range(len(closed))),
        y=closed["pnl_pct"] * 100,
        marker_color=colors,
        marker_line_width=0,
        hovertemplate=(
            "Trade #%{x}<br>"
            "Asset: %{customdata[0]}<br>"
            "Side: %{customdata[1]}<br>"
            "PnL: %{y:.2f}%<extra></extra>"
        ),
        customdata=closed[["asset", "side"]].values,
    ))
    fig.add_hline(y=0, line_dash="solid", line_color="#4B5563", line_width=0.8)
    fig.update_layout(
        plot_bgcolor="#0D0D1F", paper_bgcolor="#0D0D1F",
        font=dict(color="#E5E7EB", size=11),
        height=250, margin=dict(t=10, b=10, l=50, r=20),
        yaxis=dict(title="PnL (%)", gridcolor="#1F2937"),
        xaxis=dict(title="Trade #", gridcolor="#1F2937"),
    )
    return fig


def regime_chart(signals: pd.DataFrame) -> go.Figure:
    if signals.empty or "regime" not in signals.columns:
        return go.Figure()

    counts = signals["regime"].value_counts()
    colors = {"trend":"#22C55E","neutral":"#3B82F6","high_vol":"#F59E0B","range":"#A78BFA"}

    fig = go.Figure(go.Pie(
        labels=counts.index.tolist(),
        values=counts.values.tolist(),
        hole=0.55,
        marker=dict(
            colors=[colors.get(r,"#6B7280") for r in counts.index],
            line=dict(color="#0D0D1F", width=2)
        ),
        textfont=dict(color="white"),
    ))
    fig.update_layout(
        plot_bgcolor="#0D0D1F", paper_bgcolor="#0D0D1F",
        font=dict(color="#E5E7EB"), height=250,
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(bgcolor="#1F2937", bordercolor="#374151", borderwidth=1),
    )
    return fig


# ── Score time-series par asset ───────────────────────────────
def score_chart(signals: pd.DataFrame) -> go.Figure:
    if signals.empty:
        return go.Figure()

    fig = go.Figure()
    COLORS = {"BTCUSDT":"#F7931A","ETHUSDT":"#627EEA","SOLUSDT":"#9945FF","XRPUSDT":"#00AAE4"}

    for asset in signals["asset"].unique():
        sub = signals[signals["asset"] == asset].sort_values("ts").tail(200)
        fig.add_trace(go.Scatter(
            x=sub["ts"], y=sub["score"],
            mode="lines", name=asset.replace("USDT",""),
            line=dict(color=COLORS.get(asset,"#C9A84C"), width=1.2),
        ))

    fig.add_hline(y=4,  line_dash="dash", line_color="#22C55E", line_width=0.8,
                  annotation_text="LONG seuil", annotation_font_color="#22C55E")
    fig.add_hline(y=-4, line_dash="dash", line_color="#EF4444", line_width=0.8,
                  annotation_text="SHORT seuil", annotation_font_color="#EF4444")
    fig.add_hline(y=0,  line_dash="dot",  line_color="#374151", line_width=0.6)

    fig.update_layout(
        plot_bgcolor="#0D0D1F", paper_bgcolor="#0D0D1F",
        font=dict(color="#E5E7EB", size=11),
        height=280, margin=dict(t=10, b=10, l=40, r=20),
        yaxis=dict(title="Score composite", gridcolor="#1F2937"),
        xaxis=dict(gridcolor="#1F2937"),
        legend=dict(bgcolor="#1F2937", bordercolor="#374151", borderwidth=1),
    )
    return fig


# ── UI principale ─────────────────────────────────────────────
def main():
    # Header
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0D0D1F,#1a0533 50%,#0d1a2e);
         padding:16px 24px; border-radius:12px; margin-bottom:16px;
         border-left:4px solid #C9A84C;'>
        <h2 style='color:white; margin:0; font-size:1.4em;'>
            📈 Paper Trading Engine v1
            <span style='font-size:0.55em; background:#22c55e22; color:#22c55e;
            padding:3px 10px; border-radius:12px; margin-left:10px;
            border:1px solid #22c55e44;'>LIVE</span>
        </h2>
        <p style='color:rgba(255,255,255,0.6); margin:4px 0 0; font-size:0.85em;'>
            Adaptive Score v2 | Regime-Native Crypto | IS/OOS Validated
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Charge les donnees
    trades  = load_trades()
    snaps   = load_snapshots()
    signals = load_signals()
    m       = compute_metrics(trades, snaps)

    # Positions ouvertes
    open_t  = trades[trades["status"] == "OPEN"] if not trades.empty else pd.DataFrame()

    # ── KPIs ────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Capital", f"${m['equity']:,.0f}",
              f"{m['pnl']:+.1f}%")
    c2.metric("Sharpe", f"{m['sharpe']:.3f}",
              "OK" if m['sharpe'] > 1 else "Faible")
    c3.metric("Win Rate", f"{m['win_rate']:.1f}%",
              f"{m['nb']} trades")
    c4.metric("Profit Factor", f"{m['pf']:.3f}",
              "OK" if m['pf'] > 1.5 else "Faible")
    c5.metric("Max DD", f"{m['max_dd']:.1f}%",
              "OK" if abs(m['max_dd']) < 5 else "Attention")
    c6.metric("Positions ouvertes", len(open_t),
              f"Hold moy: {m['avg_hold']:.1f}j")

    st.divider()

    # ── Equity curve ────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**Equity curve + Drawdown**")
        if snaps.empty:
            st.info("En attente des premieres donnees...")
        else:
            st.plotly_chart(equity_chart(snaps), use_container_width=True)

    with col2:
        st.markdown("**Distribution regimes detectes**")
        if signals.empty:
            st.info("Aucun signal enregistre")
        else:
            st.plotly_chart(regime_chart(signals), use_container_width=True)

    # ── Score time-series ────────────────────────────────────
    st.markdown("**Score composite — historique des signaux**")
    if signals.empty:
        st.info("En attente des signaux...")
    else:
        st.plotly_chart(score_chart(signals), use_container_width=True)

    # ── PnL par trade ────────────────────────────────────────
    col3, col4 = st.columns([2, 1])
    with col3:
        st.markdown("**PnL par trade**")
        st.plotly_chart(pnl_chart(trades), use_container_width=True)

    with col4:
        st.markdown("**Metriques avancees**")
        adv = {
            "Best trade":   f"{m['best']:+.2f}%",
            "Worst trade":  f"{m['worst']:+.2f}%",
            "Hold moyen":   f"{m['avg_hold']:.1f}j",
            "Nb trades":    m['nb'],
        }
        for k, v in adv.items():
            color = "green" if "+" in str(v) else "red" if "-" in str(v) else "white"
            st.markdown(f"`{k}` &nbsp; **:{color}[{v}]**",
                        unsafe_allow_html=True)

    # ── Positions ouvertes ───────────────────────────────────
    st.divider()
    st.markdown("**Positions ouvertes**")
    if open_t.empty:
        st.info("Aucune position ouverte")
    else:
        display_cols = [c for c in ["asset","side","entry_time","entry_price",
                                     "quantity","regime","score"]
                        if c in open_t.columns]
        st.dataframe(
            open_t[display_cols].reset_index(drop=True),
            use_container_width=True,
        )

    # ── Trade log ────────────────────────────────────────────
    st.markdown("**Historique des trades**")
    if trades.empty:
        st.info("Aucun trade enregistre")
    else:
        closed = trades[trades["status"] == "CLOSED"].copy()
        if not closed.empty:
            closed["pnl_pct"] = (closed["pnl_pct"] * 100).round(3)
            closed["pnl_usd"] = closed["pnl_usd"].round(2)
            display = [c for c in ["asset","side","entry_time","exit_time",
                                    "entry_price","exit_price","pnl_pct",
                                    "pnl_usd","regime","score"]
                       if c in closed.columns]
            st.dataframe(
                closed[display].head(50).reset_index(drop=True),
                use_container_width=True,
            )

    # ── Auto-refresh ─────────────────────────────────────────
    st.caption(
        f"Rafraichissement auto toutes les {REFRESH_SEC}s | "
        f"Derniere MAJ : {datetime.now().strftime('%H:%M:%S')}"
    )
    time.sleep(REFRESH_SEC)
    st.rerun()


if __name__ == "__main__":
    main()
