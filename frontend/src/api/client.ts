// The only place that talks HTTP. Components use the hooks in ./queries.ts.

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// Empty in development (Vite proxies /api). The live demo sets the backend's origin,
// e.g. https://supportflow-api-e4i6.onrender.com, at build time.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

/** The URL to fetch: a same-origin path, or an absolute URL when the API lives elsewhere. */
export function apiUrl(path: string, query: Record<string, string | number | undefined> = {}): string {
  const url = new URL(`${API_BASE}/api/v1${path}`, window.location.origin)
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== '') url.searchParams.set(key, String(value))
  }
  return API_BASE ? url.href : url.pathname + url.search
}

let accessToken: string | null = null
let onUnauthorized: () => void = () => {}

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

type Method = 'GET' | 'POST' | 'PATCH'

export async function request<T>(
  method: Method,
  path: string,
  options: { body?: unknown; query?: Record<string, string | number | undefined> } = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  let response: Response
  try {
    response = await fetch(apiUrl(path, options.query), {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new ApiError(0, 'Sunucuya ulaşılamıyor. Backend uygulamasının çalıştığından emin olun.')
  }

  if (response.status === 401 && path !== '/auth/login') onUnauthorized()
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  return (await response.json()) as T
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) return 'Bazı alanlar geçersiz. Formu kontrol edip tekrar deneyin.'
    }
  } catch {
    // not JSON
  }
  return `İstek başarısız oldu (${response.status})`
}
