<template>
  <div v-if="showNavbar" class="app-shell" data-test="app-layout">
    <AppNavbar />
    <RouterView />
  </div>
  <RouterView v-else />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppNavbar from '@/components/AppNavbar.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

// El menú se muestra en todas las páginas que requieren sesión iniciada.
const showNavbar = computed(() => !!route.meta.requiresAuth && authStore.isAuthenticated)
</script>
