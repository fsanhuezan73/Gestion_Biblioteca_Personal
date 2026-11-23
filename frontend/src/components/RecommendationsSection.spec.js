import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/utils/api'
import RecommendationsSection from './RecommendationsSection.vue'

const book = (overrides = {}) => ({
  title: 'Cien años de soledad', authors: ['Gabriel García Márquez'], year: 1967,
  reason: 'Te gustó Pedro Páramo', synopsis: 'La historia de los Buendía.', cover_url: null,
  isbn: '9788497592208', in_library: false, ...overrides,
})

const result = (overrides = {}) => ({
  recommendations: [book(), book({ title: 'Aura', authors: ['Carlos Fuentes'], isbn: null, synopsis: null, in_library: true })],
  provider: 'gemini', model: 'gemini-3.5-flash-lite', generated_at: '2026-11-23T15:00:00Z',
  remaining_today: 4, daily_limit: 5, rated_books: 3, min_rated_books: 3, ...overrides,
})

async function mountWith(data) {
  vi.spyOn(api, 'get').mockResolvedValue({ data })
  const wrapper = mount(RecommendationsSection)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.restoreAllMocks()
  setActivePinia(createPinia())
})

describe('RecommendationsSection', () => {
  it('muestra las tarjetas con motivo, sinopsis y etiqueta de IA', async () => {
    const wrapper = await mountWith(result())
    expect(wrapper.find('[data-test="ai-label"]').text()).toBe('Generado por IA')
    const cards = wrapper.findAll('[data-test="recommendation"]')
    expect(cards).toHaveLength(2)
    expect(cards[0].find('[data-test="reason"]').text()).toContain('Te gustó Pedro Páramo')
    expect(cards[0].find('[data-test="synopsis"]').text()).toContain('Buendía')
    // Sin sinopsis: solo el motivo.
    expect(cards[1].find('[data-test="synopsis"]').exists()).toBe(false)
    expect(cards[1].find('[data-test="in-library"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="remaining"]').text()).toBe('Te quedan 4 de 5 hoy')
    expect(wrapper.find('[data-test="ai-notice"]').text()).toContain('nunca tus notas')
  })

  it('pide más libros valorados y deshabilita el botón', async () => {
    const wrapper = await mountWith(result({ recommendations: [], rated_books: 1 }))
    expect(wrapper.find('[data-test="not-enough"]').text()).toContain('al menos 3')
    expect(wrapper.find('[data-test="generate-recommendations"]').attributes('disabled')).toBeDefined()
  })

  it('deshabilita el botón al agotar el límite diario', async () => {
    const wrapper = await mountWith(result({ remaining_today: 0 }))
    expect(wrapper.find('[data-test="remaining"]').text()).toContain('Ya usaste')
    expect(wrapper.find('[data-test="generate-recommendations"]').attributes('disabled')).toBeDefined()
  })

  it('genera y muestra el error del backend', async () => {
    const wrapper = await mountWith(result({ recommendations: [] }))
    vi.spyOn(api, 'post').mockRejectedValue({ response: { status: 502, data: { detail: 'No pudimos confirmar ninguna recomendación.' } } })
    await wrapper.find('[data-test="generate-recommendations"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-test="recommendations-error"]').text()).toContain('No pudimos confirmar')
  })

  it('agrega a Quiero leer y avisa al padre', async () => {
    const wrapper = await mountWith(result())
    vi.spyOn(api, 'post').mockResolvedValue({ data: { id: 50, title: 'Cien años de soledad' } })
    await wrapper.find('[data-test="add-want-to-read"]').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('added')[0][0].title).toBe('Cien años de soledad')
    expect(wrapper.findAll('[data-test="in-library"]')).toHaveLength(2)
  })

  it('se oculta si la API no responde', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new Error('offline'))
    const wrapper = mount(RecommendationsSection)
    await flushPromises()
    expect(wrapper.find('[data-test="recommendations"]').exists()).toBe(false)
  })
})
