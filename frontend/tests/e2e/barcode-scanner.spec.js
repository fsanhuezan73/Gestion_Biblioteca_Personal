import { test, expect } from '@playwright/test'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { URL } from 'node:url'
import { writeBarcodeY4m } from './support/fake-barcode-video.js'

// Cámara falsa de Chrome que muestra el código de barras de «1984» (Signet).
const ISBN = '9780451524935'
const video = writeBarcodeY4m(join(tmpdir(), `isbn-${ISBN}.y4m`), ISBN)

test.use({
  permissions: ['camera'],
  launchOptions: {
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-video-capture=${video}`,
    ],
  },
})

// «nativo»: BarcodeDetector de Chrome. «WebAssembly»: el lector ZXing que usan
// Safari/iPhone y Firefox, forzado quitando el detector nativo.
for (const mode of ['nativo', 'WebAssembly']) test(`escanear (${mode}): completa el libro, avisa duplicado y lo guarda`, async ({ page }) => {
  let saved = null
  let wasmRequested = false
  page.on('request', (r) => { if (r.url().includes('zxing_reader') && r.url().endsWith('.wasm')) wasmRequested = true })
  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  if (mode === 'WebAssembly') await page.addInitScript(() => { delete globalThis.BarcodeDetector })
  await page.route('https://openlibrary.org/**', (route) => route.fulfill({
    json: { docs: [{ title: '1984', author_name: ['George Orwell'], publisher: ['Signet Classic'], first_publish_year: 1949, number_of_pages_median: 328 }] },
  }))
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname.endsWith('/books/check-isbn')) {
      expect(url.searchParams.get('isbn')).toBe(ISBN)
      return route.fulfill({ json: { isbn: ISBN, exists: true, books: [{ id: 7, title: '1984 (edición antigua)' }] } })
    }
    if (url.pathname.endsWith('/books/') && request.method() === 'POST') {
      saved = request.postDataJSON()
      return route.fulfill({ status: 201, json: { id: 99, ...saved } })
    }
    if (url.pathname.endsWith('/books/')) return route.fulfill({ json: [] })
    if (url.pathname.endsWith('/books/genres')) return route.fulfill({ json: [] })
    if (url.pathname.endsWith('/stats/')) return route.abort()
    return route.abort()
  })

  await page.goto('/library')
  await page.getByRole('link', { name: '📷 Escanear' }).click()
  await expect(page.getByRole('dialog', { name: 'Escanear código de barras' })).toBeVisible()

  // El escáner se cierra solo al detectar el código.
  await expect(page.getByRole('dialog')).toBeHidden({ timeout: 15000 })
  await expect(page.getByLabel('ISBN')).toHaveValue(ISBN)
  await expect(page.getByLabel(/^Título/)).toHaveValue('1984')
  await expect(page.getByLabel('N.º de páginas')).toHaveValue('328')
  await expect(page.getByTestId('duplicate-alert')).toContainText('1984 (edición antigua)')

  await page.getByRole('button', { name: 'Guardar libro' }).click()
  await expect(page).toHaveURL(/\/library/)
  expect(saved).toMatchObject({ title: '1984', isbn: ISBN, authors: ['George Orwell'], page_count: 328 })
  if (mode === 'WebAssembly') expect(wasmRequested).toBe(true)
})
