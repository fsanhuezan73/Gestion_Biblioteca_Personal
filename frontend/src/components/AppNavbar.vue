<template>
  <div class="container pt-3 pt-md-4">
    <nav ref="navRef" class="app-navbar navbar flex-nowrap gap-2 bg-white px-3 py-2 position-relative">
      <div class="d-flex align-items-center gap-2 min-w-0">
        <button
          type="button"
          class="btn btn-outline-secondary menu-toggle flex-shrink-0"
          :aria-expanded="open ? 'true' : 'false'"
          aria-controls="app-menu"
          aria-label="Abrir menú"
          data-test="menu-toggle"
          @click="open = !open"
        >
          ☰
        </button>
        <RouterLink to="/library" class="navbar-brand d-flex align-items-center gap-2 mb-0 text-decoration-none min-w-0">
          <span class="brand-mark brand-mark-nav">📚</span>
          <span class="fw-bold fs-5 text-dark text-truncate brand-text">Biblioteca<span class="brand-suffix"> Personal</span></span>
        </RouterLink>
      </div>

      <button class="btn btn-outline-secondary btn-sm ms-auto text-nowrap flex-shrink-0" data-test="logout" @click="handleLogout">
        Cerrar sesión
      </button>

      <ul
        v-if="open"
        id="app-menu"
        class="app-menu list-unstyled bg-white mb-0 p-2"
        aria-label="Menú principal"
        data-test="app-menu"
      >
        <li v-for="item in items" :key="item.key">
          <RouterLink
            :to="item.to"
            class="app-menu-item d-flex align-items-center gap-2 px-3 py-2 text-decoration-none"
            :class="{ active: item.key === activeKey }"
            :aria-current="item.key === activeKey ? 'page' : undefined"
            :data-test="`menu-${item.key}`"
            @click="open = false"
          >
            <span class="app-menu-icon" aria-hidden="true">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </RouterLink>
        </li>
      </ul>
    </nav>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const open = ref(false)
const navRef = ref(null)

const items = [
  { key: 'library', label: 'Mi colección', icon: '📚', to: { name: 'Library' } },
  { key: 'for-you', label: 'Para ti', icon: '✨', to: { name: 'ForYou' } },
  { key: 'stats', label: 'Estadísticas', icon: '📊', to: { name: 'Stats' } },
  { key: 'scan', label: 'Escanear libro', icon: '📷', to: { name: 'AddBook', query: { scan: '1' } } },
  { key: 'add', label: 'Añadir libro', icon: '➕', to: { name: 'AddBook' } },
  { key: 'account', label: 'Mi cuenta', icon: '👤', to: { name: 'Account' } },
]

const activeKey = computed(() => {
  switch (route.name) {
    case 'Library': return 'library'
    case 'ForYou': return 'for-you'
    case 'Stats': return 'stats'
    case 'Account': return 'account'
    case 'AddBook': return route.query.scan === '1' ? 'scan' : 'add'
    default: return null
  }
})

// Cualquier navegación (incluidos atrás/adelante) cierra el menú.
watch(() => route.fullPath, () => { open.value = false })

function onPointerDown(event) {
  if (open.value && navRef.value && !navRef.value.contains(event.target)) open.value = false
}

function onKeydown(event) {
  if (event.key === 'Escape') open.value = false
}

onMounted(() => {
  globalThis.document.addEventListener('pointerdown', onPointerDown)
  globalThis.document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  globalThis.document.removeEventListener('pointerdown', onPointerDown)
  globalThis.document.removeEventListener('keydown', onKeydown)
})

function handleLogout() {
  open.value = false
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.min-w-0 {
  min-width: 0;
}
.menu-toggle {
  width: 2.5rem;
  height: 2.5rem;
  padding: 0;
  font-size: 1.2rem;
  line-height: 1;
}
.app-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  z-index: 1030;
  min-width: 15rem;
  border: 1px solid var(--border);
  border-radius: 0.85rem;
  box-shadow: 0 12px 32px rgba(32, 48, 83, 0.14);
}
.app-menu-item {
  border-radius: 0.6rem;
  color: #2b3347;
  font-weight: 500;
}
.app-menu-item:hover,
.app-menu-item:focus-visible {
  background: #f0f3ff;
  color: var(--brand-dark);
}
.app-menu-item.active {
  background: #e9edff;
  color: var(--brand-dark);
  font-weight: 700;
}
.app-menu-icon {
  width: 1.5rem;
  text-align: center;
}
/* En pantallas angostas, el logo cede espacio para que todo quepa en una línea. */
@media (max-width: 575.98px) {
  .brand-mark-nav {
    display: none;
  }
  .brand-text {
    font-size: 1rem !important;
  }
}
@media (max-width: 419.98px) {
  .brand-suffix {
    display: none;
  }
}
</style>
