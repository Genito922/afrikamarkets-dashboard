"""
Page 3 — Analyse détaillée par titre + Historique des prix
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.brvm_scraper import get_actions
from frontend.auth_ui import render_auth_sidebar, require_plan
from frontend.auth_client import get_market_history
from utils.i18n import t, get_lang

st.set_page_config(page_title="Analyse Titre — Afrika Markets", layout="wide")

lang = get_lang()
FR   = lang == "fr"

render_auth_sidebar(fr=FR)

st.title(t("stock_title", lang))

df = get_actions()
if df.empty:
    st.error(t("data_unavailable", lang))
    st.stop()

# ── Sélection titre ───────────────────────────────────────────
titre = st.selectbox(
    t("select_stock", lang),
    df["symbole"].tolist(),
    format_func=lambda x: f"{x} — {df[df['symbole']==x]['nom'].values[0][:50]}"
)

row = df[df["symbole"] == titre].iloc[0]

# ── KPIs ──────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(t("close_price", lang), f"{row['cours']:,.0f} FCFA")
c2.metric(t("prev_price", lang),  f"{row['cours_veille']:,.0f} FCFA")
c3.metric(t("open_price", lang),  f"{row['cours_ouv']:,.0f} FCFA")
c4.metric(t("change", lang),      f"{row['variation']:+.2f}%",
          delta=f"{row['cours']-row['cours_veille']:+,.0f} FCFA")
c5.metric(t("volume", lang),      f"{row['volume']:,.0f}")

st.markdown("---")

# ── Gauge variation journalière ───────────────────────────────
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=row["variation"],
    delta={"reference": 0, "valueformat": ".2f"},
    gauge={
        "axis": {"range": [-10, 10]},
        "bar": {"color": "#00CC66" if row["variation"] >= 0 else "#FF4444"},
        "steps": [
            {"range": [-10, -5], "color": "#3B0D0D"},
            {"range": [-5,   0], "color": "#2D1A1A"},
            {"range": [0,    5], "color": "#1A2D1A"},
            {"range": [5,   10], "color": "#0D3B0D"},
        ],
        "threshold": {
            "line": {"color": "white", "width": 3},
            "thickness": 0.75, "value": 0,
        },
    },
    title={"text": f"{t('variation', lang)} {titre} (%)", "font": {"color": "white"}},
    number={"suffix": "%", "font": {"color": "white"}},
))
fig_gauge.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="white",
    height=300,
)
st.plotly_chart(fig_gauge, use_container_width=True)

# ── Signal rapide ─────────────────────────────────────────────
st.subheader(t("quick_analysis", lang))
var = row["variation"]
if var > 3:
    signal = t("signal_strong_up", lang)
elif var > 0:
    signal = t("signal_moderate_up", lang)
elif var == 0:
    signal = t("signal_flat", lang)
elif var > -3:
    signal = t("signal_moderate_down", lang)
else:
    signal = t("signal_strong_down", lang)

st.info(signal)

col1, col2 = st.columns(2)
with col1:
    direction = (
        t("dir_up", lang)   if var > 0 else
        t("dir_down", lang) if var < 0 else
        t("dir_flat", lang)
    )
    st.markdown(f"""
    **{t("information", lang)}**
    - **Symbole :** {row["symbole"]}
    - **{t("company", lang)} :** {row["nom"]}
    - **{t("sector", lang)} :** {row["secteur"]}
    """)
with col2:
    spread = abs(row["cours"] - row["cours_veille"])
    st.markdown(f"""
    **{t("session_data", lang)}**
    - **{t("range_label", lang)} :** {spread:,.0f} FCFA
    - **{t("direction", lang)} :** {direction}
    - **{t("volume", lang)} :** {row["volume"]:,.0f}
    """)

st.markdown("---")

# ── Historique des prix ───────────────────────────────────────
st.subheader(t("price_history", lang))

period_choice = st.radio(
    t("period", lang),
    options=[30, 90],
    format_func=lambda x: f"{x} {t('days', lang)}",
    horizontal=True,
    key="history_period",
)

hist_data, hist_code = get_market_history(titre, days=period_choice)

if hist_code != 200 or not hist_data.get("data"):
    st.markdown(f"""
    <div style="background:#1A1D2E; border:1px solid #FFD700; border-radius:10px;
                padding:24px; text-align:center; color:#ccc;">
        <p style="font-size:1.2em; color:#FFD700;">
            {t("history_building", lang)}
        </p>
        <p style="font-size:0.95em;">
            {t("history_auto_fill", lang)}
        </p>
        <p style="font-size:0.85em; color:#888;">
            {t("current_price", lang)} :
            <b style="color:white;"> {row['cours']:,.0f} FCFA</b> &nbsp;|&nbsp;
            {t("change_label", lang)} : <b style="color:{'#00CC66' if var >= 0 else '#FF4444'};">
            {var:+.2f}%</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

