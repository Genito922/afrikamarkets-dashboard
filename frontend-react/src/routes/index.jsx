import { Routes, Route } from "react-router-dom";
import Home from "../pages/Home";
import Dashboard from "../pages/Dashboard";
import Pricing from "../pages/Pricing";
import SGICenter from "../pages/SGICenter";
import Login from "../pages/Login";
import Register from "../pages/Register";
import NotFound from "../pages/NotFound";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/"           element={<Home />} />
      <Route path="/dashboard"  element={<Dashboard />} />
      <Route path="/pricing"    element={<Pricing />} />
      <Route path="/sgi"        element={<SGICenter />} />
      <Route path="/login"      element={<Login />} />
      <Route path="/register"   element={<Register />} />
      <Route path="*"           element={<NotFound />} />
    </Routes>
  );
}
