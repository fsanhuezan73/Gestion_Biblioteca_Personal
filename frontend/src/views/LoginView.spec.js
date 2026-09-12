import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import LoginView from './LoginView.vue'

const loginMock = vi.fn()

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    login: loginMock,
  }),
}))

describe('LoginView', () => {
  beforeEach(() => {
    loginMock.mockReset()
    loginMock.mockResolvedValue({ access_token: 'token-123' })
  })

  it('submits the login and redirects to library', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', redirect: '/login' },
        { path: '/login', component: LoginView },
        { path: '/register', component: { template: '<div>register</div>' } },
        { path: '/library', component: { template: '<div>library</div>' } },
      ],
    })
    const pushSpy = vi.spyOn(router, 'push').mockResolvedValue(true)

    const wrapper = mount(LoginView, {
      global: {
        plugins: [router],
      },
    })

    await wrapper.find('#email').setValue('user@example.com')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('form').trigger('submit')

    await wrapper.vm.$nextTick()

    expect(loginMock).toHaveBeenCalledWith('user@example.com', 'secret123')
    expect(pushSpy).toHaveBeenCalledWith('/library')
  })
})
