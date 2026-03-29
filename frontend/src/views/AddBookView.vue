<template>
  <div class="container py-4" style="max-width: 600px">
    <div class="d-flex align-items-center mb-4">
      <RouterLink to="/library" class="btn btn-outline-secondary btn-sm me-3">← Volver</RouterLink>
      <h2 class="mb-0 fw-bold">Añadir nuevo libro</h2>
    </div>

    <div class="card shadow-sm">
      <div class="card-body p-4">
        <BookForm
          :loading="loading"
          :api-error="apiError"
          submit-label="Guardar libro"
          @submit="handleSubmit"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useBooksStore } from '@/stores/books'
import BookForm from '@/components/BookForm.vue'

const router = useRouter()
const booksStore = useBooksStore()
const loading = ref(false)
const apiError = ref('')

async function handleSubmit(formData) {
  apiError.value = ''
  loading.value = true
  try {
    await booksStore.addBook(formData)
    router.push({ name: 'Library', query: { success: 'El libro se ha guardado exitosamente.' } })
  } catch (err) {
    apiError.value = err.response?.data?.detail || 'Error al guardar el libro.'
  } finally {
    loading.value = false
  }
}
</script>
