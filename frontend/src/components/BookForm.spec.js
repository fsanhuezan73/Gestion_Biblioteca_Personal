import { mount } from '@vue/test-utils'
import { beforeEach, describe, it, expect, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import BookForm from './BookForm.vue'

beforeEach(() => {
  vi.restoreAllMocks()
  setActivePinia(createPinia())
})

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
  it('al escanear autocompleta el libro, avisa si existe y conserva sus formatos', async () => {
    const { default: api } = await import('@/utils/api')
    const { flushPromises } = await import('@vue/test-utils')
    vi.spyOn(api, 'get').mockImplementation(async (url) => (url === '/books/check-isbn'
      ? { data: { isbn: '9780451524935', exists: true, books: [{ id: 7, title: '1984' }] } }
      : { data: {
        isbn: '9780451524935', found: true, title: '1984', authors: ['George Orwell'], publisher: 'Signet',
        year: 1949, page_count: 328, cover_url: null,
        sources: { title: 'openlibrary', authors: 'openlibrary', page_count: 'google_books' }, unavailable_sources: [],
      } }))
    const wrapper = mount(BookForm, {
      props: { allowScan: true },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, BarcodeScanner: { template: '<div data-test="scanner" />', emits: ['detected'] } } },
    })
    await wrapper.get('input[value="physical"]').setValue(true)
    await wrapper.get('input[value="kindle"]').setValue(true)
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
    expect(api.get).toHaveBeenCalledWith('/books/lookup', { params: { isbn: '9780451524935' } })
    expect(wrapper.text()).toContain('Datos de Open Library + Google Books')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')[0][0].formats).toEqual(['physical', 'kindle'])
  })

  it('ISBN inválido no consulta la API', async () => {
    const { default: api } = await import('@/utils/api')
    const get = vi.spyOn(api, 'get')
    const wrapper = mount(BookForm)
    await wrapper.find('#isbn').setValue('978-0-451-52493-6')
    await wrapper.findAll('button').find((b) => b.text() === 'Buscar').trigger('click')
    expect(wrapper.text()).toContain('El ISBN no es válido')
    expect(get).not.toHaveBeenCalled()
  })

  it('libro no encontrado en ninguna fuente', async () => {
    const { default: api } = await import('@/utils/api')
    const { flushPromises } = await import('@vue/test-utils')
    vi.spyOn(api, 'get').mockResolvedValue({ data: { found: false, authors: [], sources: {}, unavailable_sources: [] } })
    const wrapper = mount(BookForm)
    await wrapper.find('#isbn').setValue('9789566196181')
    await wrapper.findAll('button').find((b) => b.text() === 'Buscar').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Libro no encontrado en Open Library ni en Google Books')
  })

  it('abre el escáner si autoScan cambia a true sin perder lo escrito', async () => {
    const { flushPromises } = await import('@vue/test-utils')
    const wrapper = mount(BookForm, {
      props: { allowScan: true, autoScan: false },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, BarcodeScanner: { template: '<div data-test="scanner" />' } } },
    })
    await wrapper.find('#title').setValue('Borrador')
    expect(wrapper.find('[data-test="scanner"]').exists()).toBe(false)
    await wrapper.setProps({ autoScan: true })
    await flushPromises()
    expect(wrapper.find('[data-test="scanner"]').exists()).toBe(true)
    expect(wrapper.find('#title').element.value).toBe('Borrador')
    expect(wrapper.emitted('auto-scan-opened')).toHaveLength(1)
  })

  it('avisa al abrir el escáner automáticamente al montar', async () => {
    const { flushPromises } = await import('@vue/test-utils')
    const wrapper = mount(BookForm, {
      props: { allowScan: true, autoScan: true },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, BarcodeScanner: { template: '<div data-test="scanner" />' } } },
    })
    await flushPromises()
    expect(wrapper.find('[data-test="scanner"]').exists()).toBe(true)
    expect(wrapper.emitted('auto-scan-opened')).toHaveLength(1)
  })

  it('sin allowScan no muestra el botón Escanear', () => {
    const wrapper = mount(BookForm)
    expect(wrapper.find('[data-test="open-scanner"]').exists()).toBe(false)
  })
})

