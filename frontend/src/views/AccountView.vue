<template>
  <div class="app-shell">
    <div class="container py-4 py-md-5">
      <nav class="mb-4"><RouterLink to="/library">← Volver a mi biblioteca</RouterLink></nav>
      <div class="card shadow-sm account-card mx-auto">
        <div class="card-body p-4 p-md-5">
          <p class="page-kicker mb-1">Mi cuenta</p>
          <h1 class="page-title fw-bold mb-2">Cambiar contraseña</h1>
          <p class="text-muted mb-4">Al guardarla, se cerrarán todas tus sesiones y deberás iniciar sesión nuevamente.</p>

          <form @submit.prevent="handleChange" novalidate>
            <div class="mb-3">
              <label for="currentPassword" class="form-label">Contraseña actual</label>
              <input
                id="currentPassword"
                v-model="form.currentPassword"
                type="password"
                class="form-control"
                :class="{ 'is-invalid': errors.currentPassword }"
                autocomplete="current-password"
                required
              />
              <div v-if="errors.currentPassword" class="invalid-feedback">{{ errors.currentPassword }}</div>
            </div>
            <div class="mb-3">
              <label for="newPassword" class="form-label">Nueva contraseña</label>
              <input
                id="newPassword"
                v-model="form.newPassword"
                type="password"
                class="form-control"
                :class="{ 'is-invalid': errors.newPassword }"
                autocomplete="new-password"
                required
              />
              <div v-if="errors.newPassword" class="invalid-feedback">{{ errors.newPassword }}</div>
            </div>
            <div class="mb-4">
              <label for="confirmPassword" class="form-label">Confirma la nueva contraseña</label>
              <input
                id="confirmPassword"
                v-model="form.confirmPassword"
                type="password"
                class="form-control"
                :class="{ 'is-invalid': errors.confirmPassword }"
                autocomplete="new-password"
                required
              />
              <div v-if="errors.confirmPassword" class="invalid-feedback">{{ errors.confirmPassword }}</div>
            </div>
            <div v-if="apiError" class="alert alert-danger" role="alert">{{ apiError }}</div>
            <button class="btn btn-primary" type="submit" :disabled="loading">
              {{ loading ? 'Guardando...' : 'Guardar nueva contraseña' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { newPasswordError } from '@/utils/password'

const router = useRouter()
const authStore = useAuthStore()
const form = reactive({ currentPassword: '', newPassword: '', confirmPassword: '' })
const errors = reactive({ currentPassword: '', newPassword: '', confirmPassword: '' })
const apiError = ref('')
const loading = ref(false)

async function handleChange() {
  errors.currentPassword = form.currentPassword ? '' : 'Ingresa tu contraseña actual'
  errors.newPassword = newPasswordError(form.newPassword)
  errors.confirmPassword = form.newPassword === form.confirmPassword
    ? '' : 'Las contraseñas no coinciden'
  apiError.value = ''
  if (errors.currentPassword || errors.newPassword || errors.confirmPassword) return

  loading.value = true
  try {
    await authStore.changePassword(form.currentPassword, form.newPassword)
    router.replace({ name: 'Login', query: { passwordChanged: '1' } })
  } catch (error) {
    apiError.value = error.response?.data?.detail || 'No se pudo cambiar la contraseña.'
  } finally {
    loading.value = false
  }
}
</script>
