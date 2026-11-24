import { test, expect } from '@playwright/test'
import { URL } from 'node:url'

// La API devuelve los libros del más reciente al más antiguo.
const books = [
  { id: 1, title: 'Rayuela', authors: ['Julio Cortázar'], genre: 'Novela', year: 1963, reading_status: 'Leído', rating: 4, finished_at: '2026-02-01' },
  { id: 2, title: 'Aura', authors: ['Carlos Fuentes'], genre: 'Novela', year: 1962, reading_status: 'Leyendo', rating: null, started_at: '2026-03-01' },
  { id: 3, title: 'Ficciones', authors: ['Jorge Luis Borges'], genre: 'Cuentos', year: 1944, reading_status: 'Quiero leer', rating: null },
  { id: 4, title: 'El túnel', authors: ['Ernesto Sabato'], genre: null, year: null, reading_status: 'Leído', rating: 5, finished_at: '2025-11-20' },
]

test('tabla: ordenar por columnas con clic en los encabezados', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/books/genres')) return route.fulfill({ json: ['Cuentos', 'Novela'] })
    if (path.endsWith('/books/')) return route.fulfill({ json: books })
    return route.abort()
  })

  await page.goto('/library')
  await page.getByRole('button', { name: /Tabla/ }).click()
  const titles = page.locator('tbody tr td:nth-child(2)')
  await expect(titles).toHaveText(['Rayuela', 'Aura', 'Ficciones', 'El túnel'])

  const titleHeader = page.getByRole('button', { name: /Título/ })
  await titleHeader.click()
  await expect(titles).toHaveText(['Aura', 'El túnel', 'Ficciones', 'Rayuela'])
  await expect(page.locator('th', { has: titleHeader })).toHaveAttribute('aria-sort', 'ascending')
  await titleHeader.click()
  await expect(titles).toHaveText(['Rayuela', 'Ficciones', 'El túnel', 'Aura'])
  await expect(page.locator('th', { has: titleHeader })).toHaveAttribute('aria-sort', 'descending')

  // Año: el libro sin año queda al final en ambas direcciones.
  const yearHeader = page.getByRole('button', { name: /Año/ })
  await yearHeader.click()
  await expect(titles).toHaveText(['Ficciones', 'Aura', 'Rayuela', 'El túnel'])
  await yearHeader.click()
  await expect(titles).toHaveText(['Rayuela', 'Aura', 'Ficciones', 'El túnel'])

  // Estado en orden de lectura.
  await page.getByRole('button', { name: /Estado/ }).click()
  await expect(titles).toHaveText(['Ficciones', 'Aura', 'El túnel', 'Rayuela'])

  // El orden se mantiene al pasar por la cuadrícula y volver.
  await page.getByRole('button', { name: /Cuadrícula/ }).click()
  await page.getByRole('button', { name: /Tabla/ }).click()
  await expect(titles).toHaveText(['Ficciones', 'Aura', 'El túnel', 'Rayuela'])
})
