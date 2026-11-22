import { test, expect } from '@playwright/test'
import { URL } from 'node:url'

// API simulada con estado: una meta y un libro que pasa a «Leído».
test('definir meta, terminar un libro y ver el avance', async ({ page }) => {
  const year = new Date().getFullYear()
  let goal = null
  let book = {
    id: 101, title: 'Dune', authors: ['Frank Herbert'], reading_status: 'Leyendo',
    started_at: null, finished_at: null, page_count: 600, rating: null, personal_notes: null,
  }

  function stats() {
    const read = book.reading_status === 'Leído' && book.finished_at ? 1 : 0
    return {
      year_stats: {
        year, books_read: read, pages_read: read ? 600 : 0, avg_days_to_finish: null,
        by_month: Array.from({ length: 12 }, (_, i) => ({
          month: i + 1, books: read && i === new Date().getMonth() ? 1 : 0, pages: 0,
        })),
        top_authors: read ? [{ label: 'Frank Herbert', count: 1 }] : [],
        goal: goal && {
          target_books: goal, books_read: read, percent: Math.round((read * 100) / goal),
          expected_to_date: 0, difference: 0, remaining: goal - read, status: 'on_track',
        },
      },
      library: {
        total_books: 1, want_to_read: 0, reading: read ? 0 : 1, read, read_without_date: 0,
        avg_rating: null, rated_books: 0, ratings: [], genres: [{ label: 'Ciencia Ficción', count: 1 }],
        currently_reading: read ? [] : [{ id: 101, title: 'Dune', cover_url: null, started_at: null, days_reading: null }],
      },
      available_years: [year],
    }
  }

  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path.endsWith('/stats/')) return route.fulfill({ json: stats() })
    if (path.endsWith(`/goals/${year}`) && request.method() === 'PUT') {
      goal = request.postDataJSON().target_books
      return route.fulfill({ json: { year, target_books: goal } })
    }
    if (path.endsWith('/books/101/status')) {
      book = { ...book, reading_status: request.postDataJSON().reading_status, finished_at: `${year}-01-15` }
      return route.fulfill({ json: book })
    }
    if (path.endsWith('/books/101')) return route.fulfill({ json: book })
    if (path.endsWith('/books/genres')) return route.fulfill({ json: [] })
    if (path.endsWith('/books/')) return route.fulfill({ json: [book] })
    return route.abort()
  })

  await page.goto('/library')
  await expect(page.getByText(`🎯 Define tu meta ${year}`)).toBeVisible()
  await page.getByRole('link', { name: '📊 Estadísticas' }).click()

  await expect(page.getByText('Sin meta definida')).toBeVisible()
  await page.getByRole('button', { name: 'Definir meta' }).click()
  await page.getByLabel(`¿Cuántos libros quieres leer en ${year}?`).fill('12')
  await page.getByRole('button', { name: 'Guardar' }).click()
  await expect(page.getByText('0 de 12 libros')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Dune' })).toBeVisible()

  await page.getByRole('link', { name: 'Dune' }).click()
  await page.getByRole('combobox').first().selectOption('Leído')
  await expect(page.getByText('Término de lectura:')).toBeVisible()

  await page.goto('/stats')
  await expect(page.getByText('1 de 12 libros')).toBeVisible()
  await expect(page.getByText('Frank Herbert')).toBeVisible()
  await expect(page.locator('canvas').first()).toBeVisible()
})
