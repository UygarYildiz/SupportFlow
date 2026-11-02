// Single entry point for backend calls. Later phases add auth headers and
// typed endpoints here instead of calling fetch() from components.

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    throw new ApiError(response.status, `Request to ${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
}

export type HealthResponse = { status: 'ok' }
export type ReadinessResponse = {
  status: 'ready' | 'not_ready'
  database: 'ok' | 'unavailable'
}
