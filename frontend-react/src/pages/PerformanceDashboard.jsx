/**
 * Performance Dashboard — Plan Expert
 * Courbes equity/drawdown · heatmap mensuelle · rapports sous-systèmes · log trades
 */
import { useState, useEffect, useCallback } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  BarChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
} from "recharts";
import { apiGet } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import ComplianceBanner from "../components/ComplianceBanner";

// ── Constantes ────────────────────────────────────────────────────────────────

const RANGE_OPTIONS = [
  { key: "7d",  label: "7j" },
  { key: "30d", label: "30j" },
  { key: "90d", label: "90j" },
  { key: "all", label: "Tout" },
];

const MONTHS = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"];

const STATUS_COLOR = {
  active:   "#00c96a",
  waiting:  "#f59e0b",
  long:     "#00c96a",
  cash:     "#94a3b8",
  idle:     "#94a3b8",
  offline:  "#ff4d6d",
  inactive: "#334155",
};

const STATUS_LABEL = {
  active:   "Actif",
  waiting:  "En attente",
  long:     "LONG",
  cash:     "Cash",
  idle:     "Idle",
  offline:  "Hors ligne",
  inactive: "Inactif",
};

// ── Composants utilitaires ────────────────────────────────────────────────────

function KpiCard({ label, value, sub, positive, loading }) {
  if (loading) {
    return (
      <div style={styles.kpiCard}>
        <div style={styles.kpiSkeleton} />
        <div style={{ ...styles.kpiSkeleton, width: "60%", height: 14, marginTop: 6 }} />
      </div>
    );
  }
  const isPositive = positive == null ? null : positive;
  const valueColor =
    isPositive === null ? "#e2e8f0"
    : isPositive ? "#00c96a"
    : "#ff4d6d";

  return (
    <div style={styles.kpiCard}>
      <div style={{ ...styles.kpiValue, color: valueColor }}>{value}</div>
      <div style={styles.kpiLabel}>{label}</div>
      {sub && <div style={styles.kpiSub}>{sub}</div>}
    </div>
  );
}

function SectionTitle({ children, action }) {
  return (
    <div style={styles.sectionHeader}>
      <h3 style={styles.sectionTitle}>{children}</h3>
      {action}
    </div>
  );
}

// ── Heatmap mensuelle ─────────────────────────────────────────────────────────

