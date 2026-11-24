import { test, expect } from '@playwright/test'
import { URL } from 'node:url'

const books = Array.from({ length: 40 }, (_, i) => ({
  id: i + 1, title: `Libro ${i + 1}`, authors: ['Autora Prueba'], genre: 'Novela', year: 2000 + (i % 20),
  isbn: null, reading_status: 'Quiero leer', rating: null, cover_url: null,
}))

async function mockApi(page) {
  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/books/genres')) return route.fulfill({ json: ['Novela'] })
    if (path.endsWith('/books/')) return route.fulfill({ json: books })
    if (path.endsWith('/ai/recommendations')) return route.fulfill({ status: 503, json: {} })
    return route.abort()
  })
}

test('menú: opciones, navegación y «Cerrar sesión» fuera del menú', async ({ page }) => {
  await mockApi(page)
  await page.goto('/library')

  // La colección se muestra sola, sin la sección «Para ti».
  await expect(page.getByText('Libro 1', { exact: true })).toBeVisible()
  await expect(page.getByTestId('recommendations')).toHaveCount(0)

  const toggle = page.getByRole('button', { name: 'Abrir menú' })
  const menu = page.getByTestId('app-menu')
  await expect(menu).toHaveCount(0)
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-expanded', 'true')
  await expect(menu.getByRole('link')).toHaveText([
    /Mi colección/, /Para ti/, /Estadísticas/, /Escanear libro/, /Añadir libro/, /Mi cuenta/,
  ])
  await expect(menu.getByRole('link', { name: /Mi colección/ })).toHaveAttribute('aria-current', 'page')
  await expect(menu.getByRole('button', { name: 'Cerrar sesión' })).toHaveCount(0)

  // El menú queda en la esquina superior izquierda de la barra; «Cerrar sesión», a la derecha.
  const box = await toggle.boundingBox()
  const nav = await page.locator('nav.app-navbar').boundingBox()
  const logout = await page.getByRole('button', { name: 'Cerrar sesión' }).boundingBox()
  expect(box.x - nav.x).toBeLessThan(24)
  expect(box.y).toBeLessThan(80)
  expect(logout.x).toBeGreaterThan(box.x + 200)

  await page.keyboard.press('Escape')
  await expect(menu).toHaveCount(0)

  await toggle.click()
  await menu.getByRole('link', { name: /Para ti/ }).click()
  await expect(page).toHaveURL(/\/for-you$/)
  await expect(menu).toHaveCount(0)
  await expect(page.getByTestId('recommendations-unavailable')).toBeVisible()

  // «Escanear libro» abre el escáner cada vez que se elige, aunque ya estés en «Añadir libro».
  const scanner = page.getByRole('dialog', { name: 'Escanear código de barras' })
  for (let i = 0; i < 2; i++) {
    await toggle.click()
    await page.getByTestId('menu-scan').click()
    await expect(scanner).toBeVisible()
    await expect(page).toHaveURL(/\/books\/add$/)
    await scanner.getByRole('button', { name: 'Cerrar' }).click()
    await expect(scanner).toBeHidden()
  }

  // Las demás opciones navegan a su página.
  await toggle.click()
  await page.getByTestId('menu-add').click()
  await expect(page).toHaveURL(/\/books\/add$/)
  await toggle.click()
  await page.getByTestId('menu-account').click()
  await expect(page).toHaveURL(/\/account$/)

  await page.getByRole('button', { name: 'Cerrar sesión' }).click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(toggle).toHaveCount(0)
})

test('tabla: el encabezado queda visible al hacer scroll', async ({ page }) => {
  await mockApi(page)
  await page.goto('/library')
  await page.getByRole('button', { name: /Tabla/ }).click()

  const scroller = page.getByTestId('book-table-scroll')
  const header = scroller.locator('thead th', { hasText: 'Título' })
  await expect(header).toBeVisible()
  await scroller.scrollIntoViewIfNeeded()
  await scroller.evaluate((el) => { el.scrollTop = el.scrollHeight })
  await expect(scroller.getByText('Libro 40', { exact: true })).toBeInViewport()
  await expect(scroller.getByText('Libro 1', { exact: true })).not.toBeInViewport()

  const headerBox = await header.boundingBox()
  const scrollerBox = await scroller.boundingBox()
  expect(Math.abs(headerBox.y - scrollerBox.y)).toBeLessThan(2)
  await expect(header).toBeInViewport()
})
