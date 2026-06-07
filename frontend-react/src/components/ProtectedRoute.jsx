/**
 * ProtectedRoute — garde d'accès par authentification et plan
 *
 * Usage :
 *   <ProtectedRoute>                        → authentification requise
 *   <ProtectedRoute minPlan="pro">          → plan pro ou supérieur requis
 */
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const PLAN_ORDER = { free: 0, starter: 1, pro: 2, expert: 3 };

export default function ProtectedRoute({ children, minPlan }) {
  const { isAuthenticated, plan } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/overview" replace />;
  }

  if (minPlan) {
    const userLevel = PLAN_ORDER[plan]    ?? 0;
    const reqLevel  = PLAN_ORDER[minPlan] ?? 0;
    if (userLevel < reqLevel) {
      return <Navigate to="/pricing" replace />;
    }
  }

  return children;
}
