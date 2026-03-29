<template>
  <div class="container py-4">
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-light bg-white rounded shadow-sm px-3 mb-4">
      <span class="navbar-brand fw-bold">📚 Biblioteca Personal</span>
      <div class="ms-auto d-flex align-items-center gap-2">
        <RouterLink to="/books/add" class="btn btn-primary btn-sm">
          + Añadir libro
        </RouterLink>
        <button class="btn btn-outline-secondary btn-sm" @click="handleLogout">
          Cerrar sesión
        </button>
      </div>
    </nav>

    <!-- Toast de éxito -->
    <div
      v-if="toastMessage"
      class="alert alert-success alert-dismissible fade show"
      role="alert"
    >
      {{ toastMessage }}
      <button type="button" class="btn-close" @click="toastMessage = ''" />
    </div>

    <!-- Barra de búsqueda y filtros -->
    <div class="card shadow-sm mb-4">
      <div class="card-body pb-2">
        <!-- Búsqueda global -->
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

        <!-- Toggle filtros avanzados -->
        <button
          class="btn btn-sm btn-link text-decoration-none p-0 mb-2"
          @click="showFilters = !showFilters"
        >
          {{ showFilters ? '▼' : '▶' }} Filtros Avanzados
          <span v-if="hasActiveFilters" class="badge bg-primary ms-1">{{ activeFilterCount }}</span>
        </button>

        <!-- Panel de filtros avanzados -->
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

    <!-- Grid de libros -->
    <div v-else class="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4 g-4">
      <div v-for="book in booksStore.books" :key="book.id" class="col">
        <BookCard :book="book" />
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
