import { mount } from '@vue/test-utils'
import { beforeEach, describe, it, expect } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import BookForm from './BookForm.vue'

beforeEach(() => setActivePinia(createPinia()))

describe('BookForm', () => {
  it('validates and emits the payload when the form is valid', async () => {
    const wrapper = mount(BookForm)

    await wrapper.find('#title').setValue('Dune')
    const authorInputs = wrapper.findAll('input[type="text"]')
    await authorInputs[1].setValue('Frank Herbert')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('submit')).toHaveLength(1)
    expect(wrapper.emitted('submit')[0][0]).toMatchObject({
      title: 'Dune',
      authors: ['Frank Herbert'],
      reading_status: 'Quiero leer',
    })
  })
})

describe('BookForm · fechas y páginas', () => {
  async function fillRequired(wrapper) {
    await wrapper.find('#title').setValue('Dune')
    await wrapper.findAll('input[type="text"]')[1].setValue('Frank Herbert')
  }

  it('al marcar Leído propone la fecha de término de hoy y la envía', async () => {
    const wrapper = mount(BookForm)
    await fillRequired(wrapper)
    expect(wrapper.find('#finished_at').exists()).toBe(false)
    await wrapper.find('#reading_status').setValue('Leído')
    const finished = wrapper.find('#finished_at')
    expect(finished.element.value).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    await wrapper.find('#page_count').setValue('412')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')[0][0]).toMatchObject({
      reading_status: 'Leído',
      page_count: 412,
      started_at: null,
      finished_at: finished.element.value,
    })
  })

  it('rechaza un término anterior al inicio', async () => {
    const wrapper = mount(BookForm)
    await fillRequired(wrapper)
    await wrapper.find('#reading_status').setValue('Leído')
    await wrapper.find('#started_at').setValue('2026-03-10')
    await wrapper.find('#finished_at').setValue('2026-03-01')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.text()).toContain('anterior a la de inicio')
  })

  it('no envía fechas ocultas cuando el estado es Quiero leer', async () => {
    const wrapper = mount(BookForm, {
      props: { initialData: { title: 'Dune', authors: ['Frank Herbert'], reading_status: 'Quiero leer', started_at: '2026-01-01' } },
    })
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')[0][0]).toMatchObject({ started_at: null, finished_at: null })
  })
})

describe('BookForm · escáner', () => {
  it('al escanear completa el ISBN, busca en Open Library y avisa si ya existe', async () => {
    const { default: api } = await import('@/utils/api')
    const { vi } = await import('vitest')
    const { flushPromises } = await import('@vue/test-utils')
    vi.spyOn(api, 'get').mockResolvedValue({ data: { isbn: '9780451524935', exists: true, books: [{ id: 7, title: '1984' }] } })
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({ docs: [{ title: '1984', author_name: ['George Orwell'], number_of_pages_median: 328 }] }),
    }))
    const wrapper = mount(BookForm, {
      props: { allowScan: true },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, BarcodeScanner: { template: '<div data-test="scanner" />', emits: ['detected'] } } },
    })
    expect(wrapper.find('[data-test="open-scanner"]').exists()).toBe(true)
    await wrapper.find('[data-test="open-scanner"]').trigger('click')
    await flushPromises()
    wrapper.findComponent('[data-test="scanner"]').vm.$emit('detected', '9780451524935')
    await flushPromises()
    expect(wrapper.find('#isbn').element.value).toBe('9780451524935')
    expect(wrapper.find('#title').element.value).toBe('1984')
    expect(wrapper.find('#page_count').element.value).toBe('328')
    expect(api.get).toHaveBeenCalledWith('/books/check-isbn', { params: { isbn: '9780451524935' } })
    expect(wrapper.find('[data-test="duplicate-alert"]').text()).toContain('1984')
  })

  it('sin allowScan no muestra el botón Escanear', () => {
    const wrapper = mount(BookForm)
    expect(wrapper.find('[data-test="open-scanner"]').exists()).toBe(false)
  })
})