describe('BookForm · portada', () => {
  const EXISTING = { title: 'Dune', authors: ['Frank Herbert'], reading_status: 'Quiero leer', cover_url: 'https://covers.example/dune.jpg' }

  async function mockImages(blob = { size: 1234, type: 'image/jpeg' }) {
    const images = await import('@/utils/images')
    vi.spyOn(images, 'compressCoverImage').mockResolvedValue(blob)
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:preview')
    globalThis.URL.revokeObjectURL = vi.fn()
    return images
  }

  async function chooseFile(wrapper) {
    const input = wrapper.find('[data-test="cover-file"]')
    Object.defineProperty(input.element, 'files', { value: [{ type: 'image/png', size: 500 }], configurable: true })
    await input.trigger('change')
    const { flushPromises } = await import('@vue/test-utils')
    await flushPromises()
  }

  it('sin portada muestra el botón para subir una imagen', () => {
    const wrapper = mount(BookForm, { props: { initialData: { ...EXISTING, cover_url: null } } })
    expect(wrapper.find('[data-test="cover-preview"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="cover-upload"]').text()).toContain('Subir imagen')
    expect(wrapper.find('[data-test="cover-remove"]').exists()).toBe(false)
  })

  it('con portada permite reemplazarla o quitarla', async () => {
    const wrapper = mount(BookForm, { props: { initialData: EXISTING } })
    expect(wrapper.find('[data-test="cover-preview"]').attributes('src')).toBe(EXISTING.cover_url)
    expect(wrapper.find('[data-test="cover-upload"]').text()).toContain('Reemplazar')
    await wrapper.find('[data-test="cover-remove"]').trigger('click')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')[0][0].cover_url).toBeNull()
  })

  it('sube la imagen elegida al guardar y envía su URL', async () => {
    await mockImages()
    const { useBooksStore } = await import('@/stores/books')
    const store = useBooksStore()
    const upload = vi.spyOn(store, 'uploadCover').mockResolvedValue('https://api.example/api/v1/covers/abc')
    const wrapper = mount(BookForm, { props: { initialData: EXISTING } })

    await chooseFile(wrapper)
    expect(wrapper.find('[data-test="cover-preview"]').attributes('src')).toBe('blob:preview')
    expect(upload).not.toHaveBeenCalled() // aún no se sube

    await wrapper.find('form').trigger('submit')
    const { flushPromises } = await import('@vue/test-utils')
    await flushPromises()
    expect(upload).toHaveBeenCalledWith({ size: 1234, type: 'image/jpeg' })
    expect(wrapper.emitted('submit')[0][0].cover_url).toBe('https://api.example/api/v1/covers/abc')
  })

  it('si la subida falla no guarda el libro y muestra el error', async () => {
    await mockImages()
    const { useBooksStore } = await import('@/stores/books')
    vi.spyOn(useBooksStore(), 'uploadCover').mockRejectedValue({ response: { data: { detail: 'Formato no soportado' } } })
    const wrapper = mount(BookForm, { props: { initialData: EXISTING } })

    await chooseFile(wrapper)
    await wrapper.find('form').trigger('submit')
    const { flushPromises } = await import('@vue/test-utils')
    await flushPromises()
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.find('[data-test="cover-error"]').text()).toBe('Formato no soportado')
  })

  it('muestra el error de una imagen inválida', async () => {
    const images = await mockImages()
    images.compressCoverImage.mockRejectedValue(new images.CoverImageError('La imagen supera los 10 MB. Elige una más liviana.'))
    const wrapper = mount(BookForm, { props: { initialData: EXISTING } })
    await chooseFile(wrapper)
    expect(wrapper.find('[data-test="cover-error"]').text()).toContain('10 MB')
    expect(wrapper.find('[data-test="cover-preview"]').attributes('src')).toBe(EXISTING.cover_url)
  })

  it('acepta una URL http(s) y rechaza otras', async () => {
    const wrapper = mount(BookForm, { props: { initialData: { ...EXISTING, cover_url: null } } })
    await wrapper.find('[data-test="cover-url-toggle"]').trigger('click')
    await wrapper.find('[data-test="cover-url-input"]').setValue('javascript:alert(1)')
    await wrapper.find('[data-test="cover-url-apply"]').trigger('click')
    expect(wrapper.find('[data-test="cover-error"]').exists()).toBe(true)

    await wrapper.find('[data-test="cover-url-input"]').setValue('https://img.example/portada.jpg')
    await wrapper.find('[data-test="cover-url-apply"]').trigger('click')
    expect(wrapper.find('[data-test="cover-preview"]').attributes('src')).toBe('https://img.example/portada.jpg')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')[0][0].cover_url).toBe('https://img.example/portada.jpg')
  })
})
