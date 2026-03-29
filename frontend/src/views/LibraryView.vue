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

    <!-- Loading -->
    <div v-if="booksStore.loading" class="text-center py-5">
      <div class="spinner-border text-primary" />
    </div>

    <!-- Empty State -->
    <EmptyState v-else-if="booksStore.books.length === 0" />

    <!-- Grid de libros -->
    <div v-else class="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4 g-4">
      <div v-for="book in booksStore.books" :key="book.id" class="col">
        <BookCard :book="book" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

onMounted(() => {
  booksStore.fetchBooks()
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
