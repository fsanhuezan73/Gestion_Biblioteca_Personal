import { test, expect } from '@playwright/test'
import { URL } from 'node:url'

test('registrar formatos, combinarlos en el filtro y consultar su desglose', async ({ page }) => {
  const currentYear = new Date().getFullYear()
  const books = [
    { id: 1, title: 'Solo Kindle', authors: ['Autora'], formats: ['kindle'] },
    { id: 2, title: 'Sin clasificar', authors: ['Autor'], formats: [] },
  ]

  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const { pathname, searchParams } = new URL(request.url())
    if (pathname.endsWith('/ai/recommendations')) return route.fulfill({ status: 503 })
    if (pathname.endsWith('/books/genres')) return route.fulfill({ json: [] })
    if (pathname.endsWith('/books/')) {
      if (request.method() === 'POST') {
        const book = { ...request.postDataJSON(), id: 3 }
        books.push(book)
        return route.fulfill({ json: book, status: 201 })
      }
      const formats = searchParams.getAll('format')
      const withoutFormat = searchParams.get('without_format') === 'true'
      return route.fulfill({
        json: books.filter((book) => formats.every((code) => book.formats.includes(code))
          && (!withoutFormat || book.formats.length === 0)),
      })
    }
    if (pathname.endsWith('/books/3')) {
      const book = books.find(({ id }) => id === 3)
      if (request.method() === 'PUT') Object.assign(book, request.postDataJSON())
      return route.fulfill({ json: book })
    }
    if (pathname.endsWith('/stats/')) {
      const count = (code) => books.filter(({ formats }) => formats.includes(code)).length
      return route.fulfill({ json: {
        year_stats: {
          year: Number(searchParams.get('year') || currentYear), books_read: 0, pages_read: 0,
          avg_days_to_finish: null, by_month: Array.from({ length: 12 }, () => ({ books: 0 })),
          books_read_list: [], top_authors: [], goal: null,
        },
        library: {
          total_books: books.length, read_without_date: 0, reading: 0, want_to_read: books.length,
          avg_rating: null, rated_books: 0, ratings: [], genres: [], currently_reading: [],
          formats: {
            physical: count('physical'), kindle: count('kindle'), apple_books: count('apple_books'),
            without_format: books.filter(({ formats }) => formats.length === 0).length,
          },
        },
        available_years: [currentYear, currentYear - 1],
      } })
    }
    return route.abort()
  })

  await page.goto('/books/add')
  await page.getByLabel('Título').fill('Dune')
  await page.getByPlaceholder('Ej: J.R.R. Tolkien').fill('Frank Herbert')
  await page.getByRole('checkbox', { name: 'Físico' }).check()
  await page.getByRole('checkbox', { name: 'Kindle' }).check()
  await page.getByRole('button', { name: 'Guardar libro' }).click()
  const dune = page.getByRole('link', { name: /Dune/ })
  await expect(dune.getByTestId('book-formats').locator('span')).toHaveText(['Físico', 'Kindle'])
  await expect(page.getByRole('link', { name: /Sin clasificar/ }).getByTestId('book-formats')).toHaveCount(0)

  await page.getByRole('button', { name: /Filtros Avanzados/ }).click()
  await page.getByRole('checkbox', { name: 'Físico' }).check()
  await page.getByRole('checkbox', { name: 'Kindle' }).check()
  await expect(dune).toBeVisible()
  await expect(page.getByText('Solo Kindle')).toHaveCount(0)
  await page.getByRole('button', { name: /Tabla/ }).click()
  await expect(page.getByRole('table').getByText('Dune')).toBeVisible()
  await expect(page.getByText('Solo Kindle')).toHaveCount(0)
  await page.getByRole('checkbox', { name: 'Sin formato registrado' }).check()
  await expect(page.getByRole('checkbox', { name: 'Físico' })).not.toBeChecked()
  await expect(page.getByRole('checkbox', { name: 'Kindle' })).not.toBeChecked()
  await expect(page.getByRole('table').getByText('Sin clasificar')).toBeVisible()
  await expect(page.getByRole('table').getByText('Dune')).toHaveCount(0)
  await page.getByRole('button', { name: 'Limpiar', exact: true }).click()
  await expect(page.getByRole('checkbox', { name: 'Sin formato registrado' })).not.toBeChecked()
  await expect(page.getByRole('table').getByText('Solo Kindle')).toBeVisible()
  await page.getByRole('button', { name: /Cuadrícula/ }).click()
  await dune.click()
  await expect(page.getByText('Formato: Físico, Kindle')).toBeVisible()
  await page.getByRole('link', { name: /Editar/ }).click()
  await expect(page.getByRole('checkbox', { name: 'Físico' })).toBeChecked()
  await expect(page.getByRole('checkbox', { name: 'Kindle' })).toBeChecked()
  await page.getByRole('checkbox', { name: 'Apple Books' }).check()
  await page.getByRole('button', { name: 'Actualizar libro' }).click()
  await page.getByRole('link', { name: /Volver/ }).click()

  await page.setViewportSize({ width: 320, height: 700 })
  const labels = dune.getByTestId('book-formats')
  await expect(labels.locator('span')).toHaveText(['Físico', 'Kindle', 'Apple Books'])
  for (const label of await labels.locator('span').all()) {
    const box = await label.boundingBox()
    const container = await labels.boundingBox()
    expect(box.x + box.width).toBeLessThanOrEqual(container.x + container.width)
  }

  await page.getByRole('link', { name: /Estadísticas/ }).click()
  const distribution = page.locator('table').filter({ hasText: 'Tu biblioteca por formato' })
  await expect(distribution.locator('tbody td:nth-child(2)')).toHaveText(['1', '2', '1', '1'])
  await page.getByLabel('Año', { exact: true }).selectOption(String(currentYear - 1))
  await expect(page.getByText(`Libros leídos en ${currentYear - 1}`, { exact: true })).toBeVisible()
  await expect(distribution.locator('tbody td:nth-child(2)')).toHaveText(['1', '2', '1', '1'])
})
