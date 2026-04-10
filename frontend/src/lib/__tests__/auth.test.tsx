// frontend/src/lib/__tests__/auth.test.tsx
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '../auth'

function Probe() {
  const { token, athleteId, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="token">{token ?? 'none'}</span>
      <span data-testid="athlete">{athleteId ?? 'none'}</span>
      <button onClick={() => login('tok', 'ath1')}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => localStorage.clear())

  it('starts with null token when localStorage is empty', () => {
    render(<AuthProvider><Probe /></AuthProvider>)
    expect(screen.getByTestId('token').textContent).toBe('none')
  })

  it('restores session from localStorage on mount', async () => {
    localStorage.setItem('token', 'saved')
    localStorage.setItem('athlete_id', 'ath99')
    render(<AuthProvider><Probe /></AuthProvider>)
    // useEffect fires after render — wait for it
    await act(async () => {})
    expect(screen.getByTestId('token').textContent).toBe('saved')
    expect(screen.getByTestId('athlete').textContent).toBe('ath99')
  })

  it('stores token in localStorage after login()', () => {
    render(<AuthProvider><Probe /></AuthProvider>)
    act(() => { screen.getByText('login').click() })
    expect(localStorage.getItem('token')).toBe('tok')
    expect(localStorage.getItem('athlete_id')).toBe('ath1')
    expect(screen.getByTestId('token').textContent).toBe('tok')
  })

  it('clears localStorage after logout()', () => {
    localStorage.setItem('token', 'tok')
    localStorage.setItem('athlete_id', 'ath1')
    render(<AuthProvider><Probe /></AuthProvider>)
    act(() => { screen.getByText('logout').click() })
    expect(localStorage.getItem('token')).toBeNull()
    expect(screen.getByTestId('token').textContent).toBe('none')
  })
})
