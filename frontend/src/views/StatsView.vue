<template>
  <div class="app-shell">
    <div class="container py-4 py-md-5">
      <nav class="mb-4"><RouterLink to="/library">← Volver a mi biblioteca</RouterLink></nav>

      <div class="d-flex flex-column flex-md-row align-items-md-end justify-content-between gap-3 mb-4">
        <div>
          <p class="page-kicker mb-1">Tus lecturas</p>
          <h1 class="page-title fw-bold mb-1">Estadísticas y metas</h1>
          <p class="text-muted mb-0">Tu avance del año y un resumen de toda tu biblioteca.</p>
        </div>
        <div v-if="stats" class="d-flex align-items-center gap-2">
          <label for="stats-year" class="form-label mb-0 small text-muted">Año</label>
          <select id="stats-year" v-model.number="year" class="form-select form-select-sm" style="width: auto">
            <option v-for="y in stats.available_years" :key="y" :value="y">{{ y }}</option>
          </select>
        </div>
      </div>

      <div v-if="statsStore.loading && !stats" class="text-center py-5">
        <div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando…</span></div>
      </div>

      <div v-else-if="statsStore.error && !stats" class="alert alert-danger">
        {{ statsStore.error }}
        <button type="button" class="btn btn-link btn-sm" @click="load">Reintentar</button>
      </div>

      <template v-else-if="stats">
        <div v-if="actionError" class="alert alert-danger py-2" role="alert">{{ actionError }}</div>

        <div v-if="library.read_without_date" class="alert alert-info d-flex flex-wrap align-items-center gap-2" data-test="undated-alert">
          <span>
            ℹ️ {{ library.read_without_date }}
            {{ library.read_without_date === 1 ? 'libro leído no tiene' : 'libros leídos no tienen' }}
            fecha de término y no cuentan en las estadísticas del año.
          </span>
          <RouterLink :to="{ name: 'Library', query: { sin_fecha: '1' } }" class="btn btn-sm btn-outline-primary">
            Completar fechas
          </RouterLink>
        </div>

        <!-- Meta + indicadores -->
        <div class="row g-4 mb-4">
          <div class="col-lg-5">
            <GoalProgress
              :year="yearStats.year"
              :goal="yearStats.goal"
              :saving="savingGoal"
              @save="handleSaveGoal"
              @delete="handleDeleteGoal"
            />
          </div>
          <div class="col-lg-7">
            <div class="row g-3 h-100">
              <div v-for="tile in tiles" :key="tile.label" class="col-6 col-md-4">
                <div class="card stat-tile h-100">
                  <div class="card-body p-3">
                    <p class="stat-label mb-1">{{ tile.label }}</p>
                    <p class="stat-value mb-0">{{ tile.value }}</p>
                    <p v-if="tile.hint" class="text-muted small mb-0">{{ tile.hint }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Libros por mes -->
        <div class="mb-4">
          <StatBarChart
            :title="`Libros terminados por mes · ${yearStats.year}`"
            :subtitle="`${yearStats.books_read} ${yearStats.books_read === 1 ? 'libro' : 'libros'} en total`"
            :labels="MONTHS"
            :values="yearStats.by_month.map((m) => m.books)"
            :height="260"
            empty-text="Aún no terminas libros este año. Al marcar un libro como «Leído» aparecerá aquí."
          />
        </div>

        <div class="row g-4 mb-4">
          <div class="col-md-6">
            <StatBarChart
              title="Tu biblioteca por género"
              :labels="library.genres.map((g) => g.label)"
              :values="library.genres.map((g) => g.count)"
              horizontal
              :height="Math.max(160, library.genres.length * 34)"
              empty-text="Aún no tienes libros en tu biblioteca."
            />
          </div>
          <div class="col-md-6">
            <StatBarChart
              title="Tus valoraciones"
              :subtitle="ratingSubtitle"
              :labels="['1 ★', '2 ★', '3 ★', '4 ★', '5 ★']"
              :values="ratingValues"
              empty-text="Aún no has valorado libros."
            />
          </div>
        </div>

        <div class="row g-4">
          <div class="col-md-6">
            <div class="card h-100">
              <div class="card-body p-4">
                <h2 class="h6 fw-bold mb-3">Autores más leídos · {{ yearStats.year }}</h2>
                <ol v-if="yearStats.top_authors.length" class="list-unstyled mb-0">
                  <li
                    v-for="(author, i) in yearStats.top_authors"
                    :key="author.label"
                    class="d-flex justify-content-between py-2 border-bottom"
                  >
                    <span><span class="text-muted me-2">{{ i + 1 }}.</span>{{ author.label }}</span>
                    <span class="text-muted small">{{ author.count }} {{ author.count === 1 ? 'libro' : 'libros' }}</span>
                  </li>
                </ol>
                <p v-else class="text-muted small mb-0">Sin libros terminados este año.</p>
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="card h-100">
              <div class="card-body p-4">
                <h2 class="h6 fw-bold mb-3">Leyendo ahora</h2>
                <ul v-if="library.currently_reading.length" class="list-unstyled mb-0">
                  <li
                    v-for="book in library.currently_reading"
                    :key="book.id"
                    class="d-flex justify-content-between align-items-center gap-2 py-2 border-bottom"
                  >
                    <RouterLink :to="`/books/${book.id}`" class="text-truncate">{{ book.title }}</RouterLink>
                    <span class="text-muted small text-nowrap">
                      <template v-if="book.days_reading !== null">
                        {{ book.days_reading === 0 ? 'desde hoy' : `${book.days_reading} ${book.days_reading === 1 ? 'día' : 'días'}` }}
                      </template>
                      <template v-else>sin fecha de inicio</template>
                    </span>
                  </li>
                </ul>
                <p v-else class="text-muted small mb-0">No estás leyendo ningún libro en este momento.</p>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useStatsStore } from '@/stores/stats'
