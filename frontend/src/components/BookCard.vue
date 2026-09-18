<template>
  <RouterLink :to="`/books/${book.id}`" class="text-decoration-none">
    <div class="card h-100 book-card">
      <!-- Portada -->
      <div
        class="card-img-top d-flex align-items-center justify-content-center bg-light overflow-hidden book-cover-frame"
      >
        <img
          v-if="book.cover_url"
          :src="book.cover_url"
          :alt="book.title"
          class="book-cover-image"
        />
        <span v-else class="book-placeholder">📖</span>
      </div>
      <div class="card-body d-flex flex-column">
        <h6 class="card-title fw-bold text-dark mb-1 text-truncate" :title="book.title">
          {{ book.title }}
        </h6>
        <p class="card-text text-muted small mb-2 text-truncate">{{ book.authors?.join(', ') }}</p>
        <div class="mb-2"><BookRating :rating="book.rating" /></div>
        <div class="mt-auto d-flex gap-1 flex-wrap">
          <span v-if="book.genre" class="badge genre-badge">
            {{ book.genre }}
          </span>
          <span class="badge" :class="statusBadgeClass">
            {{ book.reading_status || 'Quiero leer' }}
          </span>
        </div>
      </div>
    </div>
  </RouterLink>
</template>

<script setup>
import { computed } from 'vue'
import BookRating from './BookRating.vue'

const props = defineProps({
  book: { type: Object, required: true },
})

const statusBadgeClass = computed(() => {
  switch (props.book.reading_status) {
    case 'Leyendo': return 'bg-warning text-dark'
    case 'Leído': return 'bg-success'
    default: return 'bg-info text-dark'
  }
})
</script>

<style scoped>
.book-card {
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
}
.book-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 18px 32px rgba(32, 48, 83, 0.14) !important;
}
.book-card:hover .book-cover-image {
  transform: scale(1.04);
}
.book-cover-frame {
  height: 220px;
  padding: 0.75rem;
  background: linear-gradient(145deg, #eef1fb 0%, #f8f9fc 100%);
  border-bottom: 1px solid #e2e7f0;
  aspect-ratio: 3 / 4;
}
.book-cover-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
  border-radius: 0.5rem;
  transition: transform 0.2s ease;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.08));
}
.book-placeholder {
  font-size: 3.5rem;
  opacity: 0.8;
}
.genre-badge {
  color: #465273;
  background: #edf0f6;
}
</style>
