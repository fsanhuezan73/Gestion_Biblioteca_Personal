import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true, // Escucha en 0.0.0.0 — necesario para Codespaces y Docker
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // IPv4 explícito — evita que Node.js use ::1 (IPv6)
        changeOrigin: true,
      },
    },
  },
})
