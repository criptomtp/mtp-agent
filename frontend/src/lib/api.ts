const BASE = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  getStats: () => request<{ total_runs: number; total_leads: number; active_runs: number }>("/api/dashboard/stats"),

  runAgents: (niche: string, count: number) =>
    request<{ status: string }>("/api/dashboard/run", {
      method: "POST",
      body: JSON.stringify({ niche, count }),
    }),

  getLeads: (params?: { status?: string; run_id?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.run_id) q.set("run_id", params.run_id);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    return request<any[]>(`/api/leads/?${q}`);
  },

  getLead: (id: string) => request<any>(`/api/leads/${id}`),

  getLeadFiles: (id: string) => request<any[]>(`/api/leads/${id}/files`),

  getRuns: (limit = 50, offset = 0) =>
    request<any[]>(`/api/runs/?limit=${limit}&offset=${offset}`),

  getRun: (id: string) => request<any>(`/api/runs/${id}`),

  getApiKeys: () => request<any[]>("/api/settings/api-keys"),

  saveApiKey: (service_name: string, key_value: string) =>
    request<any>("/api/settings/api-keys", {
      method: "POST",
      body: JSON.stringify({ service_name, key_value }),
    }),

  testApiKey: (service_name: string, key_value: string = "") =>
    request<{ valid: boolean; error?: string }>("/api/settings/api-keys/test", {
      method: "POST",
      body: JSON.stringify({ service_name, key_value }),
    }),
};
