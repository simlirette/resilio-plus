// frontend/src/lib/__tests__/api.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api, ApiError } from '../api'

describe('api.login', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    localStorage.clear()
  })

  it('returns TokenResponse on 200', async () => {
    const payload = { access_token: 'tok123', token_type: 'bearer', athlete_id: 'ath1' }
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } })
    )
    const result = await api.login('a@b.com', 'pass1234')
    expect(result.access_token).toBe('tok123')
    expect(result.athlete_id).toBe('ath1')
  })

  it('throws ApiError(401) on invalid credentials', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Invalid credentials' }), { status: 401 })
    )
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Invalid credentials' }), { status: 401 })
    )
    await expect(api.login('a@b.com', 'wrong')).rejects.toBeInstanceOf(ApiError)
    await expect(api.login('a@b.com', 'wrong')).rejects.toMatchObject({ status: 401 })
  })
})

describe('api.getWeekStatus', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()))

  it('adds Authorization header when token is in localStorage', async () => {
    localStorage.setItem('token', 'mytoken')
    const payload = { week_number: 1, plan: {}, planned_hours: 8, actual_hours: 5, completion_pct: 62.5, acwr: 1.1 }
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(payload), { status: 200 })
    )
    await api.getWeekStatus('ath1')
    const [, options] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect((options.headers as Record<string, string>)['Authorization']).toBe('Bearer mytoken')
  })

  it('throws ApiError(401) when server returns 401', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response('', { status: 401 }))
    await expect(api.getWeekStatus('ath1')).rejects.toMatchObject({ status: 401 })
  })
})
