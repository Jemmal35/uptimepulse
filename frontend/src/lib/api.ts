import axios from 'axios'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

export interface User { id: string; email: string; username: string }

export interface Site {
  id: string
  name: string
  url: string
  check_interval: number
  expected_status_code: number
  timeout_seconds: number
  is_active: boolean
  created_at: string
  last_checked_at: string | null
  latest_is_up: boolean | null
  latest_response_ms: number | null
  latest_status_code: number | null
}

export interface SitesResponse {
  total_sites: number
  total_active_sites: number
  total_inactive_sites: number
  sites: Site[]
}

export interface Incident {
  id: string
  site_id: string
  site_name: string
  site_url: string
  detected_at: string
  status_code: number | null
  error_message: string | null
  summary: string
  possible_cause: string
  confidence_score: number | null
  recommended_actions: string[]
  is_ai_generated: boolean
  created_at: string
}

// Tokens live in localStorage for simplicity. For production, prefer httpOnly cookies.
export const tokens = {
  access: () => localStorage.getItem('access'),
  refresh: () => localStorage.getItem('refresh'),
  set: (access: string, refresh?: string) => {
    localStorage.setItem('access', access)
    if (refresh) localStorage.setItem('refresh', refresh)
  },
  clear: () => {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
  },
}

const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use((config) => {
  const token = tokens.access()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// One shared refresh request, even if several calls hit a 401 at once.
let refreshing: Promise<string> | null = null

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const canRefresh =
      error.response?.status === 401 && !original._retry && tokens.refresh() && !original.url?.includes('auth/token')
    if (!canRefresh) return Promise.reject(error)

    original._retry = true
    refreshing ??= axios
      .post(`${API_URL}/auth/token/refresh/`, { refresh: tokens.refresh() })
      .then((r) => {
        tokens.set(r.data.access, r.data.refresh)
        return r.data.access as string
      })
      .finally(() => { refreshing = null })

    try {
      original.headers.Authorization = `Bearer ${await refreshing}`
      return api(original)
    } catch {
      tokens.clear()
      window.location.href = '/login'
      return Promise.reject(error)
    }
  },
)

export function errorText(err: unknown): string {
  const data = (err as { response?: { data?: unknown } })?.response?.data
  if (data && typeof data === 'object') return Object.values(data).flat().join(' ')
  return 'Could not reach the server. Check that the API is running.'
}

export default api
