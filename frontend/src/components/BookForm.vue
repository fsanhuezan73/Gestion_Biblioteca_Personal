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
          v-if="allowScan"
          type="button"
          class="btn btn-outline-primary"
          data-test="open-scanner"
          @click="showScanner = true"
        >
          📷 Escanear
        </button>
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
      <div v-if="duplicates.length" class="alert alert-warning mt-2 py-2 small mb-0" role="alert" data-test="duplicate-alert">
        ⚠️ Ya tienes este libro en tu biblioteca:
        <template v-for="(dup, i) in duplicates" :key="dup.id">
          <RouterLink :to="`/books/${dup.id}`" class="alert-link">{{ dup.title }}</RouterLink><span v-if="i < duplicates.length - 1">, </span>
        </template>.
        Puedes guardarlo igual si tienes otro ejemplar.
      </div>
    </div>

    <BarcodeScanner v-if="showScanner" @detected="handleScanned" @close="showScanner = false" />

    <!-- Portada: de la búsqueda por ISBN, subida por el usuario o desde una URL -->
    <div class="mb-3" data-test="cover-section">
      <label class="form-label">Portada</label>
      <div class="d-flex gap-3 align-items-start">
        <div class="cover-preview-frame rounded border bg-light d-flex align-items-center justify-content-center overflow-hidden">
          <span v-if="coverProcessing" class="spinner-border spinner-border-sm text-secondary" role="status" />
          <img
            v-else-if="coverPreview && !coverBroken"
            :src="coverPreview"
            alt="Portada del libro"
            class="cover-preview-image"
            data-test="cover-preview"
            @error="coverBroken = true"
          />
          <span v-else class="text-muted small text-center px-1">{{ coverPreview ? 'No se pudo cargar' : 'Sin portada' }}</span>
        </div>
        <div class="d-flex flex-column align-items-start gap-2">
          <input
            ref="coverInput"
            type="file"
            accept="image/*"
            class="d-none"
            data-test="cover-file"
            @change="onCoverFileChange"
          />
          <button
            type="button"
            class="btn btn-outline-primary btn-sm"
            data-test="cover-upload"
            :disabled="coverProcessing || coverUploading"
            @click="coverInput?.click()"
          >
            {{ coverPreview ? '🔄 Reemplazar imagen' : '📁 Subir imagen' }}
          </button>
          <button
            v-if="coverPreview"
            type="button"
            class="btn btn-link btn-sm text-danger p-0"
            data-test="cover-remove"
            :disabled="coverUploading"
            @click="removeCover"
          >
            Quitar portada
          </button>
          <button
            type="button"
            class="btn btn-link btn-sm p-0"
            data-test="cover-url-toggle"
            @click="toggleCoverUrl"
          >
            {{ showCoverUrl ? 'Cancelar URL' : 'Usar una URL de imagen' }}
          </button>
        </div>
      </div>
      <div v-if="showCoverUrl" class="input-group input-group-sm mt-2">
        <input
          id="cover_url_input"
          v-model="coverUrlDraft"
          type="url"
          class="form-control"
          placeholder="https://…/portada.jpg"
          data-test="cover-url-input"
          @keydown.enter.prevent="applyCoverUrl"
        />
        <button type="button" class="btn btn-outline-secondary" data-test="cover-url-apply" @click="applyCoverUrl">
          Usar
        </button>
      </div>
      <div v-if="coverError" class="text-danger small mt-1" role="alert" data-test="cover-error">{{ coverError }}</div>
      <div v-else-if="pendingCover" class="form-text">La imagen se subirá al guardar el libro.</div>
      <div v-else class="form-text">JPG, PNG o WebP de hasta 10 MB; se reduce automáticamente. En el celular puedes sacarle una foto.</div>
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

    <!-- Año, Género y Estado en fila -->
    <div class="row g-3 mb-3">
      <div class="col-sm-4">
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
      <div class="col-sm-4">
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
      <div class="col-sm-4">
        <label for="reading_status" class="form-label">Estado de lectura</label>
        <select
          id="reading_status"
          v-model="form.reading_status"
          class="form-select"
          @change="applyStatusDates"
        >
          <option value="Quiero leer">📘 Quiero leer</option>
          <option value="Leyendo">📖 Leyendo</option>
          <option value="Leído">✅ Leído</option>
        </select>
      </div>
    </div>

    <!-- Páginas y fechas de lectura -->
    <div class="row g-3 mb-4">
      <div class="col-sm-4">
        <label for="page_count" class="form-label">N.º de páginas</label>
        <input
          id="page_count"
          v-model.number="form.page_count"
          type="number"
          class="form-control"
          :class="{ 'is-invalid': errors.page_count }"
          placeholder="Ej: 423"
          min="1"
          max="100000"
        />
        <div v-if="errors.page_count" class="invalid-feedback">{{ errors.page_count }}</div>
      </div>
      <div v-if="form.reading_status !== 'Quiero leer'" class="col-sm-4">
        <label for="started_at" class="form-label">Fecha de inicio</label>
        <input
          id="started_at"
          v-model="form.started_at"
          type="date"
          class="form-control"
          :class="{ 'is-invalid': errors.dates }"
          :max="maxDate"
        />
      </div>
      <div v-if="form.reading_status === 'Leído'" class="col-sm-4">
        <label for="finished_at" class="form-label">Fecha de término</label>
        <input
          id="finished_at"
          v-model="form.finished_at"
          type="date"
          class="form-control"
          :class="{ 'is-invalid': errors.dates }"
          :max="maxDate"
        />
      </div>
      <div v-if="errors.dates" class="col-12 text-danger small mt-1">{{ errors.dates }}</div>
    </div>

    <div v-if="apiError" class="alert alert-danger py-2" role="alert">{{ apiError }}</div>

    <fieldset class="mb-3">
      <legend class="form-label fs-6">Formato</legend>
      <div class="d-flex flex-wrap column-gap-3 row-gap-1">
        <label v-for="{ code, label } in BOOK_FORMATS" :key="code" class="form-check mb-0">
          <input v-model="form.formats" type="checkbox" class="form-check-input" :value="code" />
          <span class="form-check-label">{{ label }}</span>
        </label>
      </div>
    </fieldset>

    <button type="submit" class="btn btn-primary w-100" :disabled="loading || coverUploading || coverProcessing">
      <span v-if="loading || coverUploading" class="spinner-border spinner-border-sm me-2" />
      {{ coverUploading ? 'Subiendo portada…' : submitLabel }}
    </button>
  </form>
