import { afterEach, describe, expect, it, vi } from 'vitest'

describe('apiUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('uses same-origin paths when no API base is configured (dev proxy)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    const { apiUrl } = await import('./client')

    expect(apiUrl('/tickets', { status: 'new', page: undefined })).toBe('/api/v1/tickets?status=new')
  })

  it('calls the configured backend origin in the live demo', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://supportflow-api.onrender.com/')
    const { apiUrl } = await import('./client')

    expect(apiUrl('/runs/9')).toBe('https://supportflow-api.onrender.com/api/v1/runs/9')
  })
})
