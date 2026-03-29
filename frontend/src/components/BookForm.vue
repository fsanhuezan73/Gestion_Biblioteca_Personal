<template>
  <form @submit.prevent="handleSubmit" novalidate>
    <!-- Título -->
    <div class="mb-3">
      <label for="title" class="form-label">Título <span class="text-danger">*</span></label>
      <input
        id="title"
        v-model="form.title"
        type="text"
        class="form-control"
        :class="{ 'is-invalid': errors.title }"
        placeholder="Ej: El Señor de los Anillos"
      />
      <div v-if="errors.title" class="invalid-feedback">{{ errors.title }}</div>
    </div>

    <!-- Autores -->
    <div class="mb-3">
      <label class="form-label">Autor(es) <span class="text-danger">*</span></label>
      <div
        v-for="(author, idx) in form.authors"
        :key="idx"
        class="d-flex gap-2 mb-2"
      >
        <input
          v-model="form.authors[idx]"
          type="text"
          class="form-control"
          :class="{ 'is-invalid': idx === 0 && errors.authors }"
          placeholder="Ej: J.R.R. Tolkien"
        />
        <button
          v-if="form.authors.length > 1"
          type="button"
          class="btn btn-outline-danger btn-sm"
          @click="removeAuthor(idx)"
        >✕</button>
      </div>
      <div v-if="errors.authors" class="text-danger small mb-1">{{ errors.authors }}</div>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="addAuthor">
        + Agregar otro autor
      </button>
    </div>

    <!-- ISBN + búsqueda automática -->
    <div class="mb-3">
      <label for="isbn" class="form-label">ISBN</label>
      <div class="input-group">
        <input
          id="isbn"
          v-model="form.isbn"
          type="text"
          class="form-control"
          placeholder="Ej: 978-84-450-7747-2"
        />
        <button
          type="button"
          class="btn btn-outline-secondary"
          :disabled="isbnSearching || !form.isbn?.trim()"
          @click="searchByISBN"
        >
          <span v-if="isbnSearching" class="spinner-border spinner-border-sm" role="status" />
          <span v-else>Buscar</span>
        </button>
      </div>
      <div
        v-if="isbnAlert"
        class="alert mt-2 py-2 small mb-0"
        :class="`alert-${isbnAlert.type}`"
        role="alert"
      >
        {{ isbnAlert.text }}
      </div>
    </div>

    <!-- Portada autocomplete preview -->
    <div v-if="form.cover_url" class="mb-3 text-center">
      <img
        :src="form.cover_url"
        alt="Portada del libro"
        class="rounded shadow-sm"
        style="max-height: 160px; object-fit: contain"
      />
      <div class="mt-1">
        <button type="button" class="btn btn-link btn-sm text-danger p-0" @click="form.cover_url = ''">
          Quitar portada
        </button>
      </div>
    </div>

    <!-- Editorial -->
    <div class="mb-3">
      <label for="publisher" class="form-label">Editorial</label>
      <input
        id="publisher"
        v-model="form.publisher"
        type="text"
        class="form-control"
        placeholder="Ej: Minotauro"
      />
    </div>

    <!-- Año y Género en fila -->
    <div class="row g-3 mb-4">
      <div class="col-sm-6">
        <label for="year" class="form-label">Año de publicación</label>
        <input
          id="year"
          v-model.number="form.year"
          type="number"
          class="form-control"
          placeholder="Ej: 1954"
          min="1000"
          max="2100"
        />
      </div>
      <div class="col-sm-6">
        <label for="genre" class="form-label">Género</label>
        <select id="genre" v-model="form.genre" class="form-select">
          <option value="">— Seleccionar —</option>
          <option>Fantasía</option>
          <option>Ciencia Ficción</option>
          <option>Novela</option>
          <option>Historia</option>
          <option>Biografía</option>
          <option>Tecnología</option>
          <option>Autoayuda</option>
          <option>Poesía</option>
          <option>Ensayo</option>
          <option>Otro</option>
        </select>
      </div>
    </div>

    <div v-if="apiError" class="alert alert-danger py-2" role="alert">{{ apiError }}</div>

    <button type="submit" class="btn btn-primary w-100" :disabled="loading">
      <span v-if="loading" class="spinner-border spinner-border-sm me-2" />
      {{ submitLabel }}
    </button>
  </form>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'

const props = defineProps({
  initialData: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  apiError: { type: String, default: '' },
  submitLabel: { type: String, default: 'Guardar' },
})

const emit = defineEmits(['submit'])

const form = reactive({
  title: '',
  authors: [''],
  isbn: '',
  publisher: '',
  year: null,
  genre: '',
  cover_url: '',
})

const errors = reactive({ title: '', authors: '' })
const isbnSearching = ref(false)
const isbnAlert = ref(null)

