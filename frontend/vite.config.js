import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'
import process from 'node:process'
import { fileURLToPath, URL } from 'node:url'

// `npm run dev:mobile`: HTTPS con certificado local para probar la cámara desde
// un celular en la misma red (la cámara exige HTTPS fuera de localhost). La API
// va por el proxy /api, así el celular no hace peticiones HTTP mixtas.
const mobileDev = process.env.VITE_DEV_HTTPS === '1'

export default defineConfig({
  plugins: [vue(), ...(mobileDev ? [basicSsl({ name: 'biblioteca-dev' })] : [])],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    exclude: ['**/tests/e2e/**', '**/node_modules/**'],
  },
})
