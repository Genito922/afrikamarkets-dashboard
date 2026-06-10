import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import LanguageSelector from "./LanguageSelector";
import ComplianceBanner from "./ComplianceBanner";

const PLAN_BADGE = {
  free:    { label: "Free",    cls: "bg-gray-700 text-gray-300" },
  starter: { label: "Starter", cls: "bg-blue-900/60 text-blue-300" },
  pro:     { label: "Pro",     cls: "bg-yellow-900/60 text-yellow-300" },
  expert:  { label: "Expert",  cls: "bg-green-900/60 text-green-300" },
};

const NAV_ITEMS = [
  { to: "/dashboard",    labelKey: "nav_dashboard",    label: "Dashboard" },
  { to: "/marche",       labelKey: "nav_marche",       label: "Marché" },
  { to: "/secteurs",     labelKey: "nav_secteurs",     label: "Secteurs" },
  { to: "/analyse",      labelKey: "nav_analyse",      label: "Analyse" },
  { to: "/portefeuille", labelKey: "nav_portfolio",    label: "Portefeuille" },
  { to: "/risques",      labelKey: "nav_warroom",      label: "War Room" },
  { to: "/sgi",           labelKey: "sgi_module1",      label: "SGI & OPCVM" },
  { to: "/international", labelKey: "nav_international", label: "Intl" },
  { to: "/crypto",        labelKey: "nav_crypto",        label: "Crypto" },
  { to: "/pricing",       labelKey: "sub_title",        label: "Abonnement" },
];

export default function Navbar() {
  const { t } = useTranslation();
  const { isAuthenticated, user, plan, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/");
  }

  const badge = PLAN_BADGE[plan] || PLAN_BADGE.free;

  return (
    <header className="sticky top-0 z-50 bg-gray-950/90 backdrop-blur border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-2 font-bold text-lg text-white hover:text-brand-400 transition-colors">
              <span className="text-2xl">🌍</span>
              <span className="hidden sm:inline">Afrika Markets</span>
              <span className="text-brand-500 hidden sm:inline">Intelligence</span>
              <span className="sm:hidden text-brand-500">AMI</span>
            </Link>
            <ComplianceBanner variant="strip" className="hidden lg:flex" />
          </div>

          {/* Nav desktop */}
          <nav className="hidden lg:flex items-center gap-0.5">
            {NAV_ITEMS.map(({ to, labelKey, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-gray-800 text-white"
                      : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                  }`
                }
              >
                {t(labelKey, label)}
              </NavLink>
            ))}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-2">
            <LanguageSelector />

            {isAuthenticated ? (
              <div className="flex items-center gap-2">
                <Link
                  to="/profile"
                  className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <span className="text-sm text-white font-medium truncate max-w-[120px]">
                    {user?.full_name?.split(" ")[0]}
                  </span>
                  <span className={`badge text-xs px-2 py-0.5 ${badge.cls}`}>
                    {badge.label}
                  </span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="btn-secondary text-sm py-2 px-3"
                >
                  {t("logout_btn", "Déconnexion")}
                </button>
              </div>
            ) : (
              <>
                <Link to="/login" className="btn-secondary text-sm py-2 px-4">
                  {t("login_btn", "Connexion")}
                </Link>
                <Link to="/register" className="btn-primary text-sm py-2 px-4 hidden sm:inline-flex">
                  {t("register_btn", "Essai gratuit")}
                </Link>
              </>
            )}

            {/* Burger mobile */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="lg:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
              aria-label="Menu"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {mobileOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                }
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="lg:hidden border-t border-gray-800 bg-gray-950 px-4 py-3 space-y-1">
          {NAV_ITEMS.map(({ to, labelKey, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? "bg-gray-800 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                }`
              }
            >
              {t(labelKey, label)}
            </NavLink>
          ))}
          {isAuthenticated && (
            <NavLink
              to="/profile"
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? "bg-gray-800 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                }`
              }
            >
              {t("profile_title", "Mon Profil")}
            </NavLink>
          )}
          {!isAuthenticated && (
            <Link
              to="/register"
              onClick={() => setMobileOpen(false)}
              className="block btn-primary text-sm text-center mt-2"
            >
              {t("register_btn", "Essai gratuit")}
            </Link>
          )}
        </div>
      )}
    </header>
  );
}
