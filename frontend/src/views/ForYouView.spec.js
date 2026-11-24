import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/utils/api'
import ForYouView from './ForYouView.vue'

beforeEach(() => {
  vi.restoreAllMocks()
  setActivePinia(createPinia())
})

describe('ForYouView', () => {
  it('muestra la sección de recomendaciones', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: {
      recommendations: [], provider: null, model: null, generated_at: null,
      remaining_today: 5, daily_limit: 5, rated_books: 3, min_rated_books: 3,
    } })
    const wrapper = mount(ForYouView)
    expect(wrapper.find('[data-test="recommendations-loading"]').exists()).toBe(true)
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/ai/recommendations')
    expect(wrapper.find('[data-test="recommendations"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="recommendations-loading"]').exists()).toBe(false)
  })

  it('avisa cuando el servicio no está disponible', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new Error('503'))
    const wrapper = mount(ForYouView)
    await flushPromises()

    expect(wrapper.find('[data-test="recommendations"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="recommendations-unavailable"]').text()).toContain('no están disponibles')
  })
})
