import { Routes, Route } from "react-router-dom";

// Public
import Home         from "../pages/Home";
import Login        from "../pages/Login";
import Register     from "../pages/Register";
import Pricing      from "../pages/Pricing";
import NotFound     from "../pages/NotFound";

// App — pages migrées (Sprint 1)
import Dashboard    from "../pages/Dashboard";
import Marche       from "../pages/Marche";
import Profile      from "../pages/Profile";
import SGICenter    from "../pages/SGICenter";

// App — pages migrées (Sprint 2)
import Secteurs     from "../pages/Secteurs";
import TitreDetail  from "../pages/TitreDetail";
import Analyse      from "../pages/Analyse";
import Portefeuille from "../pages/Portefeuille";
import Risques      from "../pages/Risques";

// Placeholder pour pages restantes (international markets)
const WIP = ({ title }) => (
  <div className="py-20 text-center">
    <p className="text-4xl mb-4">🚧</p>
    <h2 className="text-2xl font-bold text-white">{title}</h2>
    <p className="text-gray-400 mt-2">Page en cours de migration depuis Streamlit</p>
  </div>
);

export default function AppRoutes() {
  return (
    <Routes>
      {/* ── Public ───────────────────────────────────────── */}
      <Route path="/"           element={<Home />} />
      <Route path="/login"      element={<Login />} />
      <Route path="/register"   element={<Register />} />
      <Route path="/pricing"    element={<Pricing />} />

      {/* ── App ──────────────────────────────────────────── */}
      <Route path="/dashboard"      element={<Dashboard />} />
      <Route path="/marche"         element={<Marche />} />
      <Route path="/secteurs"       element={<Secteurs />} />
      <Route path="/titres/:symbole" element={<TitreDetail />} />
      <Route path="/titres"         element={<TitreDetail />} />
      <Route path="/analyse"        element={<Analyse />} />
      <Route path="/portefeuille"   element={<Portefeuille />} />
      <Route path="/risques"        element={<Risques />} />
      <Route path="/sgi"            element={<SGICenter />} />
      <Route path="/profile"        element={<Profile />} />

      {/* ── En attente ───────────────────────────────────── */}
      <Route path="/international"  element={<WIP title="Marchés Internationaux" />} />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
