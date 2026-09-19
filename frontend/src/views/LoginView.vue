<template>
  <div class="auth-page d-flex align-items-center justify-content-center p-3">
    <div class="card auth-card shadow-lg w-100">
      <div class="card-body p-4 p-md-5">
        <div class="auth-logo">📚</div>
        <p class="page-kicker text-center mb-1">Biblioteca Personal</p>
        <h2 class="card-title display-font text-center mb-1 fw-bold">Bienvenido de vuelta</h2>
        <p class="text-center text-muted mb-4">Inicia sesión en tu cuenta</p>

        <div v-if="route.query.registered" class="alert alert-success" role="alert">
          ¡Cuenta creada exitosamente! Ya puedes iniciar sesión.
        </div>
        <div v-if="route.query.passwordChanged" class="alert alert-success" role="alert">
          Contraseña actualizada. Inicia sesión nuevamente.
        </div>

        <form @submit.prevent="handleLogin" novalidate>
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

          <div class="mb-4">
            <label for="password" class="form-label">Contraseña</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              class="form-control"
              :class="{ 'is-invalid': errors.password }"
              placeholder="Tu contraseña"
              autocomplete="current-password"
            />
            <div v-if="errors.password" class="invalid-feedback">{{ errors.password }}</div>
          </div>

          <p class="text-end mb-3">
            <RouterLink to="/forgot-password">¿Olvidaste tu contraseña?</RouterLink>
          </p>

          <div v-if="apiError" class="alert alert-danger py-2" role="alert">
            {{ apiError }}
          </div>

          <button type="submit" class="btn btn-primary w-100" :disabled="loading">
            <span v-if="loading" class="spinner-border spinner-border-sm me-2" />
            Ingresar
          </button>
        </form>

        <hr />
        <p class="text-center mb-0">
          ¿No tienes cuenta?
          <RouterLink to="/register">Regístrate</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '' })
const loading = ref(false)
const apiError = ref('')

function validate() {
  errors.email = ''
  errors.password = ''
  let valid = true
  if (!form.email) { errors.email = 'Ingresa tu correo'; valid = false }
  if (!form.password) { errors.password = 'Ingresa tu contraseña'; valid = false }
  return valid
}

async function handleLogin() {
  apiError.value = ''
  if (!validate()) return

  loading.value = true
  try {
    await authStore.login(form.email, form.password)
    router.push('/library')
  } catch (err) {
    apiError.value =
      err.response?.data?.detail || 'Correo o contraseña incorrectos'
  } finally {
    loading.value = false
  }
}
</script>
