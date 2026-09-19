import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/utils/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || null)
  const user = ref(JSON.parse(localStorage.getItem('auth_user') || 'null'))

  const isAuthenticated = computed(() => !!token.value)

  async function register(email, password) {
    const { data } = await api.post('/auth/register', { email, password })
    return data
  }

  async function login(email, password) {
    const { data } = await api.post('/auth/login', { email, password })
    token.value = data.access_token
    localStorage.setItem('auth_token', data.access_token)
    return data
  }

  async function requestPasswordReset(email) {
    const { data } = await api.post('/auth/password-reset/request', { email })
    return data
  }

  async function confirmPasswordReset(resetToken, newPassword) {
    const { data } = await api.post('/auth/password-reset/confirm', {
      token: resetToken,
      new_password: newPassword,
    })
    logout()
    return data
  }

  async function changePassword(currentPassword, newPassword) {
    const { data } = await api.post('/auth/password/change', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    logout()
    return data
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
  }

  return {
    token, user, isAuthenticated, register, login, logout,
    requestPasswordReset, confirmPasswordReset, changePassword,
  }
})