</template>

<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useBooksStore } from '@/stores/books'
import { toIsbn13 } from '@/utils/isbn'
import { datesForStatus, readingDatesError, todayISO } from '@/utils/dates'
import { CoverImageError, compressCoverImage } from '@/utils/images'
import { BOOK_FORMATS } from '@/utils/bookFormats'

const props = defineProps({
  initialData: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  apiError: { type: String, default: '' },
  submitLabel: { type: String, default: 'Guardar' },
  // Escáner de código de barras (solo al añadir libros).
  allowScan: { type: Boolean, default: false },
  autoScan: { type: Boolean, default: false },
})

// El escáner (y su lector WebAssembly) se carga solo al abrirlo.
const BarcodeScanner = defineAsyncComponent(() => import('./BarcodeScanner.vue'))
const booksStore = useBooksStore()
const showScanner = ref(false)
const duplicates = ref([])

onMounted(() => {
  if (props.allowScan && props.autoScan) showScanner.value = true
})

// «Escanear libro» desde el menú estando ya en «Añadir libro»: la vista se reutiliza.
watch(() => props.autoScan, (value) => {
  if (props.allowScan && value) showScanner.value = true
})

function handleScanned(isbn) {
  showScanner.value = false
  form.isbn = isbn
  searchByISBN()
}

