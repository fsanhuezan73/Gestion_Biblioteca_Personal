import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import api from '@/utils/api'
import { GENERATE_TIMEOUT_MS, useRecommendationsStore } from './recommendations'
import { useBooksStore } from './books'

const result = (overrides = {}) => ({
  recommendations: [{ title: 'Aura', authors: ['Carlos Fuentes'], reason: 'r', isbn: '9780000000002', in_library: false }],
  provider: 'gemini', model: 'gemini-3.5-flash-lite', generated_at: '2026-11-23T15:00:00Z',
  remaining_today: 4, daily_limit: 5, rated_books: 3, min_rated_books: 3, ...overrides,
})

const httpError = (status, detail) => Object.assign(new Error('http'), { response: { status, data: detail ? { detail } : {} } })

beforeEach(() => {
  vi.restoreAllMocks()
  setActivePinia(createPinia())
})

describe('recomendaciones', () => {
  it('carga el último resultado', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: result() })
    const store = useRecommendationsStore()
    await store.fetchLatest()
    expect(store.items).toHaveLength(1)
    expect(store.canGenerate).toBe(true)
  })

  it('se marca no disponible si falla la carga, sin lanzar error', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new Error('offline'))
    const store = useRecommendationsStore()
    await store.fetchLatest()
    expect(store.unavailable).toBe(true)
  })

  it('no permite generar sin libros valorados suficientes ni sin cupo', () => {
    const store = useRecommendationsStore()
    store.data = result({ rated_books: 2 })
    expect(store.canGenerate).toBe(false)
    store.data = result({ remaining_today: 0 })
    expect(store.canGenerate).toBe(false)
  })

  it('genera con un timeout largo', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: result({ remaining_today: 3 }) })
    const store = useRecommendationsStore()
    await store.generate()
    expect(post).toHaveBeenCalledWith('/ai/recommendations', null, { timeout: GENERATE_TIMEOUT_MS })
    expect(store.data.remaining_today).toBe(3)
    expect(store.generating).toBe(false)
  })

  it('al llegar al límite muestra el mensaje y refresca el último resultado', async () => {
    vi.spyOn(api, 'post').mockRejectedValue(httpError(429, 'Ya usaste las recomendaciones de hoy. Vuelve mañana.'))
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: result({ remaining_today: 0 }) })
    const store = useRecommendationsStore()
    await store.generate()
    expect(store.error).toContain('Vuelve mañana')
    expect(get).toHaveBeenCalledWith('/ai/recommendations')
    expect(store.data.remaining_today).toBe(0)
  })

  it('tras un timeout muestra el resultado si el servidor alcanzó a guardarlo', async () => {
    vi.spyOn(api, 'post').mockRejectedValue(Object.assign(new Error('timeout'), { code: 'ECONNABORTED' }))
    vi.spyOn(api, 'get').mockResolvedValue({ data: result({ generated_at: '2026-11-23T16:00:00Z', remaining_today: 3 }) })
    const store = useRecommendationsStore()
    store.data = result({ recommendations: [], generated_at: null })
    await store.generate()
    expect(store.error).toBe('')
    expect(store.items).toHaveLength(1)
    expect(store.data.remaining_today).toBe(3)
  })

  it('tras un timeout sin resultado nuevo mantiene el aviso', async () => {
    vi.spyOn(api, 'post').mockRejectedValue(Object.assign(new Error('timeout'), { code: 'ECONNABORTED' }))
    vi.spyOn(api, 'get').mockResolvedValue({ data: result() })
    const store = useRecommendationsStore()
    store.data = result()
    await store.generate()
    expect(store.error).toContain('tardó demasiado')
  })

  it.each([
    [httpError(503), 'no está disponible'],
    [Object.assign(new Error('timeout'), { code: 'ECONNABORTED' }), 'tardó demasiado'],
  ])('mensaje de error claro (%#)', async (err, text) => {
    vi.spyOn(api, 'post').mockRejectedValue(err)
    const store = useRecommendationsStore()
    await store.generate()
    expect(store.error).toContain(text)
  })

  it('agrega a Quiero leer con los datos verificados', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { id: 9, title: 'Aura' } })
    const store = useRecommendationsStore()
    store.data = result()
    const book = store.items[0]
    await store.addToWantToRead(book)
    expect(post).toHaveBeenCalledWith('/books/', {
      title: 'Aura', authors: ['Carlos Fuentes'], isbn: '9780000000002', year: null, publisher: null,
      cover_url: null, page_count: null, reading_status: 'Quiero leer',
    })
    expect(store.items[0].in_library).toBe(true)
    expect(useBooksStore().books[0].id).toBe(9)
    expect(store.isAdding(book)).toBe(false)
  })
})
