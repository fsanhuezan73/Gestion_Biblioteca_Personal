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
import { reactive, watch } from 'vue'

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
    const res = await fetch(
      `https://www.googleapis.com/books/v1/volumes?q=isbn:${encodeURIComponent(form.isbn.trim())}`
    )
    const data = await res.json()
    if (!data.items?.length) {
      isbnAlert.value = { type: 'warning', text: 'Libro no encontrado. Por favor, ingresa los datos manualmente.' }
      return
    }
    const info = data.items[0].volumeInfo
    if (info.title) form.title = info.title
    if (info.authors?.length) form.authors = [...info.authors]
    if (info.publisher) form.publisher = info.publisher
    if (info.publishedDate) form.year = parseInt(info.publishedDate.substring(0, 4)) || form.year
    if (info.imageLinks?.thumbnail) {
      form.cover_url = info.imageLinks.thumbnail.replace('http://', 'https://')
    }
    isbnAlert.value = { type: 'success', text: 'Datos completados automáticamente. Revisa y guarda cuando estés listo.' }
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
