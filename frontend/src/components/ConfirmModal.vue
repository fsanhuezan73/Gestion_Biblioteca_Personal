<template>
  <!-- Bootstrap Modal (visible inmediatamente al montarse) -->
  <div
    class="modal d-block"
    tabindex="-1"
    role="dialog"
    style="background: rgba(0, 0, 0, 0.5)"
    @click.self="$emit('cancel')"
  >
    <div class="modal-dialog modal-dialog-centered" role="document">
      <div class="modal-content">
        <div class="modal-header border-0 pb-0">
          <h5 class="modal-title fw-bold">{{ title }}</h5>
          <button type="button" class="btn-close" @click="$emit('cancel')" />
        </div>
        <div class="modal-body">
          <p class="mb-0">{{ message }}</p>
        </div>
        <div class="modal-footer border-0 pt-0">
          <button class="btn btn-outline-secondary" @click="$emit('cancel')">Cancelar</button>
          <button class="btn btn-danger" :disabled="loading" @click="$emit('confirm')">
            <span v-if="loading" class="spinner-border spinner-border-sm me-2" />
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: 'Confirmar acción' },
  message: { type: String, required: true },
  confirmLabel: { type: String, default: 'Confirmar' },
  loading: { type: Boolean, default: false },
})

defineEmits(['confirm', 'cancel'])
</script>
