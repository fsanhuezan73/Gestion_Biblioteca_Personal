<template>
  <div class="app-shell">
    <div class="container py-4 py-md-5">
      <nav class="app-navbar navbar navbar-expand-lg navbar-light bg-white px-3 py-2 mb-4 mb-md-5">
        <RouterLink to="/library" class="navbar-brand d-flex align-items-center gap-2 mb-0 text-decoration-none">
          <span class="brand-mark">📚</span>
          <span class="fw-bold fs-5 text-dark">Biblioteca Personal</span>
        </RouterLink>
        <div class="ms-auto d-flex align-items-center gap-2">
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
        <span v-if="booksStore.books.length" class="badge rounded-pill text-bg-light border px-3 py-2">
          {{ booksStore.books.length }} {{ booksStore.books.length === 1 ? 'libro' : 'libros' }}
        </span>
      </div>

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

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const booksStore = useBooksStore()

const toastMessage = ref(route.query.success || '')
const searchQuery = ref('')
const filterGenre = ref('')
const filterStatus = ref('')
const showFilters = ref(false)
const viewMode = ref('grid')

let searchTimeout = null

const hasActiveFilters = computed(() => filterGenre.value !== '' || filterStatus.value !== '')
const activeFilterCount = computed(() => (filterGenre.value ? 1 : 0) + (filterStatus.value ? 1 : 0))
const hasActiveSearch = computed(() => searchQuery.value.trim() !== '' || hasActiveFilters.value)

onMounted(() => {
  booksStore.fetchBooks()
  booksStore.fetchGenres()
})

function buildParams() {
  const params = {}
  if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
  if (filterGenre.value) params.genre = filterGenre.value
  if (filterStatus.value) params.reading_status = filterStatus.value
  return params
}

function applyFilters() {
  booksStore.fetchBooks(buildParams())
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
  booksStore.fetchBooks()
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
