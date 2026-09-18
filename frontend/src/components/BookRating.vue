<template>
  <span v-if="rating != null" class="text-warning" :aria-label="`${rating} de 5 estrellas`">
    <span aria-hidden="true">{{ '★'.repeat(rating) }}{{ '☆'.repeat(5 - rating) }}</span>
    <span class="text-muted small ms-1" aria-hidden="true">{{ rating }}/5</span>
  </span>
  <span v-else class="text-muted small">Sin valorar</span>
</template>

<script setup>
defineProps({ rating: { type: Number, default: null } })
</script>
