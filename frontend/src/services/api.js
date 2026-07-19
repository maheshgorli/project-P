import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000";

/** Raw axios instance — use for endpoints that don't return the ApiResponse envelope */
const api = axios.create({ baseURL: BASE_URL });

/**
 * Unwrap the { success, message, data, error } envelope returned by all /api/* endpoints.
 * Throws an Error (with the server's error message) if success is false.
 *
 * Usage:
 *   const data = await apiGet("/api/disasters");
 *   // data is the inner `data` object, already unwrapped
 */
export async function apiGet(path, params = {}) {
  const res = await api.get(path, { params });
  if (!res.data.success) {
    throw new Error(res.data.error || res.data.message || "Request failed");
  }
  return res.data.data;
}

export async function apiPost(path, body = {}) {
  const res = await api.post(path, body);
  if (!res.data.success) {
    throw new Error(res.data.error || res.data.message || "Request failed");
  }
  return res.data.data;
}

export async function apiDelete(path) {
  const res = await api.delete(path);
  if (!res.data.success) {
    throw new Error(res.data.error || res.data.message || "Request failed");
  }
  return res.data.data;
}

export default api;
