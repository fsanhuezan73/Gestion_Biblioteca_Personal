<template>
  <!-- Scroll propio (vertical y horizontal) para que el encabezado quede fijo con position: sticky. -->
  <div class="table-responsive book-table-scroll" data-test="book-table-scroll">
    <table class="table table-hover align-middle mb-0">
      <thead class="table-light book-table-head">
        <tr>
          <th style="width: 56px"><span class="visually-hidden">Portada</span></th>
          <th
            v-for="column in columns"
            :key="column.key"
            :class="column.class"
            :aria-sort="ariaSort(column.key)"
          >
            <button
              type="button"
              class="sort-button"
              :class="{ active: sort?.key === column.key }"
              :data-test="`sort-${column.key}`"
              :title="`Ordenar por ${column.label}`"
              @click="emit('update:sort', nextSort(sort, column.key))"
            >
              {{ column.label }}
              <span class="sort-icon" aria-hidden="true">{{ sortIcon(column.key) }}</span>
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="book in sortedBooks"
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
          <td class="text-muted small d-none d-xl-table-cell">{{ book.isbn }}</td>
          <td>
            <span class="badge" :class="statusClass(book.reading_status)">
              {{ book.reading_status || 'Quiero leer' }}
            </span>
          </td>
          <td class="small text-nowrap" data-test="reading-summary">
            <template v-if="readingSummary(book)">
              <span :class="{ 'text-muted': readingSummary(book).missing }">
                <span class="text-muted">{{ readingSummary(book).label }}:</span> {{ readingSummary(book).date }}
              </span>
              <div v-if="readingSummary(book).daysDetail" class="text-muted">{{ readingSummary(book).daysDetail }}</div>
            </template>
          </td>
          <td class="text-nowrap"><BookRating :rating="book.rating" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import BookRating from './BookRating.vue'
import { readingSummary } from '@/utils/dates'
import { SORT_COLUMNS, nextSort, sortBooks } from '@/utils/bookSort'

const props = defineProps({
  books: { type: Array, required: true },
  // { key, direction: 'asc' | 'desc' } o null (orden recibido de la API).
  sort: { type: Object, default: null },
})
const emit = defineEmits(['update:sort'])

const columns = Object.entries(SORT_COLUMNS).map(([key, { label }]) => ({
  key,
  label,
  class: key === 'isbn' ? 'd-none d-xl-table-cell' : '',
}))

const sortedBooks = computed(() => sortBooks(props.books, props.sort?.key, props.sort?.direction))

function ariaSort(key) {
  if (props.sort?.key !== key) return 'none'
  return props.sort.direction === 'desc' ? 'descending' : 'ascending'
}

function sortIcon(key) {
  if (props.sort?.key !== key) return '↕'
  return props.sort.direction === 'desc' ? '▼' : '▲'
}

function statusClass(status) {
  switch (status) {
    case 'Leyendo': return 'bg-warning text-dark'
    case 'Leído': return 'bg-success'
    default: return 'bg-info text-dark'
  }
}
</script>

<style scoped>
.book-table-scroll {
  max-height: calc(100vh - 6rem);
  overflow-y: auto;
  border-radius: inherit;
}
.book-table-head th {
  position: sticky;
  top: 0;
  z-index: 2;
  box-shadow: inset 0 -1px 0 var(--border);
  white-space: nowrap;
}
.sort-button {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.sort-button:hover,
.sort-button:focus-visible {
  color: var(--brand);
}
.sort-button:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
  border-radius: 0.25rem;
}
.sort-icon {
  font-size: 0.7rem;
  opacity: 0.35;
}
.sort-button.active {
  color: var(--brand-dark);
}
.sort-button.active .sort-icon {
  opacity: 1;
}
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
