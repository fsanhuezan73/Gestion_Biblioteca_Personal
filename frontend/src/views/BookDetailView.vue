<template>
  <div class="container py-4" style="max-width: 700px">
    <RouterLink to="/library" class="btn btn-outline-secondary btn-sm mb-4">← Volver</RouterLink>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" />
    </div>

    <div v-else-if="book" class="card shadow-sm">
      <div class="card-body p-4">
        <!-- Portada -->
        <div
          class="d-flex align-items-center justify-content-center bg-light rounded mb-4 overflow-hidden"
          style="height: 200px"
        >
          <img
            v-if="book.cover_url"
            :src="book.cover_url"
            :alt="book.title"
            style="max-height: 100%; max-width: 100%; object-fit: contain"
          />
          <span v-else style="font-size: 5rem">📖</span>
        </div>

        <h2 class="fw-bold mb-1">{{ book.title }}</h2>
        <p class="text-muted fs-5 mb-3">{{ book.authors?.join(', ') }}</p>

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

onMounted(async () => {
  try {
    book.value = await booksStore.getBook(Number(route.params.id))
  } catch {
    router.push('/library')
  } finally {
    loading.value = false
  }
})

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
