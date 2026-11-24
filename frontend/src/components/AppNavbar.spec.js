import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '@/stores/auth'
import AppNavbar from './AppNavbar.vue'

const Stub = { template: '<div />' }

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'Login', component: Stub },
      { path: '/library', name: 'Library', component: Stub },
      { path: '/for-you', name: 'ForYou', component: Stub },
      { path: '/stats', name: 'Stats', component: Stub },
      { path: '/account', name: 'Account', component: Stub },
      { path: '/books/add', name: 'AddBook', component: Stub },
    ],
  })
}

async function mountAt(path) {
  const router = makeRouter()
  router.push(path)
  await router.isReady()
  const wrapper = mount(AppNavbar, { global: { plugins: [router] }, attachTo: document.body })
  return { wrapper, router }
}

beforeEach(() => {
  setActivePinia(createPinia())
  document.body.innerHTML = ''
})

describe('AppNavbar', () => {
  it('muestra el menú cerrado y «Cerrar sesión» fuera de él', async () => {
    const { wrapper } = await mountAt('/library')
    expect(wrapper.find('[data-test="app-menu"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="menu-toggle"]').attributes('aria-expanded')).toBe('false')
    expect(wrapper.get('[data-test="logout"]').text()).toBe('Cerrar sesión')
  })

  it('abre el menú con las opciones en orden y marca la página actual', async () => {
    const { wrapper } = await mountAt('/stats')
    await wrapper.get('[data-test="menu-toggle"]').trigger('click')

    const menu = wrapper.get('[data-test="app-menu"]')
    const labels = menu.findAll('a').map((a) => a.findAll('span').map((s) => s.text()).join(' '))
    expect(labels).toEqual([
      '📚 Mi colección', '✨ Para ti', '📊 Estadísticas', '📷 Escanear libro', '➕ Añadir libro', '👤 Mi cuenta',
    ])
    expect(labels.some((label) => label.includes('Cerrar sesión'))).toBe(false)
    expect(menu.get('[data-test="menu-stats"]').attributes('aria-current')).toBe('page')
    expect(menu.get('[data-test="menu-scan"]').attributes('href')).toBe('/books/add?scan=1')
  })

  it('distingue «Escanear libro» de «Añadir libro» por la consulta scan', async () => {
    const { wrapper } = await mountAt('/books/add?scan=1')
    await wrapper.get('[data-test="menu-toggle"]').trigger('click')
    expect(wrapper.get('[data-test="menu-scan"]').classes()).toContain('active')
    expect(wrapper.get('[data-test="menu-add"]').classes()).not.toContain('active')
  })

  it('se cierra al navegar, con Escape y al hacer clic fuera', async () => {
    const { wrapper, router } = await mountAt('/library')
    const toggle = wrapper.get('[data-test="menu-toggle"]')

    await toggle.trigger('click')
    await router.push('/for-you')
    await flushPromises()
    expect(wrapper.find('[data-test="app-menu"]').exists()).toBe(false)

    await toggle.trigger('click')
    document.dispatchEvent(new globalThis.KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(wrapper.find('[data-test="app-menu"]').exists()).toBe(false)

    await toggle.trigger('click')
    document.body.dispatchEvent(new globalThis.Event('pointerdown', { bubbles: true }))
    await flushPromises()
    expect(wrapper.find('[data-test="app-menu"]').exists()).toBe(false)
  })

  it('cierra la sesión y vuelve al login', async () => {
    localStorage.setItem('auth_token', 'tok')
    setActivePinia(createPinia())
    const { wrapper, router } = await mountAt('/library')
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(true)

    await wrapper.get('[data-test="logout"]').trigger('click')
    await flushPromises()
    expect(auth.isAuthenticated).toBe(false)
    expect(router.currentRoute.value.name).toBe('Login')
  })
})
