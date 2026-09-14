<template>
  <div class="auth-page d-flex align-items-center justify-content-center p-3">
    <div class="card auth-card shadow-lg w-100">
      <div class="card-body p-4 p-md-5">
        <div class="auth-logo">📚</div>
        <p class="page-kicker text-center mb-1">Biblioteca Personal</p>
        <h2 class="card-title display-font text-center mb-1 fw-bold">Crea tu biblioteca</h2>
        <p class="text-center text-muted mb-4">Crea tu cuenta</p>

        <div v-if="successMessage" class="alert alert-success" role="alert">
          {{ successMessage }}
        </div>

        <form @submit.prevent="handleRegister" novalidate>
          <!-- Email -->
          <div class="mb-3">
            <label for="email" class="form-label">Correo electrónico</label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              class="form-control"
              :class="{ 'is-invalid': errors.email }"
              placeholder="tu@correo.com"
              autocomplete="email"
            />
            <div v-if="errors.email" class="invalid-feedback">{{ errors.email }}</div>
          </div>

          <!-- Contraseña -->
          <div class="mb-3">
            <label for="password" class="form-label">Contraseña</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              class="form-control"
              :class="{ 'is-invalid': errors.password }"
              placeholder="Mínimo 8 caracteres"
              autocomplete="new-password"
            />
            <div v-if="errors.password" class="invalid-feedback">{{ errors.password }}</div>
          </div>

          <!-- Confirmar contraseña -->
          <div class="mb-4">
            <label for="confirmPassword" class="form-label">Confirmar contraseña</label>
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              type="password"
              class="form-control"
              :class="{ 'is-invalid': errors.confirmPassword }"
              placeholder="Repite tu contraseña"
              autocomplete="new-password"
            />
            <div v-if="errors.confirmPassword" class="invalid-feedback">
              {{ errors.confirmPassword }}
            </div>
          </div>

          <div v-if="apiError" class="alert alert-danger py-2" role="alert">
            {{ apiError }}
          </div>

          <button type="submit" class="btn btn-primary w-100" :disabled="loading">
            <span v-if="loading" class="spinner-border spinner-border-sm me-2" />
            Registrarse
          </button>
        </form>

        <hr />
        <p class="text-center mb-0">
          ¿Ya tienes cuenta?
          <RouterLink to="/login">Inicia sesión</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ email: '', password: '', confirmPassword: '' })
const errors = reactive({ email: '', password: '', confirmPassword: '' })
const loading = ref(false)
const apiError = ref('')
const successMessage = ref('')

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate() {
  errors.email = ''
  errors.password = ''
  errors.confirmPassword = ''
  let valid = true

  if (!form.email || !EMAIL_REGEX.test(form.email)) {
    errors.email = 'Ingresa un correo electrónico válido'
    valid = false
  }
  if (!form.password || form.password.length < 8) {
    errors.password = 'La contraseña debe tener al menos 8 caracteres'
    valid = false
  }
  if (form.password !== form.confirmPassword) {
    errors.confirmPassword = 'Las contraseñas no coinciden'
    valid = false
  }
  return valid
}

async function handleRegister() {
  apiError.value = ''
  if (!validate()) return

  loading.value = true
  try {
    await authStore.register(form.email, form.password)
    successMessage.value = '¡Cuenta creada exitosamente! Redirigiendo...'
    setTimeout(() => router.push('/login'), 1500)
  } catch (err) {
    apiError.value =
      err.response?.data?.detail || 'Ocurrió un error. Intenta de nuevo.'
  } finally {
    loading.value = false
  }
}
</script>
