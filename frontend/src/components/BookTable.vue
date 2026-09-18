<template>
  <div class="table-responsive">
    <table class="table table-hover align-middle mb-0">
      <thead class="table-light">
        <tr>
          <th style="width: 56px"></th>
          <th>Título</th>
          <th>Autor</th>
          <th>Género</th>
          <th>Año</th>
          <th>ISBN</th>
          <th>Estado</th>
          <th>Valoración</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="book in books"
          :key="book.id"
          class="book-row"
          role="button"
          @click="$router.push(`/books/${book.id}`)"
        >
          <td>
            <img
              v-if="book.cover_url"
              :src="book.cover_url"
              :alt="book.title"
              class="rounded book-table-cover"
              style="width: 36px; height: 48px;"
            />
            <span v-else class="d-inline-block text-center book-table-placeholder">📖</span>
          </td>
          <td class="fw-semibold text-truncate" style="max-width: 250px" :title="book.title">
            {{ book.title }}
          </td>
          <td class="text-muted text-truncate" style="max-width: 200px">
            {{ book.authors?.join(', ') }}
          </td>
          <td>
            <span v-if="book.genre" class="badge genre-badge">{{ book.genre }}</span>
          </td>
          <td class="text-muted">{{ book.year }}</td>
          <td class="text-muted small">{{ book.isbn }}</td>
          <td>
            <span class="badge" :class="statusClass(book.reading_status)">
              {{ book.reading_status || 'Quiero leer' }}
            </span>
          </td>
          <td class="text-nowrap"><BookRating :rating="book.rating" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import BookRating from './BookRating.vue'

defineProps({
  books: { type: Array, required: true },
})

function statusClass(status) {
  switch (status) {
    case 'Leyendo': return 'bg-warning text-dark'
    case 'Leído': return 'bg-success'
    default: return 'bg-info text-dark'
  }
}
</script>

<style scoped>
.book-row {
  transition: background-color 0.15s ease;
}
.book-row:hover {
  background-color: #f5f7ff;
}
.book-table-cover {
  object-fit: contain;
  object-position: center;
  background: linear-gradient(180deg, #f8f9fa 0%, #eef2f6 100%);
  padding: 2px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.book-table-placeholder {
  width: 36px;
  font-size: 1.5rem;
}
.genre-badge {
  color: #465273;
  background: #edf0f6;
}
</style>
