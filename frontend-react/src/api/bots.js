/**
 * API client — Bots & Credentials
 */
import { apiFetch, apiGet, apiPost } from "../lib/api";

export const credentialsApi = {
  list:   ()           => apiGet("/credentials", true),
  save:   (body)       => apiPost("/credentials", body, true),
  delete: (id)         => apiFetch(`/credentials/${id}`, { method: "DELETE", auth: true }),
};

export const botsApi = {
  list:         ()        => apiGet("/bots", true),
  get:          (id)      => apiGet(`/bots/${id}`, true),
  create:       (body)    => apiPost("/bots", body, true),
  update:       (id, body) => apiFetch(`/bots/${id}`, { method: "PATCH", body, auth: true }),
  delete:       (id)      => apiFetch(`/bots/${id}`, { method: "DELETE", auth: true }),
  confirmLive:  (id)      => apiPost(`/bots/${id}/confirm-live`, { confirmed: true }, true),
  start:        (id)      => apiPost(`/bots/${id}/start`, {}, true),
  stop:         (id)      => apiPost(`/bots/${id}/stop`, {}, true),
};
