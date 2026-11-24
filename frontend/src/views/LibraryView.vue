<template>
  <div class="app-shell">
    <div class="container py-4 py-md-5">
      <nav class="app-navbar navbar navbar-expand-lg navbar-light bg-white px-3 py-2 mb-4 mb-md-5">
        <RouterLink to="/library" class="navbar-brand d-flex align-items-center gap-2 mb-0 text-decoration-none">
          <span class="brand-mark">📚</span>
          <span class="fw-bold fs-5 text-dark">Biblioteca Personal</span>
        </RouterLink>
        <div class="ms-auto d-flex flex-wrap justify-content-end align-items-center gap-2">
          <RouterLink to="/stats" class="btn btn-outline-secondary btn-sm">
            📊 Estadísticas
          </RouterLink>
          <RouterLink to="/account" class="btn btn-outline-secondary btn-sm">
            Mi cuenta
          </RouterLink>
          <RouterLink
            :to="{ name: 'AddBook', query: { scan: '1' } }"
            class="btn btn-outline-primary btn-sm"
            data-test="scan-shortcut"
          >
            📷 Escanear
          </RouterLink>
          <RouterLink to="/books/add" class="btn btn-primary btn-sm">
            + Añadir libro
          </RouterLink>
          <button class="btn btn-outline-secondary btn-sm" @click="handleLogout">
            Cerrar sesión
          </button>
        </div>
      </nav>

      <div
        v-if="toastMessage"
        class="alert alert-success alert-dismissible fade show"
        role="alert"
      >
        {{ toastMessage }}
        <button type="button" class="btn-close" @click="toastMessage = ''" />
      </div>

      <div class="d-flex flex-column flex-md-row align-items-md-end justify-content-between gap-3 mb-4">
        <div>
          <p class="page-kicker mb-1">Tu colección</p>
          <h1 class="page-title fw-bold mb-1">Todos tus libros, en un solo lugar</h1>
          <p class="text-muted mb-0">Explora, organiza y sigue el ritmo de tus lecturas.</p>
        </div>
        <div class="d-flex flex-wrap align-items-center gap-2">
          <RouterLink
            v-if="statsStore.stats"
            to="/stats"
            class="badge rounded-pill goal-chip px-3 py-2 text-decoration-none"
            data-test="goal-chip"
          >
            <template v-if="currentGoal">
              🎯 Meta {{ statsStore.stats.year_stats.year }}: {{ currentGoal.books_read }}/{{ currentGoal.target_books }}
            </template>
            <template v-else>🎯 Define tu meta {{ statsStore.stats.year_stats.year }}</template>
          </RouterLink>
          <span v-if="booksStore.books.length" class="badge rounded-pill text-bg-light border px-3 py-2">
            {{ booksStore.books.length }} {{ booksStore.books.length === 1 ? 'libro' : 'libros' }}
          </span>
        </div>
      </div>

      <div v-if="undatedOnly" class="alert alert-info d-flex flex-wrap align-items-center gap-2" data-test="undated-filter">
        <span>Mostrando libros leídos sin fecha de término. Abre cada uno y usa «Editar» para agregarla.</span>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="clearAll">Mostrar todos</button>
      </div>

      <RecommendationsSection @added="onRecommendationAdded" />

      <div class="card search-panel mb-4">
        <div class="card-body p-3 p-md-4">
          <div class="input-group mb-2">
            <span class="input-group-text bg-white"><i class="bi bi-search">🔍</i></span>
            <input
              v-model="searchQuery"
              type="text"
              class="form-control"
              placeholder="Buscar por título, autor, ISBN, año o género..."
              @input="debouncedSearch"
            />
            <button
              v-if="searchQuery || hasActiveFilters"
              class="btn btn-outline-secondary"
              type="button"
              @click="clearAll"
            >
              Limpiar
            </button>
          </div>

          <button
            class="btn btn-sm btn-link text-decoration-none p-0 mb-2"
            @click="showFilters = !showFilters"
          >
            {{ showFilters ? '▼' : '▶' }} Filtros Avanzados
            <span v-if="hasActiveFilters" class="badge bg-primary ms-1">{{ activeFilterCount }}</span>
          </button>

          <div v-if="showFilters" class="row g-2 mt-1 mb-2">
            <div class="col-sm-6">
              <label class="form-label small text-muted mb-1">Género</label>
              <select v-model="filterGenre" class="form-select form-select-sm" @change="applyFilters">
                <option value="">Todos los géneros</option>
                <option v-for="g in booksStore.genres" :key="g" :value="g">{{ g }}</option>
              </select>
            </div>
            <div class="col-sm-6">
              <label class="form-label small text-muted mb-1">Estado de lectura</label>
              <select v-model="filterStatus" class="form-select form-select-sm" @change="applyFilters">
                <option value="">Todos los estados</option>
                <option value="Quiero leer">📘 Quiero leer</option>
                <option value="Leyendo">📖 Leyendo</option>
                <option value="Leído">✅ Leído</option>
              </select>
            </div>
            <fieldset class="col-12">
              <legend class="form-label small text-muted mb-1">Formato</legend>
              <div class="d-flex flex-wrap column-gap-3 row-gap-1">
                <label v-for="{ code, label } in BOOK_FORMATS" :key="code" class="form-check small mb-0">
                  <input
                    v-model="filterFormats"
                    type="checkbox"
                    class="form-check-input"
                    :value="code"
                    @change="onFormatsChanged"
                  />
                  <span class="form-check-label">{{ label }}</span>
                </label>
                <label class="form-check small mb-0">
                  <input
                    v-model="withoutFormat"
                    type="checkbox"
                    class="form-check-input"
                    @change="onWithoutFormatChanged"
                  />
                  <span class="form-check-label">{{ WITHOUT_FORMAT_LABEL }}</span>
                </label>
              </div>
              <p class="form-text mb-0">Se muestran los libros que tienen todos los formatos seleccionados.</p>
            </fieldset>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="booksStore.loading" class="text-center py-5">
        <div class="spinner-border text-primary" />
      </div>

      <!-- Empty State: no hay libros en absoluto -->
      <EmptyState v-else-if="booksStore.books.length === 0 && !hasActiveSearch" />

      <!-- Empty State: sin resultados de búsqueda/filtro -->
      <div v-else-if="booksStore.books.length === 0 && hasActiveSearch" class="text-center py-5 my-4">
        <div style="font-size: 4rem">🔍</div>
        <h4 class="mt-3 fw-bold">No se encontraron libros con estos criterios</h4>
        <p class="text-muted mb-4">Intenta con otros términos de búsqueda o cambia los filtros.</p>
        <button class="btn btn-primary" @click="clearAll">
          Limpiar filtros
        </button>
      </div>

      <!-- Toggle vista + Grid/Tabla de libros -->
      <div v-else>
        <div class="d-flex justify-content-end mb-3">
          <div class="btn-group btn-group-sm" role="group" aria-label="Cambiar vista">
            <button
              type="button"
              class="btn"
              :class="viewMode === 'grid' ? 'btn-primary' : 'btn-outline-primary'"
              title="Vista cuadrícula"
              @click="viewMode = 'grid'"
            >☷ Cuadrícula</button>
            <button
              type="button"
              class="btn"
              :class="viewMode === 'table' ? 'btn-primary' : 'btn-outline-primary'"
              title="Vista tabla"
              @click="viewMode = 'table'"
            >☰ Tabla</button>
          </div>
        </div>

        <div v-if="viewMode === 'grid'" class="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4 g-4">
          <div v-for="book in booksStore.books" :key="book.id" class="col">
            <BookCard :book="book" />
          </div>
        </div>

        <div v-else class="card shadow-sm">
          <BookTable :books="booksStore.books" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useBooksStore } from '@/stores/books'
