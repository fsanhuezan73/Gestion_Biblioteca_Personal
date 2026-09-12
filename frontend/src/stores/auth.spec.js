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
})
