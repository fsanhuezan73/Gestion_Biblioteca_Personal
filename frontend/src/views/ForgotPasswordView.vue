<template>
  <div class="auth-page d-flex align-items-center justify-content-center p-3">
    <div class="card auth-card shadow-lg w-100">
      <div class="card-body p-4 p-md-5">
        <div class="auth-logo">📚</div>
        <p class="page-kicker text-center mb-1">Biblioteca Personal</p>
        <h1 class="card-title display-font text-center mb-2 fw-bold fs-2">Recupera tu contraseña</h1>
        <p class="text-center text-muted mb-4">Te enviaremos un enlace válido durante 15 minutos.</p>

        <div v-if="success" class="alert alert-success" role="status">
          Si el correo está registrado, recibirás un enlace de recuperación.
        </div>

        <form v-else @submit.prevent="handleRequest" novalidate>
          <div class="mb-3">
            <label for="email" class="form-label">Correo electrónico</label>
            <input
              id="email"
              v-model="email"
              type="email"
              class="form-control"
              :class="{ 'is-invalid': error }"
              autocomplete="email"
              placeholder="tu@correo.com"
              required
            />
            <div v-if="error" class="invalid-feedback">{{ error }}</div>
          </div>
          <div v-if="apiError" class="alert alert-danger" role="alert">{{ apiError }}</div>
          <button type="submit" class="btn btn-primary w-100" :disabled="loading">
            {{ loading ? 'Enviando...' : 'Enviar enlace' }}
          </button>
        </form>

        <p class="text-center mt-4 mb-0"><RouterLink to="/login">Volver a iniciar sesión</RouterLink></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const email = ref('')
const error = ref('')
const apiError = ref('')
const loading = ref(false)
const success = ref(false)

async function handleRequest() {
  error.value = ''
  apiError.value = ''
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    error.value = 'Ingresa un correo electrónico válido'
    return
  }

  loading.value = true
  try {
    await authStore.requestPasswordReset(email.value)
    success.value = true
  } catch {
    apiError.value = 'El servicio de recuperación no está disponible. Intenta más tarde.'
  } finally {
    loading.value = false
  }
}
</script>