import BookCard from '@/components/BookCard.vue'
import BookTable from '@/components/BookTable.vue'
import EmptyState from '@/components/EmptyState.vue'
import RecommendationsSection from '@/components/RecommendationsSection.vue'
import { useStatsStore } from '@/stores/stats'
import { BOOK_FORMATS, WITHOUT_FORMAT_LABEL } from '@/utils/bookFormats'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const booksStore = useBooksStore()
const statsStore = useStatsStore()

const toastMessage = ref(route.query.success || '')
const searchQuery = ref('')
const filterGenre = ref('')
const filterStatus = ref('')
const filterFormats = ref([])
const withoutFormat = ref(false)
const showFilters = ref(false)
const viewMode = ref('grid')
const undatedOnly = ref(route.query.sin_fecha === '1')
const currentGoal = computed(() => statsStore.stats?.year_stats.goal ?? null)

let searchTimeout = null

const hasFormatFilter = computed(() => filterFormats.value.length > 0 || withoutFormat.value)
const activeFilterCount = computed(() => [filterGenre.value, filterStatus.value, hasFormatFilter.value].filter(Boolean).length)
const hasActiveFilters = computed(() => activeFilterCount.value > 0)
const hasActiveSearch = computed(
  () => searchQuery.value.trim() !== '' || hasActiveFilters.value || undatedOnly.value,
)

onMounted(() => {
  booksStore.fetchBooks(buildParams())
  booksStore.fetchGenres()
  // Indicador de meta: complementario, si falla no afecta a la biblioteca.
  statsStore.fetchStats().catch(() => {})
})

function buildParams() {
  const params = {}
  if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
  if (filterGenre.value) params.genre = filterGenre.value
  if (filterStatus.value) params.reading_status = filterStatus.value
  if (filterFormats.value.length) params.format = filterFormats.value
  if (withoutFormat.value) params.without_format = true
  if (undatedOnly.value) params.without_finish_date = true
  return params
}

function applyFilters() {
  booksStore.fetchBooks(buildParams())
}

function onFormatsChanged() {
  if (filterFormats.value.length) withoutFormat.value = false
  applyFilters()
}

function onWithoutFormatChanged() {
  if (withoutFormat.value) filterFormats.value = []
  applyFilters()
}

function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    applyFilters()
  }, 350)
}

function clearAll() {
  searchQuery.value = ''
  filterGenre.value = ''
  filterStatus.value = ''
  filterFormats.value = []
  withoutFormat.value = false
  if (undatedOnly.value) {
    undatedOnly.value = false
    router.replace({ name: 'Library' })
  }
  booksStore.fetchBooks()
}

function onRecommendationAdded(book) {
  toastMessage.value = `«${book.title}» se agregó a Quiero leer.`
  if (hasFormatFilter.value) applyFilters()
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.goal-chip {
  background: #e9edff;
  color: var(--brand-dark);
  font-weight: 600;
}
.goal-chip:hover {
  background: #dce2ff;
}
</style>