async function checkDuplicates(rawIsbn) {
  duplicates.value = []
  const isbn = toIsbn13(rawIsbn)
  if (!props.allowScan || !isbn) return
  try {
    const result = await booksStore.checkIsbn(isbn)
    if (form.isbn && toIsbn13(form.isbn) === isbn) duplicates.value = result.books
  } catch { /* la comprobación es solo informativa */ }
}

const emit = defineEmits(['submit'])

const form = reactive({
  title: '',
  authors: [''],
  isbn: '',
  publisher: '',
  year: null,
  genre: '',
  cover_url: '',
  reading_status: 'Quiero leer',
  page_count: null,
  formats: [],
  started_at: '',
  finished_at: '',
})

const errors = reactive({ title: '', authors: '', page_count: '', dates: '' })
const maxDate = todayISO()
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
      form.reading_status = data.reading_status ?? 'Quiero leer'
      form.page_count = data.page_count ?? null
      form.formats = [...(data.formats ?? [])]
      form.started_at = data.started_at ?? ''
      form.finished_at = data.finished_at ?? ''
    }
  },
  { immediate: true }
)

// Al cambiar el estado se proponen fechas (editables), igual que el backend.
function applyStatusDates() {
  Object.assign(form, datesForStatus(form.reading_status, form.started_at, form.finished_at))
}

function addAuthor() {
  form.authors.push('')
}

function removeAuthor(idx) {
  form.authors.splice(idx, 1)
}

const SOURCE_NAMES = { openlibrary: 'Open Library', google_books: 'Google Books' }

// Búsqueda combinada en el backend (Open Library + Google Books).
async function searchByISBN() {
  if (!form.isbn?.trim()) return
  isbnAlert.value = null
  const isbn = toIsbn13(form.isbn)
  if (!isbn) {
    isbnAlert.value = { type: 'warning', text: 'El ISBN no es válido. Revisa los dígitos (10 o 13, sin errores de tipeo).' }
    return
  }
  isbnSearching.value = true
  checkDuplicates(isbn)
  try {
    const data = await booksStore.lookupIsbn(isbn)
    if (!data.found) {
      isbnAlert.value = {
        type: 'warning',
        text: data.unavailable_sources?.length
          ? 'Los servicios de búsqueda no respondieron. Intenta nuevamente o ingresa los datos manualmente.'
          : 'Libro no encontrado en Open Library ni en Google Books. Por favor, ingresa los datos manualmente.',
      }
      return
    }
    if (data.title) form.title = data.title
    if (data.authors?.length) form.authors = [...data.authors]
    if (data.publisher) form.publisher = data.publisher
    if (data.year) form.year = data.year
    if (data.cover_url) form.cover_url = data.cover_url
    if (data.page_count && !form.page_count) form.page_count = data.page_count

    const sources = [...new Set(Object.values(data.sources || {}))].map((s) => SOURCE_NAMES[s] || s)
    const origin = `Datos de ${sources.join(' + ')}`
    isbnAlert.value = data.authors?.length
      ? { type: 'success', text: `${origin}. Revísalos antes de guardar.` }
      : { type: 'info', text: `${origin}, sin autor. Ingrésalo manualmente.` }
  } catch {
    isbnAlert.value = { type: 'warning', text: 'No se pudo completar la búsqueda. Ingresa los datos manualmente.' }
  } finally {
    isbnSearching.value = false
  }
}

