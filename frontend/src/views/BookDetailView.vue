<template>
  <div class="container py-4 py-md-5" style="max-width: 760px">
    <RouterLink to="/library" class="btn btn-outline-secondary btn-sm mb-4">← Volver</RouterLink>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" />
    </div>

    <div v-else-if="book" class="card">
      <div class="card-body p-4 p-md-5">
        <!-- Portada -->
        <div
          class="d-flex align-items-center justify-content-center rounded mb-4 overflow-hidden book-detail-cover"
        >
          <img
            v-if="book.cover_url"
            :src="book.cover_url"
            :alt="book.title"
            class="book-detail-cover-image"
          />
          <span class="book-detail-placeholder" v-else>📖</span>
        </div>

        <p class="page-kicker mb-1">Ficha del libro</p>
        <h2 class="fw-bold mb-1">{{ book.title }}</h2>
        <p class="text-muted fs-5 mb-3">{{ book.authors?.join(', ') }}</p>

        <!-- Estado de lectura -->
        <div class="mb-4">
          <label class="form-label fw-semibold small text-uppercase text-muted">Estado de lectura</label>
          <select
            class="form-select"
            style="max-width: 220px"
            :value="book.reading_status || 'Quiero leer'"
            :disabled="statusUpdating"
            @change="handleStatusChange($event.target.value)"
          >
            <option value="Quiero leer">📘 Quiero leer</option>
            <option value="Leyendo">📖 Leyendo</option>
            <option value="Leído">✅ Leído</option>
          </select>
        </div>

        <ul class="list-group list-group-flush mb-4">
          <li v-if="book.publisher" class="list-group-item px-0">
            <strong>Editorial:</strong> {{ book.publisher }}
          </li>
          <li v-if="book.genre" class="list-group-item px-0">
            <strong>Género:</strong> {{ book.genre }}
          </li>
          <li v-if="book.year" class="list-group-item px-0">
            <strong>Año:</strong> {{ book.year }}
          </li>
          <li v-if="book.isbn" class="list-group-item px-0">
            <strong>ISBN:</strong> {{ book.isbn }}
          </li>
        </ul>

        <div class="d-flex gap-2">
          <RouterLink :to="`/books/${book.id}/edit`" class="btn btn-primary">
            ✏️ Editar
          </RouterLink>
          <button class="btn btn-outline-danger" @click="showModal = true">
            🗑️ Eliminar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de confirmación de eliminación -->
    <ConfirmModal
      v-if="showModal"
      title="Eliminar libro"
      message="¿Estás seguro de que deseas eliminar este libro? Esta acción no se puede deshacer."
      confirm-label="Sí, eliminar"
      :loading="deleteLoading"
      @confirm="handleDelete"
      @cancel="showModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBooksStore } from '@/stores/books'
import ConfirmModal from '@/components/ConfirmModal.vue'

const route = useRoute()
const router = useRouter()
const booksStore = useBooksStore()

const book = ref(null)
const loading = ref(true)
const showModal = ref(false)
const deleteLoading = ref(false)
const statusUpdating = ref(false)

onMounted(async () => {
  try {
    book.value = await booksStore.getBook(Number(route.params.id))
  } catch {
    router.push('/library')
  } finally {
    loading.value = false
  }
})

async function handleStatusChange(newStatus) {
  statusUpdating.value = true
  try {
    book.value = await booksStore.updateReadingStatus(book.value.id, newStatus)
  } finally {
    statusUpdating.value = false
  }
}

async function handleDelete() {
  deleteLoading.value = true
  try {
    await booksStore.deleteBook(book.value.id)
    router.push({ name: 'Library', query: { success: 'Libro eliminado correctamente.' } })
  } finally {
    deleteLoading.value = false
    showModal.value = false
  }
}
</script>

<style scoped>
.book-detail-cover {
  width: min(100%, 280px);
  height: 360px;
  margin: 0 auto 1.5rem;
  background: linear-gradient(145deg, #eef1fb 0%, #f8f9fc 100%);
  border: 1px solid #e2e7f0;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.3);
  aspect-ratio: 3 / 4;
}
.book-detail-cover-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
  padding: 1rem;
}
.book-detail-placeholder {
  font-size: 5rem;
}
</style>
