<template>
  <div class="container py-4 py-md-5">
    <div class="d-flex align-items-center mb-4">
      <RouterLink :to="`/books/${route.params.id}`" class="btn btn-outline-secondary btn-sm me-3">
        ← Volver
      </RouterLink>
      <div>
        <p class="page-kicker mb-0">Tu colección</p>
        <h2 class="page-title mb-0 fw-bold">Editar libro</h2>
      </div>
    </div>

    <div v-if="loadingBook" class="text-center py-5">
      <div class="spinner-border text-primary" />
    </div>

    <div v-else class="card book-form-card">
      <div class="card-body p-4 p-md-5">
        <BookForm
          :initial-data="initialData"
          :loading="saving"
          :api-error="apiError"
          submit-label="Actualizar libro"
          @submit="handleSubmit"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBooksStore } from '@/stores/books'
import BookForm from '@/components/BookForm.vue'

const route = useRoute()
const router = useRouter()
const booksStore = useBooksStore()

const initialData = ref(null)
const loadingBook = ref(true)
const saving = ref(false)
const apiError = ref('')

onMounted(async () => {
  try {
    initialData.value = await booksStore.getBook(Number(route.params.id))
  } catch {
    router.push('/library')
  } finally {
    loadingBook.value = false
  }
})

async function handleSubmit(formData) {
  apiError.value = ''
  saving.value = true
  try {
    await booksStore.updateBook(Number(route.params.id), formData)
    router.push(`/books/${route.params.id}`)
  } catch (err) {
    apiError.value = err.response?.data?.detail || 'Error al actualizar el libro.'
  } finally {
    saving.value = false
  }
}
</script>
