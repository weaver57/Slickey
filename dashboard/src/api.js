const API = import.meta.env.VITE_DASHBOARD_API || "http://localhost:8000";
let csrfToken = "";

export function setCsrfToken(t) {
  csrfToken = t;
}

export async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers["X-CSRF-Token"] = csrfToken;
  }
  const r = await fetch(`${API}${path}`, {
    credentials: "include",
    headers,
    ...options,
  });
  if (!r.ok)
    throw new Error(
      (await r.json().catch(() => ({}))).detail || "Something went wrong.",
    );
  return r.status === 204 ? null : r.json();
}
