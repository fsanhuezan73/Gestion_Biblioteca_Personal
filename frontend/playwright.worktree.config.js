import { defineConfig } from '@playwright/test'
import base from './playwright.config.js'

// Puerto independiente del checkout principal. APIs simuladas por cada test.
export default defineConfig(base, {
  use: { baseURL: 'http://127.0.0.1:5175' },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5175 --strictPort',
    url: 'http://127.0.0.1:5175',
    reuseExistingServer: false,
  },
})
