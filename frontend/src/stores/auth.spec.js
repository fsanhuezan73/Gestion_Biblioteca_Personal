import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import api from '@/utils/api'
import { useAuthStore } from '@/stores/auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('logs in and stores the token in localStorage', async () => {
    const postMock = vi.spyOn(api, 'post').mockResolvedValue({
      data: { access_token: 'token-123' },
    })

    const store = useAuthStore()
    const result = await store.login('user@example.com', 'secret123')

    expect(postMock).toHaveBeenCalledWith('/auth/login', {
      email: 'user@example.com',
      password: 'secret123',
    })
    expect(result.access_token).toBe('token-123')
    expect(store.token).toBe('token-123')
    expect(localStorage.getItem('auth_token')).toBe('token-123')
    expect(store.isAuthenticated).toBe(true)
  })

  it('logs out and clears session data', () => {
    localStorage.setItem('auth_token', 'token-456')
    localStorage.setItem('auth_user', JSON.stringify({ email: 'user@example.com' }))

    const store = useAuthStore()
    store.token = 'token-456'
    store.user = { email: 'user@example.com' }

    store.logout()

    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('auth_user')).toBeNull()
  })

  it('requests a reset without storing or exposing a token', async () => {
    const postMock = vi.spyOn(api, 'post').mockResolvedValue({ data: { detail: 'Solicitud recibida' } })
    const store = useAuthStore()
    const result = await store.requestPasswordReset('user@example.com')

    expect(postMock).toHaveBeenCalledWith('/auth/password-reset/request', { email: 'user@example.com' })
    expect(result.detail).toBe('Solicitud recibida')
    expect(store.token).toBeNull()
  })

  it('clears the previous session after a successful reset', async () => {
    const postMock = vi.spyOn(api, 'post').mockResolvedValue({ data: { detail: 'Actualizada' } })
    const store = useAuthStore()
    store.token = 'old-token'
    localStorage.setItem('auth_token', 'old-token')

    await store.confirmPasswordReset('reset-secret', 'new-password')

    expect(postMock).toHaveBeenCalledWith('/auth/password-reset/confirm', {
      token: 'reset-secret', new_password: 'new-password',
    })
    expect(store.token).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
  })

  it('clears the session after a successful account password change', async () => {
    const postMock = vi.spyOn(api, 'post').mockResolvedValue({ data: { detail: 'Actualizada' } })
    const store = useAuthStore()
    store.token = 'old-token'
    localStorage.setItem('auth_token', 'old-token')

    await store.changePassword('current-password', 'new-password')

    expect(postMock).toHaveBeenCalledWith('/auth/password/change', {
      current_password: 'current-password', new_password: 'new-password',
    })
    expect(store.token).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
  })
})
