import { test, expect } from '@playwright/test'
import { URL } from 'node:url'
import { Buffer } from 'node:buffer'

// PNG 1x1 rojo: el navegador real lo decodifica, redimensiona y convierte a JPEG.
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==',
  'base64',
)

test('editar un libro sin portada: subir, reemplazar por URL y quitar', async ({ page }, testInfo) => {
  let book = {
    id: 101, title: 'Libro sin portada', authors: ['Autora'], reading_status: 'Quiero leer',
    cover_url: null, year: 2020,
  }
  const uploads = []
  const updates = []
  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path.endsWith('/covers') && request.method() === 'POST') {
      uploads.push({ type: request.headers()['content-type'], body: request.postDataBuffer() })
      return route.fulfill({ status: 201, json: { id: 'a'.repeat(32), content_type: 'image/jpeg', byte_size: 10 } })
    }
    if (path.includes('/covers/')) {
      return route.fulfill({ body: PNG, contentType: 'image/png' })
    }
    if (path.endsWith('/books/101')) {
      if (request.method() === 'PUT') {
        updates.push(request.postDataJSON())
        book = { ...book, ...request.postDataJSON() }
      }
      return route.fulfill({ json: book })
    }
    if (path.endsWith('/books/genres')) return route.fulfill({ json: [] })
    if (path.endsWith('/books/')) return route.fulfill({ json: [book] })
    return route.abort()
  })
  await page.route('https://img.example/**', (route) => route.fulfill({ body: PNG, contentType: 'image/png' }))

  await page.goto('/books/101/edit')
  const section = page.getByTestId('cover-section')
  await expect(section.getByText('Sin portada')).toBeVisible()

  // 1) Subir un archivo: vista previa inmediata, se sube recién al guardar.
  await page.getByTestId('cover-file').setInputFiles({ name: 'portada.png', mimeType: 'image/png', buffer: PNG })
  await expect(page.getByTestId('cover-preview')).toHaveAttribute('src', /^blob:/)
  await expect(section.getByText('La imagen se subirá al guardar el libro.')).toBeVisible()
  expect(uploads).toHaveLength(0)
  await page.screenshot({ path: testInfo.outputPath('portada-editar.png'), fullPage: true })

  await page.getByRole('button', { name: 'Actualizar libro' }).click()
  await expect(page).toHaveURL(/books\/101$/)
  expect(uploads).toHaveLength(1)
  expect(uploads[0].type).toBe('image/jpeg')
  expect([...uploads[0].body.subarray(0, 3)]).toEqual([0xff, 0xd8, 0xff]) // JPEG real
  expect(updates[0].cover_url).toMatch(new RegExp(`/api/v1/covers/${'a'.repeat(32)}$`))
  await expect(page.getByAltText(/portada/i).first()).toBeVisible()

  // 2) Reemplazar por una URL de internet.
  await page.goto('/books/101/edit')
  await expect(page.getByTestId('cover-upload')).toHaveText(/Reemplazar imagen/)
  await page.getByTestId('cover-url-toggle').click()
  await page.getByTestId('cover-url-input').fill('https://img.example/portada.png')
  await page.getByTestId('cover-url-apply').click()
  await expect(page.getByTestId('cover-preview')).toHaveAttribute('src', 'https://img.example/portada.png')
  await page.getByRole('button', { name: 'Actualizar libro' }).click()
  await expect(page).toHaveURL(/books\/101$/)
  expect(updates[1].cover_url).toBe('https://img.example/portada.png')
  expect(uploads).toHaveLength(1)

  // 3) Quitar la portada.
  await page.goto('/books/101/edit')
  await page.getByTestId('cover-remove').click()
  await expect(section.getByText('Sin portada')).toBeVisible()
  await page.getByRole('button', { name: 'Actualizar libro' }).click()
  await expect(page).toHaveURL(/books\/101$/)
  expect(updates[2].cover_url).toBeNull()
})

test('rechaza un archivo que no es imagen', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/books/genres')) return route.fulfill({ json: [] })
    return route.abort()
  })
  await page.goto('/books/add')
  await page.getByTestId('cover-file').setInputFiles({ name: 'doc.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4') })
  await expect(page.getByTestId('cover-error')).toContainText('no es una imagen')
})
