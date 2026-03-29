<template>
  <RouterLink :to="`/books/${book.id}`" class="text-decoration-none">
    <div class="card h-100 shadow-sm book-card">
      <!-- Portada -->
      <div
        class="card-img-top d-flex align-items-center justify-content-center bg-light overflow-hidden"
        style="height: 160px"
      >
        <img
          v-if="book.cover_url"
          :src="book.cover_url"
          :alt="book.title"
          style="height: 100%; width: 100%; object-fit: cover"
        />
        <span v-else style="font-size: 3.5rem">📖</span>
      </div>
      <div class="card-body d-flex flex-column">
        <h6 class="card-title fw-bold text-dark mb-1 text-truncate" :title="book.title">
          {{ book.title }}
        </h6>
        <p class="card-text text-muted small mb-2 text-truncate">{{ book.authors?.join(', ') }}</p>
        <div class="mt-auto d-flex gap-1 flex-wrap">
          <span v-if="book.genre" class="badge bg-secondary">
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
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  cursor: pointer;
}
.book-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12) !important;
}
</style>