function MonthlyHeatmap({ data }) {
  if (!data || data.length === 0) {
    return (
      <div style={styles.emptyBox}>
        Pas encore de données mensuelles — le paper trading doit avoir au moins 1 mois d'historique.
      </div>
    );
  }

  // Organise par année
  const years = [...new Set(data.map((d) => d.year))].sort();
  const byYearMonth = {};
  data.forEach((d) => {
    byYearMonth[`${d.year}-${d.month}`] = d.return_pct;
  });

  function cellColor(pct) {
    if (pct == null) return "#1e293b";
    if (pct >= 10)  return "#00613a";
    if (pct >= 5)   return "#008a52";
    if (pct >= 2)   return "#00c96a44";
    if (pct >= 0)   return "#00c96a22";
    if (pct >= -2)  return "#ff4d6d22";
    if (pct >= -5)  return "#ff4d6d44";
    if (pct >= -10) return "#c0253e";
    return "#7a0f28";
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={styles.heatTable}>
        <thead>
          <tr>
            <th style={styles.heatTh}>Année</th>
            {MONTHS.map((m) => (
              <th key={m} style={styles.heatTh}>{m}</th>
            ))}
            <th style={styles.heatTh}>Total</th>
          </tr>
        </thead>
        <tbody>
          {years.map((yr) => {
            let totalReturn = 1;
            const cells = MONTHS.map((_, idx) => {
              const month = idx + 1;
              const pct = byYearMonth[`${yr}-${month}`];
              if (pct != null) totalReturn *= (1 + pct / 100);
              return { month, pct };
            });
            const totalPct = (totalReturn - 1) * 100;
            return (
              <tr key={yr}>
                <td style={styles.heatYear}>{yr}</td>
                {cells.map(({ month, pct }) => (
                  <td
                    key={month}
                    style={{
                      ...styles.heatCell,
                      background: cellColor(pct),
                      color: pct == null ? "#475569" : Math.abs(pct) > 2 ? "#e2e8f0" : "#94a3b8",
                    }}
                  >
                    {pct != null ? `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%` : "—"}
                  </td>
                ))}
                <td
                  style={{
                    ...styles.heatCell,
                    background: cellColor(totalPct),
                    fontWeight: 600,
                    color: Math.abs(totalPct) > 2 ? "#e2e8f0" : "#94a3b8",
                  }}
                >
                  {totalPct > 0 ? "+" : ""}
                  {totalPct.toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Carte sous-système ────────────────────────────────────────────────────────

function SubsystemCard({ sys }) {
  const dot = STATUS_COLOR[sys.status] || "#94a3b8";
  const label = STATUS_LABEL[sys.status] || sys.status;

  return (
    <div style={styles.sysCard}>
      {/* En-tête */}
      <div style={styles.sysHeader}>
        <div>
          <div style={styles.sysName}>{sys.name}</div>
          <div style={styles.sysDesc}>{sys.description}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ ...styles.sysDot, background: dot }} />
          <span style={{ fontSize: 12, color: dot }}>{label}</span>
        </div>
      </div>

      {/* Détails selon le type */}
      {sys.id === "regime" && (
        <div style={styles.sysBody}>
          {(sys.assets || []).map((a) => (
            <div key={a.symbol} style={styles.sysRow}>
              <span style={styles.sysSym}>{a.symbol}</span>
              <span style={{
                ...styles.sysTag,
                background: a.regime === "bull" ? "#00c96a22" : "#ff4d6d22",
                color: a.regime === "bull" ? "#00c96a" : "#ff4d6d",
              }}>
                {a.regime.toUpperCase()} {a.flipped_up ? "↑FLIP" : a.flipped_down ? "↓FLIP" : ""}
              </span>
              <span style={styles.sysMeta}>
                {a.consec_days}j · RSI {a.rsi14?.toFixed(0)} · MFI {a.mfi14?.toFixed(0)}
              </span>
              <span style={{
                ...styles.sysTag,
                background: a.deploy_ready ? "#7b2ff722" : "#33415522",
                color: a.deploy_ready ? "#a78bfa" : "#64748b",
              }}>
                {a.deploy_ready ? "DEPLOY ✓" : "en attente"}
              </span>
              <span style={{
                ...styles.sysTag,
                background: a.signal_b === 1 ? "#00c96a33" : "#1e293b",
                color: a.signal_b === 1 ? "#00c96a" : "#475569",
              }}>
                {a.signal_b === 1 ? "LONG" : "----"}
              </span>
            </div>
          ))}
          {sys.run_at && (
            <div style={styles.sysFooter}>
              Dernier scan : {new Date(sys.run_at).toLocaleString("fr-FR")}
            </div>
          )}
        </div>
      )}

      {sys.id === "signal_b" && (
        <div style={styles.sysBody}>
          <div style={styles.statRow}>
            <StatPill label="Taux signal" value={`${sys.signal_rate_pct}%`} />
          </div>
          {(sys.last_signals || []).slice(0, 5).map((s, i) => (
            <div key={i} style={styles.sysRow}>
              <span style={styles.sysSym}>{s.asset}</span>
              <span style={{
                ...styles.sysTag,
                background: s.action === "BUY" ? "#00c96a22" : "#334155",
                color: s.action === "BUY" ? "#00c96a" : "#64748b",
              }}>
                {s.action}
              </span>
              <span style={styles.sysMeta}>{s.regime} · conf {s.confidence?.toFixed(0)}%</span>
              <span style={styles.sysMeta}>{s.ts ? new Date(s.ts).toLocaleDateString("fr-FR") : ""}</span>
            </div>
          ))}
        </div>
      )}

      {sys.id === "paper_executor" && (
        <div style={styles.sysBody}>
          <div style={styles.statRow}>
            <StatPill label="Trades fermés" value={sys.n_closed_trades} />
            <StatPill label="Positions ouvertes" value={sys.n_open_trades} />
            <StatPill label="Win Rate" value={`${sys.win_rate}%`} positive={sys.win_rate >= 50} />
            <StatPill label="Profit Factor" value={sys.profit_factor?.toFixed(2)} positive={sys.profit_factor >= 1} />
          </div>
          <div style={styles.statRow}>
            <StatPill label="Meilleur trade" value={`+${sys.best_trade_pct}%`} positive />
            <StatPill label="Pire trade" value={`${sys.worst_trade_pct}%`} positive={false} />
          </div>
        </div>
      )}
    </div>
  );
}

function StatPill({ label, value, positive }) {
  const color = positive == null ? "#e2e8f0" : positive ? "#00c96a" : "#ff4d6d";
  return (
    <div style={styles.statPill}>
      <div style={{ ...styles.statVal, color }}>{value ?? "—"}</div>
      <div style={styles.statLabel}>{label}</div>
    </div>
  );
}

// ── Log des trades ────────────────────────────────────────────────────────────

function TradesTable({ trades, total, page, setPage, loading }) {
  const PAGE_SIZE = 20;
  const pages = Math.ceil(total / PAGE_SIZE);

  if (loading) {
    return <div style={styles.emptyBox}>Chargement…</div>;
  }
  if (!trades || trades.length === 0) {
    return (
      <div style={styles.emptyBox}>
        Aucun trade fermé — le paper trading démarre en Phase 1 (BTC/ETH).
      </div>
    );
  }

  return (
    <>
      <div style={{ overflowX: "auto" }}>
        <table style={styles.tradeTable}>
          <thead>
            <tr>
              {["Actif", "Entrée", "Sortie", "Prix entrée", "Prix sortie", "PnL %", "Frais"].map((h) => (
                <th key={h} style={styles.tradeTh}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => {
              const pnl = parseFloat(t.pnl_pct);
              return (
                <tr key={i} style={i % 2 === 0 ? styles.tradeRowEven : styles.tradeRowOdd}>
                  <td style={styles.tradeTd}><strong>{t.asset}</strong></td>
                  <td style={styles.tradeTd}>{t.entry_time ? new Date(t.entry_time).toLocaleDateString("fr-FR") : "—"}</td>
                  <td style={styles.tradeTd}>{t.exit_time  ? new Date(t.exit_time).toLocaleDateString("fr-FR")  : "—"}</td>
                  <td style={styles.tradeTd}>{t.entry_px != null ? Number(t.entry_px).toLocaleString("fr-FR", { maximumFractionDigits: 2 }) : "—"}</td>
                  <td style={styles.tradeTd}>{t.exit_px  != null ? Number(t.exit_px ).toLocaleString("fr-FR", { maximumFractionDigits: 2 }) : "—"}</td>
                  <td style={{ ...styles.tradeTd, color: pnl >= 0 ? "#00c96a" : "#ff4d6d", fontWeight: 600 }}>
                    {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}%
                  </td>
                  <td style={{ ...styles.tradeTd, color: "#64748b" }}>
                    {t.fees != null ? `${Number(t.fees).toFixed(4)}` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div style={styles.pagination}>
          <button
            style={styles.pageBtn}
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            ‹ Préc
          </button>
          <span style={{ color: "#94a3b8", fontSize: 13 }}>
            Page {page + 1} / {pages} — {total} trades
          </span>
          <button
            style={styles.pageBtn}
            disabled={page >= pages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            Suiv ›
          </button>
        </div>
      )}
    </>
  );
}

// ── Tooltip customisé ─────────────────────────────────────────────────────────

function EquityTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={styles.tooltip}>
      <div style={{ color: "#94a3b8", marginBottom: 4, fontSize: 11 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color, fontSize: 12 }}>
          {p.name === "equity"
            ? `Equity: $${Number(p.value).toLocaleString("fr-FR", { maximumFractionDigits: 0 })}`
            : p.name === "pnl_pct"
            ? `PnL: ${p.value >= 0 ? "+" : ""}${p.value.toFixed(2)}%`
            : `DD: ${p.value.toFixed(2)}%`}
        </div>
      ))}
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function PerformanceDashboard() {
  const [range, setRange] = useState("all");
  const [overview, setOverview] = useState(null);
  const [equity, setEquity] = useState([]);
  const [monthly, setMonthly] = useState([]);
  const [subsystems, setSubsystems] = useState([]);
  const [trades, setTrades] = useState([]);
  const [tradesTotal, setTradesTotal] = useState(0);
  const [tradePage, setTradePage] = useState(0);

  const [loadingKpi, setLoadingKpi] = useState(true);
  const [loadingEquity, setLoadingEquity] = useState(true);
  const [loadingTrades, setLoadingTrades] = useState(true);

  const PAGE_SIZE = 20;

  // ── KPIs + subsystems + monthly (une seule fois) ──────────────────────────
  useEffect(() => {
    setLoadingKpi(true);
    Promise.all([
      apiGet("/performance/overview", true),
      apiGet("/performance/subsystems", true),
      apiGet("/performance/monthly", true),
    ])
      .then(([ov, sys, mo]) => {
        setOverview(ov);
        setSubsystems(sys);
        setMonthly(mo);
      })
      .catch(console.error)
      .finally(() => setLoadingKpi(false));
  }, []);

  // ── Equity series (dépend du range) ──────────────────────────────────────
  useEffect(() => {
    setLoadingEquity(true);
    apiGet(`/performance/equity?range=${range}`, true)
      .then(setEquity)
      .catch(console.error)
      .finally(() => setLoadingEquity(false));
  }, [range]);

  // ── Trades (dépend de la page) ────────────────────────────────────────────
  useEffect(() => {
    setLoadingTrades(true);
    apiGet(`/performance/trades?limit=${PAGE_SIZE}&offset=${tradePage * PAGE_SIZE}`, true)
      .then(({ trades: t, total }) => {
        setTrades(t);
        setTradesTotal(total);
      })
      .catch(console.error)
      .finally(() => setLoadingTrades(false));
  }, [tradePage]);

  // ── Dérivés KPIs ──────────────────────────────────────────────────────────
  const ov = overview || {};
  const isDbReady = ov.db_ready ?? false;

  return (
    <div style={styles.page}>
      <ComplianceBanner />

      {/* En-tête */}
      <div style={styles.pageHeader}>
        <div>
          <h1 style={styles.pageTitle}>Performance Dashboard</h1>
          <p style={styles.pageSubtitle}>
            Paper trading Signal B · Phase 1 (BTC/ETH) · {isDbReady ? "Live" : "En attente démarrage"}
          </p>
        </div>
        <div style={styles.rangeTabs}>
          {RANGE_OPTIONS.map(({ key, label }) => (
            <button
              key={key}
              style={{ ...styles.rangeTab, ...(range === key ? styles.rangeTabActive : {}) }}
              onClick={() => setRange(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── KPI Row ──────────────────────────────────────────────────────── */}
      <div style={styles.kpiGrid}>
        <KpiCard
          label="Equity"
          value={ov.equity != null ? `$${ov.equity.toLocaleString("fr-FR", { maximumFractionDigits: 0 })}` : "—"}
          sub={`Capital initial : $${(ov.capital_init ?? 10000).toLocaleString()}`}
          positive={ov.pnl_pct >= 0}
          loading={loadingKpi}
        />
        <KpiCard
          label="PnL Total"
          value={ov.pnl_pct != null ? `${ov.pnl_pct >= 0 ? "+" : ""}${ov.pnl_pct.toFixed(2)}%` : "—"}
          positive={ov.pnl_pct >= 0}
          loading={loadingKpi}
        />
        <KpiCard
          label="Sharpe (ann.)"
          value={ov.sharpe != null ? ov.sharpe.toFixed(3) : "—"}
          sub="252 barres"
          positive={ov.sharpe >= 0.5}
          loading={loadingKpi}
        />
        <KpiCard
          label="Max Drawdown"
          value={ov.max_dd_pct != null ? `${ov.max_dd_pct.toFixed(2)}%` : "—"}
          positive={ov.max_dd_pct != null && ov.max_dd_pct > -15}
          loading={loadingKpi}
        />
        <KpiCard
          label="Win Rate"
          value={ov.win_rate != null ? `${ov.win_rate.toFixed(1)}%` : "—"}
          sub={`${ov.n_trades ?? 0} trades`}
          positive={ov.win_rate >= 50}
          loading={loadingKpi}
        />
        <KpiCard
          label="Profit Factor"
          value={ov.profit_factor != null ? ov.profit_factor.toFixed(3) : "—"}
          positive={ov.profit_factor >= 1}
          loading={loadingKpi}
        />
      </div>

      {/* ── Equity Curve ─────────────────────────────────────────────────── */}
      <div style={styles.panel}>
        <SectionTitle>Courbe Equity</SectionTitle>
        {loadingEquity ? (
          <div style={{ ...styles.emptyBox, height: 200 }}>Chargement…</div>
        ) : equity.length === 0 ? (
          <div style={styles.emptyBox}>
            Aucune donnée de portefeuille — le paper engine n'a pas encore démarré.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={equity} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 11 }} tickLine={false} />
              <YAxis
                tick={{ fill: "#475569", fontSize: 11 }}
                tickLine={false}
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip content={<EquityTooltip />} />
              <ReferenceLine y={10000} stroke="#334155" strokeDasharray="4 2" />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="#00d4ff"
                strokeWidth={2}
                fill="url(#eqGrad)"
                dot={false}
                activeDot={{ r: 4, fill: "#00d4ff" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Drawdown ─────────────────────────────────────────────────────── */}
      {equity.length > 0 && (
        <div style={styles.panel}>
          <SectionTitle>Drawdown (%)</SectionTitle>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={equity} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 11 }} tickLine={false} />
              <YAxis
                tick={{ fill: "#475569", fontSize: 11 }}
                tickLine={false}
                tickFormatter={(v) => `${v.toFixed(0)}%`}
                domain={["auto", 0]}
              />
              <Tooltip
                formatter={(v) => [`${v.toFixed(2)}%`, "Drawdown"]}
                contentStyle={styles.tooltip}
                labelStyle={{ color: "#94a3b8", fontSize: 11 }}
              />
              <ReferenceLine y={-10} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: "Kill-switch −10%", fill: "#f59e0b", fontSize: 10 }} />
              <Bar dataKey="drawdown_pct" maxBarSize={8}>
                {equity.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={entry.drawdown_pct < -10 ? "#ff4d6d" : entry.drawdown_pct < -5 ? "#f59e0b" : "#7b2ff7"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Heatmap mensuelle ────────────────────────────────────────────── */}
      <div style={styles.panel}>
        <SectionTitle>Rendements Mensuels</SectionTitle>
        <MonthlyHeatmap data={monthly} />
      </div>

      {/* ── Sous-systèmes ────────────────────────────────────────────────── */}
      <div style={styles.panel}>
        <SectionTitle>Sous-Systèmes</SectionTitle>
        <div style={styles.sysGrid}>
          {loadingKpi
            ? [0, 1, 2].map((i) => (
                <div key={i} style={{ ...styles.sysCard, height: 120 }}>
                  <div style={styles.kpiSkeleton} />
                </div>
              ))
            : subsystems.map((sys) => <SubsystemCard key={sys.id} sys={sys} />)}
        </div>
      </div>

      {/* ── Log des trades ───────────────────────────────────────────────── */}
      <div style={styles.panel}>
        <SectionTitle>
          Journal des Trades
        </SectionTitle>
        <TradesTable
          trades={trades}
          total={tradesTotal}
          page={tradePage}
          setPage={setTradePage}
          loading={loadingTrades}
        />
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = {
  page: {
    minHeight: "100vh",
    background: "#0f0f1a",
    color: "#e2e8f0",
    padding: "24px 20px 48px",
    fontFamily: "'Inter', system-ui, sans-serif",
  },
  pageHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    flexWrap: "wrap",
    gap: 16,
    marginBottom: 28,
  },
  pageTitle: {
    margin: 0,
    fontSize: 26,
    fontWeight: 700,
    background: "linear-gradient(135deg, #00d4ff, #7b2ff7)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  pageSubtitle: {
    margin: "4px 0 0",
    fontSize: 13,
    color: "#64748b",
  },
  rangeTabs: {
    display: "flex",
    gap: 4,
    background: "#1a1a2e",
    borderRadius: 8,
    padding: 4,
  },
  rangeTab: {
    padding: "6px 16px",
    borderRadius: 6,
    border: "none",
    background: "transparent",
    color: "#64748b",
    fontSize: 13,
    cursor: "pointer",
    transition: "all .15s",
  },
  rangeTabActive: {
    background: "#7b2ff722",
    color: "#a78bfa",
    fontWeight: 600,
  },
  kpiGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
    gap: 12,
    marginBottom: 20,
  },
  kpiCard: {
    background: "#1a1a2e",
    border: "1px solid #1e293b",
    borderRadius: 12,
    padding: "16px 18px",
    minHeight: 80,
  },
  kpiValue: {
    fontSize: 22,
    fontWeight: 700,
    fontVariantNumeric: "tabular-nums",
  },
  kpiLabel: {
    fontSize: 12,
    color: "#64748b",
    marginTop: 4,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  kpiSub: {
    fontSize: 11,
    color: "#475569",
    marginTop: 2,
  },
  kpiSkeleton: {
    height: 22,
    background: "#1e293b",
    borderRadius: 4,
    animation: "pulse 1.5s infinite",
  },
  panel: {
    background: "#12121f",
    border: "1px solid #1e293b",
    borderRadius: 14,
    padding: "20px 22px",
    marginBottom: 16,
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  sectionTitle: {
    margin: 0,
    fontSize: 15,
    fontWeight: 600,
    color: "#94a3b8",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  emptyBox: {
    padding: "32px 16px",
    textAlign: "center",
    color: "#475569",
    fontSize: 13,
    background: "#0f0f1a",
    borderRadius: 8,
    border: "1px dashed #1e293b",
  },
  tooltip: {
    background: "#1a1a2e",
    border: "1px solid #334155",
    borderRadius: 8,
    padding: "8px 12px",
    fontSize: 12,
  },
  // Heatmap
  heatTable: {
    borderCollapse: "collapse",
    width: "100%",
    fontSize: 12,
  },
  heatTh: {
    padding: "6px 8px",
    color: "#64748b",
    fontWeight: 500,
    textAlign: "center",
    borderBottom: "1px solid #1e293b",
    fontSize: 11,
    textTransform: "uppercase",
  },
  heatYear: {
    padding: "5px 10px",
    color: "#94a3b8",
    fontWeight: 600,
    textAlign: "right",
    whiteSpace: "nowrap",
  },
  heatCell: {
    padding: "5px 6px",
    textAlign: "center",
    borderRadius: 4,
    fontSize: 11,
    fontVariantNumeric: "tabular-nums",
    minWidth: 48,
    transition: "filter .1s",
    cursor: "default",
  },
  // Sous-systèmes
  sysGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
    gap: 14,
  },
  sysCard: {
    background: "#0f0f1a",
    border: "1px solid #1e293b",
    borderRadius: 12,
    padding: 16,
  },
  sysHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 12,
  },
  sysName: {
    fontSize: 14,
    fontWeight: 600,
    color: "#e2e8f0",
  },
  sysDesc: {
    fontSize: 11,
    color: "#475569",
    marginTop: 2,
    lineHeight: 1.4,
  },
  sysDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    display: "inline-block",
  },
  sysBody: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  sysRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    flexWrap: "wrap",
  },
  sysSym: {
    fontSize: 12,
    fontWeight: 600,
    color: "#cbd5e1",
    minWidth: 72,
  },
  sysTag: {
    fontSize: 11,
    padding: "2px 8px",
    borderRadius: 4,
    fontWeight: 600,
    letterSpacing: "0.03em",
  },
  sysMeta: {
    fontSize: 11,
    color: "#64748b",
  },
  sysFooter: {
    fontSize: 10,
    color: "#334155",
    marginTop: 6,
    borderTop: "1px solid #1e293b",
    paddingTop: 6,
  },
  statRow: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
    marginBottom: 8,
  },
  statPill: {
    background: "#1a1a2e",
    borderRadius: 8,
    padding: "8px 14px",
    textAlign: "center",
    minWidth: 90,
  },
  statVal: {
    fontSize: 16,
    fontWeight: 700,
    fontVariantNumeric: "tabular-nums",
  },
  statLabel: {
    fontSize: 10,
    color: "#475569",
    marginTop: 2,
    textTransform: "uppercase",
  },
  // Trades table
  tradeTable: {
    borderCollapse: "collapse",
    width: "100%",
    fontSize: 13,
  },
  tradeTh: {
    padding: "8px 12px",
    color: "#64748b",
    fontWeight: 500,
    textAlign: "left",
    borderBottom: "1px solid #1e293b",
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  tradeTd: {
    padding: "9px 12px",
    color: "#cbd5e1",
    borderBottom: "1px solid #0f0f1a",
    fontVariantNumeric: "tabular-nums",
  },
  tradeRowEven: { background: "#12121f" },
  tradeRowOdd:  { background: "#0f0f1a" },
  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: 16,
    marginTop: 16,
  },
  pageBtn: {
    padding: "6px 16px",
    borderRadius: 6,
    border: "1px solid #334155",
    background: "#1a1a2e",
    color: "#94a3b8",
    fontSize: 13,
    cursor: "pointer",
  },
};
