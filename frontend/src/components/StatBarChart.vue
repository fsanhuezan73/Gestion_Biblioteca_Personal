<template>
  <div class="card h-100">
    <div class="card-body p-4">
      <h2 class="h6 fw-bold mb-1">{{ title }}</h2>
      <p v-if="subtitle" class="text-muted small mb-3">{{ subtitle }}</p>
      <div v-if="hasData" class="chart-box" :style="{ height: `${height}px` }">
        <Bar :data="chartData" :options="chartOptions" :aria-label="title" role="img" />
      </div>
      <p v-else class="text-muted small mb-0 py-4 text-center">{{ emptyText }}</p>

      <!-- Vista de tabla para lectores de pantalla -->
      <table v-if="hasData" class="visually-hidden">
        <caption>{{ title }}</caption>
        <thead><tr><th scope="col">Categoría</th><th scope="col">{{ seriesLabel }}</th></tr></thead>
        <tbody>
          <tr v-for="(label, i) in labels" :key="label"><td>{{ label }}</td><td>{{ values[i] }}</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { BarElement, CategoryScale, Chart as ChartJS, LinearScale, Tooltip } from 'chart.js'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip)

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  labels: { type: Array, required: true },
  values: { type: Array, required: true },
  seriesLabel: { type: String, default: 'Libros' },
  horizontal: { type: Boolean, default: false },
  height: { type: Number, default: 240 },
  emptyText: { type: String, default: 'Aún no hay datos.' },
})

// Una sola serie: un único color de marca (validado ≥ 3:1 sobre la superficie).
const BRAND = '#3c4fa3'
const GRID = '#e2e7f0'
const MUTED = '#65718a'

const hasData = computed(() => props.values.some((v) => v > 0))

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [{
    label: props.seriesLabel,
    data: props.values,
    backgroundColor: BRAND,
    hoverBackgroundColor: '#293b82',
    borderRadius: 4,
    borderSkipped: 'start',
    maxBarThickness: props.horizontal ? 18 : 28,
  }],
}))

const chartOptions = computed(() => {
  const valueAxis = {
    beginAtZero: true,
    ticks: { precision: 0, color: MUTED },
    grid: { color: GRID },
    border: { display: false },
  }
  const categoryAxis = {
    // Etiquetas horizontales también en celular (12 meses caben a 10px).
    ticks: props.horizontal
      ? { color: MUTED }
      : { color: MUTED, maxRotation: 0, autoSkip: false, font: { size: 10 } },
    grid: { display: false },
    border: { color: GRID },
  }
  return {
    indexAxis: props.horizontal ? 'y' : 'x',
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    scales: props.horizontal ? { x: valueAxis, y: categoryAxis } : { x: categoryAxis, y: valueAxis },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#18233a',
        padding: 10,
        displayColors: false,
        callbacks: { label: (ctx) => `${props.seriesLabel}: ${ctx.parsed[props.horizontal ? 'x' : 'y']}` },
      },
    },
  }
})
</script>

<style scoped>
.chart-box {
  position: relative;
}
</style>
