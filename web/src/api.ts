const API = import.meta.env.VITE_API_BASE || "";

function headers(json = true): HeadersInit {
  const token = localStorage.getItem("abhaysetu.access");
  const h: Record<string, string> = {};
  if (json) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, { ...init, headers: { ...headers(), ...(init?.headers || {}) } });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const AuthApi = {
  login: (email: string, password: string, extra: object) =>
    api("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password, ...extra }) }),
  register: (body: object) => api("/api/v1/auth/register", { method: "POST", body: JSON.stringify(body) }),
  me: () => api("/api/v1/auth/me"),
};