import GoalProgress from '@/components/GoalProgress.vue'
import StatBarChart from '@/components/StatBarChart.vue'

const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const statsStore = useStatsStore()
const year = ref(new Date().getFullYear())
const savingGoal = ref(false)
const actionError = ref('')

const stats = computed(() => statsStore.stats)
const yearStats = computed(() => stats.value.year_stats)
const library = computed(() => stats.value.library)

const numberFormat = new Intl.NumberFormat('es-CL')

const tiles = computed(() => [
  { label: `Leídos en ${yearStats.value.year}`, value: yearStats.value.books_read },
  { label: 'Páginas leídas', value: numberFormat.format(yearStats.value.pages_read) },
  {
    label: 'Días por libro',
    value: yearStats.value.avg_days_to_finish ?? '—',
    hint: yearStats.value.avg_days_to_finish === null ? 'Requiere fechas de inicio' : 'promedio',
  },
  { label: 'Leyendo ahora', value: library.value.reading },
  { label: 'Por leer', value: library.value.want_to_read },
  {
    label: 'Valoración media',
    value: library.value.avg_rating !== null ? `${library.value.avg_rating.toFixed(1)} ★` : '—',
    hint: `${library.value.rated_books} valorados`,
  },
])

const ratingValues = computed(() => [1, 2, 3, 4, 5].map(
  (r) => library.value.ratings.find((x) => x.rating === r)?.count ?? 0,
))

const ratingSubtitle = computed(() => (
  library.value.rated_books ? `${library.value.rated_books} libros valorados de ${library.value.total_books}` : ''
))

async function load() {
  try {
    await statsStore.fetchStats(year.value)
  } catch { /* el error se muestra desde el store */ }
}

async function runGoalAction(action) {
  savingGoal.value = true
  actionError.value = ''
  try {
    await action()
    await statsStore.fetchStats(year.value)
  } catch {
    actionError.value = 'No se pudo guardar la meta. Intenta nuevamente.'
  } finally {
    savingGoal.value = false
  }
}

function handleSaveGoal(target) {
  return runGoalAction(() => statsStore.saveGoal(year.value, target))
}

function handleDeleteGoal() {
  return runGoalAction(() => statsStore.deleteGoal(year.value))
}

watch(year, load)
onMounted(load)
</script>

<style scoped>
.stat-tile {
  border: 0;
  box-shadow: 0 8px 28px rgba(32, 48, 83, 0.06);
}
.stat-label {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.stat-value {
  color: var(--ink);
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.2;
}
</style>
