import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/utils/api'

export const useStatsStore = defineStore('stats', () => {
  const stats = ref(null)
  const loading = ref(false)
  const error = ref('')

  async function fetchStats(year) {
    loading.value = true
    error.value = ''
    try {
      const { data } = await api.get('/stats/', { params: year ? { year } : {} })
      stats.value = data
      return data
    } catch (err) {
      error.value = 'No se pudieron cargar las estadísticas. Intenta nuevamente.'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function saveGoal(year, targetBooks) {
    const { data } = await api.put(`/goals/${year}`, { target_books: targetBooks })
    return data
  }

  async function deleteGoal(year) {
    await api.delete(`/goals/${year}`)
  }

  return { stats, loading, error, fetchStats, saveGoal, deleteGoal }
})