watch(
  () => props.initialData,
  (data) => {
    if (data) {
      form.title = data.title ?? ''
      form.authors = data.authors?.length ? [...data.authors] : ['']
      form.isbn = data.isbn ?? ''
      form.publisher = data.publisher ?? ''
      form.year = data.year ?? null
      form.genre = data.genre ?? ''
      form.cover_url = data.cover_url ?? ''
    }
  },
  { immediate: true }
)

function addAuthor() {
  form.authors.push('')
}

function removeAuthor(idx) {
  form.authors.splice(idx, 1)
}

async function searchByISBN() {
  if (!form.isbn?.trim()) return
  isbnSearching.value = true
  isbnAlert.value = null
  try {
    const isbn = form.isbn.trim().replace(/[-\s]/g, '')

    // 1) Buscar en Open Library search (trae todo en 1 llamada cuando está completo)
    const res = await fetch(
      `https://openlibrary.org/search.json?isbn=${encodeURIComponent(isbn)}&fields=title,author_name,publisher,first_publish_year,cover_i&limit=1`
    )
    if (!res.ok) {
      isbnAlert.value = { type: 'warning', text: 'No se pudo conectar con la API. Por favor, ingresa los datos manualmente.' }
      return
    }
    const data = await res.json()
    if (!data.docs?.length) {
      isbnAlert.value = { type: 'warning', text: 'Libro no encontrado. Por favor, ingresa los datos manualmente.' }
      return
    }
    const doc = data.docs[0]
    if (doc.title) form.title = doc.title
    if (doc.author_name?.length) form.authors = [...doc.author_name]
    if (doc.publisher?.length) form.publisher = doc.publisher[0]
    if (doc.first_publish_year) form.year = doc.first_publish_year
    if (doc.cover_i) {
      form.cover_url = `https://covers.openlibrary.org/b/id/${doc.cover_i}-M.jpg`
    }

    // 2) Fallback autores: si search no trajo author_name, resolver via edition → works → authors
    if (!doc.author_name?.length) {
      try {
        const edRes = await fetch(`https://openlibrary.org/isbn/${isbn}.json`)
        if (edRes.ok) {
          const edition = await edRes.json()
          // Intentar authors directos de la edición
          if (edition.authors?.length) {
            const names = await Promise.all(
              edition.authors.map(async (a) => {
                const r = await fetch(`https://openlibrary.org${a.key}.json`)
                if (r.ok) { const d = await r.json(); return d.name }
                return null
              })
            )
            const valid = names.filter(Boolean)
            if (valid.length) form.authors = valid
          }
          // Si aún no hay autores, intentar via works
          if (form.authors.length === 1 && !form.authors[0] && edition.works?.length) {
            const wRes = await fetch(`https://openlibrary.org${edition.works[0].key}.json`)
            if (wRes.ok) {
              const work = await wRes.json()
              if (work.authors?.length) {
                const names = await Promise.all(
                  work.authors.map(async (a) => {
                    const key = a.author?.key || a.key
                    if (!key) return null
                    const r = await fetch(`https://openlibrary.org${key}.json`)
                    if (r.ok) { const d = await r.json(); return d.name }
                    return null
                  })
                )
                const valid = names.filter(Boolean)
                if (valid.length) form.authors = valid
              }
            }
          }
        }
      } catch { /* fallback silencioso — el usuario puede ingresar el autor manualmente */ }
    }

    const hasAuthor = form.authors.some((a) => a.trim())
    if (!hasAuthor) {
      isbnAlert.value = { type: 'info', text: 'Datos parcialmente completados. No se encontró el autor — ingrésalo manualmente.' }
    } else {
      isbnAlert.value = { type: 'success', text: 'Datos completados automáticamente. Revisa y guarda cuando estés listo.' }
    }
  } catch {
    isbnAlert.value = { type: 'warning', text: 'No se pudo conectar con la API. Por favor, ingresa los datos manualmente.' }
  } finally {
    isbnSearching.value = false
  }
}

function validate() {
  errors.title = ''
  errors.authors = ''
  let valid = true
  if (!form.title?.trim()) { errors.title = 'El título es obligatorio'; valid = false }
  const filled = form.authors.filter((a) => a.trim())
  if (!filled.length) { errors.authors = 'Debe indicar al menos un autor'; valid = false }
  return valid
}

function handleSubmit() {
  if (!validate()) return
  emit('submit', {
    title: form.title.trim(),
    authors: form.authors.map((a) => a.trim()).filter(Boolean),
    isbn: form.isbn || null,
    publisher: form.publisher || null,
    year: form.year || null,
    genre: form.genre || null,
    cover_url: form.cover_url || null,
  })
}
</script>
