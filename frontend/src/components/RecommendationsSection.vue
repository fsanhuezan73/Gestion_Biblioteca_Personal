<template>
  <section v-if="!store.unavailable && store.data" class="card recommendations-panel mb-4" data-test="recommendations">
    <div class="card-body p-3 p-md-4">
      <div class="d-flex flex-column flex-md-row align-items-md-center justify-content-between gap-2 mb-3">
        <div>
          <h2 class="h5 fw-bold mb-1">
            ✨ Para ti
            <span class="badge ai-badge ms-1 align-middle" data-test="ai-label">Generado por IA</span>
          </h2>
          <p class="text-muted small mb-0">Sugerencias a partir de los libros que leíste y valoraste.</p>
        </div>
        <div class="d-flex flex-column align-items-md-end gap-1">
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="!store.canGenerate"
            data-test="generate-recommendations"
            @click="store.generate()"
          >
            <span v-if="store.generating" class="spinner-border spinner-border-sm me-1" aria-hidden="true" />
            Recomiéndame qué leer
          </button>
          <span v-if="store.enoughRatedBooks" class="small text-muted" data-test="remaining">
            {{ remainingText }}
          </span>
        </div>
      </div>

      <p v-if="!store.enoughRatedBooks" class="alert alert-light border small mb-0" data-test="not-enough">
        Valora al menos {{ store.data.min_rated_books }} libros leídos para recibir recomendaciones
        (llevas {{ store.data.rated_books }}). Abre un libro leído y asígnale estrellas.
      </p>

      <p v-if="store.generating" class="small text-muted mb-3" role="status">
        Buscando libros para ti… puede tardar hasta un minuto.
      </p>

      <div v-if="store.error" class="alert alert-warning small" role="alert" data-test="recommendations-error">
        {{ store.error }}
      </div>
      <div v-if="addError" class="alert alert-danger small" role="alert">{{ addError }}</div>

      <div v-if="store.items.length" class="row row-cols-1 row-cols-md-2 row-cols-xl-3 g-3">
        <div v-for="book in store.items" :key="book.isbn || book.title" class="col">
          <article class="card h-100 recommendation-card" data-test="recommendation">
            <div class="card-body d-flex gap-3">
              <div class="rec-cover flex-shrink-0 bg-light d-flex align-items-center justify-content-center">
                <img v-if="book.cover_url" :src="book.cover_url" :alt="book.title" loading="lazy" />
                <span v-else>📖</span>
              </div>
              <div class="d-flex flex-column min-w-0 flex-grow-1">
                <h3 class="h6 fw-bold mb-0">{{ book.title }}</h3>
                <p class="small text-muted mb-2">{{ book.authors.join(', ') }}<template v-if="book.year"> · {{ book.year }}</template></p>
                <p class="small mb-2" data-test="reason"><strong>Por qué:</strong> {{ book.reason }}</p>
                <template v-if="book.synopsis">
                  <p class="small text-muted mb-1 synopsis" :class="{ expanded: expanded[key(book)] }" data-test="synopsis">
                    {{ book.synopsis }}
                  </p>
                  <button
                    v-if="book.synopsis.length > 180"
                    type="button"
                    class="btn btn-link btn-sm p-0 align-self-start mb-2"
                    @click="toggle(book)"
                  >
                    {{ expanded[key(book)] ? 'Ver menos' : 'Ver sinopsis completa' }}
                  </button>
                </template>
                <div class="mt-auto">
                  <span v-if="book.in_library" class="badge text-bg-success" data-test="in-library">✓ En tu biblioteca</span>
                  <button
                    v-else
                    type="button"
                    class="btn btn-outline-primary btn-sm"
                    :disabled="store.isAdding(book)"
                    data-test="add-want-to-read"
                    @click="add(book)"
                  >
                    + Agregar a Quiero leer
                  </button>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>

      <p class="small text-muted mt-3 mb-0" data-test="ai-notice">
        Generado por IA. Solo se envían título, autor, género y estrellas; nunca tus notas.
        <template v-if="generatedText"> Última generación: {{ generatedText }}</template>
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRecommendationsStore } from '@/stores/recommendations'

const emit = defineEmits(['added'])
const store = useRecommendationsStore()
const expanded = reactive({})
const addError = ref('')

const remainingText = computed(() => {
  const { remaining_today: left, daily_limit: limit } = store.data
  if (left === 0) return 'Ya usaste las recomendaciones de hoy'
  return `Te quedan ${left} de ${limit} hoy`
})

const generatedText = computed(() => {
  const value = store.data?.generated_at
  if (!value) return ''
  return new Date(value).toLocaleString('es-CL', { dateStyle: 'medium', timeStyle: 'short' })
})

// Siempre se consulta al abrir «Para ti»: las valoraciones y el cupo diario
// pudieron cambiar desde la última vez (se muestra lo anterior mientras tanto).
onMounted(() => {
  store.fetchLatest()
})

function key(book) {
  return book.isbn || book.title
}

function toggle(book) {
  expanded[key(book)] = !expanded[key(book)]
}

async function add(book) {
  addError.value = ''
  try {
    await store.addToWantToRead(book)
    emit('added', book)
  } catch {
    addError.value = `No se pudo agregar «${book.title}». Intenta nuevamente.`
  }
}
</script>

<style scoped>
.recommendations-panel {
  border: 1px solid #e3e7ff;
  background: linear-gradient(180deg, #f8f9ff 0%, #fff 100%);
}
.ai-badge {
  background: #efe9ff;
  color: #5b3fc4;
  font-weight: 600;
  font-size: 0.7rem;
}
.recommendation-card {
  border-color: #eceff7;
}
.rec-cover {
  width: 64px;
  height: 96px;
  border-radius: 6px;
  overflow: hidden;
  font-size: 1.6rem;
}
.rec-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.min-w-0 {
  min-width: 0;
}
.synopsis {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-line;
}
.synopsis.expanded {
  -webkit-line-clamp: unset;
  display: block;
}
</style>
