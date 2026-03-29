import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/library',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresGuest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresGuest: true },
  },
  {
    path: '/library',
    name: 'Library',
    component: () => import('@/views/LibraryView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/books/add',
    name: 'AddBook',
    component: () => import('@/views/AddBookView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/books/:id',
    name: 'BookDetail',
    component: () => import('@/views/BookDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/books/:id/edit',
    name: 'EditBook',
    component: () => import('@/views/EditBookView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/library',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation Guard global
router.beforeEach((to) => {
  const authStore = useAuthStore()

  // Ruta protegida y usuario no autenticado → /login
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'Login' }
  }

  // Ruta de guest (login/register) y usuario ya autenticado → /library
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    return { name: 'Library' }
  }
})

export default router
