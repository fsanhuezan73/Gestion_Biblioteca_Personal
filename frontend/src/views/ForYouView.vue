<template>
  <div class="app-shell">
    <div class="container py-4">
      <div class="mb-4">
        <p class="page-kicker mb-1">Recomendaciones</p>
        <h1 class="page-title fw-bold mb-1">Tu próxima lectura</h1>
        <p class="text-muted mb-0">Ideas para seguir leyendo, según tus gustos.</p>
      </div>

      <div
        v-if="toastMessage"
        class="alert alert-success alert-dismissible fade show"
        role="alert"
      >
        {{ toastMessage }}
        <button type="button" class="btn-close" aria-label="Cerrar" @click="toastMessage = ''" />
      </div>

      <RecommendationsSection @added="onAdded" />

      <div v-if="store.unavailable" class="alert alert-warning" role="alert" data-test="recommendations-unavailable">
        Las recomendaciones no están disponibles en este momento. Intenta más tarde.
      </div>
      <div v-else-if="!store.data" class="text-center py-5" role="status" data-test="recommendations-loading">
        <div class="spinner-border text-primary" aria-hidden="true" />
        <p class="text-muted small mt-2 mb-0">Cargando recomendaciones…</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import RecommendationsSection from '@/components/RecommendationsSection.vue'
import { useRecommendationsStore } from '@/stores/recommendations'

const store = useRecommendationsStore()
const toastMessage = ref('')

function onAdded(book) {
  toastMessage.value = `«${book.title}» se agregó a Quiero leer.`
}
</script>
