<template>
  <div class="auth-page d-flex align-items-center justify-content-center p-3">
    <div class="card auth-card shadow-lg w-100">
      <div class="card-body p-4 p-md-5">
        <div class="auth-logo">📚</div>
        <p class="page-kicker text-center mb-1">Biblioteca Personal</p>
        <h1 class="card-title display-font text-center mb-2 fw-bold fs-2">Nueva contraseña</h1>
        <p class="text-center text-muted mb-4">Elige una contraseña para volver a entrar.</p>

        <div v-if="success" class="alert alert-success" role="status">
          Contraseña actualizada. Las sesiones anteriores se cerraron.
        </div>
        <div v-else-if="!resetToken" class="alert alert-danger" role="alert">
          Este enlace no es válido. Solicita uno nuevo.
        </div>
        <form v-else @submit.prevent="handleReset" novalidate>
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
            <label for="confirmPassword" class="form-label">Confirma la contraseña</label>
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
          <button type="submit" class="btn btn-primary w-100" :disabled="loading">
            {{ loading ? 'Guardando...' : 'Restablecer contraseña' }}
          </button>
        </form>

        <p class="text-center mt-4 mb-0">
          <RouterLink :to="success ? '/login' : '/forgot-password'">
            {{ success ? 'Iniciar sesión' : 'Solicitar otro enlace' }}
          </RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { newPasswordError } from '@/utils/password'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const resetToken = ref(typeof route.query.token === 'string' ? route.query.token : '')
const form = reactive({ newPassword: '', confirmPassword: '' })
const errors = reactive({ newPassword: '', confirmPassword: '' })
const apiError = ref('')
const loading = ref(false)
const success = ref(false)

onMounted(() => {
  // El secreto ya está en memoria; eliminarlo de la URL y del historial visible.
  if (route.query.token) router.replace({ name: 'ResetPassword' })
})

async function handleReset() {
  errors.newPassword = newPasswordError(form.newPassword)
  errors.confirmPassword = form.newPassword === form.confirmPassword
    ? '' : 'Las contraseñas no coinciden'
  apiError.value = ''
  if (errors.newPassword || errors.confirmPassword || !resetToken.value) return

  loading.value = true
  try {
    await authStore.confirmPasswordReset(resetToken.value, form.newPassword)
    resetToken.value = ''
    success.value = true
  } catch (error) {
    apiError.value = error.response?.status === 400
      ? 'El enlace no es válido, venció o la contraseña coincide con la actual.'
      : 'No se pudo restablecer la contraseña. Intenta más tarde.'
  } finally {
    loading.value = false
  }
}
</script>
