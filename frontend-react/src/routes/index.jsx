import { Routes, Route } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";

// Public
import Home         from "../pages/Home";
import Login        from "../pages/Login";
import Register     from "../pages/Register";
import Overview     from "../pages/Overview";
import Pricing      from "../pages/Pricing";
import NotFound     from "../pages/NotFound";

// App — authentification requise
import Dashboard    from "../pages/Dashboard";
import Marche       from "../pages/Marche";
import Profile      from "../pages/Profile";

// App — plan Starter+
import Secteurs     from "../pages/Secteurs";
import TitreDetail  from "../pages/TitreDetail";
import Analyse      from "../pages/Analyse";
import Portefeuille from "../pages/Portefeuille";

// App — plan Pro+
import Risques      from "../pages/Risques";
import SGICenter    from "../pages/SGICenter";

// App — plan Expert
import MarchesInternationaux from "../pages/MarchesInternationaux";

export default function AppRoutes() {
  return (
    <Routes>
      {/* ── Public ───────────────────────────────────────── */}
      <Route path="/"         element={<Home />} />
      <Route path="/overview" element={<Overview />} />
      <Route path="/login"    element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/pricing"  element={<Pricing />} />

      {/* ── Authentification requise (tout plan) ────────── */}
      <Route path="/dashboard" element={
        <ProtectedRoute><Dashboard /></ProtectedRoute>
      } />
      <Route path="/marche" element={
        <ProtectedRoute><Marche /></ProtectedRoute>
      } />
      <Route path="/profile" element={
        <ProtectedRoute><Profile /></ProtectedRoute>
      } />

      {/* ── Plan Starter+ ────────────────────────────────── */}
      <Route path="/secteurs" element={
        <ProtectedRoute minPlan="starter"><Secteurs /></ProtectedRoute>
      } />
      <Route path="/titres/:symbole" element={
        <ProtectedRoute minPlan="starter"><TitreDetail /></ProtectedRoute>
      } />
      <Route path="/titres" element={
        <ProtectedRoute minPlan="starter"><TitreDetail /></ProtectedRoute>
      } />
      <Route path="/analyse" element={
        <ProtectedRoute minPlan="starter"><Analyse /></ProtectedRoute>
      } />
      <Route path="/portefeuille" element={
        <ProtectedRoute minPlan="starter"><Portefeuille /></ProtectedRoute>
      } />

      {/* ── Plan Pro+ ────────────────────────────────────── */}
      <Route path="/risques" element={
        <ProtectedRoute minPlan="pro"><Risques /></ProtectedRoute>
      } />
      <Route path="/sgi" element={
        <ProtectedRoute minPlan="pro"><SGICenter /></ProtectedRoute>
      } />

      {/* ── Plan Expert ──────────────────────────────────── */}
      <Route path="/international" element={
        <ProtectedRoute minPlan="expert"><MarchesInternationaux /></ProtectedRoute>
      } />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
