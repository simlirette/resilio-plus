import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createClient, setAuthToken, clearAuthToken, ApiClientError } from '../helpers'

describe('createClient', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    localStorage.clear()
  })

  it('creates client with static token', async () => {
    const payload = { id: 'ath1' }
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(payload), { status: 200 })
    )
    const client = createClient('http://localhost:8000', () => 'static-token')
    const result = await client.request('/athletes/ath1')
    expect(result).toEqual(payload)
  })

  it('adds Authorization header from getToken callback', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 })
    )
    const client = createClient('http://localhost:8000', () => 'my-token')
    await client.request('/test')
    const [, options] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect((options.headers as Record<string, string>)['Authorization']).toBe('Bearer my-token')
  })

  it('does not add Authorization header when getToken returns null', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 })
    )
    const client = createClient('http://localhost:8000', () => null)
    await client.request('/test')
    const [, options] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect((options.headers as Record<string, string>)['Authorization']).toBeUndefined()
  })

  it('throws ApiClientError with status on non-ok response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 })
    )
    const client = createClient('http://localhost:8000', () => null)
    await expect(client.request('/missing')).rejects.toBeInstanceOf(ApiClientError)
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 })
    )
    await expect(client.request('/missing')).rejects.toMatchObject({ status: 404 })
  })
})

describe('clearAuthToken', () => {
  it('removes token from localStorage', () => {
    localStorage.setItem('resilio_token', 'abc123')
    clearAuthToken()
    expect(localStorage.getItem('resilio_token')).toBeNull()
  })
})

describe('setAuthToken', () => {
  it('stores token in localStorage', () => {
    setAuthToken('tok-xyz')
    expect(localStorage.getItem('resilio_token')).toBe('tok-xyz')
  })
})
