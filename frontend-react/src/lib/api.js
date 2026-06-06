/**
 * API client — Afrika Markets Intelligence
 * Base URL : VITE_API_URL (env) ou même origine en production
 */
const BASE = import.meta.env.VITE_API_URL || "";

function authHeaders() {
  const token = localStorage.getItem("ami_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch(path, opts = {}) {
  const { auth = false, body, method = "GET", ...rest } = opts;

  const headers = {
    "Content-Type": "application/json",
    ...(auth ? authHeaders() : {}),
  };

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    ...rest,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const err = new Error(data.detail || res.statusText || "Erreur API");
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// Raccourcis
export const apiGet  = (path, auth = false) => apiFetch(path, { auth });
export const apiPost = (path, body, auth = false) =>
  apiFetch(path, { method: "POST", body, auth });
