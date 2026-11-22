<template>
  <div class="card goal-card h-100">
    <div class="card-body p-4">
      <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
        <div>
          <p class="page-kicker mb-1">Meta {{ year }}</p>
          <h2 class="h5 fw-bold mb-0">
            <template v-if="goal">{{ goal.books_read }} de {{ goal.target_books }} libros</template>
            <template v-else>Sin meta definida</template>
          </h2>
        </div>
        <button
          v-if="!editing"
          type="button"
          class="btn btn-outline-primary btn-sm"
          data-test="edit-goal"
          @click="startEdit"
        >
          {{ goal ? 'Editar meta' : 'Definir meta' }}
        </button>
      </div>

      <form v-if="editing" class="goal-form mb-3" @submit.prevent="submit">
        <label for="goal-target" class="form-label small">¿Cuántos libros quieres leer en {{ year }}?</label>
        <div class="d-flex gap-2 flex-wrap">
          <input
            id="goal-target"
            v-model.number="target"
            type="number"
            min="1"
            max="365"
            class="form-control"
            style="max-width: 120px"
            :class="{ 'is-invalid': formError }"
          />
          <button type="submit" class="btn btn-primary btn-sm" :disabled="saving">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1" />Guardar
          </button>
          <button type="button" class="btn btn-outline-secondary btn-sm" :disabled="saving" @click="editing = false">
            Cancelar
          </button>
          <button
            v-if="goal"
            type="button"
            class="btn btn-link btn-sm text-danger"
            :disabled="saving"
            @click="$emit('delete')"
          >
            Eliminar meta
          </button>
        </div>
        <div v-if="formError" class="text-danger small mt-1">{{ formError }}</div>
      </form>

      <template v-if="goal">
        <div
          class="progress goal-progress mb-2"
          role="progressbar"
          :aria-valuenow="goal.percent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`Avance de la meta: ${goal.percent}%`"
        >
          <div class="progress-bar" :style="{ width: `${goal.percent}%` }" />
        </div>
        <div class="d-flex justify-content-between small text-muted mb-3">
          <span>{{ goal.percent }}% completado</span>
          <span v-if="goal.remaining">Faltan {{ goal.remaining }}</span>
        </div>
        <p class="mb-0 small goal-status" :data-status="goal.status">
          <span aria-hidden="true">{{ statusInfo.icon }}</span> {{ statusInfo.text }}
        </p>
      </template>
      <p v-else-if="!editing" class="text-muted small mb-0">
        Define cuántos libros quieres leer este año y sigue tu avance mes a mes.
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  year: { type: Number, required: true },
  goal: { type: Object, default: null },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['save', 'delete'])

const editing = ref(false)
const target = ref(null)
const formError = ref('')

function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many}`
}

const statusInfo = computed(() => {
  const g = props.goal
  if (!g) return { icon: '', text: '' }
  const diff = Math.round(Math.abs(g.difference))
  switch (g.status) {
    case 'completed':
      return { icon: '🏆', text: '¡Meta cumplida! Felicitaciones.' }
    case 'ahead':
      return { icon: '✅', text: `Vas ${plural(diff, 'libro', 'libros')} adelantado respecto del ritmo esperado.` }
    case 'behind':
      return { icon: '⚠️', text: `Te faltan ${plural(diff, 'libro', 'libros')} para ir al día.` }
    case 'not_met':
      return { icon: '📕', text: `El año terminó con ${plural(g.books_read, 'libro leído', 'libros leídos')}.` }
    case 'upcoming':
      return { icon: '🗓️', text: 'Este año aún no comienza.' }
    default:
      return { icon: '👍', text: 'Vas al día con tu meta.' }
  }
})

function startEdit() {
  target.value = props.goal?.target_books ?? 12
  formError.value = ''
  editing.value = true
}

function submit() {
  const value = target.value
  if (!Number.isInteger(value) || value < 1 || value > 365) {
    formError.value = 'Ingresa un número entre 1 y 365'
    return
  }
  emit('save', value)
  editing.value = false
}

defineExpose({ startEdit })
</script>

<style scoped>
.goal-progress {
  height: 12px;
  border-radius: 999px;
  background: var(--canvas);
}
.goal-progress .progress-bar {
  background: var(--brand);
  border-radius: 999px;
}
.goal-status {
  color: var(--ink);
}
</style>
