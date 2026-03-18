// ═══════════════════════════════════════════════════════
// FinAI – Centralized API Service Layer (Fixed Version)
// ═══════════════════════════════════════════════════════
import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios"

// ──────────────────────────────────────────────────────
// BASE URL
// ──────────────────────────────────────────────────────
export const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1"

// ──────────────────────────────────────────────────────
// AXIOS INSTANCE
// ──────────────────────────────────────────────────────
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000, // increased from 30s → 60s
  headers: {
    "Content-Type": "application/json",
  },
})

// ──────────────────────────────────────────────────────
// REQUEST INTERCEPTOR (JWT)
// ──────────────────────────────────────────────────────
api.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  if (typeof window !== "undefined") {
    const tok = localStorage.getItem("finai_token")

    if (tok) {
      cfg.headers.Authorization = `Bearer ${tok}`
    }
  }

  return cfg
})

// ──────────────────────────────────────────────────────
// RESPONSE INTERCEPTOR
// ──────────────────────────────────────────────────────
api.interceptors.response.use(
  (r: AxiosResponse) => r,
  (e: AxiosError) => {
    if (e.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("finai_token")
      localStorage.removeItem("finai_user")

      window.location.href = "/auth/login"
    }

    return Promise.reject(e)
  }
)

// ──────────────────────────────────────────────────────
// ERROR HELPER
// ──────────────────────────────────────────────────────
export function apiError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as any
    return d?.detail ?? d?.message ?? e.message
  }

  return "Unexpected error"
}

// ══════════════════════════════════════════════════════
// AUTH
// ══════════════════════════════════════════════════════
export const authApi = {
  login: async (email: string, password: string) => {
  const { data } = await api.post("/auth/login", {
    email,
    password,
  })

  return data
},
  logout: () => {
    localStorage.removeItem("finai_token")
    localStorage.removeItem("finai_user")
  },
}

// ══════════════════════════════════════════════════════
// TRANSACTIONS
// ══════════════════════════════════════════════════════
export const txApi = {
  list: async (p: Record<string, unknown> = {}) =>
    (await api.get("/transactions", { params: p })).data,

  create: async (body: Record<string, unknown>) =>
    (await api.post("/transactions", body)).data,

  delete: async (id: string) =>
    void (await api.delete(`/transactions/${id}`)),

  categories: async () =>
    (await api.get("/transactions/categories")).data,

  monthly: async () =>
    (await api.get("/transactions/monthly-summary")).data,

  categoryBreakdown: async (months = 1) =>
    (await api.get("/transactions/category-breakdown", {
      params: { months },
    })).data,
}

// ══════════════════════════════════════════════════════
// RECEIPTS
// ══════════════════════════════════════════════════════
export const receiptsApi = {
  upload: async (file: File, opts: { force_engine?: string } = {}) => {
    const form = new FormData()
    form.append("file", file)

    if (opts.force_engine) {
      form.append("force_engine", opts.force_engine)
    }

    return (
      await api.post("/receipts/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000, // OCR may take longer
      })
    ).data
  },

  history: async (page = 1, limit = 20) =>
    (await api.get("/receipts/history", { params: { page, limit } })).data,
}

// ══════════════════════════════════════════════════════
// GOALS
// ══════════════════════════════════════════════════════
export const goalsApi = {
  list: async (status?: string) =>
    (await api.get("/goals", { params: status ? { status } : {} })).data,

  create: async (body: Record<string, unknown>) =>
    (await api.post("/goals", body)).data,

  get: async (id: string) =>
    (await api.get(`/goals/${id}`)).data,

  update: async (id: string, body: Record<string, unknown>) =>
    (await api.patch(`/goals/${id}`, body)).data,

  delete: async (id: string) =>
    void (await api.delete(`/goals/${id}`)),

  progress: async (id: string) =>
    (await api.get(`/goals/${id}/progress`)).data,

  dashboard: async () =>
    (await api.get("/goals/dashboard")).data,

  deposit: async (id: string, amount: number) =>
    (await api.post(`/goals/${id}/deposit`, { amount })).data,

  categories: async () =>
    (await api.get("/goals/categories")).data,
}

// ══════════════════════════════════════════════════════
// HEALTH SCORE
// ══════════════════════════════════════════════════════
export const healthApi = {
  score: async () => (await api.get("/health-score")).data,
}

// ══════════════════════════════════════════════════════
// FORECAST
// ══════════════════════════════════════════════════════
export const forecastApi = {
  expenses: async () => (await api.get("/forecast/expenses")).data,
  stats: async () => (await api.get("/forecast/dashboard-stats")).data,
}

// ══════════════════════════════════════════════════════
// BUDGET
// ══════════════════════════════════════════════════════
export const budgetApi = {
  optimization: async () =>
    (await api.get("/budget/optimization")).data,
}

// ══════════════════════════════════════════════════════
// FRAUD / ANOMALY
// ══════════════════════════════════════════════════════
export const fraudApi = {
  alerts: async () => (await api.get("/fraud/alerts")).data,

  resolve: async (id: string) =>
    void (await api.post(`/fraud/alerts/${id}/resolve`)),
}

// ══════════════════════════════════════════════════════
// VOICE (IMPORTANT FIX)
// ══════════════════════════════════════════════════════
export const voiceApi = {
  transcribe: async (audio: Blob) => {
    const form = new FormData()

    form.append("audio", audio, "recording.webm")

    return (
      await api.post("/voice/transcribe", form, {
        headers: {
          "Content-Type": "multipart/form-data",
        },

        timeout: 180000, // 3 minutes for Whisper
      })
    ).data
  },
}

// ──────────────────────────────────────────────────────
export default api