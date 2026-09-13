/**
 * Subscriptions API — Afrika Markets Intelligence
 * Utilise apiFetch (fetch natif + Bearer ami_token)
 */
import { apiGet, apiPost } from "../lib/api";

export const subscriptionsApi = {
  getMe:     ()     => apiGet("/subscriptions/me", true),
  cancel:    ()     => apiPost("/subscriptions/cancel", {}, true),
  resume:    ()     => apiPost("/subscriptions/resume", {}, true),
  downgrade: (plan) => apiPost(`/subscriptions/downgrade/${plan}`, {}, true),
  upgrade:   (plan) => apiPost(`/subscriptions/upgrade/${plan}`, {}, true),
};
