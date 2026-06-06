import { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

function readUser() {
  try {
    const u = localStorage.getItem("ami_user");
    return u ? JSON.parse(u) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("ami_token"));
  const [user,  setUser]  = useState(readUser);

  function login(tokenVal, userData) {
    localStorage.setItem("ami_token", tokenVal);
    localStorage.setItem("ami_user", JSON.stringify(userData));
    setToken(tokenVal);
    setUser(userData);
  }

  function logout() {
    localStorage.removeItem("ami_token");
    localStorage.removeItem("ami_user");
    setToken(null);
    setUser(null);
  }

  const isAuthenticated = !!token && !!user;
  const plan = user?.plan || "free";

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, plan, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
