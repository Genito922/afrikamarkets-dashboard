import { Link, NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import LanguageSelector from "./LanguageSelector";

export default function Navbar() {
  const { t } = useTranslation();

  const navItems = [
    { to: "/dashboard", label: t("nav_dashboard", "Dashboard") },
    { to: "/sgi",       label: t("sgi_module1",   "SGI & OPCVM") },
    { to: "/pricing",   label: t("sub_title",      "Abonnement") },
  ];

  return (
    <header className="sticky top-0 z-50 bg-gray-950/90 backdrop-blur border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-white hover:text-brand-400 transition-colors">
            <span className="text-2xl">🌍</span>
            <span>Afrika Markets</span>
            <span className="text-brand-500 ml-0.5">Intelligence</span>
          </Link>

          {/* Nav links */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-gray-800 text-white"
                      : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <LanguageSelector />
            <Link to="/login" className="btn-secondary text-sm py-2 px-4">
              {t("login_btn", "Connexion")}
            </Link>
            <Link to="/register" className="btn-primary text-sm py-2 px-4">
              {t("register_btn", "Essai gratuit")}
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
