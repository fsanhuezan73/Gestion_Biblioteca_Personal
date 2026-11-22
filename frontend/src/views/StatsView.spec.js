import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/utils/api'
import StatsView from './StatsView.vue'

vi.mock('vue-chartjs', () => ({ Bar: { name: 'Bar', template: '<canvas />' } }))

const stats = {
  year_stats: {
    year: 2026, books_read: 10, pages_read: 2700, avg_days_to_finish: 12.5,
    by_month: Array.from({ length: 12 }, (_, i) => ({ month: i + 1, books: i === 2 ? 4 : 0, pages: 0 })),
    top_authors: [{ label: 'Ursula K. Le Guin', count: 3 }],
    books_read_list: [
      { id: 31, title: 'Los desposeídos', authors: 'Ursula K. Le Guin', started_at: '2026-05-20', finished_at: '2026-06-15', days_to_finish: 26, rating: 5, page_count: 400 },
      { id: 32, title: 'Ficciones', authors: 'Borges', started_at: null, finished_at: '2026-03-02', days_to_finish: null, rating: null, page_count: null },
    ],
    goal: { target_books: 24, books_read: 10, percent: 42, expected_to_date: 12, difference: -2, remaining: 14, status: 'behind' },
  },
  library: {
    total_books: 20, want_to_read: 5, reading: 2, read: 13, read_without_date: 3, avg_rating: 4.25,
    rated_books: 8, ratings: [{ rating: 5, count: 4 }], genres: [{ label: 'Novela', count: 10 }],
    currently_reading: [{ id: 7, title: 'Dune', cover_url: null, started_at: '2026-06-22', days_reading: 10 }],
  },
  available_years: [2026, 2025],
}

function mountView() {
  return mount(StatsView, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })
}

beforeEach(() => {
  vi.restoreAllMocks()
  setActivePinia(createPinia())
})

describe('StatsView', () => {
  it('muestra indicadores, meta, autores y aviso de libros sin fecha', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: stats })
    const wrapper = mountView()
    await flushPromises()
    expect(get).toHaveBeenCalledWith('/stats/', { params: { year: new Date().getFullYear() } })
    const text = wrapper.text()
    expect(text).toContain('10 de 24 libros')
    expect(text).toContain('Te faltan 2 libros')
    expect(text).toContain('2.700')
    expect(text).toContain('4.3 ★')
    expect(text).toContain('Ursula K. Le Guin')
    expect(text).toContain('Dune')
    const list = wrapper.find('[data-test="books-read-list"]').text()
    expect(list).toContain('Los desposeídos')
    expect(list).toContain('Ficciones')
    expect(list).toContain('26 días')
    expect(wrapper.find('[data-test="undated-alert"]').text()).toContain('3 libros leídos')
  })

  it('cambia de año y guarda la meta del año seleccionado', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: stats })
    const put = vi.spyOn(api, 'put').mockResolvedValue({ data: { year: 2025, target_books: 30 } })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('#stats-year').setValue('2025')
    await flushPromises()
    expect(get).toHaveBeenLastCalledWith('/stats/', { params: { year: 2025 } })
    await wrapper.find('[data-test="edit-goal"]').trigger('click')
    await wrapper.find('#goal-target').setValue('30')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(put).toHaveBeenCalledWith('/goals/2025', { target_books: 30 })
  })

  it('muestra un error recuperable si la API falla', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new Error('offline'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('No se pudieron cargar las estadísticas')
  })
})
