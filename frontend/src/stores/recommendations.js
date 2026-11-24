import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import api from '@/utils/api'
import { useAuthStore } from '@/stores/auth'
import { useBooksStore } from '@/stores/books'

// La IA y la verificación en catálogos, más el arranque en frío de Render, pueden
// tardar bastante más que una petición normal.
export const GENERATE_TIMEOUT_MS = 90000

const ERROR_MESSAGES = {
  422: 'Necesitas más libros leídos con valoración para recibir recomendaciones.',
  429: 'Ya usaste las recomendaciones de hoy. Vuelve mañana.',
  502: 'No pudimos confirmar ninguna recomendación en los catálogos. Intenta de nuevo.',
  503: 'El servicio de recomendaciones no está disponible ahora. Intenta más tarde.',
}

function errorMessage(err) {
  if (err.code === 'ECONNABORTED') return 'La solicitud tardó demasiado. Intenta de nuevo en un momento.'
  const status = err.response?.status
  return err.response?.data?.detail || ERROR_MESSAGES[status] || 'No se pudieron generar recomendaciones. Intenta nuevamente.'
}

export const useRecommendationsStore = defineStore('recommendations', () => {
  const data = ref(null)
  const generating = ref(false)
  const error = ref('')
  const unavailable = ref(false)
  const adding = ref({})

  const items = computed(() => data.value?.recommendations ?? [])

  function reset() {
    data.value = null
    error.value = ''
    unavailable.value = false
    adding.value = {}
  }

  // Las recomendaciones son personales: al cerrar sesión o entrar con otra
  // cuenta (sin recargar la página) se descartan las del usuario anterior.
  const authStore = useAuthStore()
  watch(() => authStore.token, reset)

  const enoughRatedBooks = computed(() => !!data.value && data.value.rated_books >= data.value.min_rated_books)
  const canGenerate = computed(
    () => enoughRatedBooks.value && data.value.remaining_today > 0 && !generating.value,
  )

  async function fetchLatest() {
    const token = authStore.token
    try {
      const { data: result } = await api.get('/ai/recommendations')
      // Respuesta de una sesión anterior: no se muestra.
      if (authStore.token !== token) return
      data.value = result
      unavailable.value = false
    } catch {
      // Sección complementaria: si falla, se oculta sin afectar la biblioteca.
      unavailable.value = true
    }
  }

  async function generate() {
    generating.value = true
    error.value = ''
    const previousGeneratedAt = data.value?.generated_at ?? null
    const token = authStore.token
    try {
      const { data: result } = await api.post('/ai/recommendations', null, { timeout: GENERATE_TIMEOUT_MS })
      if (authStore.token === token) data.value = result
    } catch (err) {
      if (authStore.token !== token) return
      error.value = errorMessage(err)
      // Se refresca el contador y el último resultado: tras un timeout del navegador,
      // el servidor pudo terminar igual y guardar recomendaciones nuevas.
      if (err.response?.status !== 422) {
        await fetchLatest()
        const arrived = data.value?.generated_at && data.value.generated_at !== previousGeneratedAt
        if (arrived && err.response?.status !== 429) error.value = ''
      }
    } finally {
      generating.value = false
    }
  }

  async function addToWantToRead(book) {
    const key = book.isbn || book.title
    adding.value = { ...adding.value, [key]: true }
    try {
      const booksStore = useBooksStore()
      const created = await booksStore.addBook({
        title: book.title,
        authors: book.authors?.length ? book.authors : ['Desconocido'],
        isbn: book.isbn || null,
        year: book.year || null,
        publisher: book.publisher || null,
        cover_url: book.cover_url || null,
        page_count: book.page_count || null,
        reading_status: 'Quiero leer',
      })
      book.in_library = true
      return created
    } finally {
      const rest = { ...adding.value }
      delete rest[key]
      adding.value = rest
    }
  }

  function isAdding(book) {
    return !!adding.value[book.isbn || book.title]
  }

  return {
    data, generating, error, unavailable, items, enoughRatedBooks, canGenerate,
    fetchLatest, generate, addToWantToRead, isAdding, reset,
  }
})
