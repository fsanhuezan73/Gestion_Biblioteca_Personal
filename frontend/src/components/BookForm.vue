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

    <!-- ISBN -->
    <div class="mb-3">
      <label for="isbn" class="form-label">ISBN</label>
      <input
        id="isbn"
        v-model="form.isbn"
        type="text"
        class="form-control"
        placeholder="Ej: 978-84-450-7747-2"
      />
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
})

const errors = reactive({ title: '', authors: '' })

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
  })
}
</script>