function validate() {
  errors.title = ''
  errors.authors = ''
  errors.page_count = ''
  errors.dates = ''
  let valid = true
  if (!form.title?.trim()) { errors.title = 'El título es obligatorio'; valid = false }
  const filled = form.authors.filter((a) => a.trim())
  if (!filled.length) { errors.authors = 'Debe indicar al menos un autor'; valid = false }
  const pages = form.page_count
  if (pages !== null && pages !== '' && (!Number.isInteger(pages) || pages < 1 || pages > 100000)) {
    errors.page_count = 'Ingresa un número entre 1 y 100000'
    valid = false
  }
  const { started_at, finished_at } = visibleDates()
  errors.dates = readingDatesError(started_at, finished_at)
  if (errors.dates) valid = false
  return valid
}

// Solo se envían las fechas visibles para el estado elegido.
function visibleDates() {
  return {
    started_at: form.reading_status !== 'Quiero leer' ? form.started_at : '',
    finished_at: form.reading_status === 'Leído' ? form.finished_at : '',
  }
}

// --- Portada ---------------------------------------------------------------
// La imagen elegida se comprime al instante, pero se sube recién al guardar:
// así no quedan imágenes huérfanas si el usuario cancela el formulario.
const coverInput = ref(null)
const pendingCover = ref(null)
const pendingCoverUrl = ref('')
const coverProcessing = ref(false)
const coverUploading = ref(false)
const coverError = ref('')
const coverBroken = ref(false)
const showCoverUrl = ref(false)
const coverUrlDraft = ref('')

const coverPreview = computed(() => pendingCoverUrl.value || form.cover_url)
watch(coverPreview, () => { coverBroken.value = false })

function clearPendingCover() {
  if (pendingCoverUrl.value) globalThis.URL.revokeObjectURL(pendingCoverUrl.value)
  pendingCover.value = null
  pendingCoverUrl.value = ''
}

onBeforeUnmount(clearPendingCover)

async function onCoverFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = '' // permite volver a elegir el mismo archivo
  if (!file) return
  coverError.value = ''
  coverProcessing.value = true
  try {
    const blob = await compressCoverImage(file)
    clearPendingCover()
    pendingCover.value = blob
    pendingCoverUrl.value = globalThis.URL.createObjectURL(blob)
    showCoverUrl.value = false
  } catch (err) {
    coverError.value = err instanceof CoverImageError ? err.message : 'No se pudo procesar la imagen.'
  } finally {
    coverProcessing.value = false
  }
}

function removeCover() {
  clearPendingCover()
  form.cover_url = ''
  coverError.value = ''
}

function toggleCoverUrl() {
  showCoverUrl.value = !showCoverUrl.value
  coverUrlDraft.value = ''
  coverError.value = ''
}

function applyCoverUrl() {
  const url = coverUrlDraft.value.trim()
  if (!/^https?:\/\/\S+$/i.test(url) || url.length > 500) {
    coverError.value = 'Ingresa una URL válida que empiece con http:// o https://'
    return
  }
  clearPendingCover()
  form.cover_url = url
  coverError.value = ''
  showCoverUrl.value = false
}

async function handleSubmit() {
  if (!validate()) return
  if (pendingCover.value) {
    coverError.value = ''
    coverUploading.value = true
    try {
      form.cover_url = await booksStore.uploadCover(pendingCover.value)
      clearPendingCover()
    } catch (err) {
      coverError.value = err.response?.data?.detail || 'No se pudo subir la portada. Intenta nuevamente.'
      return
    } finally {
      coverUploading.value = false
    }
  }
  emit('submit', {
    title: form.title.trim(),
    authors: form.authors.map((a) => a.trim()).filter(Boolean),
    isbn: form.isbn || null,
    publisher: form.publisher || null,
    year: form.year || null,
    genre: form.genre || null,
    cover_url: form.cover_url || null,
    reading_status: form.reading_status || 'Quiero leer',
    page_count: form.page_count || null,
    formats: [...form.formats],
    started_at: visibleDates().started_at || null,
    finished_at: visibleDates().finished_at || null,
  })
}
</script>

<style scoped>
.cover-preview-frame {
  width: 96px;
  height: 144px;
  flex-shrink: 0;
}

.cover-preview-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
