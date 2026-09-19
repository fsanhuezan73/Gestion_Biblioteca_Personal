import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ForgotPasswordView from './ForgotPasswordView.vue'
import ResetPasswordView from './ResetPasswordView.vue'
import AccountView from './AccountView.vue'

const requestMock = vi.fn()
const confirmMock = vi.fn()
const changeMock = vi.fn()

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    requestPasswordReset: requestMock,
    confirmPasswordReset: confirmMock,
    changePassword: changeMock,
  }),
}))

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'Login', component: { template: '<div>login</div>' } },
      { path: '/forgot-password', name: 'ForgotPassword', component: ForgotPasswordView },
      { path: '/reset-password', name: 'ResetPassword', component: ResetPasswordView },
      { path: '/account', name: 'Account', component: AccountView },
      { path: '/library', name: 'Library', component: { template: '<div>library</div>' } },
    ],
  })
}

describe('password views', () => {
  beforeEach(() => {
    requestMock.mockReset().mockResolvedValue({})
    confirmMock.mockReset().mockResolvedValue({})
    changeMock.mockReset().mockResolvedValue({})
  })

  it('requests a link with a generic success message', async () => {
    const router = makeRouter()
    await router.push('/forgot-password')
    const wrapper = mount(ForgotPasswordView, { global: { plugins: [router] } })
    await wrapper.find('#email').setValue('user@example.com')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(requestMock).toHaveBeenCalledWith('user@example.com')
    expect(wrapper.find('[role="status"]').text()).toContain('Si el correo está registrado')
  })

  it('removes the secret from the URL and confirms the password', async () => {
    const router = makeRouter()
    await router.push('/reset-password?token=reset-secret')
    const wrapper = mount(ResetPasswordView, { global: { plugins: [router] } })
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/reset-password')

    await wrapper.find('#newPassword').setValue('new-password')
    await wrapper.find('#confirmPassword').setValue('new-password')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalledWith('reset-secret', 'new-password')
    expect(wrapper.find('[role="status"]').text()).toContain('sesiones anteriores')
  })

  it('does not submit without a token', async () => {
    const router = makeRouter()
    await router.push('/reset-password')
    const wrapper = mount(ResetPasswordView, { global: { plugins: [router] } })
    expect(wrapper.text()).toContain('Este enlace no es válido')
    expect(confirmMock).not.toHaveBeenCalled()
  })

  it('changes the password from the account and returns to login', async () => {
    const router = makeRouter()
    await router.push('/account')
    const wrapper = mount(AccountView, { global: { plugins: [router] } })
    await wrapper.find('#currentPassword').setValue('current-password')
    await wrapper.find('#newPassword').setValue('new-password')
    await wrapper.find('#confirmPassword').setValue('new-password')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(changeMock).toHaveBeenCalledWith('current-password', 'new-password')
    expect(router.currentRoute.value.name).toBe('Login')
  })

  it('rejects nonmatching confirmation before calling the API', async () => {
    const router = makeRouter()
    await router.push('/account')
    const wrapper = mount(AccountView, { global: { plugins: [router] } })
    await wrapper.find('#currentPassword').setValue('current-password')
    await wrapper.find('#newPassword').setValue('new-password')
    await wrapper.find('#confirmPassword').setValue('other-password')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('Las contraseñas no coinciden')
    expect(changeMock).not.toHaveBeenCalled()
  })
})
