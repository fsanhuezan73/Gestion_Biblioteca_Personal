<template>
  <section class="border-top pt-4 mb-4" aria-labelledby="personal-details-title">
    <h3 id="personal-details-title" class="h5">Mi valoración y notas</h3>
    <p id="personal-details-help" class="text-muted small">Solo tú puedes ver estos datos en tu biblioteca.</p>
    <form aria-describedby="personal-details-help" @submit.prevent="save">
      <fieldset :disabled="saving">
        <legend class="visually-hidden">Editar valoración y notas personales</legend>
        <div class="mb-3">
          <label for="personal-rating" class="form-label">Mi valoración</label>
          <select id="personal-rating" v-model="rating" class="form-select" style="max-width: 260px">
            <option :value="null">Sin valorar</option>
            <option v-for="value in 5" :key="value" :value="value">
              {{ '★'.repeat(value) }} — {{ value }} de 5
            </option>
          </select>
        </div>
        <div class="mb-3">
          <label for="personal-notes" class="form-label">Mis notas personales</label>
          <textarea
            id="personal-notes"
            v-model="notes"
            class="form-control"
            rows="6"
            aria-describedby="personal-notes-help"
            :aria-invalid="notesLength > 5000"
            placeholder="Escribe una reseña, una cita o lo que quieras recordar de este libro…"
          ></textarea>
          <div id="personal-notes-help" class="form-text" :class="{ 'text-danger': notesLength > 5000 }">
            {{ notesLength }} / 5000 caracteres. Puedes dejarlo vacío para borrar las notas.
          </div>
        </div>
        <p v-if="error" role="alert" class="alert alert-danger py-2">{{ error }}</p>
        <p v-if="success && !dirty" role="status" class="alert alert-success py-2">{{ success }}</p>
        <p v-if="dirty" class="small text-muted">Tienes cambios sin guardar.</p>
        <div class="d-flex gap-2 flex-wrap">
          <button class="btn btn-primary" type="submit" :disabled="!dirty || notesLength > 5000">
            {{ saving ? 'Guardando…' : 'Guardar valoración y notas' }}
          </button>
          <button class="btn btn-outline-secondary" type="button" :disabled="!dirty" @click="reset">
            Descartar cambios
          </button>
        </div>
      </fieldset>
    </form>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useBooksStore } from '@/stores/books'

const props = defineProps({ book: { type: Object, required: true } })
const emit = defineEmits(['saved'])
const booksStore = useBooksStore()
const rating = ref(null)
const notes = ref('')
const saving = ref(false)
const error = ref('')
const success = ref('')
const notesLength = computed(() => Array.from(notes.value).length)
const dirty = computed(() => rating.value !== (props.book.rating ?? null)
  || notes.value !== (props.book.personal_notes ?? ''))

function reset() {
  rating.value = props.book.rating ?? null
  notes.value = props.book.personal_notes ?? ''
  error.value = ''
  success.value = ''
}

// Cambiar el estado de lectura no debe borrar un borrador de notas.
watch(() => props.book.id, reset, { immediate: true })

async function save() {
  if (saving.value || !dirty.value) return
  error.value = ''
  success.value = ''
  if (notesLength.value > 5000) {
    error.value = 'Las notas no pueden superar los 5000 caracteres.'
    return
  }
  const changes = {}
  if (rating.value !== (props.book.rating ?? null)) changes.rating = rating.value
  if (notes.value !== (props.book.personal_notes ?? '')) changes.personal_notes = notes.value || null
  saving.value = true
  try {
    const updatedBook = await booksStore.updatePersonalDetails(props.book.id, changes)
    rating.value = updatedBook.rating ?? null
    notes.value = updatedBook.personal_notes ?? ''
    emit('saved', updatedBook)
    success.value = 'Valoración y notas guardadas.'
  } catch {
    error.value = 'No se pudieron guardar los cambios. Tus notas siguen aquí; vuelve a intentarlo.'
  } finally {
    saving.value = false
  }
}

defineExpose({ dirty })
</script>