else:
    df_hist = pd.DataFrame(hist_data["data"])
    df_hist["date"] = pd.to_datetime(df_hist["date"])
    df_hist = df_hist.sort_values("date")

    color_line = "#00CC66" if df_hist["cours"].iloc[-1] >= df_hist["cours"].iloc[0] else "#FF4444"

    fig_hist = go.Figure()

    fig_hist.add_trace(go.Scatter(
        x=df_hist["date"],
        y=df_hist["cours"],
        mode="lines",
        name=t("close_col", lang),
        line={"color": color_line, "width": 2},
        fill="tozeroy",
        fillcolor=f"rgba({'0,204,102' if color_line == '#00CC66' else '255,68,68'},0.08)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.0f} FCFA<extra></extra>",
    ))

    if len(df_hist) >= 10:
        df_hist["ma10"] = df_hist["cours"].rolling(10).mean()
        fig_hist.add_trace(go.Scatter(
            x=df_hist["date"],
            y=df_hist["ma10"],
            mode="lines",
            name="MA10",
            line={"color": "#FFD700", "width": 1.5, "dash": "dash"},
            hovertemplate="MA10 : %{y:,.0f} FCFA<extra></extra>",
        ))

    delta_pct = (
        (df_hist["cours"].iloc[-1] / df_hist["cours"].iloc[0] - 1) * 100
        if df_hist["cours"].iloc[0] > 0 else 0
    )
    delta_color = "#00CC66" if delta_pct >= 0 else "#FF4444"

    fig_hist.update_layout(
        title=dict(
            text=(
                f"{titre} — {period_choice}{t('days', lang)} &nbsp;&nbsp;"
                f"<span style='color:{delta_color};'>({delta_pct:+.2f}%)</span>"
            ),
            font={"color": "white", "size": 15},
        ),
        xaxis={"showgrid": False, "color": "#aaa"},
        yaxis={
            "showgrid": True,
            "gridcolor": "#1F2232",
            "color": "#aaa",
            "tickformat": ",.0f",
            "ticksuffix": " F",
        },
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        height=380,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        hovermode="x unified",
        margin={"t": 60, "b": 30},
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    with st.expander("📊 " + t("trading_volumes", lang), expanded=False):
        fig_vol = go.Figure(go.Bar(
            x=df_hist["date"],
            y=df_hist["volume"],
            marker_color="#006B3F",
            opacity=0.8,
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Volume : %{y:,.0f}<extra></extra>",
        ))
        fig_vol.update_layout(
            xaxis={"showgrid": False, "color": "#aaa"},
            yaxis={"showgrid": True, "gridcolor": "#1F2232", "color": "#aaa", "tickformat": ",.0f"},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            height=220,
            margin={"t": 10, "b": 30},
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric(f"{t('high_label', lang)} {period_choice}{t('days', lang)}",
              f"{df_hist['cours'].max():,.0f} FCFA")
    s2.metric(f"{t('low_label', lang)} {period_choice}{t('days', lang)}",
              f"{df_hist['cours'].min():,.0f} FCFA")
    s3.metric(t("period_return", lang), f"{delta_pct:+.2f}%")
    s4.metric(t("avg_volume", lang),    f"{df_hist['volume'].mean():,.0f}")
