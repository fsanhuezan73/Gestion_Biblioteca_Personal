import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import api from '@/utils/api'
import { useBooksStore } from './books'

beforeEach(() => {
  vi.restoreAllMocks()
  setActivePinia(createPinia())
})

describe('guardar valoración y notas', () => {
  it('envía PATCH y actualiza el resumen sin incluir notas', async () => {
    const store = useBooksStore()
    store.books = [{ id: 101, rating: null }]
    const saved = { id: 101, rating: 5, personal_notes: 'Privado' }
    const patch = vi.spyOn(api, 'patch').mockResolvedValue({ data: saved })
    expect(await store.updatePersonalDetails(101, { rating: 5 })).toEqual(saved)
    expect(patch).toHaveBeenCalledWith('/books/101/personal', { rating: 5 })
    expect(store.books).toEqual([{ id: 101, rating: 5 }])
  })

  it('no modifica el catálogo cuando falla la API', async () => {
    const store = useBooksStore()
    store.books = [{ id: 101, rating: 3 }]
    vi.spyOn(api, 'patch').mockRejectedValue(new Error('offline'))
    await expect(store.updatePersonalDetails(101, { rating: 5 })).rejects.toThrow('offline')
    expect(store.books[0].rating).toBe(3)
  })
})

describe('subir portada', () => {
  it('envía la imagen como cuerpo binario y devuelve la URL absoluta', async () => {
    const store = useBooksStore()
    const blob = { type: 'image/jpeg', size: 10 }
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { id: 'abc123' } })
    const url = await store.uploadCover(blob)
    expect(post).toHaveBeenCalledWith('/covers', blob, { headers: { 'Content-Type': 'image/jpeg' } })
    expect(url).toBe(new globalThis.URL(`${api.defaults.baseURL}/covers/abc123`, window.location.origin).href)
    expect(url).toMatch(/^https?:\/\/.+\/covers\/abc123$/)
  })
})
